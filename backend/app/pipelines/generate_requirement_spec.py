"""요구사항정의서 LLM 생성 파이프라인.

원천 문서(RFP·회의록·기존 요구사항 등)를 받아 검증된 RequirementSpecDocument(JSON 모델)를
생성한다. 렌더링(docx)은 별도 단계이며, 이 함수는 JSON 생성까지만 책임진다.

이 산출물은 체인의 머리에 해당한다 — 여기서 확정된 REQ ID 가 화면정의서·테스트시나리오의
요건 참조 출처가 된다.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from app.config import get_settings
from app.llm.prompts import REQUIREMENT_SPEC_SYSTEM, build_requirement_spec_prompt
from app.pipelines.chunking import generate_map_reduce
from app.pipelines.source_loader import SourceDocument, load_source
from app.schemas.requirement_spec import RequirementSpecDocument

logger = logging.getLogger(__name__)


def generate_requirement_spec(
    input_path: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    model: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> RequirementSpecDocument:
    """원천 문서에서 검증된 요구사항정의서(JSON 모델)를 생성한다.

    model 이 주어지면 그 모델을, 없으면 설정의 requirement_spec_model(또는 기본 모델)을 쓴다.
    on_progress 가 주어지면 단계 전환 시 단계명(parsing/generating)을 통지한다 (SSE 진행 표시용).
    """
    if on_progress is not None:
        on_progress("parsing")
    logger.info("원천 문서 파싱(요구사항정의서): %s", input_path)
    source = load_source(input_path)

    if on_progress is not None:
        on_progress("generating")
    logger.info("요구사항정의서 LLM 생성 시작 (Map-Reduce 적용 가능)")

    def build_prompt(src: SourceDocument) -> str:
        return build_requirement_spec_prompt(
            src,
            RequirementSpecDocument,
            project_name=project_name,
            system_name=system_name,
            author=author,
            written_date=written_date,
        )

    requirement_spec = generate_map_reduce(
        source,
        RequirementSpecDocument,
        build_prompt,
        system=REQUIREMENT_SPEC_SYSTEM,
        model=model or get_settings().requirement_spec_model,
        on_progress=on_progress,
    )
    logger.info("요구사항정의서 생성 완료: 요건 %d건", len(requirement_spec.requirements))
    return requirement_spec
