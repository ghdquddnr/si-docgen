"""잡 진행 상태 SSE 스트림 테스트.

진행 순서는 read_job_state 를 스크립트된 시퀀스로 대체해 결정론적으로 검증하고,
종료는 실제 잡(모킹 LLM 으로 완료)으로 스트림이 닫히는지 확인한다.
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
from app.db.session import rebind_engine

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
    monkeypatch.setenv("SIDOCGEN_SSE_POLL_INTERVAL", "0")
    get_settings.cache_clear()
    engine = rebind_engine(f"sqlite:///{tmp_path / 't.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        "app.llm.generate.complete_json",
        lambda *a, **k: json.dumps(MOCK_SCENARIO, ensure_ascii=False),
    )
    yield TestClient(app)
    get_settings.cache_clear()


def _collect_event_data(client: TestClient, url: str) -> list[dict[str, Any]]:
    """SSE 스트림에서 data 페이로드(JSON)를 순서대로 수집한다."""
    payloads: list[dict[str, Any]] = []
    with client.stream("GET", url) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("data:"):
                payloads.append(json.loads(line[len("data:") :].strip()))
    return payloads


def test_진행_단계가_순서대로_전달(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    states = [
        {"status": "pending", "progress": None, "error": None, "terminal": False},
        {"status": "running", "progress": "parsing", "error": None, "terminal": False},
        {"status": "running", "progress": "generating", "error": None, "terminal": False},
        {"status": "succeeded", "progress": "done", "error": None, "terminal": True},
    ]
    seq = iter(states)
    holder = {"cur": states[0]}

    def fake_read(job_id: str) -> dict[str, Any]:
        try:
            holder["cur"] = next(seq)
        except StopIteration:
            pass
        return holder["cur"]

    monkeypatch.setattr("app.api.routers.events.read_job_state", fake_read)

    payloads = _collect_event_data(client, "/jobs/any/events")
    assert [p["status"] for p in payloads] == ["pending", "running", "running", "succeeded"]
    assert [p["progress"] for p in payloads] == [None, "parsing", "generating", "done"]


def test_완료된_잡_스트림_종료(client: TestClient) -> None:
    files = {"file": ("req.md", b"REQ-001", "text/markdown")}
    job_id = client.post("/jobs", files=files).json()["id"]  # 백그라운드 완료됨

    payloads = _collect_event_data(client, f"/jobs/{job_id}/events")
    assert payloads, "최소 1개 이벤트가 있어야 한다"
    assert payloads[-1]["status"] == "succeeded"
    assert payloads[-1]["terminal"] is True


def test_없는_잡_에러_이벤트(client: TestClient) -> None:
    payloads = _collect_event_data(client, "/jobs/none/events")
    assert payloads == [{"detail": "잡을 찾을 수 없습니다"}]
