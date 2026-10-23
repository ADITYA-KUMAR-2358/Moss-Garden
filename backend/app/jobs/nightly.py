"""Scheduled sync. Running it twice does not award the same commit twice."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import get_sessionmaker
from app.integrations.github import GitHubClient
from app.models import User
from app.security import decrypt_token
from app.services.garden import sync_repositories

logger = logging.getLogger(__name__)


def run_nightly() -> None:
    session = get_sessionmaker()()
    try:
        users = session.scalars(select(User).where(User.is_demo.is_(False), User.token_encrypted.is_not(None))).all()
        today = datetime.now(timezone.utc).date()
        for user in users:
            try:
                token = decrypt_token(user.token_encrypted or "")
                sync_repositories(session, user, GitHubClient(token), today)
            except Exception:
                logger.exception("sync failed for user %s", user.id)
                session.rollback()
    finally:
        session.close()
