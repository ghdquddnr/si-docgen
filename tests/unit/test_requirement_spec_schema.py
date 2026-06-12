"""요구사항정의서 스키마 경계값 테스트."""

import pytest
from pydantic import ValidationError

from app.schemas import requirement_spec as rs

VALID_REQ = {
    "req_id": "REQ-001",
    "name": "사용자 로그인",
    "category": "기능",
    "priority": "상",
    "description": "사용자는 ID와 비밀번호로 로그인할 수 있어야 한다.",
}

VALID_DOC = {
    "project_name": "테스트 프로젝트",
    "system_name": "테스트 시스템",
    "doc_no": "REQ-SPEC-2026-001",
    "author": "홍길동",
    "written_date": "2026-06-13",
    "requirements": [VALID_REQ],
}


def test_유효한_문서_통과() -> None:
    doc = rs.RequirementSpecDocument.model_validate(VALID_DOC)
    assert doc.revisions == []
    assert doc.requirements[0].note == ""


@pytest.mark.parametrize("bad_req_id", ["REQ-1", "REQ001", "TC-001", ""])
def test_잘못된_요건_ID_거부(bad_req_id: str) -> None:
    with pytest.raises(ValidationError):
        rs.Requirement.model_validate({**VALID_REQ, "req_id": bad_req_id})


@pytest.mark.parametrize("bad_priority", ["최상", "high", "1", ""])
def test_허용되지_않는_중요도_거부(bad_priority: str) -> None:
    with pytest.raises(ValidationError):
        rs.Requirement.model_validate({**VALID_REQ, "priority": bad_priority})


@pytest.mark.parametrize("field", ["name", "category", "description"])
def test_빈_필수_문자열_거부(field: str) -> None:
    with pytest.raises(ValidationError):
        rs.Requirement.model_validate({**VALID_REQ, field: ""})


def test_빈_요건_목록_거부() -> None:
    with pytest.raises(ValidationError):
        rs.RequirementSpecDocument.model_validate({**VALID_DOC, "requirements": []})


def test_잘못된_개정일_거부() -> None:
    bad_rev = {"version": "1.0", "revised_date": "13/06/2026", "author": "홍", "description": "x"}
    with pytest.raises(ValidationError):
        rs.Revision.model_validate(bad_rev)
