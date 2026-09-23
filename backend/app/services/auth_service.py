from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path


_ITERATIONS = 310_000
_TOKEN_TTL_SECONDS = 60 * 60 * 8
_sessions: dict[str, tuple[str, float]] = {}
_lock = threading.RLock()


def _database_path() -> Path:
    configured = os.getenv("AUTH_DB_PATH")
    path = Path(configured) if configured else Path("backend/data/auth.sqlite3")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path())
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _ITERATIONS
    )
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    _, password_hash = _hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(password_hash, expected_hash)


def create_user(email: str, password: str) -> bool:
    salt, password_hash = _hash_password(password)
    try:
        with _connection() as connection:
            connection.execute(
                "INSERT INTO users(email, password_hash, password_salt, created_at) "
                "VALUES (?, ?, ?, datetime('now'))",
                (email, password_hash, salt),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate_user(email: str, password: str) -> bool:
    with _connection() as connection:
        row = connection.execute(
            "SELECT password_hash, password_salt FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    return bool(row and _verify_password(password, row[1], row[0]))


def issue_token(email: str) -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        _purge_expired_sessions()
        _sessions[token] = (email, time.time() + _TOKEN_TTL_SECONDS)
    return token


def resolve_token(token: str | None) -> str | None:
    if not token:
        return None
    with _lock:
        _purge_expired_sessions()
        session = _sessions.get(token)
        return session[0] if session else None


def revoke_token(token: str | None) -> None:
    if token:
        with _lock:
            _sessions.pop(token, None)


def token_ttl_seconds() -> int:
    return _TOKEN_TTL_SECONDS


def _purge_expired_sessions() -> None:
    now = time.time()
    expired = [token for token, (_, expires_at) in _sessions.items() if expires_at <= now]
    for token in expired:
        _sessions.pop(token, None)
