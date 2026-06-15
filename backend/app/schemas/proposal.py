"""제안서(proposal) 산출물의 Pydantic 스키마.

RFP(제안요청서)를 분석해 생성하는 제안서 초안. LLM 은 구조화된 JSON(표지 정보 + 슬라이드별
제목·핵심 불릿)까지만 만들고, PPTX 렌더링은 결정론적 렌더러가 템플릿을 보존하며 수행한다.
표준 SI 제안서 목차(사업 이해·추진 전략·수행 방안·일정·조직·품질/보안·기대 효과)를 권장한다.
"""

from datetime import date

from pydantic import BaseModel, Field, field_validator


class ProposalSlide(BaseModel):
    """제안서 슬라이드 1장 — 제목과 핵심 불릿."""

    title: str = Field(..., min_length=1, description="슬라이드 제목 (예: 사업 이해, 추진 전략)")
    bullets: list[str] = Field(
        ..., min_length=1, description="핵심 내용 불릿 목록 (각 항목 한 줄, 최소 1건)"
    )

    @field_validator("bullets")
    @classmethod
    def _no_empty_bullets(cls, v: list[str]) -> list[str]:
        if any(not b.strip() for b in v):
            raise ValueError("빈 불릿은 허용되지 않습니다")
        return v


class ProposalDocument(BaseModel):
    """제안서 산출물 전체 — 표지 정보와 슬라이드 목록."""

    project_name: str = Field(..., min_length=1, description="사업명/프로젝트명 (표지)")
    system_name: str = Field("", description="시스템명 (선택, 표지)")
    author: str = Field(..., min_length=1, description="제안사 (표지)")
    written_date: date = Field(..., description="제안 일자 (YYYY-MM-DD)")
    title: str = Field(..., min_length=1, description="제안서 제목 (예: 차세대 포털 구축 제안서)")
    client: str = Field(..., min_length=1, description="발주처 (표지)")
    slides: list[ProposalSlide] = Field(
        ..., min_length=1, description="제안서 슬라이드 목록 (최소 1건)"
    )
