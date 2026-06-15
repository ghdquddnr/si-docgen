"""웹 요건 머리 체인 잡(with_requirements) e2e 테스트 (LLM 모킹).

업로드 → 4종 체인(요건정의서 + 시나리오 + 화면) → 저장 → 렌더 → docx 다운로드를 확인한다.
"""

import io
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.api.main import app
from app.config import get_settings
from app.db.base import Base
from app.db.models import Job, JobStatus
from app.db.session import SessionLocal, rebind_engine

REQUIREMENT_SPEC: dict[str, Any] = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-14",
    "doc_no": "REQ-SPEC-2026-001",
    "revisions": [
        {"version": "1.0", "revised_date": "2026-06-14", "author": "A", "description": "최초 작성"}
    ],
    "requirements": [
        {
            "req_id": "REQ-001",
            "name": "사용자 로그인",
            "category": "기능",
            "priority": "상",
            "description": "ID/PW 로 로그인한다.",
            "note": "",
        },
        {
            "req_id": "REQ-002",
            "name": "공지사항 관리",
            "category": "기능",
            "priority": "중",
            "description": "공지를 등록·수정·삭제한다.",
            "note": "",
        },
    ],
}

SCENARIO: dict[str, Any] = {
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

SCREEN_SPEC: dict[str, Any] = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-14",
    "screens": [
        {
            "screen_id": "SCR-001",
            "screen_name": "로그인",
            "menu_path": "홈 > 로그인",
            "req_ids": ["REQ-001"],
            "fields": [{"no": 1, "name": "ID", "field_type": "텍스트박스", "required": True}],
        }
    ],
}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("SIDOCGEN_STORAGE_DIR", str(tmp_path / "jobs"))
    get_settings.cache_clear()
    engine = rebind_engine(f"sqlite:///{tmp_path / 't.db'}")
    Base.metadata.create_all(engine)

    def fake(prompt: str, *, system: str | None = None, json_schema=None, model=None) -> str:
        sys_text = system or ""
        if "요구사항정의서" in sys_text:
            payload = REQUIREMENT_SPEC
        elif "화면" in sys_text:
            payload = SCREEN_SPEC
        else:
            payload = SCENARIO
        return json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr("app.llm.generate.complete_json", fake)
    yield TestClient(app)
    get_settings.cache_clear()


def _req_job(client: TestClient) -> str:
    resp = client.post(
        "/jobs",
        files={"file": ("req.md", b"REQ-001", "text/markdown")},
        data={"with_requirements": "true"},
    )
    assert resp.status_code == 201
    assert resp.json()["with_requirements"] is True
    return resp.json()["id"]


def test_요건정의서_잡은_요건정의서만_저장(client: TestClient) -> None:
    # 문서별 메뉴: 요구사항정의서 잡은 요건정의서 docx 만 생성(시나리오·화면 없음)
    job_id = _req_job(client)
    assert client.get(f"/jobs/{job_id}").json()["status"] == "succeeded"

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        assert job.status is JobStatus.SUCCEEDED
        assert job.requirement_spec_json is not None
        assert job.scenario_json is None
        assert job.screen_spec_json is None
        assert len(job.requirement_spec_json["requirements"]) == 2


def test_요구사항정의서_조회(client: TestClient) -> None:
    job_id = _req_job(client)
    resp = client.get(f"/jobs/{job_id}/requirement-spec")
    assert resp.status_code == 200
    assert resp.json()["requirements"][0]["req_id"] == "REQ-001"


def test_렌더_후_docx_다운로드(client: TestClient) -> None:
    job_id = _req_job(client)
    render = client.post(f"/jobs/{job_id}/render")
    assert render.status_code == 200
    # 요건정의서 잡은 docx 만 렌더(RTM·시나리오는 테스트 설계 메뉴 소관)
    assert set(render.json()["downloads"]) == {"requirement_spec"}

    docx = client.get(f"/jobs/{job_id}/download/requirement_spec")
    assert docx.status_code == 200
    text = "\n".join(p.text for p in Document(io.BytesIO(docx.content)).paragraphs)
    assert "사용자 로그인" in text


def test_비요건_잡은_요구사항정의서_없음_409(client: TestClient) -> None:
    resp = client.post("/jobs", files={"file": ("req.md", b"REQ-001", "text/markdown")})
    job_id = resp.json()["id"]
    assert resp.json()["with_requirements"] is False
    assert client.get(f"/jobs/{job_id}/requirement-spec").status_code == 409
