"""Persistent rows. The game projection can be rebuilt from commits."""

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int | None] = mapped_column(unique=True)
    login: Mapped[str] = mapped_column(String(80))
    display_name: Mapped[str] = mapped_column(String(120))
    token_encrypted: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("user_id", "github_repo_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    github_repo_id: Mapped[int]
    full_name: Mapped[str] = mapped_column(String(200))
    selected: Mapped[bool] = mapped_column(default=False)
    accessible: Mapped[bool] = mapped_column(default=True)


class CommitRecord(Base):
    __tablename__ = "commits"
    __table_args__ = (UniqueConstraint("repository_id", "sha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"))
    sha: Mapped[str] = mapped_column(String(40))
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    message: Mapped[str] = mapped_column(Text)
    quality: Mapped[float]
    signals: Mapped[str] = mapped_column(String(200), default="")
    quality_source: Mapped[str] = mapped_column(String(20))


class XpLedger(Base):
    __tablename__ = "xp_ledger"
    __table_args__ = (CheckConstraint("amount >= 0", name="xp_amount_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    source_key: Mapped[str] = mapped_column(String(220), unique=True)
    amount: Mapped[int]
    reason: Mapped[str] = mapped_column(String(40))
    day: Mapped[date] = mapped_column(Date)


class GardenDay(Base):
    __tablename__ = "garden_days"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    day: Mapped[date] = mapped_column(Date)
    commit_count: Mapped[int]
    commit_xp: Mapped[int]
    bonus_xp: Mapped[int]
    rush: Mapped[bool] = mapped_column(default=False)


class Plant(Base):
    __tablename__ = "plants"
    __table_args__ = (UniqueConstraint("user_id", "slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    slot: Mapped[int]
    species: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(200))
    name_source: Mapped[str] = mapped_column(String(20))
    maturity: Mapped[int]
    planted_on: Mapped[date] = mapped_column(Date)


class Badge(Base):
    __tablename__ = "badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    badge_id: Mapped[str] = mapped_column(String(40))
    earned_on: Mapped[date] = mapped_column(Date)


class Journal(Base):
    __tablename__ = "journals"
    __table_args__ = (UniqueConstraint("user_id", "week_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    week_key: Mapped[str] = mapped_column(String(12))
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))
    week_start: Mapped[date | None] = mapped_column(Date)


class JournalAudio(Base):
    __tablename__ = "journal_audio"
    __table_args__ = (UniqueConstraint("user_id", "week_start", name="uq_journal_audio_week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    week_start: Mapped[date] = mapped_column(Date)
    voice_id: Mapped[str] = mapped_column(String(80))
    audio: Mapped[bytes] = mapped_column(LargeBinary)


class UsageLog(Base):
    __tablename__ = "usage_log"
    __table_args__ = (CheckConstraint("characters >= 0", name="usage_characters_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    purpose: Mapped[str] = mapped_column(String(20))
    characters: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AiCache(Base):
    __tablename__ = "ai_cache"

    cache_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AiUsage(Base):
    __tablename__ = "ai_usage"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    request_count: Mapped[int] = mapped_column(default=0)
