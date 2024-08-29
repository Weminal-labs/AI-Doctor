import sys
sys.path.append("D:/Weminal/Aptopus-AI/src/chatbot")
import socketio
from AI.query_processor.question_processing import QuestionProcessor
from AI.answer_generation.answer_generation import answer_question
from AI.context_retrieval.context_retrieval import ContextRetriever
from AI.config.config import AIModel
import pymongo
from aiohttp import web
import aiohttp_cors
from aiohttp_cors import setup as cors_setup, ResourceOptions
from AI.config.prompts import *

sio = sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app, socketio_path='/ws')

class WebSocketManager:
    def __init__(self):
        self.model = AIModel().claude_3_haiku
        # print(self.model)
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.client = pymongo.MongoClient(self.mongodb_uri)
        self.db = self.client['octopus']
        self.chat_history_dictionary = self.db.history.find()
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
        # TODO gọi từ db chat_history

    @sio.on('connect')
    async def connect(sid):
        print(f"Client kết nối: {sid}")
        await sio.emit('connected', {'message': 'Bạn đã kết nối thành công', 'sid': sid}, room=sid)


    @sio.on('disconnect')
    async def disconnect(sid):
        print(f"Client ngắt kết nối: {sid}")

    @sio.on('receive_question')
    async def handle_receive_question(self, sid, data):
        self.question = data['data']
        rewritten_question = QuestionProcessor().rewrite_question(self.question, self.chat_history)
        self.rewritten_question = rewritten_question
        # await websocket.send_text(rewritten_question)
        is_retrieval = QuestionProcessor().question_classification(self.rewritten_question)
        self.is_retrieval = True if int(is_retrieval) == 1 else False
        self.package_id, self.is_package_id = QuestionProcessor().get_package_id(self.rewritten_question)
        
        if self.is_retrieval == True or self.is_package_id == False:
            follow_up_question_list = QuestionProcessor().get_follow_up_questions(self.rewritten_question, "")
            response_data = follow_up_question_list.follow_up_questions
            await sio.emit('follow_up', {'sid': sid, 'data': response_data}, room=sid)
        else:
            await sio.emit('stream_start', {'sid': sid}, room=sid) 

    @sio.on('receive_follow_up_question')
    async def handle_follow_up_question(self, sid, data):
        follow_up_questions = data['data']['follow_up_question']
        follow_up_answers = data['data']['follow_up_answer']
        final_question = QuestionProcessor().get_final_question(self.rewritten_question, follow_up_questions, follow_up_answers)
        response_data =  final_question
        self.rewritten_question = final_question
        await sio.emit('final_question', {'sid': sid, 'data': response_data}, room=sid)

    @sio.on('get_context_ids')
    async def handle_get_context_ids(self, sid, data: dict):
        final_question = data['data']
        context_ids = ContextRetriever().get_context_ids_relevant(final_question)
        response_data = context_ids
        await sio.emit("id_relevants", {'sid': sid, 'data': response_data}, room=sid)

    @sio.on('user_selected_context_ids')
    async def handle_user_selected_context_ids(self, sid, data):
        if self.package_id.startswith("0x") or self.is_package_id == True:
            self.context += "\n" + ContextRetriever().get_context_with_package_id(self.package_id)
            
        if self.is_retrieval == True:
            selected_ids = data['selected_ids']
            final_context_id = ContextRetriever().get_id_relevant(selected_ids)
            await sio.emit('final_relevant_docs', {'sid': sid, 'data': final_context_id}, room=sid)
            context = ContextRetriever().get_context(final_context_id)
            self.context += "\n" + context
    
    @sio.on('get_answer')  
    async def handle_answer(self, sid):
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
        for chunk in self.model.stream(messages):
            await sio.emit("answer", {"sid": sid, "data": chunk.content})
    # ... existing code ...

async def index(request):
    html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Kiểm tra WebSocket</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    </head>
    <body>
        <h1>Kiểm tra WebSocket</h1>
        <input type="text" id="questionInput" placeholder="Nhập câu hỏi">
        <button onclick="sendQuestion()">Gửi câu hỏi</button>
        <div id="output"></div>

        <script>
            const socket = io('http://localhost:8080', {path: '/ws'});
            
            socket.on('connect', () => {
                console.log('Đã kết nối');
                appendMessage('Đã kết nối với server');
            });

            socket.on('connected', (data) => {
                appendMessage(data.message);
            });

            socket.on('follow_up', (data) => {
                appendMessage('Câu hỏi tiếp theo: ' + JSON.stringify(data.data));
            });

            socket.on('stream_start', (data) => {
                appendMessage('Bắt đầu luồng');
            });

            socket.on('final_question', (data) => {
                appendMessage('Câu hỏi cuối cùng: ' + data.data);
            });

            socket.on('id_relevants', (data) => {
                appendMessage('ID liên quan: ' + JSON.stringify(data.data));
            });

            socket.on('final_relevant_docs', (data) => {
                appendMessage('Tài liệu liên quan cuối cùng: ' + JSON.stringify(data.data));
            });

            socket.on('answer', (data) => {
                appendMessage('Câu trả lời: ' + data.data);
            });

            function sendQuestion() {
                const question = document.getElementById('questionInput').value;
                socket.emit('receive_question', {data: question});
            }

            function appendMessage(message) {
                const output = document.getElementById('output');
                output.innerHTML += '<p>' + message + '</p>';
            }
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

# ... existing code ...
# Thêm route cho trang chủ
# async def index(request):
#     current_dir = os.path.dirname(__file__)
#     file_path = os.path.join(current_dir, 'chat_template.html')
#     with open(file_path, 'r', encoding='utf-8') as f:
#         return web.Response(text=f.read(), content_type='text/html')


if __name__ == '__main__':
    web.run_app(app, host='localhost', port=8080)