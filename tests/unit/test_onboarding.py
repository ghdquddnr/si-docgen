"""양식 온보딩 분석기 테스트.

우리 템플릿(.xlsx)을 입력으로 자체 검증한다 — 표지 셀·헤더 행·컬럼 매핑이 정확히 제안되는지.
"""

from pathlib import Path

import pytest

from app import cli
from app.onboarding import (
    TemplateAnalysisError,
    analyze_xlsx_template,
    format_report,
)

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "backend" / "templates"


def test_wbs_양식_분석() -> None:
    a = analyze_xlsx_template(TEMPLATES / "wbs.xlsx", "wbs")
    assert a.cover == {
        "project_name": "B5",
        "system_name": "F5",
        "author": "B6",
        "written_date": "F6",
    }
    assert a.header_row == 8
    assert a.style_row == 9
    assert [c.column_letter for c in a.columns] == ["A", "B", "C", "D", "E", "F", "G", "H"]
    assert a.warnings == []


def test_table_spec_양식_분석() -> None:
    # table_spec 표지는 시스템명이 G 열(B5/G5/B6/G6)
    a = analyze_xlsx_template(TEMPLATES / "table_spec.xlsx", "table_spec")
    assert a.cover["project_name"] == "B5"
    assert a.cover["system_name"] == "G5"
    assert a.header_row == 8
    # 모든 기대 컬럼이 매핑됨 (미발견 없음)
    assert all(c.column_letter for c in a.columns)
    assert a.warnings == []


def test_interface_spec_양식_분석() -> None:
    a = analyze_xlsx_template(TEMPLATES / "interface_spec.xlsx", "interface_spec")
    assert a.header_row == 8
    assert all(c.column_letter for c in a.columns)
    assert a.warnings == []


def test_종류_불일치는_경고() -> None:
    # wbs 양식을 table_spec 으로 분석 → 헤더 매칭 빈약 → 경고
    a = analyze_xlsx_template(TEMPLATES / "wbs.xlsx", "table_spec")
    assert a.warnings  # 비어 있지 않음


def test_미지원_종류_거부() -> None:
    with pytest.raises(TemplateAnalysisError, match="지원하지 않는"):
        analyze_xlsx_template(TEMPLATES / "wbs.xlsx", "screen_spec")


def test_없는_파일_거부() -> None:
    with pytest.raises(TemplateAnalysisError, match="없습니다"):
        analyze_xlsx_template(TEMPLATES / "nope.xlsx", "wbs")


def test_보고서_문자열() -> None:
    a = analyze_xlsx_template(TEMPLATES / "wbs.xlsx", "wbs")
    report = format_report(a)
    assert "양식 분석: wbs" in report
    assert "B5" in report
    assert "헤더 행] 8" in report


def test_cli_analyze_template_종료코드_0() -> None:
    code = cli.main(["analyze-template", "--input", str(TEMPLATES / "wbs.xlsx"), "--kind", "wbs"])
    assert code == 0


def test_cli_analyze_template_없는_파일_종료코드_1(tmp_path: Path) -> None:
    code = cli.main(["analyze-template", "--input", str(tmp_path / "x.xlsx"), "--kind", "wbs"])
    assert code == 1
