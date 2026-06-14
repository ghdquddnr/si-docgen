"""화면정의서 LLM 생성 파이프라인.

원천 문서와 요건 ID 목록을 받아 검증된 ScreenSpecDocument(JSON 모델)를 생성한다.
렌더링(pptx)·목업 생성은 별도 단계이며, 이 함수는 JSON 생성까지만 책임진다.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from app.config import get_settings
from app.llm.generate import generate_validated
from app.llm.prompts import SCREEN_SPEC_SYSTEM, build_screen_spec_prompt
from app.pipelines.source_loader import load_source
from app.schemas.screen_spec import ScreenSpecDocument

logger = logging.getLogger(__name__)


def generate_screen_spec(
    input_path: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    req_ids: list[str],
    model: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> ScreenSpecDocument:
    """원천 문서에서 검증된 화면정의서(JSON 모델)를 생성한다.

    req_ids 는 화면이 참조할 수 있는 요건 ID 집합(보통 테스트시나리오의 요건 ID)을 전달해
    화면↔요건 추적성을 유도한다. model 이 주어지면 그 모델을, 없으면 설정의 screen_spec_model.
    """
    if on_progress is not None:
        on_progress("parsing")
    logger.info("원천 문서 파싱(화면정의서): %s", input_path)
    source = load_source(input_path)

    if on_progress is not None:
        on_progress("generating")
    logger.info("화면정의서 LLM 생성 시작 (검증-재시도 루프)")
    prompt = build_screen_spec_prompt(
        source,
        ScreenSpecDocument,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        req_ids=req_ids,
    )
    screen_spec = generate_validated(
        prompt,
        ScreenSpecDocument,
        system=SCREEN_SPEC_SYSTEM,
        model=model or get_settings().screen_spec_model,
    )
    logger.info("화면정의서 생성 완료: 화면 %d개", len(screen_spec.screens))
    return screen_spec
