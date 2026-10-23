import time
from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_sessionmaker
from app.integrations.github import CommitCandidate, RepoCandidate
from app.main import CONTENT_SECURITY_POLICY, create_app
from app.models import AiCache, User
from app.security import SESSION_MAX_AGE, decrypt_token, read_user_id, sign_user_id


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'security.db'}")
    monkeypatch.setenv("SESSION_SECRET", "security-secret")
    monkeypatch.setenv("DEMO_SEED", "true")
    monkeypatch.setenv("AI_ENABLED", "false")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "")
    monkeypatch.setenv("ENVIRONMENT", "local")
    return monkeypatch


def test_session_cookie_round_trip(env):
    assert read_user_id(sign_user_id(7)) == 7


@pytest.mark.parametrize(
    "cookie",
    [None, "", "7", "7.abc", "x.1.sig", "7.x.sig", "7.1.2.3", "7." + "1" * 300 + ".sig"],
)
def test_malformed_session_cookies_are_rejected(env, cookie):
    assert read_user_id(cookie) is None


def test_forged_and_legacy_cookies_are_rejected(env):
    good = sign_user_id(7)
    user, issued, signature = good.split(".")
    assert read_user_id(f"8.{issued}.{signature}") is None
    assert read_user_id(f"{user}.{int(issued) + 1}.{signature}") is None
    legacy = good.rsplit(".", 2)[0] + "." + signature
    assert read_user_id(legacy) is None


def test_session_expires_after_thirty_days(env):
    issued = int(time.time()) - SESSION_MAX_AGE - 10
    assert read_user_id(sign_user_id(7, issued_at=issued)) is None
    fresh = int(time.time()) - SESSION_MAX_AGE + 60
    assert read_user_id(sign_user_id(7, issued_at=fresh)) == 7


def test_cookie_signed_with_another_secret_is_rejected(env):
    cookie = sign_user_id(7)
    env.setenv("SESSION_SECRET", "a-different-secret")
    assert read_user_id(cookie) is None


def test_unreadable_token_becomes_a_clear_error(env):
    env.setenv("TOKEN_FERNET_KEY", Fernet.generate_key().decode())
    other = Fernet(Fernet.generate_key()).encrypt(b"token").decode()
    with pytest.raises(RuntimeError, match="Sign in with GitHub again"):
        decrypt_token(other)


def test_security_headers_on_every_response(env):
    with TestClient(create_app()) as client:
        for path in ("/healthz", "/api/auth/status", "/api/garden"):
            headers = client.get(path).headers
            assert headers["x-content-type-options"] == "nosniff"
            assert headers["x-frame-options"] == "DENY"
            assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
            assert "camera=()" in headers["permissions-policy"]
        assert client.get("/api/auth/status").headers["cache-control"] == "no-store"
        assert "content-security-policy" not in client.get("/healthz").headers


def test_production_hides_api_docs_and_adds_csp_and_hsts(env):
    env.setenv("ENVIRONMENT", "production")
    with TestClient(create_app()) as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404
        headers = client.get("/healthz").headers
        assert headers["content-security-policy"] == CONTENT_SECURITY_POLICY
        assert "frame-ancestors 'none'" in CONTENT_SECURITY_POLICY
        assert "script-src 'self'" in CONTENT_SECURITY_POLICY
        assert headers["strict-transport-security"].startswith("max-age=31536000")


def test_local_keeps_api_docs(env):
    with TestClient(create_app()) as client:
        assert client.get("/docs").status_code == 200


def test_demo_garden_cannot_be_deleted(env):
    with TestClient(create_app()) as client:
        client.post("/api/demo/enter")
        assert client.delete("/api/account").status_code == 403
        assert client.get("/api/garden").status_code == 200


class FakeGitHub:
    profile = {"id": 77, "login": "grace", "name": "Grace " + "H" * 300}

    def __init__(self, token):
        self.token = token

    def _request(self, url):
        return 200, self.profile, None

    def current_login(self):
        return self.profile["login"]

    def list_repos(self):
        return [RepoCandidate(9, "grace/moss", False)]

    def iter_commits(self, full_name, login, since):
        yield [CommitCandidate("c" * 40, "docs: tidy", datetime.now(timezone.utc))]


def sign_in(client):
    client.get("/auth/github", follow_redirects=False)
    state = client.cookies.get("moss_oauth_state")
    return client.get("/auth/github/callback", params={"code": "c", "state": state}, follow_redirects=False)


@pytest.fixture
def player_env(env):
    env.setenv("GITHUB_CLIENT_ID", "app-client")
    env.setenv("GITHUB_CLIENT_SECRET", "app-secret")
    env.setenv("TOKEN_FERNET_KEY", Fernet.generate_key().decode())
    env.setattr("app.api.routes.exchange_code", lambda **_kwargs: "player-token")
    env.setattr("app.api.routes.GitHubClient", FakeGitHub)
    env.setattr("app.api.routes._last_sync", {})
    return env


def test_callback_trims_long_names_and_reuses_the_account(player_env):
    with TestClient(create_app()) as client:
        assert sign_in(client).status_code == 307
        assert sign_in(client).status_code == 307
        session = get_sessionmaker()()
        try:
            users = session.scalars(select(User).where(User.is_demo.is_(False))).all()
            assert len(users) == 1
            assert len(users[0].display_name) == 120
            assert users[0].github_id == 77
        finally:
            session.close()


