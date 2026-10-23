from datetime import date, datetime, timedelta, timezone

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.integrations.github import CommitCandidate, RepoCandidate
from app.main import app


def test_demo_garden_is_stable_and_hides_private_details(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'demo.db'}")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("DEMO_SEED", "true")
    monkeypatch.setenv("AI_ENABLED", "false")
    monkeypatch.setenv("AUDIO_ENABLED", "false")
    monkeypatch.setenv("JOURNAL_NARRATION_ENABLED", "false")

    with TestClient(app) as client:
        health = client.get("/healthz")
        assert health.status_code == 200
        entered = client.post("/api/demo/enter")
        assert entered.status_code == 200
        first = client.get("/api/garden")
        second = client.get("/api/garden")
        assert first.status_code == 200
        assert second.json()["xp"] == first.json()["xp"]
        assert second.json()["xp"] > 0
        body = second.json()
        assert "demo/garden" not in body["share"]["text"]
        assert body["share"]["intent_url"].startswith("https://twitter.com/intent/tweet?text=")
        assert "—" not in body["journal"]["body"]
        assert body["journal"]["audio"] is False
        assert body["badges"] and all(len(badge["earned_on"]) == 10 for badge in body["badges"])
        profile = body["profile"]
        assert profile["avatar_url"] is None and profile["github_url"] is None
        assert profile["commits"] > 0 and profile["active_days"] > 0
        assert profile["member_since"] and profile["first_commit_day"]
        assert body["journal"]["week_start"]
        week = date.today() - timedelta(days=date.today().weekday())
        refused = client.get(f"/api/journal/{week.isoformat()}/audio")
        assert refused.status_code == 404
        refused_delete = client.delete("/api/account")
        assert refused_delete.status_code == 403
        assert client.get("/api/garden").status_code == 200


def test_github_status_is_off_until_the_app_is_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'auth.db'}")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "")
    monkeypatch.setenv("TOKEN_FERNET_KEY", "")
    with TestClient(app) as client:
        status = client.get("/api/auth/status")
        assert status.status_code == 200
        assert status.json() == {"github": False, "setup": True}
        assert client.get("/auth/github").status_code == 503
        setup = client.get("/auth/github/setup")
        assert setup.status_code == 200
        assert "https://github.com/settings/apps/new" in setup.text
        assert '\\"public\\": true' in setup.text
        assert "hook_attributes" not in setup.text
        assert "http://localhost:5173/auth/github/callback" in setup.text
        assert "moss_setup_state" in setup.headers.get("set-cookie", "")
        assert client.get("/auth/github/setup/callback", params={"code": "nope"}).status_code == 400


def test_production_github_sign_in_uses_the_render_address(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'render.db'}")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://moss-garden-api.onrender.com")
    monkeypatch.setenv("GITHUB_OAUTH_CALLBACK_URL", "")
    monkeypatch.setenv("GITHUB_SCOPES", "read:user")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "")
    monkeypatch.setenv("TOKEN_FERNET_KEY", "")
    with TestClient(app) as client:
        assert client.get("/api/auth/status").json() == {"github": False, "setup": False}
        assert client.get("/auth/github/setup").status_code == 404
        assert client.get("/auth/github/setup/callback", params={"code": "x"}).status_code == 404
        page = client.get("/auth/github", headers={"Accept": "text/html"}, follow_redirects=False)
        assert page.headers["location"] == "/?github=off"
        assert client.get("/auth/github").status_code == 503

        monkeypatch.setenv("GITHUB_CLIENT_ID", "live-client")
        monkeypatch.setenv("GITHUB_CLIENT_SECRET", "live-secret")
        monkeypatch.setenv("TOKEN_FERNET_KEY", Fernet.generate_key().decode())
        assert client.get("/api/auth/status").json() == {"github": True, "setup": False}
        start = client.get("/auth/github", follow_redirects=False)
        target = start.headers["location"]
        assert "redirect_uri=https%3A%2F%2Fmoss-garden-api.onrender.com%2Fauth%2Fgithub%2Fcallback" in target
        assert "scope=read%3Auser" in target
        assert "public_repo" not in target

        monkeypatch.setenv("GITHUB_OAUTH_CALLBACK_URL", "http://localhost:5173/auth/github/callback")
        target = client.get("/auth/github", follow_redirects=False).headers["location"]
        assert "localhost" not in target
        assert "redirect_uri=https%3A%2F%2Fmoss-garden-api.onrender.com%2Fauth%2Fgithub%2Fcallback" in target

        monkeypatch.setenv("RENDER_EXTERNAL_URL", "")
        target = client.get(
            "/auth/github",
            headers={"host": "moss-garden-api.onrender.com", "x-forwarded-proto": "https"},
            follow_redirects=False,
        ).headers["location"]
        assert "redirect_uri=https%3A%2F%2Fmoss-garden-api.onrender.com%2Fauth%2Fgithub%2Fcallback" in target


