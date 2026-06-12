"""요구사항정의서(requirement_spec) 산출물의 Pydantic 스키마.

필드 description 은 한국어로 작성하며, 이후 LLM 프롬프트의 스키마 설명으로 재사용된다.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Revision(BaseModel):
    """개정 이력 표의 행 1개."""

    version: str = Field(..., min_length=1, description="버전 (예: 1.0)")
    revised_date: date = Field(..., description="개정일 (YYYY-MM-DD)")
    author: str = Field(..., min_length=1, description="작성자")
    description: str = Field(..., min_length=1, description="변경 내용 요약")


class Requirement(BaseModel):
    """요건 1건 — 요건 목록 표의 행 1개와 요건 상세 섹션 1개에 대응한다."""

    req_id: str = Field(
        ...,
        pattern=r"^REQ-\d{3,}$",
        description="요건 ID. 'REQ-' 접두사 + 3자리 이상 숫자 (예: REQ-001)",
    )
    name: str = Field(..., min_length=1, description="요건명 (간결한 명사형)")
    category: str = Field(
        ..., min_length=1, description="요건 구분 (예: 기능, 비기능, 인터페이스, 보안)"
    )
    priority: Literal["상", "중", "하"] = Field(..., description="중요도 (상/중/하)")
    description: str = Field(..., min_length=1, description="요건 상세 설명")
    note: str = Field("", description="비고. 없으면 빈 문자열")


class RequirementSpecDocument(BaseModel):
    """요구사항정의서 산출물 전체 — 표지 정보, 개정 이력, 요건 목록/상세."""

    project_name: str = Field(..., min_length=1, description="프로젝트명 (표지)")
    system_name: str = Field(..., min_length=1, description="시스템명 (표지)")
    doc_no: str = Field(..., min_length=1, description="문서번호 (예: REQ-SPEC-2026-001)")
    author: str = Field(..., min_length=1, description="작성자 (표지)")
    written_date: date = Field(..., description="작성일 (YYYY-MM-DD)")
    revisions: list[Revision] = Field(
        default_factory=list, description="개정 이력 목록 (최초 작성 포함)"
    )
    requirements: list[Requirement] = Field(
        ..., min_length=1, description="요건 목록. 최소 1건 필요하며 목록 표와 상세 섹션에 사용"
    )
