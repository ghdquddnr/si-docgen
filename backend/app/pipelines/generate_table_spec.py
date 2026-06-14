"""테이블정의서 LLM 생성 파이프라인.

원천 문서를 받아 검증된 TableSpecDocument(테이블·컬럼 JSON)를 생성한다.
REQ→SCR→TC 체인과 독립적인 산출물이다 (WBS 와 동일).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.llm.generate import generate_validated
from app.llm.prompts import TABLE_SPEC_SYSTEM, build_table_spec_prompt
from app.pipelines.source_loader import load_source
from app.renderers.table_spec_renderer import render_table_spec
from app.schemas.table_spec import TableSpecDocument

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
TABLE_SPEC_TEMPLATE = ROOT / "backend" / "templates" / "table_spec.xlsx"


@dataclass(frozen=True)
class TableSpecResult:
    """테이블정의서 산출물 경로와 통계."""

    table_spec_path: Path
    table_count: int
    column_count: int


def generate_table_spec(
    input_path: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    model: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> TableSpecDocument:
    """원천 문서에서 검증된 테이블정의서(JSON 모델)를 생성한다.

    model 이 주어지면 그 모델을, 없으면 설정의 table_spec_model(또는 기본 모델)을 쓴다.
    """
    if on_progress is not None:
        on_progress("parsing")
    logger.info("원천 문서 파싱(테이블정의서): %s", input_path)
    source = load_source(input_path)

    if on_progress is not None:
        on_progress("generating")
    logger.info("테이블정의서 LLM 생성 시작 (검증-재시도 루프)")
    prompt = build_table_spec_prompt(
        source,
        TableSpecDocument,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
    )
    table_spec = generate_validated(
        prompt,
        TableSpecDocument,
        system=TABLE_SPEC_SYSTEM,
        model=model or get_settings().table_spec_model,
    )
    logger.info("테이블정의서 생성 완료: 테이블 %d개", len(table_spec.tables))
    return table_spec


def generate_and_render_table_spec(
    input_path: Path,
    output_dir: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    model: str | None = None,
) -> TableSpecResult:
    """원천 문서 1건에서 테이블정의서를 생성·렌더링한다 (CLI 일괄 흐름)."""
    doc = generate_table_spec(
        input_path,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        model=model,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    path = render_table_spec(doc, TABLE_SPEC_TEMPLATE, output_dir / "table_spec.xlsx")
    column_count = sum(len(t.columns) for t in doc.tables)
    logger.info(
        "테이블정의서 렌더링 완료: %s (테이블 %d · 컬럼 %d)", path, len(doc.tables), column_count
    )
    return TableSpecResult(
        table_spec_path=path, table_count=len(doc.tables), column_count=column_count
    )
