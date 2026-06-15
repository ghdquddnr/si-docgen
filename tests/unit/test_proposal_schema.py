"""제안서 스키마 경계값 테스트."""

import pytest
from pydantic import ValidationError

from app.schemas.proposal import ProposalDocument, ProposalSlide

VALID: dict = {
    "project_name": "P",
    "author": "제안사",
    "written_date": "2026-06-16",
    "title": "제안서",
    "client": "발주처",
    "slides": [{"title": "사업 이해", "bullets": ["배경", "목표"]}],
}


def test_유효_문서_검증_통과() -> None:
    doc = ProposalDocument.model_validate(VALID)
    assert doc.slides[0].title == "사업 이해"
    assert doc.system_name == ""  # 선택 필드 기본값


def test_슬라이드_0건_거부() -> None:
    with pytest.raises(ValidationError):
        ProposalDocument.model_validate({**VALID, "slides": []})


def test_불릿_0건_거부() -> None:
    with pytest.raises(ValidationError):
        ProposalSlide(title="x", bullets=[])


def test_빈_불릿_거부() -> None:
    with pytest.raises(ValidationError):
        ProposalSlide(title="x", bullets=["정상", "   "])


def test_빈_제목_거부() -> None:
    with pytest.raises(ValidationError):
        ProposalSlide(title="", bullets=["a"])


def test_발주처_누락_거부() -> None:
    bad = {k: v for k, v in VALID.items() if k != "client"}
    with pytest.raises(ValidationError):
        ProposalDocument.model_validate(bad)
