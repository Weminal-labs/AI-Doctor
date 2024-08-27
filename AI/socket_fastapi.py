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
html = """<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off" placeholder="Nhập tin nhắn"/>
            <select id="messageType">
                <option value="receive_question">Nhận câu hỏi</option>
                <option value="receive_follow_up_question">Nhận câu hỏi tiếp theo</option>
                <option value="get_context_ids">Lấy ID ngữ cảnh</option>
                <option value="user_selected_context_ids">ID ngữ cảnh đã chọn</option>
            </select>
            <button>Gửi</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
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
                    question: input.value
                }
                ws.send(JSON.stringify(data))
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>"""

class WebSocketManager:
    def __init__(self):
        self.model = AIModel().claude_3_haiku
        print(self.model)
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.client = pymongo.MongoClient(self.mongodb_uri)
        self.db = self.client['octopus']
        self.chat_history_dictionary = self.db.history.find()
        self.question = ''
        self.rewritten_question = ''
        self.context = ''
        self.final_question = ''
        self.is_package_id = False
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

        
    async def handle_receive_question(self, websocket: WebSocket, data: dict):
        question = data['question']
        self.question = question
        rewritten_question = QuestionProcessor().rewrite_question(question, self.chat_history)
        self.rewritten_question = rewritten_question
        await websocket.send_text(rewritten_question)
        is_retrieval = QuestionProcessor().question_classification(rewritten_question)
        self.is_retrieval = True if int(is_retrieval) == 1 else False
        self.package_id, self.is_package_id = QuestionProcessor().get_package_id(self.rewritten_question)
        
        if self.is_retrieval == True or self.is_package_id == False:
            follow_up_question_list = QuestionProcessor().get_follow_up_questions(question, "")
            response_data = {
                '_type': 'follow_up',
                'data': follow_up_question_list.follow_up_questions
            }
            await websocket.send_json(response_data)
        else:
            await websocket.send_text('stream_start')

    async def handle_follow_up_question(self, websocket: WebSocket, data: dict):
        follow_up_questions = data['follow_up_question']
        follow_up_answers = data['follow_up_answer']
        final_question = QuestionProcessor().get_final_question(self.rewritten_question, follow_up_questions, follow_up_answers)
        response_data = {
            '_type': 'final_question',
            'data': final_question
        }
        self.rewritten_question = final_question
        await websocket.send_json(response_data)

    async def handle_get_context_ids(self, websocket: WebSocket, data: dict):
        final_question = data['final_question']
        context_ids = ContextRetriever().get_context_ids_relevant(final_question)
        response_data = {
            '_type': 'relevant_docs',
            'data': context_ids
        }
        await websocket.send_json(response_data)

    async def handle_user_selected_context_ids(self, websocket: WebSocket, data: dict):
        selected_ids = data['selected_ids']
        context = ContextRetriever().get_context(selected_ids)
        self.context += "\n" + context
        if self.package_id.startswith("0x") != '' or self.is_package_id == True:
            self.context += "\n" + ContextRetriever().get_context_with_package_id(self.package_id)
        prompt = answer_question_prompt.format(question=self.rewritten_question, context=self.context, chat_history=self.chat_history)
        if self.is_retrieval == True:
            prompt = self.rewritten_question
        for chunk in self.model.astream.invoke(prompt):
            await websocket.send_text(chunk.content + " ")

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
    except Exception as e:
        print(e)