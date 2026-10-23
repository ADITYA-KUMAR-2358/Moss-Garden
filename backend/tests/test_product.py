import json
from datetime import date, datetime, timezone

import pytest
from io import BytesIO
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.ai.budget import reserve_request
from app.ai.schema import parse_quality_payload
from app.config import Settings
from app.db import get_engine
from app.integrations.backboard import BackboardLLMClient
from app.integrations.github import eligible_commit, parse_next_link
from app.models import AiUsage, Base, CommitRecord, UsageLog, User, XpLedger
from app.integrations.elevenlabs import ElevenLabsError, generate_sound
from app.services.garden import journal_audio_for, remember_projection, store_candidates
from app.services.seed import seed_demo
from app.integrations.github import CommitCandidate
from app.models import Repository


def _session(tmp_path):
    url = f"sqlite:///{tmp_path / 'garden.db'}"
    engine = get_engine.__wrapped__ if False else None
    from app.db import _engines
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker as maker

    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return maker(bind=engine, expire_on_commit=False)()


def test_duplicate_candidates_do_not_double_xp(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "false")
    session = _session(tmp_path)
    user = seed_demo(session, today=date(2026, 10, 21))
    before = session.scalar(select(func.sum(XpLedger.amount)))
    repository = session.scalar(select(Repository))
    again = [
        CommitCandidate(
            sha="demo00",
            message="Clarify the day boundary",
            committed_at=datetime(2026, 10, 6, 15, tzinfo=timezone.utc),
        )
    ]
    assert store_candidates(session, user, repository, again, None) == 0
    remember_projection(session, user, date(2026, 10, 21))
    after = session.scalar(select(func.sum(XpLedger.amount)))
    assert after == before
    assert session.scalar(select(func.count(CommitRecord.id))) == 14


def test_budget_blocks_and_cache_does_not_spend(tmp_path):
    session = _session(tmp_path)
    today = date(2026, 10, 21)
    assert reserve_request(session, today, 0) is False
    assert reserve_request(session, today, 1) is True
    assert reserve_request(session, today, 1) is False
    session.commit()
    assert session.get(AiUsage, today).request_count == 1

    calls = []

    def transport(url, headers, body):
        calls.append(body)
        return 200, {"content": json.dumps({"quality": 0.8, "signals": ["test"], "note": "tests"})}

    settings = Settings(
        _env_file=None,
        ai_enabled=True,
        ai_daily_request_budget=2,
        backboard_api_key="test-key",
        backboard_llm_provider="openrouter",
        backboard_model_name="google/gemma-4-E4B-it",
    )
    client = BackboardLLMClient(settings, session, today, transport)
    first = client.complete_json(cache_key="one", prompt="hello")
    second = client.complete_json(cache_key="one", prompt="hello")
    assert first == second
    assert len(calls) == 1
    assert calls[0]["llm_provider"] == "openrouter"
    assert calls[0]["model_name"] == "google/gemma-4-E4B-it"
    assert "gpt-4o" not in json.dumps(calls[0])


def test_ai_disabled_and_missing_model_do_not_call(tmp_path):
    session = _session(tmp_path)
    calls = []
    settings = Settings(
        _env_file=None,
        ai_enabled=False,
        ai_daily_request_budget=5,
        backboard_api_key="test-key",
        backboard_llm_provider="google",
        backboard_model_name="google/gemma-4-E4B-it",
    )
    client = BackboardLLMClient(settings, session, date(2026, 10, 21), lambda *args: calls.append(args))
    assert client.complete_json(cache_key="x", prompt="y") is None
    settings.ai_enabled = True
    settings.backboard_model_name = None
    assert client.complete_json(cache_key="x", prompt="y") is None
    assert calls == []


def test_invalid_model_json_is_rejected():
    assert parse_quality_payload({"quality": 2, "signals": []}) is None
    assert parse_quality_payload({"quality": 0.4, "signals": ["nope"]}) is None
    parsed = parse_quality_payload({"quality": 0, "signals": ["uncertain"], "note": "unsure"})
    assert parsed is not None
    assert parsed.weight == 0
    assert parsed.source == "model"


def test_github_parser_skips_merges_and_other_authors():
    own = {
        "sha": "abc",
        "parents": [{}],
        "author": {"login": "ada"},
        "commit": {"message": "Fix the gate", "author": {"date": "2026-10-01T00:00:00Z"}},
    }
    merge = dict(own, parents=[{}, {}], sha="def")
    other = dict(own, author={"login": "grace"}, sha="ghi")
    assert eligible_commit(own, "ada").sha == "abc"
    assert eligible_commit(merge, "ada") is None
    assert eligible_commit(other, "ada") is None
    assert parse_next_link('<https://api.github.com/x?page=2>; rel="next"') == "https://api.github.com/x?page=2"


def test_runtime_package_does_not_name_closed_model_hosts():
    text = "\n".join(path.read_text(encoding="utf-8") for path in Path("app").rglob("*.py"))
    assert "generativelanguage.googleapis.com" not in text
    assert "api.x.ai" not in text
    assert "gpt-4o" not in text


def test_sound_generation_rejects_a_duration_outside_the_documented_range():
    with pytest.raises(ElevenLabsError):
        generate_sound("test-key", "soft rain", duration_seconds=0.1)
    with pytest.raises(ElevenLabsError):
        generate_sound("test-key", "soft rain", prompt_influence=1.5)


def test_narration_is_skipped_over_the_monthly_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIO_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "CalmVoice1")
    monkeypatch.setenv("ELEVENLABS_MONTHLY_CHAR_CAP", "0")
    session = _session(tmp_path)
    user = seed_demo(session, today=date(2026, 10, 21))
    called = []
    monkeypatch.setattr("app.integrations.elevenlabs.narrate", lambda *args, **kwargs: called.append(args) or b"mp3")
    view = remember_projection(session, user, date(2026, 10, 21))
    assert called == []
    assert view["journal"]["audio"] is False


def test_narration_is_stored_once_per_week(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIO_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "CalmVoice1")
    monkeypatch.setenv("ELEVENLABS_MONTHLY_CHAR_CAP", "3000")
    session = _session(tmp_path)
    user = seed_demo(session, today=date(2026, 10, 21))
    called = []

    def narrate(_api_key, _voice_id, text):
        called.append(text)
        return b"mp3-bytes"

    monkeypatch.setattr("app.integrations.elevenlabs.narrate", narrate)
    first = remember_projection(session, user, date(2026, 10, 21))
    second = remember_projection(session, user, date(2026, 10, 21))
    assert first["journal"]["audio"] is True
    assert second["journal"]["audio"] is True
    assert len(called) == 1
    spent = session.scalar(select(func.sum(UsageLog.characters)).where(UsageLog.purpose == "tts"))
    assert spent == len(called[0])
    audio = journal_audio_for(session, user, date.fromisoformat(first["journal"]["week_start"]))
    assert audio == b"mp3-bytes"
