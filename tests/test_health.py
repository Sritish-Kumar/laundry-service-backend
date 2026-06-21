from sqlalchemy.exc import OperationalError

from app.dependencies.database import get_db
from app.main import app


def test_health_returns_backend_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Backend is healthy",
        "data": {"status": "healthy"},
    }


def test_ready_returns_database_status(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Database is ready",
        "data": {"status": "ready"},
    }


def test_ready_returns_503_when_database_is_unavailable(client):
    class UnavailableDatabase:
        def execute(self, statement):
            raise OperationalError("SELECT 1", {}, Exception("database unavailable"))

    def override_unavailable_db():
        yield UnavailableDatabase()

    original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_unavailable_db

    try:
        response = client.get("/ready")
    finally:
        if original_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = original_override

    assert response.status_code == 503
    assert response.json() == {
        "success": False,
        "message": "Database is not ready",
        "data": {"status": "not_ready"},
    }
