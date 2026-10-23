"""HTTP routes for the garden, GitHub connection, and optional narration."""

import json
import logging
import secrets
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, Response as RawResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, get_engine
from app.integrations.github import GitHubClient, GitHubError, authorize_url, convert_app_manifest, exchange_code
from app.jobs.nightly import start_nightly
from app.local_env import upsert_env
from app.models import Repository, User
from app.security import decrypt_token, encrypt_token, read_user_id, sign_user_id
from app.services.garden import delete_user, journal_audio_for, remember_projection, start_from_github, sync_repositories

logger = logging.getLogger(__name__)
from app.services.seed import seed_demo

router = APIRouter()
_STATE_COOKIE = "moss_oauth_state"
_SETUP_COOKIE = "moss_setup_state"
_SESSION_COOKIE = "moss_session"


class RepoSelection(BaseModel):
    full_names: list[str]


def current_user(request: Request, session: Session = Depends(get_db)) -> User:
    user_id = read_user_id(request.cookies.get(_SESSION_COOKIE))
    if user_id is None:
        raise HTTPException(status_code=401, detail="Sign in to open this garden")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to open this garden")
    return user


def _set_session(response: Response, user_id: int) -> None:
    response.set_cookie(
        _SESSION_COOKIE,
        sign_user_id(user_id),
        httponly=True,
        samesite="lax",
        secure=get_settings().environment == "production",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


@router.post("/api/demo/enter")
def enter_demo(session: Session = Depends(get_db)):
    user = seed_demo(session)
    response = Response(content='{"ok":true}', media_type="application/json")
    _set_session(response, user.id)
    return response


@router.get("/api/garden")
def garden(user: User = Depends(current_user), session: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    return remember_projection(session, user, today)


@router.get("/api/repos")
def repos(user: User = Depends(current_user), session: Session = Depends(get_db)):
    rows = session.scalars(select(Repository).where(Repository.user_id == user.id)).all()
    return {
        "repos": [
            {
                "full_name": row.full_name,
                "selected": row.selected,
                "accessible": row.accessible,
            }
            for row in rows
        ]
    }


@router.post("/api/repos")
def select_repos(body: RepoSelection, user: User = Depends(current_user), session: Session = Depends(get_db)):
    chosen = set(body.full_names)
    rows = session.scalars(select(Repository).where(Repository.user_id == user.id)).all()
    known = {row.full_name for row in rows}
    unknown = chosen - known
    if unknown:
        raise HTTPException(status_code=400, detail="Unknown repository")
    for row in rows:
        row.selected = row.full_name in chosen
    return {"selected": sorted(chosen)}


@router.post("/api/sync")
def sync(user: User = Depends(current_user), session: Session = Depends(get_db)):
    if user.is_demo:
        return {"imported": 0, "status": "demo"}
    if not user.token_encrypted:
        raise HTTPException(status_code=400, detail="GitHub is not connected")
    try:
        token = decrypt_token(user.token_encrypted)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    try:
        return sync_repositories(session, user, GitHubClient(token))
    except GitHubError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/auth/status")
def auth_status():
    settings = get_settings()
    ready = bool(settings.github_client_id and settings.github_client_secret and settings.token_fernet_key)
    return {"github": ready}


@router.get("/auth/github")
def github_start(request: Request):
    settings = get_settings()
    if not settings.github_client_id or not settings.github_client_secret or not settings.token_fernet_key:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    state = secrets.token_urlsafe(24)
    target = authorize_url(
        client_id=settings.github_client_id,
        redirect_uri=_callback_url(request),
        scopes="" if settings.github_app_slug else settings.github_scopes,
        state=state,
    )
    response = RedirectResponse(target)
    response.set_cookie(
        _STATE_COOKIE,
        state,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=600,
        path="/",
    )
    return response


@router.get("/auth/github/callback")
def github_callback(code: str, state: str, request: Request, session: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    if not state or state != request.cookies.get(_STATE_COOKIE):
        raise HTTPException(status_code=400, detail="GitHub sign-in state did not match")
    try:
        token = exchange_code(
            client_id=settings.github_client_id,
            client_secret=settings.github_client_secret,
            code=code,
            redirect_uri=_callback_url(request),
        )
        encrypted = encrypt_token(token)
        login = GitHubClient(token).current_login()
    except (GitHubError, RuntimeError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    profile = GitHubClient(token)._request("https://api.github.com/user")[1]
    github_id = int(profile["id"]) if isinstance(profile, dict) and profile.get("id") else None
    user = session.scalar(select(User).where(User.github_id == github_id)) if github_id else None
    if user is None:
        user = User(
            github_id=github_id,
            login=login,
            display_name=str(profile.get("name") or login) if isinstance(profile, dict) else login,
            token_encrypted=encrypted,
            is_demo=False,
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.flush()
    else:
        user.login = login
        user.display_name = str(profile.get("name") or login) if isinstance(profile, dict) else login
        user.token_encrypted = encrypted
        session.flush()
    session.commit()
    try:
        start_from_github(session, user, GitHubClient(token))
    except Exception:
        logger.exception("github garden start failed")
    response = RedirectResponse("/#garden")
    _set_session(response, user.id)
    response.delete_cookie(_STATE_COOKIE, path="/")
    return response


def _browser_origin(request: Request) -> str:
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host:
        scheme = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
        return f"{scheme}://{host}"
    parts = urlsplit(get_settings().github_oauth_callback_url)
    return f"{parts.scheme}://{parts.netloc}"


def _callback_url(request: Request) -> str:
    settings = get_settings()
    if settings.environment == "production":
        return settings.github_oauth_callback_url
    return f"{_browser_origin(request)}/auth/github/callback"


def _configured() -> bool:
    settings = get_settings()
    return bool(settings.github_client_id and settings.github_client_secret and settings.token_fernet_key)


@router.get("/auth/github/setup")
def github_setup(request: Request):
    """Send the browser to GitHub so this person can approve a read-only app."""
    if _configured():
        return RedirectResponse("/auth/github")
    state = secrets.token_urlsafe(24)
    origin = _browser_origin(request)
    callbacks = []
    for url in (
        f"{origin}/auth/github/callback",
        "http://localhost:5173/auth/github/callback",
        "http://127.0.0.1:5173/auth/github/callback",
        "http://localhost:8000/auth/github/callback",
    ):
        if url not in callbacks:
            callbacks.append(url)
    manifest = {
        "name": "Moss Garden",
        "url": origin,
        "redirect_url": f"{origin}/auth/github/setup/callback",
        "callback_urls": callbacks,
        "setup_url": f"{origin}/auth/github",
        "public": True,
        "request_oauth_on_install": False,
        "default_permissions": {"contents": "read"},
    }
    payload = json.dumps(json.dumps(manifest).replace("<", "\\u003c"))
    page = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Connect GitHub</title></head>
<body>
<p>Taking you to GitHub to approve Moss Garden. It asks for read-only access to repositories you choose.</p>
<form id="manifest-form" action="https://github.com/settings/apps/new?state={state}" method="post">
<input type="hidden" name="manifest" id="manifest-value">
</form>
<script>
document.getElementById("manifest-value").value = {payload};
document.getElementById("manifest-form").submit();
</script>
</body>
</html>"""
    response = HTMLResponse(page)
    response.set_cookie(
        _SETUP_COOKIE,
        state,
        httponly=True,
        samesite="lax",
        secure=get_settings().environment == "production",
        max_age=600,
        path="/",
    )
    return response


@router.get("/auth/github/setup/callback")
def github_setup_callback(code: str, request: Request, state: str = ""):
    expected = request.cookies.get(_SETUP_COOKIE)
    if not expected or state != expected:
        raise HTTPException(status_code=400, detail="GitHub setup state did not match")
    try:
        created = convert_app_manifest(code)
    except GitHubError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    settings = get_settings()
    updates = {
        "GITHUB_CLIENT_ID": str(created["client_id"]),
        "GITHUB_CLIENT_SECRET": str(created["client_secret"]),
        "GITHUB_APP_SLUG": str(created.get("slug") or ""),
        "GITHUB_OAUTH_CALLBACK_URL": _callback_url(request),
    }
    if not settings.token_fernet_key:
        from cryptography.fernet import Fernet

        updates["TOKEN_FERNET_KEY"] = Fernet.generate_key().decode()
    if not settings.session_secret:
        updates["SESSION_SECRET"] = secrets.token_hex(32)
    upsert_env(updates)
    slug = updates["GITHUB_APP_SLUG"]
    target = f"https://github.com/apps/{slug}/installations/new" if slug else "/auth/github"
    response = RedirectResponse(target)
    response.delete_cookie(_SETUP_COOKIE, path="/")
    return response


@router.post("/api/jobs/nightly", status_code=202)
def nightly_sync(request: Request):
    expected = get_settings().sync_secret
    if not expected:
        raise HTTPException(status_code=503, detail="SYNC_SECRET is not set")
    given = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not secrets.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Sync secret did not match")
    if not database_ready():
        raise HTTPException(status_code=503, detail="Database is not configured")
    if not start_nightly():
        return {"status": "running"}
    return {"status": "started"}


@router.post("/api/logout")
def logout():
    response = Response(content='{"ok":true}', media_type="application/json")
    response.delete_cookie(_SESSION_COOKIE, path="/")
    return response


@router.delete("/api/account")
def remove_account(user: User = Depends(current_user), session: Session = Depends(get_db)):
    delete_user(session, user)
    response = Response(content='{"ok":true}', media_type="application/json")
    response.delete_cookie(_SESSION_COOKIE, path="/")
    return response


@router.get("/api/journal/{week_start}/audio")
def journal_audio(week_start: date, user: User = Depends(current_user), session: Session = Depends(get_db)):
    audio = journal_audio_for(session, user, week_start)
    if not audio:
        raise HTTPException(status_code=404, detail="No narration for this week")
    return RawResponse(content=audio, media_type="audio/mpeg")


def database_ready() -> bool:
    try:
        get_engine()
        return True
    except RuntimeError:
        return False
