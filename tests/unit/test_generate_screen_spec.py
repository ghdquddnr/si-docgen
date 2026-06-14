"""화면정의서 LLM 생성 파이프라인 테스트 (LLM 모킹).

complete_json 을 고정 응답으로 모킹해 generate_screen_spec 의 검증·반환을 확인한다.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.pipelines.generate_screen_spec import generate_screen_spec

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tests" / "fixtures" / "sources" / "sample_requirements.md"

MOCK_SCREEN_SPEC: dict[str, Any] = {
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
            "fields": [
                {"no": 1, "name": "사용자 ID", "field_type": "텍스트박스", "required": True},
                {"no": 2, "name": "비밀번호", "field_type": "비밀번호", "required": True},
            ],
            "logic": ["ID/PW 검증", "실패 5회 시 잠금"],
        },
        {
            "screen_id": "SCR-002",
            "screen_name": "게시글 작성",
            "menu_path": "홈 > 게시판 > 작성",
            "req_ids": ["REQ-002"],
            "fields": [{"no": 1, "name": "제목", "field_type": "텍스트박스", "required": True}],
            "logic": ["등록 시 목록 갱신"],
        },
    ],
}


@pytest.fixture
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.llm.generate.complete_json",
        lambda *a, **k: json.dumps(MOCK_SCREEN_SPEC, ensure_ascii=False),
    )


def test_화면정의서_생성_및_검증(mock_llm: None) -> None:
    doc = generate_screen_spec(
        INPUT,
        project_name="P",
        system_name="S",
        author="A",
        written_date="2026-06-14",
        req_ids=["REQ-001", "REQ-002"],
    )
    assert len(doc.screens) == 2
    assert doc.screens[0].screen_id == "SCR-001"
    assert doc.screens[0].req_ids == ["REQ-001"]


def test_진행_콜백_단계_통지(mock_llm: None) -> None:
    stages: list[str] = []
    generate_screen_spec(
        INPUT,
        project_name="P",
        system_name="S",
        author="A",
        written_date="2026-06-14",
        req_ids=["REQ-001"],
        on_progress=stages.append,
    )
    assert stages == ["parsing", "generating"]
