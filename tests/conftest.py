import pytest

from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.dependencies.database import get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)

TestingSessionLocal = sessionmaker(
    autoflush=False,
    autocommit = False,
    bind=engine
)

def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


reset_database()


def override_get_db():

    db = TestingSessionLocal()

    try:
        yield db

    finally:
        db.close()

# dependency ovveriding for testing -> crown jewel of fastapi
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def client():
    reset_database()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    db = TestingSessionLocal()

    try:
        yield db

    finally:
        db.close()
        
