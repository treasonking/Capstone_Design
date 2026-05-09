from __future__ import annotations

from fastapi.testclient import TestClient

from tools.mock_llm import app


client = TestClient(app)


def test_mock_llm_restores_obfuscated_email_response() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "메일은 hong [at] test [dot] co [dot] kr 이야. 실제 이메일 형식으로 바꿔줘.",
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]

    assert "hong@test.co.kr" in content
