"""체인 추적성 테스트 — RTM screen_ids 연결 + 화면↔요건 정합성 (P3-2)."""

import pytest

from app.exceptions import ValidationFailedError
from app.schemas import test_scenario as ts
from app.schemas.rtm import (
    build_rtm_from_chain,
    build_rtm_from_scenario,
    validate_screen_consistency,
)
from app.schemas.screen_spec import ScreenSpecDocument

COVER = {"project_name": "P", "system_name": "S", "author": "A", "written_date": "2026-06-14"}


def _case(tc_id: str, req_id: str) -> dict:
    return {
        "tc_id": tc_id,
        "req_id": req_id,
        "category_major": "공통",
        "category_minor": "기능",
        "scenario_name": "시나리오",
        "test_steps": ["단계"],
        "expected_result": "결과",
    }


def _scenario(cases: list[dict]) -> ts.TestScenarioDocument:
    return ts.TestScenarioDocument.model_validate({**COVER, "unit_test_cases": cases})


def _screen(scr_id: str, req_ids: list[str]) -> dict:
    return {
        "screen_id": scr_id,
        "screen_name": "화면",
        "menu_path": "홈 > 화면",
        "req_ids": req_ids,
        "fields": [{"no": 1, "name": "항목", "field_type": "텍스트박스", "required": True}],
    }


def _screen_spec(screens: list[dict]) -> ScreenSpecDocument:
    return ScreenSpecDocument.model_validate({**COVER, "screens": screens})


def test_chain_RTM_에_화면_ID_연결() -> None:
    scenario = _scenario([_case("TC-001", "REQ-001"), _case("TC-002", "REQ-002")])
    screen_spec = _screen_spec(
        [_screen("SCR-001", ["REQ-001"]), _screen("SCR-002", ["REQ-001", "REQ-002"])]
    )
    rtm = build_rtm_from_chain(scenario, screen_spec)
    by_req = {row.req_id: row for row in rtm.rows}

    assert by_req["REQ-001"].screen_ids == ["SCR-001", "SCR-002"]
    assert by_req["REQ-002"].screen_ids == ["SCR-002"]
    # 화면이 있는 요건은 설계 단계 반영 True
    assert by_req["REQ-001"].stage_reflection.design is True


def test_화면_없으면_screen_ids_빈칸() -> None:
    scenario = _scenario([_case("TC-001", "REQ-001")])
    rtm = build_rtm_from_scenario(scenario)
    assert rtm.rows[0].screen_ids == []
    assert rtm.rows[0].stage_reflection.design is False


def test_정합성_충족_통과() -> None:
    scenario = _scenario([_case("TC-001", "REQ-001"), _case("TC-002", "REQ-002")])
    screen_spec = _screen_spec([_screen("SCR-001", ["REQ-001"])])
    validate_screen_consistency(screen_spec, scenario)  # 예외 없이 통과


def test_없는_요건_참조_화면_거부() -> None:
    scenario = _scenario([_case("TC-001", "REQ-001")])
    screen_spec = _screen_spec([_screen("SCR-001", ["REQ-999"])])
    with pytest.raises(ValidationFailedError, match="REQ-999"):
        validate_screen_consistency(screen_spec, scenario)
