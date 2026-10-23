"""Create the demo garden without starting the server."""

from app.db import get_engine, get_sessionmaker
from app.models import Base
from app.services.seed import seed_demo


def main() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    session = get_sessionmaker()()
    try:
        user = seed_demo(session)
        session.commit()
        print(f"demo user {user.login} is ready")
    finally:
        session.close()


if __name__ == "__main__":
    main()
