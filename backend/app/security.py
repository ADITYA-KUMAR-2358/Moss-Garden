"""Session cookies and token encryption. Secrets stay on the server."""

import hashlib
import hmac
import secrets

from app.config import get_settings

_DEV_SESSION_SECRET = secrets.token_hex(32)


def session_secret() -> str:
    settings = get_settings()
    if settings.session_secret:
        return settings.session_secret
    if settings.environment == "production":
        raise RuntimeError("SESSION_SECRET is required when ENVIRONMENT is production")
    return _DEV_SESSION_SECRET


def sign_user_id(user_id: int) -> str:
    payload = str(user_id)
    signature = hmac.new(session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_user_id(cookie: str | None) -> int | None:
    if not cookie or "." not in cookie:
        return None
    payload, signature = cookie.rsplit(".", 1)
    expected = hmac.new(session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    if not payload.isdigit():
        return None
    return int(payload)


def encrypt_token(token: str) -> str:
    key = _fernet_key()
    from cryptography.fernet import Fernet

    return Fernet(key).encrypt(token.encode()).decode()


def decrypt_token(stored: str) -> str:
    key = _fernet_key()
    from cryptography.fernet import Fernet

    return Fernet(key).decrypt(stored.encode()).decode()


def _fernet_key() -> bytes:
    settings = get_settings()
    if not settings.token_fernet_key:
        raise RuntimeError("TOKEN_FERNET_KEY is required to store a GitHub token")
    return settings.token_fernet_key.encode()
