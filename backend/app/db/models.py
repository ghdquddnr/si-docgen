"""ORM 모델 정의.

타입은 특정 DB 에 종속되지 않게 선택한다 (JSON, String 등 이식 가능 타입).
status 등 열거형은 native_enum=False 로 VARCHAR 저장 → PostgreSQL/MySQL 전환 시 호환.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Boolean, DateTime, String, Text, false, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobStatus(StrEnum):
    """생성 잡 상태."""

    PENDING = "pending"  # 생성 대기
    RUNNING = "running"  # 파이프라인 실행 중
    SUCCEEDED = "succeeded"  # 생성 완료 (검수 가능)
    FAILED = "failed"  # 생성 실패


class Job(Base):
    """산출물 생성 잡 1건 — 업로드부터 검수·렌더링까지의 상태를 담는다."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, native_enum=False, length=16), default=JobStatus.PENDING, index=True
    )
    input_filename: Mapped[str] = mapped_column(String(255))
    # 진행 단계 표시(파싱/LLM 생성/완료 등). SSE 스트림용 세분 상태이며 status 와 별개
    progress: Mapped[str | None] = mapped_column(String(32), nullable=True)
    project_name: Mapped[str] = mapped_column(String(255), default="프로젝트")
    system_name: Mapped[str] = mapped_column(String(255), default="시스템")
    author: Mapped[str] = mapped_column(String(255), default="작성자")
    written_date: Mapped[str] = mapped_column(String(10), default="")
    # 발주처(client) — 제안서 표지에 쓰인다. 다른 산출물에서는 비어 있어도 무방
    client: Mapped[str] = mapped_column(String(255), default="", server_default="")
    # 생성/검수된 테스트시나리오 JSON (검증 통과본). 미생성이면 null
    scenario_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 체인 실행 여부(화면정의서까지 생성) 및 생성된 화면정의서 JSON
    with_screens: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    screen_spec_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 요구사항정의서를 체인의 머리로 생성하는지 여부 및 생성된 요구사항정의서 JSON
    with_requirements: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    requirement_spec_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # WBS(작업분해구조) 생성 여부·결과 JSON·일정 기준 시작일 (체인과 독립적인 산출물)
    with_wbs: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    wbs_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    start_date: Mapped[str] = mapped_column(String(10), default="", server_default="")
    # 테이블정의서 생성 여부·결과 JSON (체인과 독립적인 산출물)
    with_table_spec: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    table_spec_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 인터페이스정의서 생성 여부·결과 JSON (체인과 독립적인 산출물)
    with_interface_spec: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    interface_spec_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 사용자 매뉴얼 생성 여부·결과 JSON (체인과 독립적인 산출물). 화면 캡처는 별도 업로드
    with_user_manual: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    user_manual_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 제안서(RFP→PPTX) 생성 여부·결과 JSON (체인과 독립적인 산출물)
    with_proposal: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    proposal_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 단계별 모델 오버라이드(잡 단위). 미지정이면 설정/기본 모델
    requirement_spec_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scenario_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    screen_spec_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    wbs_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    table_spec_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    interface_spec_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_manual_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    proposal_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # 산출물 종류별 선택한 양식(템플릿) id 맵 {kind: template_id}. 없으면 기본 양식 사용
    template_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 실패 시 사람이 읽을 오류 메시지
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class TemplateFolder(Base):
    """양식 보관함 폴더 (회사/고객사별 분류용 트리). parent_id 로 계층 구성."""

    __tablename__ = "template_folders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Template(Base):
    """사용자가 업로드한 산출물 양식(템플릿) 1건. 구조는 기본 양식과 호환되어야 한다(B1)."""

    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    # 산출물 종류 (test_scenario/rtm/requirement_spec/screen_spec/wbs/table_spec/...)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    folder_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
