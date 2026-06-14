"""다중 산출물 체인 오케스트레이션 (Phase 3, B1-2 확장).

흐름: 원천 문서 → (옵션) 요구사항정의서(LLM) → 테스트시나리오(LLM) + 화면정의서(LLM)
→ RTM 파생(screen_ids 연결) → REQ→SCR→TC 정합성 검증 → 산출물 렌더링.

with_requirements=True 면 요구사항정의서가 체인의 머리가 되어 확정 REQ ID 를
시나리오·화면 생성에 주입하고, RTM 요건명을 요구사항정의서에서 채운다(docx 포함 4종).
LLM 호출은 generate_requirement_spec / generate_scenario / generate_screen_spec 로 격리된다.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from app.pipelines.generate_requirement_spec import generate_requirement_spec
from app.pipelines.generate_screen_spec import generate_screen_spec
from app.pipelines.generate_test_scenario import (
    RTM_TEMPLATE,
    TEST_SCENARIO_TEMPLATE,
    generate_scenario,
)
from app.renderers.docx_renderer import render_requirement_spec
from app.renderers.pptx_renderer import render_screen_spec
from app.renderers.rtm_renderer import render_rtm
from app.renderers.xlsx_renderer import render_test_scenario
from app.schemas.requirement_spec import RequirementSpecDocument
from app.schemas.rtm import (
    build_rtm_from_chain,
    validate_requirement_consistency,
    validate_rtm_consistency,
    validate_screen_consistency,
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
SCREEN_SPEC_TEMPLATE = ROOT / "backend" / "templates" / "screen_spec.pptx"
REQUIREMENT_SPEC_TEMPLATE = ROOT / "backend" / "templates" / "requirement_spec.docx"


@dataclass(frozen=True)
class ChainResult:
    """체인 산출물 경로와 통계."""

    test_scenario_path: Path
    rtm_path: Path
    screen_spec_path: Path
    unit_count: int
    integration_count: int
    requirement_count: int
    screen_count: int
    requirement_spec_path: Path | None = None


def generate_chain(
    input_path: Path,
    output_dir: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    with_requirements: bool = False,
) -> ChainResult:
    """원천 문서 1건에서 테스트시나리오·화면정의서·RTM(+옵션 요구사항정의서)을 생성·렌더링한다.

    with_requirements=True 면 요구사항정의서를 먼저 생성해 체인의 머리로 삼는다.
    """
    cover = {
        "project_name": project_name,
        "system_name": system_name,
        "author": author,
        "written_date": written_date,
    }

    requirement_spec: RequirementSpecDocument | None = None
    req_pairs: list[tuple[str, str]] | None = None
    if with_requirements:
        requirement_spec = generate_requirement_spec(input_path, **cover)
        req_pairs = [(r.req_id, r.name) for r in requirement_spec.requirements]

    scenario = generate_scenario(input_path, requirements=req_pairs, **cover)

    if requirement_spec is not None:
        # 화면도 요구사항정의서의 확정 REQ ID 만 참조하도록 그 집합을 전달
        screen_req_ids = [r.req_id for r in requirement_spec.requirements]
    else:
        screen_req_ids = sorted(
            {c.req_id for c in scenario.unit_test_cases + scenario.integration_test_cases}
        )

    screen_spec = generate_screen_spec(input_path, req_ids=screen_req_ids, **cover)

    # REQ→SCR→TC 추적성 검증
    if requirement_spec is not None:
        validate_requirement_consistency(requirement_spec, scenario, screen_spec)
    else:
        validate_screen_consistency(screen_spec, scenario)
    rtm = build_rtm_from_chain(scenario, screen_spec, requirement_spec)
    validate_rtm_consistency(rtm, scenario)
    logger.info(
        "체인 생성 완료: 요건 %d · 화면 %d · 단위 %d · 통합 %d",
        len(rtm.rows),
        len(screen_spec.screens),
        len(scenario.unit_test_cases),
        len(scenario.integration_test_cases),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    ts_path = render_test_scenario(
        scenario, TEST_SCENARIO_TEMPLATE, output_dir / "test_scenario.xlsx"
    )
    rtm_path = render_rtm(rtm, RTM_TEMPLATE, output_dir / "rtm.xlsx")
    screen_path = render_screen_spec(
        screen_spec, SCREEN_SPEC_TEMPLATE, output_dir / "screen_spec.pptx"
    )
    req_path: Path | None = None
    if requirement_spec is not None:
        req_path = render_requirement_spec(
            requirement_spec, REQUIREMENT_SPEC_TEMPLATE, output_dir / "requirement_spec.docx"
        )
    logger.info("렌더링 완료: %s, %s, %s, %s", req_path, ts_path, rtm_path, screen_path)

    return ChainResult(
        test_scenario_path=ts_path,
        rtm_path=rtm_path,
        screen_spec_path=screen_path,
        unit_count=len(scenario.unit_test_cases),
        integration_count=len(scenario.integration_test_cases),
        requirement_count=len(rtm.rows),
        screen_count=len(screen_spec.screens),
        requirement_spec_path=req_path,
    )
