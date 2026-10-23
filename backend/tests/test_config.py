import pytest
from pydantic import ValidationError

from app.config import Settings, normalize_database_url
from app.db import get_engine


def test_render_postgres_url_uses_psycopg_dialect():
    raw = "postgresql://moss:secret@dpg-abc:5432/moss_garden"
    assert (
        normalize_database_url(raw)
        == "postgresql+psycopg://moss:secret@dpg-abc:5432/moss_garden"
    )


def test_legacy_postgres_scheme_uses_psycopg_dialect():
    raw = "postgres://moss:secret@localhost:5432/moss_garden"
    assert (
        normalize_database_url(raw)
        == "postgresql+psycopg://moss:secret@localhost:5432/moss_garden"
    )


def test_settings_defaults_keep_providers_off(monkeypatch):
    for name in (
        "AI_ENABLED",
        "AUDIO_ENABLED",
        "JOURNAL_NARRATION_ENABLED",
        "DATABASE_URL",
        "BACKBOARD_API_KEY",
        "BACKBOARD_MODEL_NAME",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.ai_enabled is False
    assert settings.audio_enabled is False
    assert settings.journal_narration_enabled is False
    assert settings.elevenlabs_monthly_char_cap == 3000
    assert settings.ai_daily_request_budget == 0
    assert settings.database_url is None
    assert settings.backboard_model_name is None
    assert settings.backboard_base_url == "https://app.backboard.io/api"


def test_blank_database_url_is_unset(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "  ")
    settings = Settings(_env_file=None)
    assert settings.database_url is None


def test_negative_ai_budget_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ai_daily_request_budget=-1)


def test_negative_narration_cap_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, elevenlabs_monthly_char_cap=-1)


def test_engine_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("app.db.get_settings", lambda: Settings(_env_file=None))
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        get_engine()
