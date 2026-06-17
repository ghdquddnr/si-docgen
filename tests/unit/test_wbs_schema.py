"""WBS 스키마 경계값 테스트 — ID 유일성·기간·선행 참조·순환 검증."""

import pytest
from pydantic import ValidationError

from app.schemas.wbs import WBSDocument

COVER = {
    "project_name": "P",
    "system_name": "S",
    "author": "A",
    "written_date": "2026-06-14",
    "start_date": "2026-07-01",
}


def _leaf(id_: str, *, duration: int = 3, preds: list[str] | None = None) -> dict:
    return {
        "id": id_,
        "name": id_,
        "role": "역할",
        "duration_days": duration,
        "effort_md": 3,
        "predecessors": preds or [],
        "deliverable": "산출물",
    }


def _doc(tasks: list[dict]) -> dict:
    return {**COVER, "tasks": tasks}


def test_정상_문서_통과() -> None:
    doc = WBSDocument.model_validate(
        _doc([{"id": "a", "name": "분석", "children": [_leaf("a1"), _leaf("a2", preds=["a1"])]}])
    )
    assert len(doc.tasks) == 1
    assert doc.tasks[0].is_summary


def test_빈_태스크_목록_거부() -> None:
    with pytest.raises(ValidationError):
        WBSDocument.model_validate(_doc([]))


def test_중복_id_거부() -> None:
    with pytest.raises(ValidationError, match="중복"):
        WBSDocument.model_validate(_doc([_leaf("dup"), _leaf("dup")]))


def test_작업_태스크_기간_0_거부() -> None:
    with pytest.raises(ValidationError, match="기간"):
        WBSDocument.model_validate(_doc([_leaf("a", duration=0)]))


def test_존재하지_않는_선행_거부() -> None:
    with pytest.raises(ValidationError, match="선행"):
        WBSDocument.model_validate(_doc([_leaf("a", preds=["없음"])]))


def test_요약_태스크를_선행으로_참조해도_통과() -> None:
    # 'sum' 은 요약 태스크(자식 보유) → 선행 참조 가능
    tasks = [
        {"id": "sum", "name": "요약", "children": [_leaf("sum-c")]},
        _leaf("b", preds=["sum"]),
    ]
    doc = WBSDocument.model_validate(_doc(tasks))
    assert len(doc.tasks) == 2


def test_자기_자신_선행_거부() -> None:
    with pytest.raises(ValidationError, match="자기 자신"):
        WBSDocument.model_validate(_doc([_leaf("a", preds=["a"])]))


def test_순환_선행_거부() -> None:
    tasks = [_leaf("a", preds=["b"]), _leaf("b", preds=["a"])]
    with pytest.raises(ValidationError, match="순환"):
        WBSDocument.model_validate(_doc(tasks))
