"""단계별 모델 오버라이드 테스트 (P3-4).

설정의 scenario_model/screen_spec_model 이 해당 단계 LLM 호출에 분리 적용되는지,
complete_json 에 전달되는 model 인자를 가로채 확인한다.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app.config import get_settings
from app.pipelines.generate_screen_spec import generate_screen_spec
from app.pipelines.generate_test_scenario import generate_scenario

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tests" / "fixtures" / "sources" / "sample_requirements.md"

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

COVER = {"project_name": "P", "system_name": "S", "author": "A", "written_date": "2026-06-14"}


@pytest.fixture
def captured_models(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str | None]]:
    seen: dict[str, str | None] = {}

    def fake(prompt: str, *, system: str | None = None, json_schema=None, model=None) -> str:
        kind = "screen" if system and "화면" in system else "scenario"
        seen[kind] = model
        return json.dumps(SCREEN_SPEC if kind == "screen" else SCENARIO, ensure_ascii=False)

    monkeypatch.setattr("app.llm.generate.complete_json", fake)
    get_settings.cache_clear()
    yield seen
    get_settings.cache_clear()


def test_단계별_모델_분리_적용(
    captured_models: dict[str, str | None], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SIDOCGEN_SCENARIO_MODEL", "ollama/model-a")
    monkeypatch.setenv("SIDOCGEN_SCREEN_SPEC_MODEL", "ollama/model-b")
    get_settings.cache_clear()

    generate_scenario(INPUT, **COVER)
    generate_screen_spec(INPUT, **COVER, req_ids=["REQ-001"])

    assert captured_models["scenario"] == "ollama/model-a"
    assert captured_models["screen"] == "ollama/model-b"


def test_미설정_시_None_으로_기본모델_위임(captured_models: dict[str, str | None]) -> None:
    # scenario_model/screen_spec_model 미지정 → model 인자는 None (client 가 llm_model 사용)
    generate_scenario(INPUT, **COVER)
    assert captured_models["scenario"] is None
