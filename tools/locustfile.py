from __future__ import annotations

from locust import HttpUser, between, task


class ProxyUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task
    def proxy_chat(self) -> None:
        self.client.post(
            "/proxy/chat",
            json={
                "message": "민원 요약 요청입니다. 개인정보 없이 일반적인 안내만 작성해줘.",
                "policy_id": "default",
                "user_id": "load-test-session",
                "model": "mock",
            },
            name="/proxy/chat",
        )
