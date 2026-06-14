"""인터페이스정의서 스키마 경계값 테스트 — ID 형식·유일성·최소 건수."""

import pytest
from pydantic import ValidationError

from app.schemas.interface_spec import InterfaceSpecDocument

COVER = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-14",
}


def _field(name: str) -> dict:
    return {"name": name, "data_type": "String(20)", "required": True, "description": "설명"}


def _interface(if_id: str, fields: list[dict]) -> dict:
    return {
        "interface_id": if_id,
        "name": "연계",
        "send_system": "A시스템",
        "recv_system": "B시스템",
        "method": "REST API",
        "cycle": "실시간",
        "fields": fields,
    }


def _doc(interfaces: list[dict]) -> dict:
    return {**COVER, "interfaces": interfaces}


def test_정상_문서_통과() -> None:
    doc = InterfaceSpecDocument.model_validate(
        _doc([_interface("IF-001", [_field("A"), _field("B")])])
    )
    assert len(doc.interfaces) == 1
    assert doc.interfaces[0].method == "REST API"


def test_빈_인터페이스_목록_거부() -> None:
    with pytest.raises(ValidationError):
        InterfaceSpecDocument.model_validate(_doc([]))


def test_빈_항목_목록_거부() -> None:
    with pytest.raises(ValidationError):
        InterfaceSpecDocument.model_validate(_doc([_interface("IF-001", [])]))


def test_IF_ID_형식_위반_거부() -> None:
    with pytest.raises(ValidationError):
        InterfaceSpecDocument.model_validate(_doc([_interface("X-001", [_field("A")])]))


def test_인터페이스_ID_중복_거부() -> None:
    with pytest.raises(ValidationError, match="인터페이스 ID"):
        InterfaceSpecDocument.model_validate(
            _doc([_interface("IF-001", [_field("A")]), _interface("IF-001", [_field("B")])])
        )


def test_항목명_중복_거부() -> None:
    with pytest.raises(ValidationError, match="항목명"):
        InterfaceSpecDocument.model_validate(
            _doc([_interface("IF-001", [_field("A"), _field("A")])])
        )
