"""Broad checks for the game rules and the HTTP garden.

Each parameter is its own case. The sweep is meant to stay above 200 cases.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import (
    LEVEL_STEP,
    MATURITY_BLOOM_AT,
    VITALITY_FLOOR,
    VITALITY_MAX,
    XP_DAILY_CAP,
)
from app.game.engine import Activity, level_for_xp, level_threshold, project, season_for, stage_for
from app.game.journal import weekly_journal
from app.game.names import fallback_plant_copy
from app.game.quality import score_message
from app.main import app


def _commit(day: date, sha: str, quality: float = 1.0, signals=()):
    return Activity(
        repo_key="demo/garden",
        sha=sha,
        committed_at=datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc),
        quality=quality,
        signals=signals,
    )


@pytest.mark.parametrize("xp", range(0, 200))
def test_level_sits_between_its_thresholds(xp):
    level = level_for_xp(xp)
    assert 1 <= level <= 100
    assert level_threshold(level) <= xp
    if level < 100:
        assert xp < level_threshold(level + 1)
    assert level_threshold(level) == (0 if level <= 1 else LEVEL_STEP * (level - 1) * level // 2)


@pytest.mark.parametrize("month", range(1, 13))
def test_every_month_has_one_season(month):
    season = season_for(date(2026, month, 15))
    expected = {12: "frost", 1: "frost", 2: "frost", 3: "rain", 4: "rain", 5: "rain", 6: "sun", 7: "sun", 8: "sun"}.get(month, "leaf")
    assert season == expected


@pytest.mark.parametrize("maturity", list(range(0, 121, 5)))
def test_stage_bands_do_not_skip(maturity):
    stage = stage_for(maturity)
    if maturity >= 100:
        assert stage == "bloom"
    elif maturity >= 70:
        assert stage == "mature"
    elif maturity >= 30:
        assert stage == "young"
    else:
        assert stage == "sprout"


@pytest.mark.parametrize(
    ("message", "weight", "signals"),
    [
        ("", 0.35, ()),
        ("wip", 0.45, ()),
        ("update", 0.45, ()),
        ("fix", 0.45, ()),
        ("misc", 0.45, ()),
        (".", 0.45, ()),
        ("commit", 0.45, ()),
        ("Add regression test", 0.85, ("test",)),
        ("Update the spec", 0.85, ("test",)),
        ("Write the docs", 0.85, ("docs",)),
        ("Revise the readme", 0.85, ("docs",)),
        ("fix the retry", 0.85, ("fix",)),
        ("squash the bug", 0.85, ("fix",)),
        ("refactor the parser", 0.85, ("maintenance",)),
        ("clean the helper", 0.85, ("maintenance",)),
        ("Rename the helper", 0.7, ()),
        ("docker compose up", 0.7, ()),
        ("fixture stays local", 0.7, ()),
        ("special case for names", 0.7, ()),
        ("ab", 0.35, ()),
    ],
)
def test_quality_words_match_whole_words(message, weight, signals):
    scored = score_message(message)
    assert scored.weight == weight
    assert scored.signals == signals
    assert 0 <= scored.weight <= 1


@pytest.mark.parametrize("count", range(1, 21))
def test_one_day_never_pays_more_than_the_cap(count):
    day = date(2026, 6, 2)
    activities = [_commit(day, f"c{index:02d}") for index in range(count)]
    state = project(activities, day)
    assert state.xp <= XP_DAILY_CAP
    assert state.days[0].commit_count == count
    assert state.days[0].commit_xp <= XP_DAILY_CAP
    assert state.fresh is False
    assert state.badges[0] == "first-commit"


@pytest.mark.parametrize("gap", range(0, 31))
def test_vitality_never_falls_through_the_floor(gap):
    start = date(2026, 3, 1)
    state = project([_commit(start, "a")], start + timedelta(days=gap))
    assert VITALITY_FLOOR <= state.vitality <= VITALITY_MAX
    assert state.xp == 10
    assert state.plants[0].maturity == 8


@pytest.mark.parametrize("species", ["moss", "fern", "clover", "thyme", "camellia", "maple", "unknown"])
def test_fallback_names_are_stable(species):
    first = fallback_plant_copy(species, 3)
    second = fallback_plant_copy(species, 3)
    assert first == second
    assert isinstance(first, tuple)
    assert first[0]


@pytest.mark.parametrize("active,xp,blooms,quiet", [(0, 0, 0, 7), (3, 40, 1, 4), (7, 120, 0, 0), (1, 10, 0, 6)])
def test_journal_text_avoids_em_dashes(active, xp, blooms, quiet):
    text = weekly_journal(active_days=active, xp=xp, blooms=blooms, quiet_days=quiet)
    assert "—" not in text
    assert text.strip()


def test_future_commits_wait_until_their_day():
    today = date(2026, 10, 22)
    state = project([_commit(today + timedelta(days=3), "later")], today)
    assert state.xp == 0
    assert state.fresh is True
    assert state.plants == ()


def test_duplicate_sha_is_counted_once():
    day = date(2026, 10, 22)
    state = project([_commit(day, "same"), _commit(day, "same")], day)
    assert state.xp == 10
    assert len(state.awards) == 1


def test_same_sha_in_two_repos_both_count():
    day = date(2026, 10, 22)
    first = _commit(day, "same")
    second = Activity(first.repo_key.replace("demo", "other"), first.sha, first.committed_at, 1.0, ())
    state = project([first, second], day)
    assert state.xp == 15


@pytest.fixture
def garden_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'sweep.db'}")
    monkeypatch.setenv("SESSION_SECRET", "sweep-secret")
    monkeypatch.setenv("DEMO_SEED", "true")
    monkeypatch.setenv("AI_ENABLED", "false")
    monkeypatch.setenv("AUDIO_ENABLED", "false")
    with TestClient(app) as client:
        yield client


def test_health_and_logged_out_garden(garden_client):
    assert garden_client.get("/healthz").json() == {"status": "ok"}
    assert garden_client.get("/api/garden").status_code == 401
    assert garden_client.get("/api/repos").status_code == 401
    assert garden_client.post("/api/sync").status_code == 401


def test_demo_round_trip_fields(garden_client):
    assert garden_client.post("/api/demo/enter").status_code == 200
    body = garden_client.get("/api/garden").json()
    assert body["demo"] is True
    assert body["xp"] >= 0
    assert body["level"] >= 1
    assert body["vitality"] >= VITALITY_FLOOR
    assert body["season"] in {"frost", "rain", "sun", "leaf"}
    assert "—" not in body["journal"]["body"]
    assert body["share"]["intent_url"].startswith("https://twitter.com/intent/tweet?text=")
    assert isinstance(body["plants"], list)
    assert isinstance(body["badges"], list)
    assert body["audio"]["spring_level"] == 3
    for plant in body["plants"]:
        assert plant["stage"] in {"sprout", "young", "mature", "bloom"}
        assert 0 <= plant["maturity"] <= MATURITY_BLOOM_AT


def test_logout_closes_the_session(garden_client):
    garden_client.post("/api/demo/enter")
    assert garden_client.post("/api/logout").status_code == 200
    assert garden_client.get("/api/garden").status_code == 401


def test_bad_journal_audio_and_github_state(garden_client):
    garden_client.post("/api/demo/enter")
    assert garden_client.get("/api/journal/2026-10-19/audio").status_code == 404
    assert garden_client.get("/api/journal/not-a-date/audio").status_code == 422
    assert garden_client.get("/auth/github").status_code == 503
    assert garden_client.get("/auth/github/callback", params={"code": "x", "state": "y"}).status_code == 503


def test_icons_are_served(garden_client):
    for name in ("favicon.svg", "favicon.ico", "favicon-32.png", "apple-touch-icon.png"):
        response = garden_client.get(f"/{name}")
        assert response.status_code == 200, name
        assert response.content