def test_a_player_signs_in_with_their_github_account(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'player.db'}")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "app-client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "app-secret")
    monkeypatch.setenv("TOKEN_FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("DEMO_SEED", "false")
    monkeypatch.setenv("AI_ENABLED", "false")

    class PlayerGitHub:
        def __init__(self, token):
            assert token == "player-token"

        def current_login(self):
            return "ada"

        def _request(self, url):
            return 200, {"id": 42, "login": "ada", "name": "Ada"}, None

        def list_repos(self):
            return [
                RepoCandidate(7, "ada/moss", False),
                RepoCandidate(8, "other/lib", False),
            ]

        def iter_commits(self, full_name, login, since):
            if full_name != "ada/moss":
                yield []
                return
            yield [CommitCandidate("a" * 40, "grow the moss", datetime.now(timezone.utc))]

    monkeypatch.setattr("app.api.routes.exchange_code", lambda **_kwargs: "player-token")
    monkeypatch.setattr("app.api.routes.GitHubClient", PlayerGitHub)

    with TestClient(app) as client:
        start = client.get("/auth/github", follow_redirects=False)
        assert start.status_code == 307
        assert start.headers["location"].startswith("https://github.com/login/oauth/authorize?")
        assert "client_id=app-client" in start.headers["location"]
        state = client.cookies.get("moss_oauth_state")
        done = client.get(
            "/auth/github/callback",
            params={"code": "from-ada", "state": state},
            follow_redirects=False,
        )
        assert done.status_code == 307
        assert done.headers["location"] == "/#garden"
        garden = client.get("/api/garden")
        assert garden.status_code == 200
        body = garden.json()
        assert body["login"] == "ada"
        assert body["demo"] is False
        assert body["xp"] > 0
        assert body["profile"]["avatar_url"] == "https://github.com/ada.png?size=160"
        assert body["profile"]["github_url"] == "https://github.com/ada"
        assert body["profile"]["commits"] == 1
        assert body["profile"]["repos"] == 1
        repos = client.get("/api/repos").json()["repos"]
        selected = [row["full_name"] for row in repos if row["selected"]]
        assert selected == ["ada/moss"]


def test_nightly_sync_needs_the_shared_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'nightly.db'}")
    monkeypatch.setenv("DEMO_SEED", "false")
    started = []
    monkeypatch.setattr("app.api.routes.start_nightly", lambda: started.append(1) or len(started) == 1)

    with TestClient(app) as client:
        monkeypatch.setenv("SYNC_SECRET", "")
        assert client.post("/api/jobs/nightly").status_code == 503
        monkeypatch.setenv("SYNC_SECRET", "night-key")
        assert client.post("/api/jobs/nightly").status_code == 401
        assert client.post("/api/jobs/nightly", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert started == []
        first = client.post("/api/jobs/nightly", headers={"Authorization": "Bearer night-key"})
        assert first.status_code == 202
        assert first.json() == {"status": "started"}
        again = client.post("/api/jobs/nightly", headers={"Authorization": "Bearer night-key"})
        assert again.json() == {"status": "running"}


def test_logged_out_garden_asks_for_a_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'logged-out.db'}")
    monkeypatch.setenv("DEMO_SEED", "false")
    with TestClient(app) as client:
        assert client.get("/api/garden").status_code == 401
