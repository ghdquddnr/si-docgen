"""요구사항정의서 LLM 생성 파이프라인 테스트 (LLM 모킹).

complete_json 을 고정 응답으로 모킹해 generate_requirement_spec 의 검증·반환을 확인한다.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.pipelines.generate_requirement_spec import generate_requirement_spec

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tests" / "fixtures" / "sources" / "sample_requirements.md"

MOCK_REQUIREMENT_SPEC: dict[str, Any] = {
    "project_name": "통합 업무포털",
    "system_name": "업무포털",
    "doc_no": "REQ-SPEC-2026-001",
    "author": "작성자",
    "written_date": "2026-06-14",
    "revisions": [
        {
            "version": "1.0",
            "revised_date": "2026-06-14",
            "author": "작성자",
            "description": "최초 작성",
        }
    ],
    "requirements": [
        {
            "req_id": "REQ-001",
            "name": "사용자 로그인",
            "category": "기능",
            "priority": "상",
            "description": "ID/PW 로 로그인하며 5회 오류 시 계정을 잠근다.",
            "note": "",
        },
        {
            "req_id": "REQ-002",
            "name": "공지사항 관리",
            "category": "기능",
            "priority": "중",
            "description": "공지 작성 권한자가 공지를 등록·수정·삭제한다.",
            "note": "",
        },
    ],
}


@pytest.fixture
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.llm.generate.complete_json",
        lambda *a, **k: json.dumps(MOCK_REQUIREMENT_SPEC, ensure_ascii=False),
    )


def test_요구사항정의서_생성_및_검증(mock_llm: None) -> None:
    doc = generate_requirement_spec(
        INPUT,
        project_name="통합 업무포털",
        system_name="업무포털",
        author="작성자",
        written_date="2026-06-14",
    )
    assert len(doc.requirements) == 2
    assert doc.requirements[0].req_id == "REQ-001"
    assert doc.doc_no == "REQ-SPEC-2026-001"
    assert doc.revisions[0].version == "1.0"


def test_진행_콜백_단계_통지(mock_llm: None) -> None:
    stages: list[str] = []
    generate_requirement_spec(
        INPUT,
        project_name="P",
        system_name="S",
        author="A",
        written_date="2026-06-14",
        on_progress=stages.append,
    )
    assert stages == ["parsing", "generating"]


def test_모델_오버라이드_전달(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_complete_json(*_a: Any, **kwargs: Any) -> str:
        captured["model"] = kwargs.get("model")
        return json.dumps(MOCK_REQUIREMENT_SPEC, ensure_ascii=False)

    monkeypatch.setattr("app.llm.generate.complete_json", fake_complete_json)
    generate_requirement_spec(
        INPUT,
        project_name="P",
        system_name="S",
        author="A",
        written_date="2026-06-14",
        model="ollama/gemma4:e4b",
    )
    assert captured["model"] == "ollama/gemma4:e4b"
