from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import uuid
import re

app = FastAPI()

MOCK_LLM_URL = "http://localhost:8001/v1/chat/completions"
TIMEOUT_SECONDS = 10


class ProxyRequest(BaseModel):
    message: str
    policy_id: str = "default"


class ProxyResponse(BaseModel):
    request_id: str
    action: str
    reason_code: str | None
    content: str | None


def check_policy(message: str):
    if re.search(r"01[0-9]-\d{3,4}-\d{4}", message):
        return "MASK", "PII_PHONE"
    return "ALLOW", None


def mask_message(message: str):
    return re.sub(r"01[0-9]-\d{3,4}-\d{4}", "***-****-****", message)


@app.post("/proxy/chat")
async def proxy_chat(req: ProxyRequest):
    request_id = str(uuid.uuid4())
    action, reason_code = check_policy(req.message)

    if action == "BLOCK":
        return ProxyResponse(
            request_id=request_id,
            action="BLOCK",
            reason_code=reason_code,
            content=None
        )

    if action == "MASK":
        processed_message = mask_message(req.message)
    else:
        processed_message = req.message

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            llm_resp = await client.post(MOCK_LLM_URL, json={
                "messages": [{"role": "user", "content": processed_message}]
            })
        llm_content = llm_resp.json()["choices"][0]["message"]["content"]

    except httpx.TimeoutException:
        return ProxyResponse(
            request_id=request_id,
            action="ERROR",
            reason_code="TIMEOUT",
            content=None
        )

    return ProxyResponse(
        request_id=request_id,
        action=action,
        reason_code=reason_code,
        content=llm_content
    )