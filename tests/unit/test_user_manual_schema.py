"""사용자 매뉴얼 스키마 경계값 테스트 — 최소 건수·필수 필드."""

import pytest
from pydantic import ValidationError

from app.schemas.user_manual import UserManualDocument

COVER = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-14",
}


def _step(instruction: str = "수행", ref: str = "") -> dict:
    return {"instruction": instruction, "screen_ref": ref, "caption": ""}


def _section(title: str, steps: list[dict]) -> dict:
    return {"title": title, "description": "설명", "steps": steps}


def _doc(sections: list[dict]) -> dict:
    return {**COVER, "sections": sections}


def test_정상_문서_통과() -> None:
    doc = UserManualDocument.model_validate(
        _doc([_section("로그인", [_step("ID 입력", "SCR-001"), _step("로그인 클릭")])])
    )
    assert len(doc.sections) == 1
    assert doc.sections[0].steps[0].screen_ref == "SCR-001"


def test_빈_섹션_목록_거부() -> None:
    with pytest.raises(ValidationError):
        UserManualDocument.model_validate(_doc([]))


def test_빈_단계_목록_거부() -> None:
    with pytest.raises(ValidationError):
        UserManualDocument.model_validate(_doc([_section("로그인", [])]))


def test_빈_수행내용_거부() -> None:
    with pytest.raises(ValidationError):
        UserManualDocument.model_validate(_doc([_section("로그인", [_step("")])]))


def test_screen_ref_캡션_기본값() -> None:
    doc = UserManualDocument.model_validate(_doc([_section("로그인", [{"instruction": "수행"}])]))
    step = doc.sections[0].steps[0]
    assert step.screen_ref == ""
    assert step.caption == ""
