"""사용자 매뉴얼(user_manual) 산출물의 Pydantic 스키마.

매뉴얼은 섹션(기능)별 단계 설명과 화면 캡처로 구성된다. 캡처 이미지는 LLM 출력(JSON)에
바이너리로 담지 않고, 각 단계가 **이미지 키(screen_ref)** 로 참조한다. 실제 이미지 삽입은
렌더링 단계에서 별도로 전달되는 이미지 맵으로 처리하며, 캡처 방식(실제 앱/생성 화면)과 무관하다.
"""

from datetime import date

from pydantic import BaseModel, Field


class ManualStep(BaseModel):
    """매뉴얼 단계 1개 — 수행 설명과 (선택적) 화면 캡처 참조."""

    instruction: str = Field(
        ..., min_length=1, description="단계 수행 내용 (예: ID/PW 입력 후 로그인)"
    )
    screen_ref: str = Field(
        "",
        description="연관 화면/캡처 키 (예: SCR-001). 렌더 시 이미지 삽입에 사용. 없으면 빈 문자열",
    )
    caption: str = Field("", description="이미지 캡션. 없으면 빈 문자열")


class ManualSection(BaseModel):
    """매뉴얼 섹션 1개 — 기능/메뉴 단위의 단계 묶음."""

    title: str = Field(..., min_length=1, description="섹션 제목 (예: 로그인)")
    description: str = Field("", description="섹션 개요. 없으면 빈 문자열")
    steps: list[ManualStep] = Field(..., min_length=1, description="단계 목록 (최소 1건)")


class UserManualDocument(BaseModel):
    """사용자 매뉴얼 산출물 전체 — 표지 정보와 섹션 목록."""

    project_name: str = Field(..., min_length=1, description="프로젝트명 (표지)")
    system_name: str = Field(..., min_length=1, description="시스템명 (표지)")
    author: str = Field(..., min_length=1, description="작성자 (표지)")
    written_date: date = Field(..., description="작성일 (YYYY-MM-DD)")
    sections: list[ManualSection] = Field(..., min_length=1, description="섹션 목록 (최소 1건)")
