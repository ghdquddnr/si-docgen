"""인터페이스정의서 LLM 생성 파이프라인.

원천 문서를 받아 검증된 InterfaceSpecDocument(인터페이스·메시지 항목 JSON)를 생성한다.
REQ→SCR→TC 체인과 독립적인 산출물이다 (WBS·테이블정의서와 동일).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.llm.prompts import INTERFACE_SPEC_SYSTEM, build_interface_spec_prompt
from app.pipelines.chunking import generate_map_reduce
from app.pipelines.source_loader import SourceDocument, load_source
from app.renderers.interface_spec_renderer import render_interface_spec
from app.schemas.interface_spec import InterfaceSpecDocument

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
INTERFACE_SPEC_TEMPLATE = ROOT / "backend" / "templates" / "interface_spec.xlsx"


@dataclass(frozen=True)
class InterfaceSpecResult:
    """인터페이스정의서 산출물 경로와 통계."""

    interface_spec_path: Path
    interface_count: int
    field_count: int


def generate_interface_spec(
    input_path: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    model: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> InterfaceSpecDocument:
    """원천 문서에서 검증된 인터페이스정의서(JSON 모델)를 생성한다.

    model 이 주어지면 그 모델을, 없으면 설정의 interface_spec_model(또는 기본 모델)을 쓴다.
    """
    if on_progress is not None:
        on_progress("parsing")
    logger.info("원천 문서 파싱(인터페이스정의서): %s", input_path)
    source = load_source(input_path)

    if on_progress is not None:
        on_progress("generating")
    logger.info("인터페이스정의서 LLM 생성 시작 (Map-Reduce 적용 가능)")

    def build_prompt(src: SourceDocument) -> str:
        return build_interface_spec_prompt(
            src,
            InterfaceSpecDocument,
            project_name=project_name,
            system_name=system_name,
            author=author,
            written_date=written_date,
        )

    interface_spec = generate_map_reduce(
        source,
        InterfaceSpecDocument,
        build_prompt,
        system=INTERFACE_SPEC_SYSTEM,
        model=model or get_settings().interface_spec_model,
        on_progress=on_progress,
    )
    logger.info("인터페이스정의서 생성 완료: 인터페이스 %d개", len(interface_spec.interfaces))
    return interface_spec


def generate_and_render_interface_spec(
    input_path: Path,
    output_dir: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    model: str | None = None,
) -> InterfaceSpecResult:
    """원천 문서 1건에서 인터페이스정의서를 생성·렌더링한다 (CLI 일괄 흐름)."""
    doc = generate_interface_spec(
        input_path,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        model=model,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    path = render_interface_spec(doc, INTERFACE_SPEC_TEMPLATE, output_dir / "interface_spec.xlsx")
    field_count = sum(len(i.fields) for i in doc.interfaces)
    logger.info(
        "인터페이스정의서 렌더링 완료: %s (인터페이스 %d · 항목 %d)",
        path,
        len(doc.interfaces),
        field_count,
    )
    return InterfaceSpecResult(
        interface_spec_path=path, interface_count=len(doc.interfaces), field_count=field_count
    )
