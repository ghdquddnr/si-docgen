"""WBS LLM 생성 파이프라인 테스트 (LLM 모킹).

complete_json 을 고정 응답으로 모킹해 generate_wbs 의 검증·반환을 확인한다.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.pipelines.generate_wbs import generate_wbs

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tests" / "fixtures" / "sources" / "sample_requirements.md"

MOCK_WBS: dict[str, Any] = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-14",
    "start_date": "2026-07-01",
    "tasks": [
        {
            "id": "analysis",
            "name": "분석",
            "children": [
                {
                    "id": "req-analysis",
                    "name": "요구사항 분석",
                    "role": "PL",
                    "duration_days": 5,
                    "effort_md": 10,
                    "deliverable": "요구사항정의서",
                },
                {
                    "id": "screen-design",
                    "name": "화면 설계",
                    "role": "기획",
                    "duration_days": 4,
                    "effort_md": 8,
                    "predecessors": ["req-analysis"],
                    "deliverable": "화면정의서",
                },
            ],
        },
        {
            "id": "test",
            "name": "통합 시험",
            "role": "QA",
            "duration_days": 5,
            "effort_md": 10,
            "predecessors": ["screen-design"],
            "deliverable": "테스트결과서",
        },
    ],
}

COVER = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-14",
    "start_date": "2026-07-01",
}


@pytest.fixture
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.llm.generate.complete_json",
        lambda *a, **k: json.dumps(MOCK_WBS, ensure_ascii=False),
    )


def test_WBS_생성_및_검증(mock_llm: None) -> None:
    doc = generate_wbs(INPUT, **COVER)
    assert len(doc.tasks) == 2
    assert doc.tasks[0].is_summary
    assert doc.tasks[0].children[1].predecessors == ["req-analysis"]


def test_진행_콜백_단계_통지(mock_llm: None) -> None:
    stages: list[str] = []
    generate_wbs(INPUT, **COVER, on_progress=stages.append)
    assert stages == ["parsing", "generating"]


def test_모델_오버라이드_전달(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_complete_json(*_a: Any, **kwargs: Any) -> str:
        captured["model"] = kwargs.get("model")
        return json.dumps(MOCK_WBS, ensure_ascii=False)

    monkeypatch.setattr("app.llm.generate.complete_json", fake_complete_json)
    generate_wbs(INPUT, **COVER, model="ollama/gemma4:e4b")
    assert captured["model"] == "ollama/gemma4:e4b"
