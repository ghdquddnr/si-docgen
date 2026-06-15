"""LLM 설정 API e2e 테스트 — 제공자·키(암호화)·모델 레지스트리."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config import get_settings
from app.db.base import Base
from app.db.models import ApiCredential
from app.db.session import SessionLocal, rebind_engine


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("SIDOCGEN_SECRET_KEY", "test-secret-key-for-encryption")
    get_settings.cache_clear()
    engine = rebind_engine(f"sqlite:///{tmp_path / 't.db'}")
    Base.metadata.create_all(engine)
    yield TestClient(app)
    get_settings.cache_clear()


def test_제공자_목록(client: TestClient) -> None:
    resp = client.get("/llm/providers")
    assert resp.status_code == 200
    providers = {p["provider"]: p for p in resp.json()}
    assert set(providers) == {"ollama", "openai", "gemini", "anthropic", "xai"}
    assert providers["ollama"]["needs_key"] is False
    assert providers["anthropic"]["needs_key"] is True


def test_키_저장_마스킹_그리고_평문_미노출(client: TestClient) -> None:
    resp = client.post(
        "/llm/credentials",
        json={"provider": "anthropic", "label": "운영 키", "api_key": "sk-ant-secret-9999"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["provider"] == "anthropic"
    assert body["key_preview"].endswith("9999")
    assert "sk-ant-secret-9999" not in str(body)  # 평문 미노출
    # DB 에는 평문이 아니라 암호문으로 저장된다
    with SessionLocal() as db:
        cred = db.query(ApiCredential).one()
        assert cred.encrypted_key != "sk-ant-secret-9999"
        assert "sk-ant-secret-9999" not in cred.encrypted_key


def test_키_없는_제공자_키등록_거부(client: TestClient) -> None:
    resp = client.post("/llm/credentials", json={"provider": "ollama", "api_key": "x"})
    assert resp.status_code == 400


def test_상용모델_키없이_추가_거부(client: TestClient) -> None:
    resp = client.post(
        "/llm/models", json={"provider": "openai", "model": "openai/gpt-4o", "label": "GPT-4o"}
    )
    assert resp.status_code == 400  # OpenAI 키 미등록


def test_키_등록후_모델_추가_그리고_생성화면_목록(client: TestClient) -> None:
    cred = client.post(
        "/llm/credentials", json={"provider": "openai", "api_key": "sk-openai-1234"}
    ).json()
    made = client.post(
        "/llm/models",
        json={
            "provider": "openai",
            "model": "openai/gpt-4o",
            "label": "GPT-4o",
            "credential_id": cred["id"],
        },
    )
    assert made.status_code == 201
    # ollama 모델은 키 없이 추가 가능
    assert (
        client.post(
            "/llm/models", json={"provider": "ollama", "model": "ollama/gemma4:e4b"}
        ).status_code
        == 201
    )
    enabled = client.get("/llm/models", params={"enabled_only": "true"}).json()
    assert {m["model"] for m in enabled} == {"openai/gpt-4o", "ollama/gemma4:e4b"}


def test_모델_비활성화_후_목록에서_제외(client: TestClient) -> None:
    m = client.post("/llm/models", json={"provider": "ollama", "model": "ollama/qwen3:14b"}).json()
    assert client.patch(f"/llm/models/{m['id']}", json={"enabled": False}).status_code == 200
    enabled = client.get("/llm/models", params={"enabled_only": "true"}).json()
    assert all(x["model"] != "ollama/qwen3:14b" for x in enabled)


def test_키_삭제시_모델_연결_해제(client: TestClient) -> None:
    cred = client.post(
        "/llm/credentials", json={"provider": "xai", "api_key": "xai-key-5678"}
    ).json()
    m = client.post(
        "/llm/models",
        json={"provider": "xai", "model": "xai/grok-beta", "credential_id": cred["id"]},
    ).json()
    assert client.delete(f"/llm/credentials/{cred['id']}").json() == {"deleted": True}
    after = next(x for x in client.get("/llm/models").json() if x["id"] == m["id"])
    assert after["credential_id"] is None  # 연결 해제됨(모델은 유지)
