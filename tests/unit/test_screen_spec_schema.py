"""화면정의서 스키마 경계값 테스트 (P3-1 에서 추가된 req_ids 포함)."""

import pytest
from pydantic import ValidationError

from app.schemas.screen_spec import Screen, ScreenSpecDocument

VALID_SCREEN = {
    "screen_id": "SCR-001",
    "screen_name": "로그인",
    "menu_path": "홈 > 로그인",
    "req_ids": ["REQ-001"],
    "fields": [
        {"no": 1, "name": "사용자 ID", "field_type": "텍스트박스", "required": True},
    ],
}

VALID_DOC = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-14",
    "screens": [VALID_SCREEN],
}


def test_유효한_화면_통과() -> None:
    screen = Screen.model_validate(VALID_SCREEN)
    assert screen.req_ids == ["REQ-001"]


def test_req_ids_기본_빈_목록() -> None:
    screen = Screen.model_validate({**VALID_SCREEN, "req_ids": []})
    assert screen.req_ids == []
    # req_ids 미지정 시에도 기본 빈 목록 (기존 호환)
    no_field = {k: v for k, v in VALID_SCREEN.items() if k != "req_ids"}
    assert Screen.model_validate(no_field).req_ids == []


@pytest.mark.parametrize("bad_req_id", ["REQ-1", "REQ001", "SCR-001", "req-001"])
def test_잘못된_req_id_형식_거부(bad_req_id: str) -> None:
    with pytest.raises(ValidationError):
        Screen.model_validate({**VALID_SCREEN, "req_ids": [bad_req_id]})


@pytest.mark.parametrize("bad_scr_id", ["SCR-1", "SCR001", "REQ-001", ""])
def test_잘못된_screen_id_형식_거부(bad_scr_id: str) -> None:
    with pytest.raises(ValidationError):
        Screen.model_validate({**VALID_SCREEN, "screen_id": bad_scr_id})


def test_항목_없는_화면_거부() -> None:
    with pytest.raises(ValidationError):
        Screen.model_validate({**VALID_SCREEN, "fields": []})


def test_화면_없는_문서_거부() -> None:
    with pytest.raises(ValidationError):
        ScreenSpecDocument.model_validate({**VALID_DOC, "screens": []})
