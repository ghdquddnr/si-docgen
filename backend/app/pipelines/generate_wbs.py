"""WBS(작업분해구조) LLM 생성 파이프라인.

원천 문서를 받아 검증된 WBSDocument(태스크 트리 JSON)를 생성한다. 계층 번호·일정·공수
합산은 렌더러가 계산하므로, 이 단계의 LLM 출력은 구조(트리·기간·공수·선행)까지만 책임진다.
WBS 는 REQ→SCR→TC 체인과 독립적인 산출물이다.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from app.config import get_settings
from app.llm.generate import generate_validated
from app.llm.prompts import WBS_SYSTEM, build_wbs_prompt
from app.pipelines.source_loader import load_source
from app.schemas.wbs import WBSDocument

logger = logging.getLogger(__name__)


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
