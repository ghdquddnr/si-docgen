"""API 요청/응답 Pydantic 스키마.

ORM 모델(Job)과 분리해 외부 노출 형태를 명시적으로 관리한다.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import JobStatus


class JobOut(BaseModel):
    """잡 조회 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: JobStatus
    input_filename: str
    project_name: str
    system_name: str
    author: str
    written_date: str
    with_screens: bool
    with_requirements: bool
    with_wbs: bool
    with_table_spec: bool
    with_interface_spec: bool
    error: str | None
    created_at: datetime


class RenderOut(BaseModel):
    """재렌더링 결과 요약."""

    unit_count: int
    integration_count: int
    requirement_count: int
    screen_count: int
    downloads: dict[str, str]  # kind -> 다운로드 경로
