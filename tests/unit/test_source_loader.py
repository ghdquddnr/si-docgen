"""원천 문서 파서 단위 테스트 (픽스처: tests/fixtures/sources/)."""

from pathlib import Path

import pytest

from app.exceptions import SourceParseError
from app.pipelines.source_loader import load_source

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sources"


def test_md_본문_추출() -> None:
    doc = load_source(FIXTURES / "sample_requirements.md")
    assert doc.filename == "sample_requirements.md"
    assert "REQ-001 사용자 로그인" in doc.text
    assert "기안 상신" in doc.text
    assert doc.tables == []


def test_docx_본문과_표_추출() -> None:
    doc = load_source(FIXTURES / "sample_requirements.docx")
    assert "비밀번호 5회 오류 시 계정을 잠금 처리한다" in doc.text
    assert len(doc.tables) == 1
    assert doc.tables[0][0] == ["요건 ID", "요건명", "중요도"]
    assert doc.tables[0][1] == ["REQ-001", "사용자 로그인", "상"]


def test_pdf_본문_추출() -> None:
    doc = load_source(FIXTURES / "sample_requirements.pdf")
    assert "REQ-001" in doc.text
    assert "기안 문서를 상신" in doc.text


def test_미지원_확장자_거부(tmp_path: Path) -> None:
    bad = tmp_path / "source.hwp"
    bad.write_bytes(b"dummy")
    with pytest.raises(SourceParseError, match="지원하지 않는"):
        load_source(bad)


def test_없는_파일_거부() -> None:
    with pytest.raises(SourceParseError, match="원천 문서가 없습니다"):
        load_source(FIXTURES / "missing.docx")


def test_손상된_docx_거부(tmp_path: Path) -> None:
    broken = tmp_path / "broken.docx"
    broken.write_bytes(b"this is not a zip")
    with pytest.raises(SourceParseError, match="열 수 없습니다"):
        load_source(broken)
