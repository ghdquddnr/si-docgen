"""웹 제안서 잡(with_proposal) e2e 테스트 (LLM 모킹)."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pptx import Presentation

from app.api.main import app
from app.config import get_settings
from app.db.base import Base
from app.db.models import Job, JobStatus
from app.db.session import SessionLocal, rebind_engine

PROPOSAL: dict[str, Any] = {
    "project_name": "차세대 포털 사업",
    "system_name": "고객 포털",
    "author": "제안사",
    "client": "한국전력공사",
    "written_date": "2026-06-16",
    "title": "차세대 포털 구축 제안서",
    "slides": [
        {"title": "사업 이해", "bullets": ["배경", "목표"]},
        {"title": "추진 전략", "bullets": ["전략1", "전략2"]},
        {"title": "기대 효과", "bullets": ["효과1"]},
    ],
}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("SIDOCGEN_STORAGE_DIR", str(tmp_path / "jobs"))
    get_settings.cache_clear()
    engine = rebind_engine(f"sqlite:///{tmp_path / 't.db'}")
    Base.metadata.create_all(engine)

    def fake(prompt: str, *, system: str | None = None, json_schema=None, model=None) -> str:
        return json.dumps(PROPOSAL, ensure_ascii=False)

    monkeypatch.setattr("app.llm.generate.complete_json", fake)
    yield TestClient(app)
    get_settings.cache_clear()


def _proposal_job(client: TestClient) -> str:
    resp = client.post(
        "/jobs",
        files={"file": ("rfp.md", "RFP 본문".encode(), "text/markdown")},
        data={"with_proposal": "true", "client": "한국전력공사"},
    )
    assert resp.status_code == 201
    assert resp.json()["with_proposal"] is True
    assert resp.json()["client"] == "한국전력공사"
    return resp.json()["id"]


def test_제안서_잡_저장(client: TestClient) -> None:
    job_id = _proposal_job(client)
    assert client.get(f"/jobs/{job_id}").json()["status"] == "succeeded"
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        assert job.status is JobStatus.SUCCEEDED
        assert job.proposal_json is not None
        assert job.proposal_json["title"] == "차세대 포털 구축 제안서"


def test_제안서_조회(client: TestClient) -> None:
    job_id = _proposal_job(client)
    resp = client.get(f"/jobs/{job_id}/proposal")
    assert resp.status_code == 200
    assert resp.json()["slides"][0]["title"] == "사업 이해"


def test_제안서_편집_저장(client: TestClient) -> None:
    job_id = _proposal_job(client)
    edited = dict(PROPOSAL)
    edited["slides"] = [{"title": "수정 섹션", "bullets": ["수정 불릿"]}]
    resp = client.put(f"/jobs/{job_id}/proposal", json=edited)
    assert resp.status_code == 200
    got = client.get(f"/jobs/{job_id}/proposal").json()
    assert got["slides"][0]["title"] == "수정 섹션"


def test_제안서_편집_스키마위반_422(client: TestClient) -> None:
    job_id = _proposal_job(client)
    bad = dict(PROPOSAL)
    bad["slides"] = []  # 슬라이드 0건 (min_length=1 위반)
    assert client.put(f"/jobs/{job_id}/proposal", json=bad).status_code == 422


def test_렌더_후_pptx_다운로드(client: TestClient) -> None:
    job_id = _proposal_job(client)
    render = client.post(f"/jobs/{job_id}/render")
    assert render.status_code == 200
    assert "proposal" in render.json()["downloads"]

    dl = client.get(f"/jobs/{job_id}/download/proposal")
    assert dl.status_code == 200
    prs = Presentation(__import__("io").BytesIO(dl.content))
    # 표지 + 목차 + 내용 3 = 5 슬라이드
    assert len(prs.slides) == 5


def test_비제안서_잡은_409(client: TestClient) -> None:
    resp = client.post("/jobs", files={"file": ("rfp.md", b"RFP", "text/markdown")})
    job_id = resp.json()["id"]
    assert resp.json()["with_proposal"] is False
    assert client.get(f"/jobs/{job_id}/proposal").status_code == 409
