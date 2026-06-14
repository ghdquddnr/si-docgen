"""요건추적표(RTM, requirement traceability matrix) 산출물의 Pydantic 스키마.

필드 description 은 한국어로 작성하며, 이후 LLM 프롬프트의 스키마 설명으로 재사용된다.
RTM 은 테스트시나리오와 동시 생성하여 ID 정합성(요건↔화면↔TC 추적성)을 보장한다.
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.exceptions import ValidationFailedError
from app.schemas.requirement_spec import RequirementSpecDocument
from app.schemas.screen_spec import ScreenSpecDocument
from app.schemas.test_scenario import TestScenarioDocument

# 리스트 항목에 ID 형식 제약을 부여하기 위한 제약 문자열 타입
ReqId = Annotated[str, StringConstraints(pattern=r"^REQ-\d{3,}$")]
ScrId = Annotated[str, StringConstraints(pattern=r"^SCR-\d{3,}$")]
TcId = Annotated[str, StringConstraints(pattern=r"^TC-\d{3,}$")]
ProgramId = Annotated[str, StringConstraints(min_length=1)]


class StageReflection(BaseModel):
    """단계별 반영 여부 — SI 표준 공정(분석/설계/구현/시험)에서의 반영 상태."""

    analysis: bool = Field(False, description="분석 단계 반영 여부")
    design: bool = Field(False, description="설계 단계 반영 여부")
    implementation: bool = Field(False, description="구현 단계 반영 여부")
    test: bool = Field(False, description="시험 단계 반영 여부")


class RTMRow(BaseModel):
    """요건추적표의 행 1개 — 요건 1건과 그에 연관된 화면/프로그램/TC 추적 정보."""

    req_id: ReqId = Field(..., description="요건 ID. 'REQ-' 접두사 + 3자리 이상 숫자 (예: REQ-001)")
    req_name: str = Field(..., min_length=1, description="요건명 (한 문장 요약)")
    screen_ids: list[ScrId] = Field(
        default_factory=list,
        description="연관 화면 ID 목록 (SCR-xxx). 백엔드 전용 등 화면이 없으면 빈 목록",
    )
    program_ids: list[ProgramId] = Field(
        default_factory=list, description="연관 프로그램 ID 목록. 없으면 빈 목록"
    )
    tc_ids: list[TcId] = Field(
        default_factory=list,
        description="연관 테스트케이스 ID 목록 (TC-xxx). 시험 미작성 단계면 빈 목록",
    )
    stage_reflection: StageReflection = Field(
        default_factory=StageReflection,
        description="단계별(분석/설계/구현/시험) 반영 여부",
    )


class RTMDocument(BaseModel):
    """요건추적표 산출물 전체 — 표지 정보와 추적 행 목록."""

    project_name: str = Field(..., min_length=1, description="프로젝트명 (표지 정보 영역)")
    system_name: str = Field(..., min_length=1, description="시스템명 (표지 정보 영역)")
    author: str = Field(..., min_length=1, description="작성자 (표지 정보 영역)")
    written_date: date = Field(..., description="작성일 (YYYY-MM-DD)")
    rows: list[RTMRow] = Field(default_factory=list, description="요건추적표 행 목록")

    @model_validator(mode="after")
    def _check_unique_req_id(self) -> "RTMDocument":
        """RTM 은 요건 1건당 1행이므로 요건 ID 중복을 금지한다."""
        seen: set[str] = set()
        duplicates: set[str] = set()
        for row in self.rows:
            if row.req_id in seen:
                duplicates.add(row.req_id)
            seen.add(row.req_id)
        if duplicates:
            raise ValueError(f"요건 ID 가 중복되었습니다: {sorted(duplicates)}")
        return self


def validate_rtm_consistency(rtm: RTMDocument, scenario: TestScenarioDocument) -> None:
    """RTM 과 테스트시나리오 간 ID 정합성을 검증한다.

    절대 원칙 6(존재하지 않는 ID 참조 금지)의 구현 지점:
    - RTM 이 참조하는 모든 TC ID 는 테스트시나리오에 존재해야 한다 (TC ID ⊆ 시나리오 TC).
    - 테스트시나리오가 참조하는 모든 요건 ID 는 RTM 에 추적되어 있어야 한다 (요건 추적 완전성).

    위반 시 어떤 ID 가 문제인지 포함한 ValidationFailedError 를 올린다.
    """
    scenario_cases = scenario.unit_test_cases + scenario.integration_test_cases
    scenario_tc_ids = {c.tc_id for c in scenario_cases}
    scenario_req_ids = {c.req_id for c in scenario_cases}
    rtm_tc_ids = {tc for row in rtm.rows for tc in row.tc_ids}
    rtm_req_ids = {row.req_id for row in rtm.rows}

    dangling_tc = rtm_tc_ids - scenario_tc_ids
    untraced_req = scenario_req_ids - rtm_req_ids

    errors: list[str] = []
    if dangling_tc:
        errors.append(f"RTM 이 참조하는 TC ID 가 테스트시나리오에 없음: {sorted(dangling_tc)}")
    if untraced_req:
        errors.append(f"테스트시나리오의 요건 ID 가 RTM 에 추적되지 않음: {sorted(untraced_req)}")
    if errors:
        raise ValidationFailedError(" / ".join(errors))


def _screen_ids_by_req(screen_spec: "ScreenSpecDocument | None") -> dict[str, list[str]]:
    """요건 ID → 그 요건을 실현하는 화면 ID 목록 (화면 순서 유지, 중복 제거)."""
    mapping: dict[str, list[str]] = {}
    if screen_spec is None:
        return mapping
    for screen in screen_spec.screens:
        for req_id in screen.req_ids:
            ids = mapping.setdefault(req_id, [])
            if screen.screen_id not in ids:
                ids.append(screen.screen_id)
    return mapping


def build_rtm_from_chain(
    scenario: TestScenarioDocument,
    screen_spec: "ScreenSpecDocument | None" = None,
    requirement_spec: "RequirementSpecDocument | None" = None,
) -> RTMDocument:
    """테스트시나리오(+선택적 화면정의서/요구사항정의서)로부터 RTM 을 결정론적으로 파생한다.

    요건 ID 별로 테스트케이스를 묶어 추적 행을 만들고, 화면정의서가 주어지면 각 요건의
    screen_ids 를 채운다. 구성상 RTM 의 요건/TC ID 가 시나리오와 항상 일치한다.

    requirement_spec 이 주어지면(체인의 머리) 그것을 요건의 단일 진실 공급원으로 삼는다:
    - 행은 요구사항정의서의 요건마다 1행 생성한다(TC 가 아직 없는 요건도 추적 행으로 노출 →
      커버리지 공백이 보인다).
    - req_name 은 요구사항정의서의 정식 요건명을 사용한다(시나리오 대분류 대체 한계 해소).
    미지정 시 기존 동작: 시나리오에 등장한 요건만 행으로 만들고, 요건명은 '대분류 - 중분류' 로 대체.

    공통 한계: 프로그램 ID 는 비운다(범위 밖). 단계별 반영은 분석=True, 설계=화면 유무,
    시험=TC 유무로 파생한다.
    """
    cases = scenario.unit_test_cases + scenario.integration_test_cases
    tc_ids_by_req: dict[str, list[str]] = {}
    fallback_name_by_req: dict[str, str] = {}
    for case in cases:
        tc_ids_by_req.setdefault(case.req_id, []).append(case.tc_id)
        fallback_name_by_req.setdefault(
            case.req_id, f"{case.category_major} - {case.category_minor}"
        )

    screens_by_req = _screen_ids_by_req(screen_spec)

    if requirement_spec is not None:
        # 요구사항정의서의 요건 순서·정식 요건명을 기준으로 행을 만든다
        ordered = [(r.req_id, r.name) for r in requirement_spec.requirements]
    else:
        ordered = [(req_id, fallback_name_by_req[req_id]) for req_id in tc_ids_by_req]

    rows = [
        RTMRow(
            req_id=req_id,
            req_name=req_name,
            screen_ids=screens_by_req.get(req_id, []),
            tc_ids=tc_ids_by_req.get(req_id, []),
            stage_reflection=StageReflection(
                analysis=True,
                design=bool(screens_by_req.get(req_id)),  # 화면 설계가 있으면 설계 반영
                implementation=False,
                test=bool(tc_ids_by_req.get(req_id)),  # TC 가 있으면 시험 반영
            ),
        )
        for req_id, req_name in ordered
    ]
    return RTMDocument(
        project_name=scenario.project_name,
        system_name=scenario.system_name,
        author=scenario.author,
        written_date=scenario.written_date,
        rows=rows,
    )


def build_rtm_from_scenario(scenario: TestScenarioDocument) -> RTMDocument:
    """테스트시나리오만으로 RTM 을 파생한다 (화면 ID 는 비움). build_rtm_from_chain 의 단축형."""
    return build_rtm_from_chain(scenario, None)


def validate_requirement_consistency(
    requirement_spec: RequirementSpecDocument,
    scenario: TestScenarioDocument,
    screen_spec: "ScreenSpecDocument | None" = None,
) -> None:
    """체인의 머리(요구사항정의서) 기준 요건 추적성을 검증한다.

    요구사항정의서를 REQ ID 의 단일 진실 공급원으로 삼아, 시나리오와 화면정의서가
    참조하는 모든 요건 ID 가 요구사항정의서에 존재하는지 확인한다(유령 참조 거부).
    요구사항정의서에 TC/화면이 아직 없는 요건이 있어도 통과한다(단방향 — 커버리지 공백 허용).
    위반 시 어떤 ID 가 문제인지 포함한 ValidationFailedError 를 올린다.
    """
    spec_req_ids = {r.req_id for r in requirement_spec.requirements}
    scenario_cases = scenario.unit_test_cases + scenario.integration_test_cases
    scenario_req_ids = {c.req_id for c in scenario_cases}
    screen_req_ids = (
        {req_id for s in screen_spec.screens for req_id in s.req_ids} if screen_spec else set()
    )

    errors: list[str] = []
    unknown_scenario = scenario_req_ids - spec_req_ids
    unknown_screen = screen_req_ids - spec_req_ids
    if unknown_scenario:
        errors.append(
            f"테스트시나리오 요건 ID 가 요구사항정의서에 없음: {sorted(unknown_scenario)}"
        )
    if unknown_screen:
        errors.append(f"화면이 참조하는 요건 ID 가 요구사항정의서에 없음: {sorted(unknown_screen)}")
    if errors:
        raise ValidationFailedError(" / ".join(errors))


def validate_screen_consistency(
    screen_spec: "ScreenSpecDocument", scenario: TestScenarioDocument
) -> None:
    """화면정의서와 테스트시나리오 간 요건 추적성을 검증한다 (REQ→SCR 고리).

    화면이 참조하는 모든 요건 ID 는 테스트시나리오가 다루는 요건 집합에 존재해야 한다.
    위반(존재하지 않는 요건 참조) 시 ValidationFailedError.
    """
    scenario_cases = scenario.unit_test_cases + scenario.integration_test_cases
    scenario_req_ids = {c.req_id for c in scenario_cases}
    screen_req_ids = {req_id for s in screen_spec.screens for req_id in s.req_ids}

    unknown = screen_req_ids - scenario_req_ids
    if unknown:
        raise ValidationFailedError(
            f"화면이 참조하는 요건 ID 가 테스트시나리오에 없음: {sorted(unknown)}"
        )
