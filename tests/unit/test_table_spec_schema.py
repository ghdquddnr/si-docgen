"""테이블정의서 스키마 경계값 테스트 — 테이블/컬럼 유일성·최소 건수."""

import pytest
from pydantic import ValidationError

from app.schemas.table_spec import TableSpecDocument

COVER = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-14",
}


def _col(physical: str, *, pk: bool = False) -> dict:
    return {
        "logical_name": physical,
        "physical_name": physical,
        "data_type": "VARCHAR(50)",
        "is_pk": pk,
        "is_nullable": not pk,
        "description": "설명",
    }


def _table(physical: str, columns: list[dict]) -> dict:
    return {"logical_name": physical, "physical_name": physical, "columns": columns}


def _doc(tables: list[dict]) -> dict:
    return {**COVER, "tables": tables}


def test_정상_문서_통과() -> None:
    doc = TableSpecDocument.model_validate(
        _doc([_table("TB_USER", [_col("USER_ID", pk=True), _col("NAME")])])
    )
    assert len(doc.tables) == 1
    assert doc.tables[0].columns[0].is_pk


def test_빈_테이블_목록_거부() -> None:
    with pytest.raises(ValidationError):
        TableSpecDocument.model_validate(_doc([]))


def test_빈_컬럼_목록_거부() -> None:
    with pytest.raises(ValidationError):
        TableSpecDocument.model_validate(_doc([_table("TB_USER", [])]))


def test_테이블_물리명_중복_거부() -> None:
    with pytest.raises(ValidationError, match="테이블 물리명"):
        TableSpecDocument.model_validate(
            _doc([_table("TB_USER", [_col("A")]), _table("TB_USER", [_col("B")])])
        )


def test_컬럼_물리명_중복_거부() -> None:
    with pytest.raises(ValidationError, match="컬럼 물리명"):
        TableSpecDocument.model_validate(_doc([_table("TB_USER", [_col("ID"), _col("ID")])]))