@pytest.mark.parametrize("profile", [{}, {"login": "grace"}, {"id": 77}, ["not", "a", "dict"]])
def test_callback_refuses_a_profile_without_id_or_login(player_env, profile):
    player_env.setattr(FakeGitHub, "profile", profile)
    with TestClient(create_app()) as client:
        response = sign_in(client)
        assert response.status_code == 502
        assert "moss_session" not in response.headers.get("set-cookie", "")


def test_callback_hides_github_error_details(player_env):
    from app.integrations.github import GitHubError

    def broken(**_kwargs):
        raise GitHubError("bad_verification_code secret-looking-detail")

    player_env.setattr("app.api.routes.exchange_code", broken)
    with TestClient(create_app()) as client:
        response = sign_in(client)
        assert response.status_code == 502
        assert "secret-looking-detail" not in response.text


def test_callback_rejects_a_mismatched_state(player_env):
    with TestClient(create_app()) as client:
        client.get("/auth/github", follow_redirects=False)
        response = client.get("/auth/github/callback", params={"code": "c", "state": "forged"}, follow_redirects=False)
        assert response.status_code == 400


def test_sync_has_a_cooldown(player_env):
    with TestClient(create_app()) as client:
        sign_in(client)
        player_env.setattr("app.api.routes._last_sync", {})
        assert client.post("/api/sync").status_code == 200
        again = client.post("/api/sync")
        assert again.status_code == 429
        assert "Try again in" in again.json()["detail"]


def test_sync_with_an_unreadable_token_asks_to_sign_in_again(player_env):
    with TestClient(create_app()) as client:
        sign_in(client)
        player_env.setenv("TOKEN_FERNET_KEY", Fernet.generate_key().decode())
        player_env.setattr("app.api.routes._last_sync", {})
        response = client.post("/api/sync")
        assert response.status_code == 409
        assert "Sign in with GitHub again" in response.json()["detail"]


def test_deleting_an_account_clears_its_ai_cache(player_env):
    with TestClient(create_app()) as client:
        sign_in(client)
        session = get_sessionmaker()()
        try:
            user_id = session.scalar(select(User.id).where(User.github_id == 77))
            for key in (f"name:{user_id}:1:moss", f"journal:{user_id}:2026-W43:1:7:1", "name:999:1:moss"):
                session.add(AiCache(cache_key=key, payload="{}", created_at=datetime.now(timezone.utc)))
            session.commit()
        finally:
            session.close()
        assert client.delete("/api/account").status_code == 200
        session = get_sessionmaker()()
        try:
            remaining = set(session.scalars(select(AiCache.cache_key)).all())
            assert remaining == {"name:999:1:moss"}
        finally:
            session.close()


def test_api_routes_need_a_session(env):
    with TestClient(create_app()) as client:
        for method, path in (
            ("get", "/api/garden"),
            ("get", "/api/repos"),
            ("post", "/api/sync"),
            ("get", "/api/export"),
            ("delete", "/api/account"),
            ("get", "/api/journal/2026-10-19/audio"),
        ):
            assert getattr(client, method)(path).status_code == 401, path
        assert client.post("/api/preferences", json={"ai": True}).status_code == 401
        assert client.post("/api/repos", json={"full_names": []}).status_code == 401


def test_cross_site_writes_are_refused(env):
    with TestClient(create_app()) as client:
        client.post("/api/demo/enter")
        evil = {"Origin": "https://evil.example"}
        assert client.post("/api/logout", headers=evil).status_code == 403
        assert client.delete("/api/account", headers=evil).status_code == 403
        assert client.post("/api/demo/enter", headers=evil).status_code == 403
        same = {"Origin": "http://testserver"}
        assert client.post("/api/logout", headers=same).status_code == 200
        assert client.get("/api/auth/status", headers=evil).status_code == 200


def test_demo_garden_is_replanted_when_it_drifts_into_the_past(env):
    from datetime import date, timedelta

    from app.models import CommitRecord
    from app.services.seed import seed_demo

    with TestClient(create_app()):
        session = get_sessionmaker()()
        try:
            old = date.today() - timedelta(days=40)
            user = seed_demo(session, today=old)
            session.commit()
            first_id = user.id
            again = seed_demo(session, today=date.today())
            session.commit()
            latest = max(row.committed_at for row in session.scalars(select(CommitRecord).where(CommitRecord.user_id == again.id)))
            assert again.id == first_id
            assert latest.date() >= date.today() - timedelta(days=1)
            assert len(session.scalars(select(CommitRecord).where(CommitRecord.user_id == again.id)).all()) == 14
        finally:
            session.close()


def test_nightly_job_rejects_missing_and_wrong_secrets(env):
    env.setenv("SYNC_SECRET", "night-key")
    with TestClient(create_app()) as client:
        assert client.post("/api/jobs/nightly").status_code == 401
        assert client.post("/api/jobs/nightly", headers={"Authorization": "night-key-but-longer"}).status_code == 401
        assert client.post("/api/jobs/nightly", headers={"Authorization": "Bearer "}).status_code == 401
