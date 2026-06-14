"""인터페이스정의서(interface_spec) 산출물의 Pydantic 스키마.

목록형 — 인터페이스별 메시지 항목을 한 시트의 행으로 펼쳐 표현한다.
필드 description 은 한국어로 작성하며, 이후 LLM 프롬프트의 스키마 설명으로 재사용된다.
"""

from datetime import date

from pydantic import BaseModel, Field, model_validator


class MessageField(BaseModel):
    """인터페이스 메시지 항목 1개 — 인터페이스정의서의 데이터 행 1개에 대응한다."""

    name: str = Field(..., min_length=1, description="항목명 (예: 사용자 ID)")
    data_type: str = Field(
        ..., min_length=1, description="데이터 타입(길이 포함). 예: String(20), Number, Date"
    )
    required: bool = Field(..., description="필수 여부 (표에는 Y/N 으로 표기)")
    description: str = Field("", description="항목 설명. 없으면 빈 문자열")


class Interface(BaseModel):
    """인터페이스 1개 — 송수신/연계 메타 정보와 메시지 항목 목록."""

    interface_id: str = Field(
        ...,
        pattern=r"^IF-\d{3,}$",
        description="인터페이스 ID. 'IF-' 접두사 + 3자리 이상 숫자 (예: IF-001)",
    )
    name: str = Field(..., min_length=1, description="인터페이스명 (예: 사용자 정보 연계)")
    send_system: str = Field(..., min_length=1, description="송신 시스템 (예: 인사시스템)")
    recv_system: str = Field(..., min_length=1, description="수신 시스템 (예: 포털시스템)")
    method: str = Field(
        ..., min_length=1, description="연계 방식 (예: REST API, FTP, MQ, DB Link, Web Service)"
    )
    cycle: str = Field(..., min_length=1, description="연계 주기 (예: 실시간, 일 1회 배치, 수시)")
    fields: list[MessageField] = Field(..., min_length=1, description="메시지 항목 목록 (최소 1건)")

    @model_validator(mode="after")
    def _check_unique_field(self) -> "Interface":
        """한 인터페이스 안에서 항목명은 유일해야 한다."""
        names = [f.name for f in self.fields]
        dups = sorted({n for n in names if names.count(n) > 1})
        if dups:
            raise ValueError(f"항목명이 중복되었습니다 ({self.interface_id}): {dups}")
        return self


class InterfaceSpecDocument(BaseModel):
    """인터페이스정의서 산출물 전체 — 표지 정보와 인터페이스 목록."""

    project_name: str = Field(..., min_length=1, description="프로젝트명 (표지)")
    system_name: str = Field(..., min_length=1, description="시스템명 (표지)")
    author: str = Field(..., min_length=1, description="작성자 (표지)")
    written_date: date = Field(..., description="작성일 (YYYY-MM-DD)")
    interfaces: list[Interface] = Field(..., min_length=1, description="인터페이스 목록 (최소 1건)")

    @model_validator(mode="after")
    def _check_unique_interface(self) -> "InterfaceSpecDocument":
        """인터페이스 ID 는 문서 전체에서 유일해야 한다."""
        ids = [i.interface_id for i in self.interfaces]
        dups = sorted({i for i in ids if ids.count(i) > 1})
        if dups:
            raise ValueError(f"인터페이스 ID 가 중복되었습니다: {dups}")
        return self
