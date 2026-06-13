"""헬스체크 엔드포인트 테스트."""

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_health_200() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
