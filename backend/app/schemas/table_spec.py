"""테이블정의서(table_spec) 산출물의 Pydantic 스키마.

목록형 테이블정의서 — 테이블별 컬럼을 한 시트의 행으로 펼쳐 표현한다.
필드 description 은 한국어로 작성하며, 이후 LLM 프롬프트의 스키마 설명으로 재사용된다.
"""

from datetime import date

from pydantic import BaseModel, Field, model_validator


class Column(BaseModel):
    """테이블 컬럼 1개 — 테이블정의서의 데이터 행 1개에 대응한다."""

    logical_name: str = Field(..., min_length=1, description="컬럼 논리명 (예: 사용자 ID)")
    physical_name: str = Field(..., min_length=1, description="컬럼 물리명 (예: USER_ID)")
    data_type: str = Field(
        ..., min_length=1, description="데이터 타입(길이 포함). 예: VARCHAR(50), NUMBER, DATE"
    )
    is_pk: bool = Field(False, description="기본키(PK) 여부")
    is_nullable: bool = Field(True, description="Null 허용 여부 (표에는 Y/N 으로 표기)")
    fk_ref: str = Field(
        "", description="외래키 참조 (예: USERS.USER_ID). 외래키가 아니면 빈 문자열"
    )
    default: str = Field("", description="기본값. 없으면 빈 문자열")
    description: str = Field("", description="컬럼 설명. 없으면 빈 문자열")


class Table(BaseModel):
    """테이블 1개 — 메타 정보와 컬럼 목록."""

    logical_name: str = Field(..., min_length=1, description="테이블 논리명 (예: 사용자)")
    physical_name: str = Field(..., min_length=1, description="테이블 물리명 (예: TB_USER)")
    description: str = Field("", description="테이블 설명. 없으면 빈 문자열")
    columns: list[Column] = Field(..., min_length=1, description="컬럼 목록 (최소 1건)")

    @model_validator(mode="after")
    def _check_unique_column(self) -> "Table":
        """한 테이블 안에서 컬럼 물리명은 유일해야 한다."""
        names = [c.physical_name for c in self.columns]
        dups = sorted({n for n in names if names.count(n) > 1})
        if dups:
            raise ValueError(f"컬럼 물리명이 중복되었습니다 ({self.physical_name}): {dups}")
        return self


class TableSpecDocument(BaseModel):
    """테이블정의서 산출물 전체 — 표지 정보와 테이블 목록."""

    project_name: str = Field(..., min_length=1, description="프로젝트명 (표지)")
    system_name: str = Field(..., min_length=1, description="시스템명 (표지)")
    author: str = Field(..., min_length=1, description="작성자 (표지)")
    written_date: date = Field(..., description="작성일 (YYYY-MM-DD)")
    tables: list[Table] = Field(..., min_length=1, description="테이블 목록 (최소 1건)")

    @model_validator(mode="after")
    def _check_unique_table(self) -> "TableSpecDocument":
        """테이블 물리명은 문서 전체에서 유일해야 한다."""
        names = [t.physical_name for t in self.tables]
        dups = sorted({n for n in names if names.count(n) > 1})
        if dups:
            raise ValueError(f"테이블 물리명이 중복되었습니다: {dups}")
        return self
