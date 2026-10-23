"""Demo gardener. The same login is created once."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.game.quality import score_message
from app.models import Badge, CommitRecord, GardenDay, Journal, Plant, Repository, User, XpLedger
from app.services.garden import remember_projection

# The demo keeps a recent-looking history so visitors never land on a garden frozen weeks ago.
DEMO_STALE_AFTER_DAYS = 2

_MESSAGES = (
    "Clarify the day boundary",
    "Add a regression test for quiet weeks",
    "Rename the helper",
    "Fix the empty-state copy",
    "Write the setup notes",
    "Adjust the maturity check",
    "Clean the session cookie path",
    "Add a regression test for duplicate commits",
    "Tighten the share text",
    "Fix the drought floor",
    "Document the weekly bonus",
    "Rename the plant stage labels",
    "Add a regression test for the daily cap",
    "Leave the soil as it is",
)


def _latest_demo_day(session: Session, user: User):
    latest = session.scalar(select(func.max(CommitRecord.committed_at)).where(CommitRecord.user_id == user.id))
    return latest.date() if latest else None


def _clear_demo(session: Session, user: User) -> None:
    for model in (Badge, Plant, GardenDay, XpLedger, Journal, CommitRecord, Repository):
        session.execute(delete(model).where(model.user_id == user.id))
    session.flush()


def seed_demo(session: Session, today=None) -> User:
    """Return the shared demo gardener, replanting its history when it has drifted into the past."""
    today = today or datetime.now(timezone.utc).date()
    user = session.scalar(select(User).where(User.login == "demo", User.is_demo.is_(True)))
    if user is not None:
        latest = _latest_demo_day(session, user)
        if latest is not None and latest >= today - timedelta(days=DEMO_STALE_AFTER_DAYS):
            return user
        _clear_demo(session, user)
    else:
        user = User(
            login="demo",
            display_name="Demo gardener",
            is_demo=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.flush()
    repository = Repository(
        user_id=user.id,
        github_repo_id=0,
        full_name="demo/garden",
        selected=True,
        accessible=True,
    )
    session.add(repository)
    session.flush()
    # 14 cared-for days inside a 16-day window, with two quiet days.
    quiet = {4, 9}
    slot = 0
    now = datetime.now(timezone.utc)
    for offset in range(15, -1, -1):
        if offset in quiet:
            continue
        message = _MESSAGES[slot % len(_MESSAGES)]
        scored = score_message(message)
        moment = datetime.combine(today - timedelta(days=offset), datetime.min.time(), timezone.utc)
        moment = min(moment.replace(hour=15), max(moment, now - timedelta(minutes=1)))
        session.add(
            CommitRecord(
                user_id=user.id,
                repository_id=repository.id,
                sha=f"demo{slot:02d}",
                committed_at=moment,
                message=message,
                quality=scored.weight,
                signals=",".join(scored.signals),
                quality_source="rules",
            )
        )
        slot += 1
    session.flush()
    remember_projection(session, user, today)
    return user
