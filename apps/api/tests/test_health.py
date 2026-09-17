from fastapi.testclient import TestClient

from daily_win_api.main import app

client = TestClient(app)


def test_health_returns_ok_without_secrets() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    body = response.text.lower()
    assert "password" not in body
    assert "database_url" not in body
    assert "postgresql" not in body
