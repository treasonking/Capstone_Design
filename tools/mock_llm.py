import re

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from backend.app.detection.email_normalization import restore_obfuscated_emails

app = FastAPI()
_EMAIL_RESTORE_HINT = re.compile(
    r"(실제\s*이메일\s*형식|이메일\s*형식으로\s*바꿔|restore\s+the\s+email|convert\s+to\s+an?\s+email)",
    flags=re.IGNORECASE,
)


class ChatRequest(BaseModel):
    messages: list
    model: str = "mock"


@app.post("/v1/chat/completions")
async def mock_chat(req: ChatRequest):
    last_msg = req.messages[-1]["content"] if req.messages else ""
    _, restored_emails = restore_obfuscated_emails(last_msg)
    if restored_emails and _EMAIL_RESTORE_HINT.search(last_msg):
        content = f"변환된 이메일은 {restored_emails[0]} 입니다."
    elif restored_emails:
        content = f"복원된 이메일 후보는 {restored_emails[0]} 입니다."
    else:
        content = f"[Mock 응답] 입력 받음: {last_msg[:30]}..."
    return {
        "id": "mock-001",
        "choices": [{
            "message": {
                "role": "assistant",
                "content": content
            }
        }]
    }


if __name__ == "__main__":
    uvicorn.run("tools.mock_llm:app", host="0.0.0.0", port=8001, reload=False)
