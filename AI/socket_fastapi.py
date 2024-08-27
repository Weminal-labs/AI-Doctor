import sys
sys.path.append("D:/Weminal/Aptopus-AI/src/chatbot")
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from AI.query_processor.question_processing import QuestionProcessor
from AI.answer_generation.answer_generation import answer_question
from AI.context_retrieval.context_retrieval import ContextRetriever
from AI.config.config import AIModel
import pymongo
from AI.config.prompts import *
import json
import os

app = FastAPI()

# HTML for testing
html = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat</title>
</head>
<body>
    <h1>WebSocket Chat</h1>
    <h2>ID của bạn: <span id="ws-id"></span></h2>
    <form action="" onsubmit="sendMessage(event)">
        <input type="text" id="messageText" autocomplete="off" placeholder="Nhập tin nhắn"/>
        <select id="messageType">
            <option value="receive_question">Nhận câu hỏi</option>
            <option value="receive_follow_up_question">Nhận câu hỏi tiếp theo</option>
            <option value="get_context_ids">Lấy ID ngữ cảnh</option>
            <option value="user_selected_context_ids">ID ngữ cảnh đã chọn</option>
            <option value="handle_answer">Xử lý câu trả lời</option>
        </select>
        <button>Gửi</button>
    </form>
    <ul id='messages'>
    </ul>
    <script>
        var client_id = 12345
        document.querySelector("#ws-id").textContent = client_id;
        var ws = new WebSocket(`ws://localhost:8000/ws/12345`);
        ws.onmessage = function(event) {
            var messages = document.getElementById('messages')
            var message = document.createElement('li')
            var content = document.createTextNode(event.data)
            message.appendChild(content)
            messages.appendChild(message)
        };
        function sendMessage(event) {
            var input = document.getElementById("messageText")
            var type = document.getElementById("messageType")
            var data = {
                type: type.value,
                data: input.value
            }
            ws.send(JSON.stringify(data))
            input.value = ''
            event.preventDefault()
        }
    </script>
</body>
</html>"""


# class for websocket
class WebSocketManager:
    def __init__(self):
        self.model = AIModel().claude_3_haiku 
        # get history from mongodb
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.client = pymongo.MongoClient(self.mongodb_uri)
        self.db = self.client['octopus']
        self.chat_history_dictionary = self.db.history.find()
        # init variable 
        self.question = ''
        self.rewritten_question = ''
        self.context = ''
        self.final_context_id = []
        self.final_question = ''
        self.is_package_id = False
        self.package_id = ''
        self.is_retrieval = False
        self.chat_history = ''
        if self.chat_history_dictionary:
            for item in self.chat_history_dictionary:
                self.chat_history += "USER's QUESTION:   \n" + item['user'] + "ASSISTANT's ANSWER:    \n" + item['assistant']
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

        
    async def handle_receive_question(self, websocket: WebSocket, data):
        self.question = data['data']
        rewritten_question = QuestionProcessor().rewrite_question(self.question, self.chat_history)
        self.rewritten_question = rewritten_question
        # await websocket.send_text(rewritten_question)
        is_retrieval = QuestionProcessor().question_classification(self.rewritten_question)
        self.is_retrieval = True if int(is_retrieval) == 1 else False
        # print("chạy tới này rồi")
        self.package_id, self.is_package_id = QuestionProcessor().get_package_id(self.rewritten_question)
        
        if self.is_retrieval == True or self.is_package_id == False:
            follow_up_question_list = QuestionProcessor().get_follow_up_questions(self.rewritten_question, "")
            response_data = {
                'type': 'follow_up',
                'data': follow_up_question_list.follow_up_questions
            }
            await websocket.send_json(response_data)
        else:
            await websocket.send_text('stream_start')

    async def handle_follow_up_question(self, websocket: WebSocket, data: dict):
        follow_up_questions = data['data']['follow_up_question']
        follow_up_answers = data['data']['follow_up_answer']
        final_question = QuestionProcessor().get_final_question(self.rewritten_question, follow_up_questions, follow_up_answers)
        response_data = {
            'type': 'final_question',
            'data': final_question
        }
        self.rewritten_question = final_question
        await websocket.send_json(response_data)

    async def handle_get_context_ids(self, websocket: WebSocket, data: dict):
        final_question = data['data']
        context_ids = ContextRetriever().get_context_ids_relevant(final_question)
        response_data = {
            'type': 'relevant_docs',
            'data': context_ids
        }
        await websocket.send_json(response_data)

    async def handle_user_selected_context_ids(self, websocket: WebSocket, data: dict):
        if self.package_id.startswith("0x") or self.is_package_id == True:
            self.context += "\n" + ContextRetriever().get_context_with_package_id(self.package_id)
            
        if self.is_retrieval == True:
            selected_ids = data['selected_ids']
            final_context_id = ContextRetriever().get_id_relevant(selected_ids)
            context = ContextRetriever().get_context(final_context_id)
            self.context += "\n" + context
            
    async def handle_answer(self, websocket: WebSocket):
        if self.package_id.startswith("0x") or self.is_package_id == True:
            prompt = answer_question_prompt.format(question=self.rewritten_question, context=self.context, chat_history=self.chat_history)
        elif self.is_retrieval == True:
            prompt = answer_question_prompt.format(question=self.rewritten_question, context=self.context, chat_history=self.chat_history)
        else:
            prompt = self.rewritten_question
        messages = [
    (
        "system",
        "You are a seasoned and experienced programmer for the Move programming language on the Aptos.",
            ),
            ("human", prompt),
        ]
        # answer = ''
        for chunk in self.model.stream(messages):
            await websocket.send_json({"type":"answer", "data": chunk.content})
        #     print("chunk.content:   ",chunk.content)
        #     try:
        #         answer += chunk.content
        #         print("answer:   ", answer)
        #     except:
        #         pass
        # await websocket.send_text("Final answer:    \n" +answer)

ws_manager = WebSocketManager()

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data['type'] == 'receive_question':
                await ws_manager.handle_receive_question(websocket, data)
            elif data['type'] == 'receive_follow_up_question':
                await ws_manager.handle_follow_up_question(websocket, data)
            elif data['type'] == 'get_context_ids':
                await ws_manager.handle_get_context_ids(websocket, data)
            elif data['type'] == 'user_selected_context_ids':
                await ws_manager.handle_user_selected_context_ids(websocket, data)
            elif data['type'] == 'handle_answer':
                await ws_manager.handle_answer(websocket)
    except Exception as e:
        print(e)