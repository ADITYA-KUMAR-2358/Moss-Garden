"""Database engine. Connections are created only when a caller asks for one."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_MISSING_DATABASE_URL = (
    "DATABASE_URL is required to open the database. "
    "Set it in the environment or in .env. "
    "Example: postgresql+psycopg://moss:moss@localhost:5432/moss_garden"
)
_engines: dict[str, Engine] = {}


def get_engine() -> Engine:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError(_MISSING_DATABASE_URL)
    url = settings.database_url
    if url not in _engines:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engines[url] = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    return _engines[url]


def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
