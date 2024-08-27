import os
from dotenv import load_dotenv
# import google.generativeai as genai
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
        # self.configure_google_ai()
        self.configure_aws_bedrock()
        

    # def configure_google_ai(self):
    #     genconfigure(api_key=os.getenv("GOOGLE_API_KEY"))
        
    #     generation_config = {
    #         "temperature": 0.1,
    #         "top_p": 0.95,
    #         "top_k": 64,
    #         "max_output_tokens": 8192,
    #         "response_mime_type": "application/json",
    #     }
        
    #     self.model_gemini = genGenerativeModel(
    #         model_name="gemini-1.5-flash",
    #         generation_config=generation_config,
    #     )
    #     self.chat_session = self.model_gemini.start_chat()

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