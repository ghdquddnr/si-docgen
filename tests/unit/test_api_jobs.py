"""업로드 → 생성 잡 엔드포인트 e2e 테스트 (LLM 모킹, 임시 DB/스토리지).

TestClient 는 BackgroundTasks 를 응답 후 동기 실행하므로, POST 직후 잡이 완료된다.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config import get_settings
from app.db.base import Base
from app.db.models import Job, JobStatus
from app.db.session import SessionLocal, rebind_engine

MOCK_SCENARIO: dict[str, Any] = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-14",
    "unit_test_cases": [
        {
            "tc_id": "TC-001",
            "req_id": "REQ-001",
            "category_major": "사용자 관리",
            "category_minor": "로그인",
            "scenario_name": "정상 로그인",
            "test_steps": ["로그인 화면 접속", "ID/PW 입력"],
            "expected_result": "메인 이동",
        }
    ],
    "integration_test_cases": [],
}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("SIDOCGEN_STORAGE_DIR", str(tmp_path / "jobs"))
    get_settings.cache_clear()
    engine = rebind_engine(f"sqlite:///{tmp_path / 't.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        "app.llm.generate.complete_json",
        lambda *a, **k: json.dumps(MOCK_SCENARIO, ensure_ascii=False),
    )
    yield TestClient(app)
    get_settings.cache_clear()


def test_업로드_생성_성공(client: TestClient) -> None:
    files = {"file": ("req.md", b"# requirements\nREQ-001", "text/markdown")}
    resp = client.post("/jobs", files=files, data={"project_name": "P", "author": "A"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] in {"succeeded", "running", "pending"}

    job_id = body["id"]
    got = client.get(f"/jobs/{job_id}")
    assert got.status_code == 200
    assert got.json()["status"] == "succeeded"  # 백그라운드 완료됨


def test_생성_결과_DB_저장(client: TestClient) -> None:
    files = {"file": ("req.md", b"REQ-001 sample", "text/markdown")}
    job_id = client.post("/jobs", files=files).json()["id"]

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        assert job is not None
        assert job.status is JobStatus.SUCCEEDED
        assert job.scenario_json is not None
        assert job.scenario_json["unit_test_cases"][0]["tc_id"] == "TC-001"


def test_미지원_확장자_400(client: TestClient) -> None:
    files = {"file": ("req.hwp", b"x", "application/octet-stream")}
    resp = client.post("/jobs", files=files)
    assert resp.status_code == 400


def test_존재하지_않는_잡_404(client: TestClient) -> None:
    assert client.get("/jobs/none").status_code == 404
