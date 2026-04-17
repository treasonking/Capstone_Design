from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class ChatRequest(BaseModel):
    messages: list
    model: str = "mock"

@app.post("/v1/chat/completions")
async def mock_chat(req: ChatRequest):
    last_msg = req.messages[-1]["content"] if req.messages else ""
    return {
        "id": "mock-001",
        "choices": [{
            "message": {
                "role": "assistant",
                "content": f"[Mock 응답] 입력 받음: {last_msg[:30]}..."
            }
        }]
    }


if __name__ == "__main__":
    uvicorn.run("tools.mock_llm:app", host="0.0.0.0", port=8001, reload=False)
