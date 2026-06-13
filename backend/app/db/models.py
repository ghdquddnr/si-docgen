"""ORM 모델 정의.

타입은 특정 DB 에 종속되지 않게 선택한다 (JSON, String 등 이식 가능 타입).
status 등 열거형은 native_enum=False 로 VARCHAR 저장 → PostgreSQL/MySQL 전환 시 호환.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, String, Text, func
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
    # 생성/검수된 테스트시나리오 JSON (검증 통과본). 미생성이면 null
    scenario_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 실패 시 사람이 읽을 오류 메시지
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
