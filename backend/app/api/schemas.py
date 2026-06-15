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
    with_user_manual: bool
    error: str | None
    created_at: datetime


class RenderOut(BaseModel):
    """재렌더링 결과 요약."""

    unit_count: int
    integration_count: int
    requirement_count: int
    screen_count: int
    downloads: dict[str, str]  # kind -> 다운로드 경로


class TemplateOut(BaseModel):
    """업로드된 양식(템플릿) 조회 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    kind: str
    folder_id: str | None
    original_filename: str
    created_at: datetime


class TemplateFolderOut(BaseModel):
    """양식 폴더 조회 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    parent_id: str | None
    created_at: datetime


class TemplateKindOut(BaseModel):
    """선택 가능한 양식 종류(라벨·확장자)."""

    kind: str
    label: str
    ext: str


class TemplateLibraryOut(BaseModel):
    """양식 보관함 전체 — 폴더·양식·종류 목록 (프론트가 트리로 구성)."""

    folders: list[TemplateFolderOut]
    templates: list[TemplateOut]
    kinds: list[TemplateKindOut]
