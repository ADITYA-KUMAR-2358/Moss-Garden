"""Environment settings and the numeric game rules.

Every XP, cap, multiplier, and timing window lives in this module.
See docs/02-GAME-DESIGN.md.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Garden day boundaries use UTC. See docs/02-GAME-DESIGN.md.
GARDEN_TIMEZONE = "UTC"

XP_BASE = 10
XP_DAILY_CAP = 40
XP_ORDER_MULTIPLIERS = (1.0, 0.5, 0.25, 0.1)
XP_RUSH_COMMIT_COUNT = 8
WEEKLY_STEADY_DAYS = 4
WEEKLY_STEADY_BONUS_XP = 15

VITALITY_START = 30
VITALITY_MAX = 100
VITALITY_FLOOR = 20
VITALITY_DROUGHT_BELOW = 40
VITALITY_ACTIVE_GAIN = 12
VITALITY_REST_LOSS = 6
VITALITY_RECOVERY_FLOOR = 50

MATURITY_PER_ACTIVE_DAY = 8
MATURITY_YOUNG_AT = 30
MATURITY_MATURE_AT = 70
MATURITY_BLOOM_AT = 100

LEVEL_STEP = 40
BADGE_ACTIVE_DAYS = 7
BADGE_RETURN_GAP_DAYS = 7
BADGE_LEVELS = (3, 5)
AUDIO_SPRING_LEVEL = 3
AUDIO_RAIN_LEVEL = 4

GITHUB_HISTORY_DAYS = 90

PLANT_SPECIES = (
    {"id": "moss", "label": "Moss", "min_level": 1},
    {"id": "fern", "label": "Fern", "min_level": 2},
    {"id": "clover", "label": "Clover", "min_level": 3},
    {"id": "thyme", "label": "Thyme", "min_level": 4},
    {"id": "camellia", "label": "Camellia", "min_level": 5},
    {"id": "maple", "label": "Maple", "min_level": 6},
)

BADGE_LABELS = {
    "first-commit": "First sprout",
    "steady-week": "Steady week",
    "seven-days": "Seven cared-for days",
    "mature": "First mature plant",
    "bloom": "First bloom",
    "level-3": "Level 3",
    "level-5": "Level 5",
    "returned": "Came back",
    "caretaker": "Caretaker",
}

CARETAKER_SIGNALS = ("test", "docs", "fix", "maintenance")


def normalize_database_url(url: str) -> str:
    """Use the psycopg v3 SQLAlchemy dialect for PostgreSQL URLs.

    Render's connectionString uses postgresql://. SQLAlchemy treats that
    scheme as psycopg2 unless the driver is named explicitly.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "local"
    database_url: str | None = None

    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_app_slug: str | None = None
    github_oauth_callback_url: str | None = None
    # Kept for the existing Render deployment. Vercel uses the explicit callback URL.
    render_external_url: str | None = None

    backboard_api_key: str | None = None
    backboard_base_url: str = "https://app.backboard.io/api"
    backboard_llm_provider: str | None = None
    backboard_model_name: str | None = None

    ai_enabled: bool = False
    ai_daily_request_budget: int = 0
    ai_include_commit_messages: bool = False

    audio_enabled: bool = False
    journal_narration_enabled: bool = False
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None
    elevenlabs_model_id: str = "eleven_v4"
    elevenlabs_monthly_char_cap: int = 3000

    # read:user is read-only. public_repo would also grant write access to public repositories.
    github_scopes: str = "read:user"
    session_secret: str | None = None
    token_fernet_key: str | None = None
    sync_secret: str | None = None
    demo_seed: bool = True
    serve_frontend: bool = True

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("DATABASE_URL must be a string")
        stripped = value.strip()
        if stripped == "":
            return None
        return normalize_database_url(stripped)

    @field_validator("ai_daily_request_budget")
    @classmethod
    def _budget_cannot_be_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("AI_DAILY_REQUEST_BUDGET cannot be negative")
        return value

    @field_validator("elevenlabs_monthly_char_cap")
    @classmethod
    def _character_cap_cannot_be_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("ELEVENLABS_MONTHLY_CHAR_CAP cannot be negative")
        return value


def get_settings() -> Settings:
    return Settings()
