# main.py
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from langchain_anthropic import ChatAnthropic
import asyncio
from AI.config.config import AIModel
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get():
    with open("static/index.html", "r") as file:
        return file.read()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        prompt = await websocket.receive_text()
        
        model = AIModel().claude_3_haiku
        await websocket.send_text("[START]")
        async for chunk in model.astream(prompt):
            await websocket.send_text(chunk.content+" ")
        
        # Send a special message to indicate the end of the response
        await websocket.send_text("[END]")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# requirements.txt
