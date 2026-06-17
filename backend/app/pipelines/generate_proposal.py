"""제안서(RFP→PPTX) LLM 생성 파이프라인.

고객사 RFP 를 받아 검증된 ProposalDocument(표지 정보 + 슬라이드별 제목·불릿 JSON)를 생성한다.
PPTX 렌더링은 결정론적 렌더러가 템플릿을 보존하며 수행하고, 목차 슬라이드는 렌더러가
섹션 제목에서 자동 생성한다. REQ→SCR→TC 체인과 독립적인 산출물이다.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.llm.prompts import PROPOSAL_SYSTEM, build_proposal_prompt
from app.pipelines.chunking import generate_map_reduce
from app.pipelines.source_loader import SourceDocument, load_source
from app.renderers.proposal_renderer import render_proposal
from app.schemas.proposal import ProposalDocument

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
PROPOSAL_TEMPLATE = ROOT / "backend" / "templates" / "proposal.pptx"


@dataclass(frozen=True)
class ProposalResult:
    """제안서 산출물 경로와 통계."""

    proposal_path: Path
    slide_count: int  # 표지·목차 제외, 내용 슬라이드 수
    bullet_count: int


def generate_proposal(
    input_path: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    client: str,
    written_date: str,
    model: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> ProposalDocument:
    """RFP 에서 검증된 제안서(JSON 모델)를 생성한다.

    model 이 주어지면 그 모델을, 없으면 설정의 proposal_model(또는 기본 모델)을 쓴다.
    """
    if on_progress is not None:
        on_progress("parsing")
    logger.info("원천 문서 파싱(제안서): %s", input_path)
    source = load_source(input_path)

    if on_progress is not None:
        on_progress("generating")
    logger.info("제안서 LLM 생성 시작 (Map-Reduce 적용 가능)")

    def build_prompt(src: SourceDocument) -> str:
        return build_proposal_prompt(
            src,
            ProposalDocument,
            project_name=project_name,
            system_name=system_name,
            author=author,
            client=client,
            written_date=written_date,
        )

    proposal = generate_map_reduce(
        source,
        ProposalDocument,
        build_prompt,
        system=PROPOSAL_SYSTEM,
        model=model or get_settings().proposal_model,
        on_progress=on_progress,
    )
    logger.info("제안서 생성 완료: 슬라이드 %d개", len(proposal.slides))
    return proposal


def generate_and_render_proposal(
    input_path: Path,
    output_dir: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    client: str,
    written_date: str,
    model: str | None = None,
) -> ProposalResult:
    """RFP 1건에서 제안서를 생성·렌더링한다 (CLI 일괄 흐름)."""
    doc = generate_proposal(
        input_path,
        project_name=project_name,
        system_name=system_name,
        author=author,
        client=client,
        written_date=written_date,
        model=model,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    path = render_proposal(doc, PROPOSAL_TEMPLATE, output_dir / "proposal.pptx")
    bullet_count = sum(len(s.bullets) for s in doc.slides)
    logger.info(
        "제안서 렌더링 완료: %s (슬라이드 %d · 불릿 %d)", path, len(doc.slides), bullet_count
    )
    return ProposalResult(
        proposal_path=path, slide_count=len(doc.slides), bullet_count=bullet_count
    )
