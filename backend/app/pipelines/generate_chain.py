"""다중 산출물 체인 오케스트레이션 (Phase 3).

흐름: 원천 문서 → 테스트시나리오(LLM) + 화면정의서(LLM) → RTM 파생(screen_ids 연결)
→ REQ→SCR→TC 정합성 검증 → 엑셀 2종 + PPT 1종 렌더링.

목업 이미지(HTML→PNG)는 브라우저 의존이라 기본 미생성(옵션). LLM 호출은
generate_scenario / generate_screen_spec 두 곳으로 격리된다.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from app.pipelines.generate_screen_spec import generate_screen_spec
from app.pipelines.generate_test_scenario import (
    RTM_TEMPLATE,
    TEST_SCENARIO_TEMPLATE,
    generate_scenario,
)
from app.renderers.pptx_renderer import render_screen_spec
from app.renderers.rtm_renderer import render_rtm
from app.renderers.xlsx_renderer import render_test_scenario
from app.schemas.rtm import (
    build_rtm_from_chain,
    validate_rtm_consistency,
    validate_screen_consistency,
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
SCREEN_SPEC_TEMPLATE = ROOT / "backend" / "templates" / "screen_spec.pptx"


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


def generate_chain(
    input_path: Path,
    output_dir: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
) -> ChainResult:
    """원천 문서 1건에서 테스트시나리오·화면정의서·RTM 을 함께 생성·렌더링한다."""
    scenario = generate_scenario(
        input_path,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
    )
    req_ids = sorted({c.req_id for c in scenario.unit_test_cases + scenario.integration_test_cases})

    screen_spec = generate_screen_spec(
        input_path,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        req_ids=req_ids,
    )

    # REQ→SCR→TC 추적성 검증
    validate_screen_consistency(screen_spec, scenario)
    rtm = build_rtm_from_chain(scenario, screen_spec)
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
    logger.info("렌더링 완료: %s, %s, %s", ts_path, rtm_path, screen_path)

    return ChainResult(
        test_scenario_path=ts_path,
        rtm_path=rtm_path,
        screen_spec_path=screen_path,
        unit_count=len(scenario.unit_test_cases),
        integration_count=len(scenario.integration_test_cases),
        requirement_count=len(rtm.rows),
        screen_count=len(screen_spec.screens),
    )
