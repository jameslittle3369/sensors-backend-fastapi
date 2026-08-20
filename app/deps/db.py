from collections.abc import Iterator

from sqlmodel import Session

from app.core.db import engine


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
