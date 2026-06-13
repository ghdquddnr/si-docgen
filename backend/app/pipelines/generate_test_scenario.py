"""테스트시나리오 + RTM 생성 파이프라인 오케스트레이션.

흐름: 원천 문서 파싱 → LLM 으로 테스트시나리오 JSON 생성(검증-재시도 루프)
→ 시나리오에서 RTM 결정론적 파생 → 정합성 검증 → 엑셀 2종 렌더링.

LLM 호출은 generate_validated 한 곳으로 격리되며, RTM 은 LLM 을 거치지 않는다.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from app.llm.generate import generate_validated
from app.llm.prompts import TEST_SCENARIO_SYSTEM, build_test_scenario_prompt
from app.pipelines.source_loader import load_source
from app.renderers.rtm_renderer import render_rtm
from app.renderers.xlsx_renderer import render_test_scenario
from app.schemas.rtm import build_rtm_from_scenario, validate_rtm_consistency
from app.schemas.test_scenario import TestScenarioDocument

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
TEST_SCENARIO_TEMPLATE = ROOT / "backend" / "templates" / "test_scenario.xlsx"
RTM_TEMPLATE = ROOT / "backend" / "templates" / "rtm.xlsx"


@dataclass(frozen=True)
class GenerateResult:
    """파이프라인 산출물 경로와 생성 통계."""

    test_scenario_path: Path
    rtm_path: Path
    unit_count: int
    integration_count: int
    requirement_count: int


def generate_scenario(
    input_path: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
) -> TestScenarioDocument:
    """원천 문서 1건에서 검증된 테스트시나리오(JSON 모델)를 생성한다 (렌더링 제외).

    웹 흐름에서는 이 결과를 저장해 사람이 검수한 뒤 render_scenario_and_rtm 으로 렌더링한다.
    표지 정보(project_name 등)는 원천 문서에서 안정적으로 추출하기 어려워 인자로 받는다.
    """
    logger.info("원천 문서 파싱: %s", input_path)
    source = load_source(input_path)

    logger.info("테스트시나리오 LLM 생성 시작 (검증-재시도 루프)")
    prompt = build_test_scenario_prompt(
        source,
        TestScenarioDocument,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
    )
    scenario = generate_validated(prompt, TestScenarioDocument, system=TEST_SCENARIO_SYSTEM)
    logger.info(
        "테스트시나리오 생성 완료: 단위 %d건 + 통합 %d건",
        len(scenario.unit_test_cases),
        len(scenario.integration_test_cases),
    )
    return scenario


def render_scenario_and_rtm(scenario: TestScenarioDocument, output_dir: Path) -> GenerateResult:
    """검증된 테스트시나리오로 RTM 을 파생하고 엑셀 2종을 렌더링한다 (LLM 미사용).

    검수 후 편집된 시나리오에도 동일하게 적용된다.
    """
    rtm = build_rtm_from_scenario(scenario)
    validate_rtm_consistency(rtm, scenario)  # 파생 결과의 ID 정합성 재확인 (방어적)
    logger.info("RTM 파생 완료: 요건 %d건", len(rtm.rows))

    output_dir.mkdir(parents=True, exist_ok=True)
    ts_path = render_test_scenario(
        scenario, TEST_SCENARIO_TEMPLATE, output_dir / "test_scenario.xlsx"
    )
    rtm_path = render_rtm(rtm, RTM_TEMPLATE, output_dir / "rtm.xlsx")
    logger.info("렌더링 완료: %s, %s", ts_path, rtm_path)

    return GenerateResult(
        test_scenario_path=ts_path,
        rtm_path=rtm_path,
        unit_count=len(scenario.unit_test_cases),
        integration_count=len(scenario.integration_test_cases),
        requirement_count=len(rtm.rows),
    )


def generate_test_scenario_and_rtm(
    input_path: Path,
    output_dir: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
) -> GenerateResult:
    """원천 문서 1건에서 테스트시나리오·RTM 엑셀을 생성한다 (CLI 용 일괄 흐름)."""
    scenario = generate_scenario(
        input_path,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
    )
    return render_scenario_and_rtm(scenario, output_dir)
