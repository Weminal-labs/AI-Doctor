import sys
# sys.path.append("D:/Weminal/Aptopus-AI/src/chatbot")
import socketio
from query_processor.question_processing import QuestionProcessor
from answer_generation.answer_generation import answer_question
from context_retrieval.context_retrieval import ContextRetriever
from config.config import AIModel
import pymongo
from aiohttp import web
from aiohttp_cors import setup as cors_setup, ResourceOptions
from config.prompts import *

sio = socketio.AsyncServer(async_mode='aiohttp')
app = web.Application()
sio.attach(app, socketio_path='/ws')

class WebSocketManager:
    def __init__(self):
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
            
        # TODO gọi từ db chat_history

    @sio.on('connect')
    async def connect(sid, environ):
        print(f"Client kết nối: {sid}")
        await sio.emit('connected', {'message': 'Bạn đã kết nối thành công', 'sid': sid}, room=sid)


    @sio.on('disconnect')
    async def disconnect(sid):
        print(f"Client ngắt kết nối: {sid}")

    async def index(request):
        return web.Response(text="Server WebSocket đang chạy", content_type='text/html')

    

    @sio.on('receive_question')
    async def handle_receive_question(self, sid, data):
        # Nhận câu hỏi từ front-end
        question = data['question']
        self.question = question
        rewritten_question =  QuestionProcessor().rewrite_question(question, self.chat_history )
        self.rewritten_question = rewritten_question
        is_retrieval = QuestionProcessor().question_classification(rewritten_question)
        self.is_retrieval = True if int(is_retrieval) == 1 else False
        self.package_id, self.is_package_id = QuestionProcessor().get_package_id(self.rewritten_question)
        
        if self.is_retrieval == True or self.is_package_id == False:
            # Phân tích câu hỏi và trả về danh sách câu hỏi follow-up
            follow_up_question_list = QuestionProcessor().get_follow_up_questions(question, "")
            response_data = {
                '_type': 'follow_up',
                'data': follow_up_question_list.follow_up_questions
            }
            await sio.emit('follow_up', {'_type': 'follow_up', 'data': response_data}, room=sid)
        else:
            await sio.emit('stream_start', '', room=sid) 

    @sio.on('receive_follow_up_question')
    async def handle_follow_up_question(self, sid, data):
        # Nhận câu hỏi follow-up từ front-end
        follow_up_questions = data['follow_up_question']
        follow_up_answers = data['follow_up_answer']
        # Tạo câu hỏi cuối từ câu hỏi follow-up
        final_question = QuestionProcessor().get_final_question(self.rewritten_question, follow_up_questions, follow_up_answers)
        # TODO streaming final question
        # for chunk in AIModel().claude_3_haiku.astream.invoke(answer_question_prompt.format(question = self.rewritten_question, context = self.context, chat_history = self.chat_history)):
        response_data = {
            '_type': 'final_question',
            'data': final_question
        }
        self.rewritten_question = final_question
        await sio.emit('final_question', response_data, room=sid)

    @sio.on('get_context_ids')
    async def handle_get_context_ids(self, sid, data):
        # Nhận câu hỏi cuối từ front-end
        final_question = data['final_question']
        # Truy vấn context và trả về mảng ID
        context_ids = ContextRetriever().get_context_ids_relevant(final_question)
        response_data = {
            '_type': 'relevant_docs',
            'data': context_ids
        }
        # Dòng này gửi dữ liệu về các tài liệu liên quan đến client thông qua kênh 'relevant_docs' và chỉ định phòng là sid.
        await sio.emit('relevant_docs', response_data, room=sid)

    @sio.on('user_selected_context_ids')
    async def handle_user_selected_context_ids(self, sid, data):
        # Nhận mảng ID đã chọn từ front-end
        selected_ids = data['selected_ids']
        context = ContextRetriever().get_context(selected_ids)
        self.context += "\n" + context
        # package_id, is_package_id = QuestionProcessor().get_package_id(self.rewritten_question)
        if self.package_id.startswith("0x") != '' or self.is_package_id == True:
            self.context += "\n" + ContextRetriever().get_context_with_package_id(self.package_id)
        # Xử lý câu trả lời cuối cùng dựa trên các ID đã chọn
        prompt = answer_question_prompt.format(question = self.rewritten_question, context = self.context, chat_history = self.chat_history)
        if self.is_retrieval == True:
            prompt = self.rewritten_question
        for chunk in AIModel().claude_3_haiku.astream.invoke(prompt):
            await sio.emit('stream_start', chunk, room=sid)
    app.router.add_get('/', index)
if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=8080)
    