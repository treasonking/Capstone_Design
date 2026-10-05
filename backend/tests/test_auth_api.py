from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.api.proxy import app


client = TestClient(app)


def test_signup_login_me_and_logout(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.sqlite3"))
    credentials = {"email": "User@example.com", "password": "correct horse"}

    signup = client.post("/auth/signup", json=credentials)
    assert signup.status_code == 201
    assert signup.json() == {"email": "user@example.com"}

    login = client.post("/auth/login", json=credentials)
    assert login.status_code == 200
    payload = login.json()
    assert payload["email"] == "user@example.com"
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]

    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    assert client.get("/auth/me", headers=headers).json() == {
        "email": "user@example.com"
    }
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_duplicate_signup_and_invalid_login(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.sqlite3"))
    credentials = {"email": "user@example.com", "password": "correct horse"}

    assert client.post("/auth/signup", json=credentials).status_code == 201
    duplicate = client.post("/auth/signup", json=credentials)
    assert duplicate.status_code == 409

    invalid_password = client.post(
        "/auth/login",
        json={"email": credentials["email"], "password": "wrong password"},
    )
    assert invalid_password.status_code == 401


def test_auth_rejects_invalid_email_and_short_password(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.sqlite3"))
    response = client.post(
        "/auth/signup",
        json={"email": "not-an-email", "password": "short"},
    )
    assert response.status_code == 422


def test_auth_rejects_invalid_or_expired_session() -> None:
    assert client.get(
        "/auth/me",
        headers={"Authorization": "Bearer expired-or-invalid-token"},
    ).status_code == 401
