"""검수 화면 편집 — 화면정의서/요구사항정의서 PUT 재검증·저장 (B2-1).

요건 머리 체인 잡(requirement_spec + screen_spec 모두 존재)을 만든 뒤 각 PUT 을 검증한다.
"""

import io
import json
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.api.main import app
from app.config import get_settings
from app.db.base import Base
from app.db.session import rebind_engine

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
        }
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
        data={"with_requirements": "true", "author": "A"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _screen_job(client: TestClient) -> str:
    # 테스트 설계 묶음(with_screens): 시나리오 + 화면정의서 생성
    resp = client.post(
        "/jobs",
        files={"file": ("req.md", b"REQ-001", "text/markdown")},
        data={"with_screens": "true", "author": "A"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── 화면정의서 PUT ─────────────────────────────────────────────────────────


def test_화면정의서_편집_저장(client: TestClient) -> None:
    job_id = _screen_job(client)
    edited = deepcopy(SCREEN_SPEC)
    edited["screens"][0]["screen_name"] = "로그인 화면(수정)"
    assert client.put(f"/jobs/{job_id}/screen-spec", json=edited).status_code == 200
    assert client.get(f"/jobs/{job_id}/screen-spec").json()["screens"][0]["screen_name"] == (
        "로그인 화면(수정)"
    )


def test_화면정의서_스키마_위반_422(client: TestClient) -> None:
    job_id = _screen_job(client)
    bad = deepcopy(SCREEN_SPEC)
    bad["screens"][0]["screen_id"] = "X-001"  # SCR-xxx 형식 위반
    assert client.put(f"/jobs/{job_id}/screen-spec", json=bad).status_code == 422


# ── 요구사항정의서 PUT ──────────────────────────────────────────────────────


def test_요구사항정의서_편집_렌더_반영(client: TestClient) -> None:
    job_id = _req_job(client)
    edited = deepcopy(REQUIREMENT_SPEC)
    edited["requirements"][0]["name"] = "사용자 로그인(수정)"
    assert client.put(f"/jobs/{job_id}/requirement-spec", json=edited).status_code == 200

    # 편집본이 렌더된 docx 에 반영되는지 확인
    client.post(f"/jobs/{job_id}/render")
    docx = client.get(f"/jobs/{job_id}/download/requirement_spec")
    text = "\n".join(p.text for p in Document(io.BytesIO(docx.content)).paragraphs)
    assert "사용자 로그인(수정)" in text


def test_요구사항정의서_빈_요건_422(client: TestClient) -> None:
    job_id = _req_job(client)
    bad = deepcopy(REQUIREMENT_SPEC)
    bad["requirements"] = []  # min_length=1 위반
    assert client.put(f"/jobs/{job_id}/requirement-spec", json=bad).status_code == 422


def test_비요건_잡은_요구사항정의서_편집_409(client: TestClient) -> None:
    resp = client.post("/jobs", files={"file": ("req.md", b"REQ-001", "text/markdown")})
    job_id = resp.json()["id"]
    assert client.put(f"/jobs/{job_id}/requirement-spec", json=REQUIREMENT_SPEC).status_code == 409


def test_스펙_버전_이력_저장_목록_및_롤백(client: TestClient) -> None:
    job_id = _req_job(client)

    # 1. 최초 수정 발생 시 이전 버전(최초 AI 생성)이 버전 1로 보관되고,
    # 새 수정 데이터가 버전 2로 인서트됨
    edited1 = deepcopy(REQUIREMENT_SPEC)
    edited1["requirements"][0]["name"] = "사용자 로그인(수정1)"
    resp = client.put(f"/jobs/{job_id}/requirement-spec", json=edited1)
    assert resp.status_code == 200

    # 2. 버전 이력 목록 조회 검증
    versions = client.get(f"/jobs/{job_id}/versions?spec_type=requirement_spec")
    assert versions.status_code == 200
    version_list = versions.json()
    # 버전 2(현재 활성/수정본)와 버전 1(과거 백업/최초) 총 2개의 이력이 존재해야 함
    assert len(version_list) == 2
    assert version_list[0]["version"] == 2
    assert version_list[1]["version"] == 1

    # 3. 추가 수정 발생 시 버전 3가 생성되어 누적되는지 검증
    edited2 = deepcopy(REQUIREMENT_SPEC)
    edited2["requirements"][0]["name"] = "사용자 로그인(수정2)"
    resp2 = client.put(f"/jobs/{job_id}/requirement-spec", json=edited2)
    assert resp2.status_code == 200

    versions = client.get(f"/jobs/{job_id}/versions?spec_type=requirement_spec")
    assert len(versions.json()) == 3
    assert versions.json()[0]["version"] == 3

    # 4. 과거 버전 1 상세조회 검증
    detail = client.get(f"/jobs/{job_id}/versions/1?spec_type=requirement_spec")
    assert detail.status_code == 200
    assert detail.json()["requirements"][0]["name"] == "사용자 로그인"  # 최초 버전 데이터 보존 확인

    # 5. 과거 버전 1로 롤백 수행 검증
    rollback = client.post(f"/jobs/{job_id}/rollback/1?spec_type=requirement_spec")
    assert rollback.status_code == 200

    # 롤백 적용 후 실시간 스펙 데이터가 롤백 완료 상태("사용자 로그인")로 돌아왔는지 검증
    current_spec = client.get(f"/jobs/{job_id}/requirement-spec")
    assert current_spec.status_code == 200
    assert current_spec.json()["requirements"][0]["name"] == "사용자 로그인"

    # 롤백 행위 또한 히스토리 상에서 최신 버전(버전 4)으로 백업 누적 확인
    versions = client.get(f"/jobs/{job_id}/versions?spec_type=requirement_spec")
    assert len(versions.json()) == 4
    assert versions.json()[0]["version"] == 4
    assert versions.json()[0]["updated_by"] == "A"
