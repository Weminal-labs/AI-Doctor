import sys
sys.path.append('D:/Weminal/Aptopus-AI/src/chatbot/project_root')  # Thêm đường dẫn vào sys.path
from app.main import app
import sys

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)