"""테스트시나리오(test_scenario) 산출물의 Pydantic 스키마.

필드 description 은 한국어로 작성하며, 이후 LLM 프롬프트의 스키마 설명으로 재사용된다.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """테스트케이스 1건 — 엑셀 시트의 데이터 행 1개에 대응한다."""

    tc_id: str = Field(
        ...,
        pattern=r"^TC-\d{3,}$",
        description="테스트케이스 ID. 'TC-' 접두사 + 3자리 이상 숫자 (예: TC-001)",
    )
    req_id: str = Field(
        ...,
        pattern=r"^REQ-\d{3,}$",
        description="연관 요건 ID. 'REQ-' 접두사 + 3자리 이상 숫자 (예: REQ-012)",
    )
    category_major: str = Field(
        ..., min_length=1, description="대분류 — 업무 영역 (예: 사용자 관리)"
    )
    category_minor: str = Field(..., min_length=1, description="중분류 — 세부 기능 (예: 로그인)")
    scenario_name: str = Field(..., min_length=1, description="테스트 시나리오명 (한 문장 요약)")
    precondition: str = Field(
        "", description="테스트 수행 전 충족해야 할 사전조건. 없으면 빈 문자열"
    )
    test_steps: list[str] = Field(
        ...,
        min_length=1,
        description="테스트 절차. 단계별 문자열 목록이며 렌더링 시 '1. …' 형태로 번호가 붙는다",
    )
    expected_result: str = Field(..., min_length=1, description="테스트 절차 수행 후의 기대 결과")
    result: Literal["Pass", "Fail"] | None = Field(
        None, description="수행 결과. Pass 또는 Fail, 미수행 상태면 null"
    )
    note: str = Field("", description="비고. 없으면 빈 문자열")


class TestScenarioDocument(BaseModel):
    """테스트시나리오 산출물 전체 — 표지 정보와 단위/통합 테스트케이스 목록."""

    project_name: str = Field(..., min_length=1, description="프로젝트명 (표지 정보 영역)")
    system_name: str = Field(..., min_length=1, description="시스템명 (표지 정보 영역)")
    author: str = Field(..., min_length=1, description="작성자 (표지 정보 영역)")
    written_date: date = Field(..., description="작성일 (YYYY-MM-DD)")
    unit_test_cases: list[TestCase] = Field(
        default_factory=list, description="'단위테스트' 시트에 들어갈 테스트케이스 목록"
    )
    integration_test_cases: list[TestCase] = Field(
        default_factory=list, description="'통합테스트' 시트에 들어갈 테스트케이스 목록"
    )
