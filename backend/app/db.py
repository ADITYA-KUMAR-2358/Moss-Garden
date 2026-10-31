"""Database engine. Connections are created only when a caller asks for one."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

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
        if url.startswith("sqlite"):
            _engines[url] = create_engine(
                url,
                pool_pre_ping=True,
                connect_args={"check_same_thread": False},
            )
        else:
            # Vercel may run many short-lived function instances. Do not retain
            # idle connections in each instance and exhaust the Postgres limit.
            _engines[url] = create_engine(url, poolclass=NullPool, pool_pre_ping=True)
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
