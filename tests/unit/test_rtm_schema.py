"""요건추적표(RTM) 스키마 경계값 테스트.

잘못된 ID 형식, 요건 ID 중복, 빈 필수 문자열이 검증에서 걸리는지 확인한다.
"""

import pytest
from pydantic import ValidationError

from app.schemas.rtm import RTMDocument, RTMRow, StageReflection

VALID_ROW = {
    "req_id": "REQ-001",
    "req_name": "사용자 로그인",
    "screen_ids": ["SCR-001"],
    "program_ids": ["AUTH-LOGIN"],
    "tc_ids": ["TC-001"],
    "stage_reflection": {"analysis": True, "design": True, "implementation": True, "test": True},
}

VALID_DOC = {
    "project_name": "테스트 프로젝트",
    "system_name": "테스트 시스템",
    "author": "홍길동",
    "written_date": "2026-06-13",
}


def test_유효한_행_통과() -> None:
    row = RTMRow.model_validate(VALID_ROW)
    assert row.req_id == "REQ-001"
    assert row.screen_ids == ["SCR-001"]


def test_기본값_적용() -> None:
    row = RTMRow.model_validate({"req_id": "REQ-001", "req_name": "요건"})
    assert row.screen_ids == []
    assert row.program_ids == []
    assert row.tc_ids == []
    assert row.stage_reflection == StageReflection()


@pytest.mark.parametrize("bad_req_id", ["REQ-1", "REQ001", "req-001", "SCR-001", ""])
def test_잘못된_요건_ID_형식_거부(bad_req_id: str) -> None:
    with pytest.raises(ValidationError):
        RTMRow.model_validate({**VALID_ROW, "req_id": bad_req_id})


@pytest.mark.parametrize("bad_scr_id", ["SCR-1", "SCR001", "REQ-001", "scr-001"])
def test_잘못된_화면_ID_형식_거부(bad_scr_id: str) -> None:
    with pytest.raises(ValidationError):
        RTMRow.model_validate({**VALID_ROW, "screen_ids": [bad_scr_id]})


@pytest.mark.parametrize("bad_tc_id", ["TC-1", "TC001", "REQ-001", "tc-001"])
def test_잘못된_TC_ID_형식_거부(bad_tc_id: str) -> None:
    with pytest.raises(ValidationError):
        RTMRow.model_validate({**VALID_ROW, "tc_ids": [bad_tc_id]})


def test_빈_요건명_거부() -> None:
    with pytest.raises(ValidationError):
        RTMRow.model_validate({**VALID_ROW, "req_name": ""})


def test_빈_프로그램_ID_거부() -> None:
    with pytest.raises(ValidationError):
        RTMRow.model_validate({**VALID_ROW, "program_ids": [""]})


def test_빈_행_목록은_허용() -> None:
    doc = RTMDocument.model_validate(VALID_DOC)
    assert doc.rows == []


def test_요건_ID_중복_거부() -> None:
    rows = [
        {"req_id": "REQ-001", "req_name": "요건 A"},
        {"req_id": "REQ-001", "req_name": "요건 B"},
    ]
    with pytest.raises(ValidationError, match="중복"):
        RTMDocument.model_validate({**VALID_DOC, "rows": rows})


def test_서로_다른_요건_ID_는_허용() -> None:
    rows = [
        {"req_id": "REQ-001", "req_name": "요건 A"},
        {"req_id": "REQ-002", "req_name": "요건 B"},
    ]
    doc = RTMDocument.model_validate({**VALID_DOC, "rows": rows})
    assert len(doc.rows) == 2
