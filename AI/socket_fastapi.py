
# sys.path.append("D:/Weminal/Aptopus-AI/src/chatbot")  # Append the path to the chatbot directory
import sys
import os
import json
import pymongo
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from AI.query_processor.question_processing import QuestionProcessor
from AI.answer_generation.answer_generation import answer_question
from AI.context_retrieval.context_retrieval import ContextRetriever
from AI.config.config import AIModel
from AI.config.prompts import *

app = FastAPI()  # Initialize the FastAPI application


class WebSocketManager:
    def __init__(self):
        self.model = AIModel().claude_3_haiku  # Initialize the AI model
        self.mongodb_uri = os.getenv("MONGODB_URI")  # Get the MongoDB URI from environment variables
        self.client = pymongo.MongoClient(self.mongodb_uri)  # Connect to MongoDB
        self.db = self.client['octopus']  # Select the database
        self.chat_history_dictionary = self.db.history.find()  # Find all chat history documents
        self.question = ''  # Initialize the question
        self.rewritten_question = ''  # Initialize the rewritten question
        self.context = ''  # Initialize the context
        self.final_context_id = []  # Initialize the final context ID list
        self.final_question = ''  # Initialize the final question
        self.is_package_id = False  # Initialize the package ID flag
        self.package_id = ''  # Initialize the package ID
        self.is_retrieval = False  # Initialize the retrieval flag
        self.chat_history = ''  # Initialize the chat history
        if self.chat_history_dictionary:
            for item in self.chat_history_dictionary:
                self.chat_history += f"USER's QUESTION:\n{item['user']}ASSISTANT's ANSWER:\n{item['assistant']}"  # Build the chat history
        self.active_connections: list[WebSocket] = []  # Initialize the active connections list

    async def connect(self, websocket: WebSocket):
        await websocket.accept()  # Accept the WebSocket connection
        self.active_connections.append(websocket)  # Add the WebSocket to the active connections list

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)  # Remove the WebSocket from the active connections list

    async def handle_receive_question(self, websocket: WebSocket, data):
        """

        Args:
            data: Data from front-end
            format:
                {"data": "question of user }
        """
        self.question = data['data']  # Set the question
        question_processor = QuestionProcessor()  # Initialize the question processor
        self.rewritten_question = question_processor.rewrite_question(self.question, self.chat_history)  # Rewrite the question
        # print(self.rewritten_question)
        await websocket.send_text(self.rewritten_question)
        self.is_retrieval = bool(int(question_processor.question_classification(self.rewritten_question)))  # Determine if retrieval is needed
        # print(self.is_retrieval)
        if self.is_retrieval:
            self.package_id, self.is_package_id = question_processor.get_package_id(self.rewritten_question)
            if not self.is_package_id: # Get the package ID and determine if it's a package IDor not self.is_package_id:
                follow_up_question_list = question_processor.get_follow_up_questions(self.rewritten_question, "")  # Get follow-up questions
                response_data = {
                    'type': 'follow_up',
                    'data': follow_up_question_list.follow_up_questions
                }
                await websocket.send_json(response_data)  # Send follow-up questions
        else:
            await websocket.send_text('stream_start')  # Send stream start message

    async def handle_follow_up_question(self, websocket: WebSocket, data: dict):
        """

        Args:
            websocket (WebSocket): _description_
            data (dict): follow-up question and answer
            format:
                {
                    "data" : {
                            "follow_up_question" : ["question 1", "question 2",..],
                            "follow_up_answer": ["answer 1", "answer 2",..]
                            }
                }
        """
        follow_up_questions = data['data']['follow_up_question']  # Get follow-up questions
        follow_up_answers = data['data']['follow_up_answer']  # Get follow-up answers
        final_question = QuestionProcessor().get_final_question(
            self.rewritten_question, follow_up_questions, follow_up_answers
        )  # Get the final question
        response_data = {
            'type': 'final_question',
            'data': final_question
        }
        self.rewritten_question = final_question  # Update the rewritten question
        await websocket.send_json(response_data)  # Send the final question

    async def handle_get_context_ids(self, websocket: WebSocket):
        context_ids = ContextRetriever().get_context_ids_relevant(self.final_question)  # Get relevant context IDs
        response_data = {
            'type': 'relevant_docs',
            'data': context_ids
        }
        await websocket.send_json(response_data)  # Send the relevant context IDs

    async def handle_user_selected_context_ids(self, websocket: WebSocket, data: dict):
        """

        Args:
            websocket (WebSocket): _description_
            data (list[int]): follow-up question and answer
            format:
                {
                    "selected_ids" : [index 1, index 2]
                }
        """
        context_retriever = ContextRetriever()  # Initialize the context retriever
        if self.package_id.startswith("0x") or self.is_package_id:
            self.context += f"\n{context_retriever.get_context_with_package_id(self.package_id)}"  # Add context with package ID
            
        if self.is_retrieval:
            selected_ids = data['selected_ids']  # Get selected IDs
            final_context_id = context_retriever.get_id_relevant(selected_ids)  # Get the final context ID
            websocket.send_json({"final_id_relevants": final_context_id})
            context = context_retriever.get_context(final_context_id)  # Get the context
            self.context += f"\n{context}"  # Add the context

    async def handle_answer(self, websocket: WebSocket):
        if self.package_id.startswith("0x") or self.is_package_id or self.is_retrieval:
            prompt = answer_question_prompt.format(
                question=self.rewritten_question,
                context=self.context,
                chat_history=self.chat_history
            )  # Format the prompt for package ID or retrieval
        else:
            prompt = self.rewritten_question  # Use the rewritten question as the prompt
        await websocket.send_text("prompt:  "+prompt)
        messages = [
            ("system", "You are a seasoned and experienced programmer for the Move programming language on the Aptos."),
            ("human", prompt),
        ]
        
        for chunk in self.model.stream(messages):
            await websocket.send_json({"type": "answer", "data": chunk.content})  # Send the answer

ws_manager = WebSocketManager()

@app.get("/")
async def get():
    with open("AI/chat.html", "r", encoding="utf-8") as file:
        html = file.read()
    return HTMLResponse(html)  # Return the HTML response

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await ws_manager.connect(websocket)  # Connect the WebSocket
    try:
        while True:
            data = await websocket.receive_json()  # Receive JSON data
            match data['type']:
                case 'receive_question':
                    await ws_manager.handle_receive_question(websocket, data)  # Handle receive question
                case 'receive_follow_up_question':
                    await ws_manager.handle_follow_up_question(websocket, data)  # Handle receive follow-up question
                case 'get_context_ids':
                    await ws_manager.handle_get_context_ids(websocket, data)  # Handle get context IDs
                case 'user_selected_context_ids':
                    await ws_manager.handle_user_selected_context_ids(websocket, data)  # Handle user selected context IDs
                case 'handle_answer':
                    await ws_manager.handle_answer(websocket)  # Handle answer
    except Exception as e:
        print(e)  # Print any exceptions