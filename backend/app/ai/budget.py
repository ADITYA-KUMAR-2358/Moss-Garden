"""Daily model-call budget. The cap stops calls. Cached reads do not spend it."""

from datetime import date

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AiUsage


def reserve_request(session: Session, day: date, cap: int) -> bool:
    if cap <= 0:
        return False
    updated = session.execute(
        update(AiUsage)
        .where(AiUsage.day == day, AiUsage.request_count < cap)
        .values(request_count=AiUsage.request_count + 1)
    )
    if updated.rowcount:
        return True
    try:
        with session.begin_nested():
            session.add(AiUsage(day=day, request_count=1))
            session.flush()
    except IntegrityError:
        updated = session.execute(
            update(AiUsage)
            .where(AiUsage.day == day, AiUsage.request_count < cap)
            .values(request_count=AiUsage.request_count + 1)
        )
        return bool(updated.rowcount)
    return True
