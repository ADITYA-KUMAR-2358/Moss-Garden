from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.ai.schema import parse_journal_payload
from app.integrations.github import CommitCandidate, RepoCandidate
from app.main import app


class PlayerGitHub:
    def __init__(self, token):
        self.token = token

    def current_login(self):
        return "ada"

    def _request(self, url):
        return 200, {"id": 42, "login": "ada", "name": "Ada"}, None

    def list_repos(self):
        return [RepoCandidate(7, "ada/moss", False)]

    def iter_commits(self, full_name, login, since):
        now = datetime.now(timezone.utc)
        yield [
            CommitCandidate("a" * 40, "docs: grow the moss", now),
            CommitCandidate("b" * 40, "test: cover the fern", now),
        ]


def fake_model(url, headers, body):
    prompt = body["content"]
    if "Name a garden plant" in prompt:
        return 200, {"content": {"name": "Quiet Lantern", "description": "A slow light by the stones."}}
    if "journal" in prompt:
        assert "ada/moss" not in prompt
        return 200, {"content": {"body": "Two cared-for days this week. The moss settled \u2014 nothing was rushed."}}
    return 500, {}


@pytest.fixture
def player(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ai.db'}")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "app-client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "app-secret")
    monkeypatch.setenv("TOKEN_FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("DEMO_SEED", "true")
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("AI_DAILY_REQUEST_BUDGET", "20")
    monkeypatch.setenv("AI_INCLUDE_COMMIT_MESSAGES", "false")
    monkeypatch.setenv("BACKBOARD_API_KEY", "test-key")
    monkeypatch.setenv("BACKBOARD_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("BACKBOARD_MODEL_NAME", "google/gemma-4-26b-a4b-it")
    monkeypatch.setattr("app.api.routes.exchange_code", lambda **_kwargs: "player-token")
    monkeypatch.setattr("app.api.routes.GitHubClient", PlayerGitHub)
    monkeypatch.setattr("app.api.routes._last_sync", {})
    monkeypatch.setattr("app.integrations.backboard._default_transport", fake_model)
    with TestClient(app) as client:
        client.get("/auth/github", follow_redirects=False)
        state = client.cookies.get("moss_oauth_state")
        client.get("/auth/github/callback", params={"code": "c", "state": state}, follow_redirects=False)
        assert client.post("/api/sync").status_code == 200
        yield client


def test_ai_is_off_until_the_gardener_turns_it_on(player):
    body = player.get("/api/garden").json()
    assert body["ai"] == {
        "available": True,
        "enabled": False,
        "model": "Gemma 4, an open-weight model, through Backboard",
        "can_change": True,
    }
    assert body["journal"]["source"] == "rules"
    assert all(plant["name_source"] != "model" for plant in body["plants"])


def test_turning_ai_on_names_plants_and_writes_the_journal(player):
    turned = player.post("/api/preferences", json={"ai": True})
    assert turned.status_code == 200
    assert turned.json()["ai"] is True
    assert turned.json()["journal"] is True
    body = player.get("/api/garden").json()
    assert body["ai"]["enabled"] is True
    assert body["journal"]["source"] == "model"
    assert "\u2014" not in body["journal"]["body"]
    assert body["journal"]["body"].startswith("Two cared-for days this week.")
    assert any(plant["name"] == "Quiet Lantern" and plant["name_source"] == "model" for plant in body["plants"])

    off = player.post("/api/preferences", json={"ai": False})
    assert off.json()["ai"] is False
    assert player.get("/api/garden").json()["journal"]["source"] == "rules"


def test_ai_cannot_be_turned_on_when_the_server_has_no_model(player, monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "false")
    refused = player.post("/api/preferences", json={"ai": True})
    assert refused.status_code == 409
    assert player.get("/api/garden").json()["ai"]["available"] is False


def test_demo_garden_settings_stay_fixed(player):
    player.post("/api/demo/enter")
    assert player.get("/api/garden").json()["ai"]["can_change"] is False
    assert player.post("/api/preferences", json={"ai": True}).status_code == 403


def test_export_has_the_whole_garden_and_no_token(player):
    response = player.get("/api/export")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    data = response.json()
    assert data["format"] == "moss-garden-export"
    assert data["gardener"]["login"] == "ada"
    assert {row["sha"] for row in data["commits"]} == {"a" * 40, "b" * 40}
    assert data["repositories"][0]["full_name"] == "ada/moss"
    assert data["plants"] and data["xp_ledger"] and data["journals"]
    assert "token" not in response.text.lower()


def test_home_page_is_revalidated_after_each_deploy(player):
    page = player.get("/")
    if page.status_code == 503:
        pytest.skip("frontend build is missing")
    assert page.headers["cache-control"] == "no-cache"


def test_export_needs_a_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'nobody.db'}")
    with TestClient(app) as client:
        assert client.get("/api/export").status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"body": 3},
        {"body": "too short"},
        {"body": "Keep your streak alive, the garden is waiting for you today."},
        {"body": "See https://example.com for more about this calm little week."},
        {"body": "x" * 701},
    ],
)
def test_journal_payload_rejects_unsafe_text(payload):
    assert parse_journal_payload(payload) is None


def test_journal_payload_removes_dashes():
    assert parse_journal_payload({"body": "A quiet week \u2014 the fern held still and nothing was lost."}) == (
        "A quiet week, the fern held still and nothing was lost."
    )
