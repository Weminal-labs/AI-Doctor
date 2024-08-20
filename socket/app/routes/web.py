from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
from app.websocket_manager import manager
from pydantic import BaseModel

router = APIRouter()

class Message(BaseModel):
    content: str

@router.get("/", response_class=HTMLResponse)
async def get():
    html_file = Path("static/index.html").read_text()
    return html_file

@router.post("/send_message")
async def send_message(message: Message):
    await manager.broadcast(message.content)
    return {"status": "Message sent"}