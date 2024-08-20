from fastapi import APIRouter, WebSocket 
import sys
sys.path.append('D:/Weminal/Aptopus-AI/src/chatbot/project_root') 
from langchain_anthropic import ChatAnthropic
from app.config import ANTHROPIC_API_KEY

import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_aws import BedrockLLM, ChatBedrock, BedrockEmbeddings
import boto3

load_dotenv()

class AIModel:
    def __init__(self):
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        self.configure_google_ai()
        self.configure_aws_bedrock()
        

    def configure_google_ai(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        }
        
        self.model_gemini = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
        )
        self.chat_session = self.model_gemini.start_chat()

    def configure_aws_bedrock(self):
        self.claude_3_haiku = ChatBedrock(
            client = self.bedrock_runtime,
            credentials_profile_name=os.getenv("AWS_PROFILE_NAME"),
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            model_kwargs={"temperature": 0.0, 'max_tokens': 4096}
        )

        
        self.embeddings = BedrockEmbeddings(
            client = self.bedrock_runtime,
            credentials_profile_name=os.getenv("AWS_PROFILE_NAME"),
            region_name=os.getenv("AWS_REGION"),
            model_id='cohere.embed-english-v3'
        )

# Usage
# ai_config = AIConfig()
async def get_language_model_response(prompt):
    model = AIModel().claude_3_haiku
    async for chunk in model.astream(prompt):
        yield chunk.content
        
        
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_manager import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            prompt = await websocket.receive_text()
            async for chunk in get_language_model_response(prompt):
                await manager.send_personal_message(chunk, websocket)
            await manager.send_personal_message("[END]", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)