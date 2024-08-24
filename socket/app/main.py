# socket/app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import web, ws

app = FastAPI()

# Sửa lại đường dẫn đến thư mục tĩnh
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(web.router)
app.include_router(ws.router)