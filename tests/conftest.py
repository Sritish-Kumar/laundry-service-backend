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

Base.metadata.create_all(bind=engine)


def override_get_db():
    
    db = TestingSessionLocal()

    try:
        yield db

    finally:
        db.close()

# dependency ovveriding for testing -> crown jewel of fastapi
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
        
