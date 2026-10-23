"""Demo gardener. The same login is created once."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.game.quality import score_message
from app.models import CommitRecord, Repository, User
from app.services.garden import remember_projection

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


def seed_demo(session: Session, today=None) -> User:
    existing = session.scalar(select(User).where(User.login == "demo", User.is_demo.is_(True)))
    if existing is not None:
        return existing
    today = today or datetime.now(timezone.utc).date()
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
    for offset in range(15, -1, -1):
        if offset in quiet:
            continue
        message = _MESSAGES[slot % len(_MESSAGES)]
        scored = score_message(message)
        moment = datetime.combine(today - timedelta(days=offset), datetime.min.time(), timezone.utc)
        moment = moment.replace(hour=15)
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
