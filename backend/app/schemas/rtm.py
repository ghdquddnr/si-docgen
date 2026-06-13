"""요건추적표(RTM, requirement traceability matrix) 산출물의 Pydantic 스키마.

필드 description 은 한국어로 작성하며, 이후 LLM 프롬프트의 스키마 설명으로 재사용된다.
RTM 은 테스트시나리오와 동시 생성하여 ID 정합성(요건↔화면↔TC 추적성)을 보장한다.
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.exceptions import ValidationFailedError
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
