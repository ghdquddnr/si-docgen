"""테스트시나리오 스키마 경계값 테스트.

빈 리스트, 잘못된 ID 형식, 허용되지 않는 값이 검증에서 걸리는지 확인한다.
"""

import pytest
from pydantic import ValidationError

# 클래스명이 Test* 라 pytest 가 테스트로 오인 수집하지 않도록 모듈로 임포트한다
from app.schemas import test_scenario as ts

VALID_CASE = {
    "tc_id": "TC-001",
    "req_id": "REQ-001",
    "category_major": "공통",
    "category_minor": "로그인",
    "scenario_name": "정상 로그인",
    "test_steps": ["로그인 화면에 접속한다"],
    "expected_result": "메인 화면으로 이동한다",
}

VALID_DOC = {
    "project_name": "테스트 프로젝트",
    "system_name": "테스트 시스템",
    "author": "홍길동",
    "written_date": "2026-06-13",
}


def test_유효한_테스트케이스_통과() -> None:
    case = ts.TestCase.model_validate(VALID_CASE)
    assert case.result is None
    assert case.precondition == ""
    assert case.note == ""


@pytest.mark.parametrize("bad_tc_id", ["TC-1", "TC001", "tc-001", "ABC-001", ""])
def test_잘못된_TC_ID_형식_거부(bad_tc_id: str) -> None:
    with pytest.raises(ValidationError):
        ts.TestCase.model_validate({**VALID_CASE, "tc_id": bad_tc_id})


@pytest.mark.parametrize("bad_req_id", ["REQ-1", "REQ001", "SCR-001", ""])
def test_잘못된_요건_ID_형식_거부(bad_req_id: str) -> None:
    with pytest.raises(ValidationError):
        ts.TestCase.model_validate({**VALID_CASE, "req_id": bad_req_id})


def test_빈_테스트_절차_거부() -> None:
    with pytest.raises(ValidationError):
        ts.TestCase.model_validate({**VALID_CASE, "test_steps": []})


@pytest.mark.parametrize("field", ["category_major", "category_minor", "scenario_name"])
def test_빈_필수_문자열_거부(field: str) -> None:
    with pytest.raises(ValidationError):
        ts.TestCase.model_validate({**VALID_CASE, field: ""})


@pytest.mark.parametrize("bad_result", ["보류", "pass", "PASS", "N/A"])
def test_허용되지_않는_결과_값_거부(bad_result: str) -> None:
    with pytest.raises(ValidationError):
        ts.TestCase.model_validate({**VALID_CASE, "result": bad_result})


def test_빈_테스트케이스_목록은_허용() -> None:
    doc = ts.TestScenarioDocument.model_validate(VALID_DOC)
    assert doc.unit_test_cases == []
    assert doc.integration_test_cases == []


def test_잘못된_작성일_거부() -> None:
    with pytest.raises(ValidationError):
        ts.TestScenarioDocument.model_validate({**VALID_DOC, "written_date": "2026년 6월 13일"})


def test_중복_TC_ID_거부() -> None:
    dup = {**VALID_CASE, "tc_id": "TC-001"}
    other = {**VALID_CASE, "tc_id": "TC-001", "scenario_name": "다른 시나리오"}
    with pytest.raises(ValidationError, match="중복"):
        ts.TestScenarioDocument.model_validate(
            {**VALID_DOC, "unit_test_cases": [dup], "integration_test_cases": [other]}
        )
