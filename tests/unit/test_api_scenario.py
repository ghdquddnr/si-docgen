"""시나리오 조회 + 검수(편집) 엔드포인트 테스트.

편집본은 TestScenarioDocument 로 재검증되어 스키마 위반·TC ID 중복이 422 로 거부된다.
"""

import copy
import json
import uuid
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
            "category_major": "공통",
            "category_minor": "로그인",
            "scenario_name": "정상",
            "test_steps": ["단계"],
            "expected_result": "결과",
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


def _create_completed_job(client: TestClient) -> str:
    # 시나리오만 보유한 완료 잡을 직접 시드한다(시나리오 엔드포인트 단위 검증용)
    job_id = uuid.uuid4().hex
    with SessionLocal() as db:
        db.add(
            Job(
                id=job_id,
                input_filename="req.md",
                status=JobStatus.SUCCEEDED,
                scenario_json=copy.deepcopy(MOCK_SCENARIO),
            )
        )
        db.commit()
    return job_id


def test_시나리오_조회(client: TestClient) -> None:
    job_id = _create_completed_job(client)
    resp = client.get(f"/jobs/{job_id}/scenario")
    assert resp.status_code == 200
    assert resp.json()["unit_test_cases"][0]["tc_id"] == "TC-001"


def test_시나리오_미생성_409(client: TestClient) -> None:
    with SessionLocal() as db:
        db.add(Job(id="pending-1", input_filename="x.md", status=JobStatus.PENDING))
        db.commit()
    assert client.get("/jobs/pending-1/scenario").status_code == 409


def test_유효_편집본_저장(client: TestClient) -> None:
    job_id = _create_completed_job(client)
    edited = copy.deepcopy(MOCK_SCENARIO)
    edited["unit_test_cases"][0]["scenario_name"] = "검수로 수정한 시나리오"

    resp = client.put(f"/jobs/{job_id}/scenario", json=edited)
    assert resp.status_code == 200

    got = client.get(f"/jobs/{job_id}/scenario").json()
    assert got["unit_test_cases"][0]["scenario_name"] == "검수로 수정한 시나리오"


def test_TC_ID_중복_편집본_422(client: TestClient) -> None:
    job_id = _create_completed_job(client)
    bad = copy.deepcopy(MOCK_SCENARIO)
    dup_case = copy.deepcopy(bad["unit_test_cases"][0])
    bad["unit_test_cases"].append(dup_case)  # 같은 TC-001 중복
    assert client.put(f"/jobs/{job_id}/scenario", json=bad).status_code == 422


def test_잘못된_TC_ID_형식_편집본_422(client: TestClient) -> None:
    job_id = _create_completed_job(client)
    bad = copy.deepcopy(MOCK_SCENARIO)
    bad["unit_test_cases"][0]["tc_id"] = "TC1"  # 패턴 위반
    assert client.put(f"/jobs/{job_id}/scenario", json=bad).status_code == 422


def test_없는_잡_편집_404(client: TestClient) -> None:
    assert client.put("/jobs/none/scenario", json=MOCK_SCENARIO).status_code == 404
