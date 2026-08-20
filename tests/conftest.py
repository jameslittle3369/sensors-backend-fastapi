import os

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine
from starlette.testclient import TestClient

import app.models  # noqa: F401 -- registers all tables on SQLModel.metadata
from app.deps.db import get_session
from app.main import app as fastapi_app

# A dedicated Postgres test database (needs the citext extension enabled,
# same as rpi4-db) -- NOT the production database. Point this at a local
# or scratch Postgres instance, e.g.:
#   createdb sensors_test && psql sensors_test -c 'CREATE EXTENSION citext'
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres@localhost/sensors_test"
)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def session(engine):
    # Each test runs inside an outer transaction that's rolled back at
    # the end, mirroring pytest-django's django_db isolation -- nothing
    # a test writes leaks into the next one.
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture
def client(session):
    fastapi_app.dependency_overrides[get_session] = lambda: session
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
