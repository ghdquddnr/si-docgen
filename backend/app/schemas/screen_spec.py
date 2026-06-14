"""화면정의서(screen_spec) 산출물의 Pydantic 스키마.

필드 description 은 한국어로 작성하며, 이후 LLM 프롬프트의 스키마 설명으로 재사용된다.
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# 화면이 실현하는 요건 ID (REQ-xxx). 리스트 항목 형식 제약용
ReqId = Annotated[str, StringConstraints(pattern=r"^REQ-\d{3,}$")]


class ScreenField(BaseModel):
    """화면 항목 정의 표의 행 1개 — 목업의 번호 오버레이와 1:1 대응한다."""

    no: int = Field(..., ge=1, le=20, description="항목 번호. 목업 이미지의 ①②③ 번호와 일치 (1~20)")
    name: str = Field(..., min_length=1, description="항목명 (예: 사용자 ID)")
    field_type: str = Field(
        ..., min_length=1, description="항목 유형 (예: 텍스트박스, 콤보박스, 버튼, 그리드)"
    )
    required: bool = Field(..., description="필수 입력 여부 (표에는 Y/N 으로 표기)")
    description: str = Field("", description="항목 설명. 없으면 빈 문자열")


class Screen(BaseModel):
    """화면 1개 — 화면정의 표준 슬라이드 1장에 대응한다."""

    screen_id: str = Field(
        ...,
        pattern=r"^SCR-\d{3,}$",
        description="화면 ID. 'SCR-' 접두사 + 3자리 이상 숫자 (예: SCR-001)",
    )
    screen_name: str = Field(..., min_length=1, description="화면명 (예: 로그인)")
    menu_path: str = Field(
        ..., min_length=1, description="메뉴 경로 (예: 홈 > 사용자 관리 > 사용자 등록)"
    )
    req_ids: list[ReqId] = Field(
        default_factory=list,
        description="이 화면이 실현하는 연관 요건 ID 목록 (REQ-xxx). 추적성(요건→화면)에 사용",
    )
    fields: list[ScreenField] = Field(..., min_length=1, description="항목 정의 목록 (최소 1건)")
    logic: list[str] = Field(
        default_factory=list,
        description="처리 로직 설명. 줄 단위 목록이며 렌더링 시 '1. …' 형태로 번호가 붙는다",
    )


class ScreenSpecDocument(BaseModel):
    """화면정의서 산출물 전체 — 표지 정보와 화면 목록."""

    project_name: str = Field(..., min_length=1, description="프로젝트명 (표지)")
    system_name: str = Field(..., min_length=1, description="시스템명 (표지)")
    author: str = Field(..., min_length=1, description="작성자 (표지)")
    written_date: date = Field(..., description="작성일 (YYYY-MM-DD)")
    screens: list[Screen] = Field(
        ..., min_length=1, description="화면 목록. 화면 1개 = 슬라이드 1장"
    )
