"""WBS(작업분해구조) LLM 생성 파이프라인.

원천 문서를 받아 검증된 WBSDocument(태스크 트리 JSON)를 생성한다. 계층 번호·일정·공수
합산은 렌더러가 계산하므로, 이 단계의 LLM 출력은 구조(트리·기간·공수·선행)까지만 책임진다.
WBS 는 REQ→SCR→TC 체인과 독립적인 산출물이다.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.llm.generate import generate_validated
from app.llm.prompts import WBS_SYSTEM, build_wbs_prompt
from app.pipelines.source_loader import load_source
from app.renderers.wbs_renderer import render_wbs
from app.schemas.wbs import WBSDocument, WBSTask

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
WBS_TEMPLATE = ROOT / "backend" / "templates" / "wbs.xlsx"


@dataclass(frozen=True)
class WBSResult:
    """WBS 산출물 경로와 통계."""

    wbs_path: Path
    total_count: int
    leaf_count: int


def generate_wbs(
    input_path: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    start_date: str,
    model: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> WBSDocument:
    """원천 문서에서 검증된 WBS(태스크 트리 JSON 모델)를 생성한다.

    start_date 는 일정 계산의 기준일이며 렌더링 단계에서 사용된다(LLM 출력은 구조만).
    model 이 주어지면 그 모델을, 없으면 설정의 wbs_model(또는 기본 모델)을 쓴다.
    """
    if on_progress is not None:
        on_progress("parsing")
    logger.info("원천 문서 파싱(WBS): %s", input_path)
    source = load_source(input_path)

    if on_progress is not None:
        on_progress("generating")
    logger.info("WBS LLM 생성 시작 (검증-재시도 루프)")
    prompt = build_wbs_prompt(
        source,
        WBSDocument,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        start_date=start_date,
    )
    wbs = generate_validated(
        prompt,
        WBSDocument,
        system=WBS_SYSTEM,
        model=model or get_settings().wbs_model,
    )
    logger.info("WBS 생성 완료: 최상위 %d개", len(wbs.tasks))
    return wbs


def _count(tasks: list[WBSTask]) -> tuple[int, int]:
    """(전체 태스크 수, 작업(leaf) 수)를 센다."""
    total = leaves = 0
    for task in tasks:
        total += 1
        if task.children:
            ct, cl = _count(task.children)
            total += ct
            leaves += cl
        else:
            leaves += 1
    return total, leaves


def generate_and_render_wbs(
    input_path: Path,
    output_dir: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    start_date: str,
    model: str | None = None,
) -> WBSResult:
    """원천 문서 1건에서 WBS 를 생성·렌더링한다 (CLI 일괄 흐름)."""
    wbs = generate_wbs(
        input_path,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        start_date=start_date,
        model=model,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    path = render_wbs(wbs, WBS_TEMPLATE, output_dir / "wbs.xlsx")
    total, leaves = _count(wbs.tasks)
    logger.info("WBS 렌더링 완료: %s (전체 %d · 작업 %d)", path, total, leaves)
    return WBSResult(wbs_path=path, total_count=total, leaf_count=leaves)
