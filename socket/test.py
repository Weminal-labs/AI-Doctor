from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import time
from langchain_aws import BedrockLLM, ChatBedrock, BedrockEmbeddings
from services import AIModel

app = FastAPI()

async def data_generator(prompt):
      # 1 second delay to simulate streaming
    model = AIModel().claude_3_haiku
    async for chunk in model.astream(prompt):
        yield chunk.content

from fastapi import Query  # Thêm import

@app.get("/stream")
def stream_data(query: str = Query(...)):  # Định nghĩa kiểu dữ liệu cho query
    return StreamingResponse(data_generator(query),
                              headers={ "Content-Type": "text/event-stream" })  # Không thay đổi
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")