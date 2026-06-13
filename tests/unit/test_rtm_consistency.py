"""RTM ↔ 테스트시나리오 ID 정합성 검증 테스트.

존재하지 않는 TC/REQ ID 참조가 validate_rtm_consistency 에서 거부되는지 확인한다
(CLAUDE.md 절대 원칙 6: 존재하지 않는 ID 참조 발견 시 검증 실패).
"""

import pytest

from app.exceptions import ValidationFailedError
from app.schemas import test_scenario as ts  # 클래스명이 Test* 라 pytest 오인 수집 방지
from app.schemas.rtm import RTMDocument, validate_rtm_consistency

COVER = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-13",
}


def _case(tc_id: str, req_id: str) -> dict:
    return {
        "tc_id": tc_id,
        "req_id": req_id,
        "category_major": "공통",
        "category_minor": "로그인",
        "scenario_name": "시나리오",
        "test_steps": ["단계 1"],
        "expected_result": "결과",
    }


def _scenario(cases: list[dict]) -> ts.TestScenarioDocument:
    return ts.TestScenarioDocument.model_validate({**COVER, "unit_test_cases": cases})


def _rtm(rows: list[dict]) -> RTMDocument:
    return RTMDocument.model_validate({**COVER, "rows": rows})


def test_정합성_충족_시_통과() -> None:
    scenario = _scenario([_case("TC-001", "REQ-001"), _case("TC-002", "REQ-001")])
    rtm = _rtm([{"req_id": "REQ-001", "req_name": "로그인", "tc_ids": ["TC-001", "TC-002"]}])
    validate_rtm_consistency(rtm, scenario)  # 예외 없이 통과해야 한다


def test_RTM_이_없는_TC_참조_시_거부() -> None:
    scenario = _scenario([_case("TC-001", "REQ-001")])
    rtm = _rtm([{"req_id": "REQ-001", "req_name": "로그인", "tc_ids": ["TC-001", "TC-999"]}])
    with pytest.raises(ValidationFailedError, match="TC-999"):
        validate_rtm_consistency(rtm, scenario)


def test_시나리오_요건이_RTM_에_없으면_거부() -> None:
    scenario = _scenario([_case("TC-001", "REQ-001"), _case("TC-002", "REQ-002")])
    rtm = _rtm([{"req_id": "REQ-001", "req_name": "로그인", "tc_ids": ["TC-001", "TC-002"]}])
    with pytest.raises(ValidationFailedError, match="REQ-002"):
        validate_rtm_consistency(rtm, scenario)


def test_RTM_이_시험_미작성_요건을_가져도_통과() -> None:
    # RTM 에 TC 가 아직 없는 요건(시험 미반영)이 있어도 시나리오 정합성과는 무관하다
    scenario = _scenario([_case("TC-001", "REQ-001")])
    rtm = _rtm(
        [
            {"req_id": "REQ-001", "req_name": "로그인", "tc_ids": ["TC-001"]},
            {"req_id": "REQ-002", "req_name": "미작성 요건", "tc_ids": []},
        ]
    )
    validate_rtm_consistency(rtm, scenario)
