"""Session cookies and token encryption. Secrets stay on the server."""

import hashlib
import hmac
import secrets
import time

from app.config import get_settings

_DEV_SESSION_SECRET = secrets.token_hex(32)
SESSION_MAX_AGE = 60 * 60 * 24 * 30


def session_secret() -> str:
    settings = get_settings()
    if settings.session_secret:
        return settings.session_secret
    if settings.environment == "production":
        raise RuntimeError("SESSION_SECRET is required when ENVIRONMENT is production")
    return _DEV_SESSION_SECRET


def _signature(payload: str) -> str:
    return hmac.new(session_secret().encode(), f"session:{payload}".encode(), hashlib.sha256).hexdigest()


def sign_user_id(user_id: int, issued_at: int | None = None) -> str:
    issued = int(time.time()) if issued_at is None else issued_at
    payload = f"{user_id}.{issued}"
    return f"{payload}.{_signature(payload)}"


def read_user_id(cookie: str | None, now: int | None = None) -> int | None:
    """Return the signed user id, or None for a forged, malformed or expired cookie."""
    if not cookie or cookie.count(".") != 2 or len(cookie) > 200:
        return None
    user_part, issued_part, signature = cookie.split(".")
    if not user_part.isdigit() or not issued_part.isdigit():
        return None
    if not hmac.compare_digest(signature, _signature(f"{user_part}.{issued_part}")):
        return None
    age = (int(time.time()) if now is None else now) - int(issued_part)
    if age < -300 or age > SESSION_MAX_AGE:
        return None
    return int(user_part)


def encrypt_token(token: str) -> str:
    key = _fernet_key()
    from cryptography.fernet import Fernet

    return Fernet(key).encrypt(token.encode()).decode()


def decrypt_token(stored: str) -> str:
    key = _fernet_key()
    from cryptography.fernet import Fernet, InvalidToken

    try:
        return Fernet(key).decrypt(stored.encode()).decode()
    except InvalidToken as error:
        raise RuntimeError("The stored GitHub token could not be read. Sign in with GitHub again.") from error


def _fernet_key() -> bytes:
    settings = get_settings()
    if not settings.token_fernet_key:
        raise RuntimeError("TOKEN_FERNET_KEY is required to store a GitHub token")
    return settings.token_fernet_key.encode()
