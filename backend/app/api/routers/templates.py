"""양식 보관함 라우터 — 폴더/양식 CRUD, 기본 양식 다운로드.

업로드 양식은 기본 양식과 구조 호환 검증을 통과해야 저장된다(B1). 검증 실패는 400.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.schemas import TemplateFolderOut, TemplateKindOut, TemplateLibraryOut, TemplateOut
from app.db.models import Template, TemplateFolder
from app.db.session import get_db
from app.services import templates_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])

MEDIA_TYPES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class FolderIn(BaseModel):
    """폴더 생성 요청."""

    name: str
    parent_id: str | None = None


@router.get("", response_model=TemplateLibraryOut)
def get_library(db: Annotated[Session, Depends(get_db)]) -> TemplateLibraryOut:
    """양식 보관함 전체(폴더·양식·선택 가능 종류)를 반환한다."""
    return TemplateLibraryOut(
        folders=[TemplateFolderOut.model_validate(f) for f in svc.list_folders(db)],
        templates=[TemplateOut.model_validate(t) for t in svc.list_templates(db)],
        kinds=[
            TemplateKindOut(kind=k, label=svc.KIND_LABELS[k], ext=svc.KIND_EXT[k])
            for k in svc.DEFAULT_TEMPLATES
        ],
    )


@router.post("/folders", response_model=TemplateFolderOut, status_code=201)
def create_folder(body: FolderIn, db: Annotated[Session, Depends(get_db)]) -> TemplateFolder:
    """폴더를 생성한다 (parent_id 로 트리 구성)."""
    try:
        return svc.create_folder(db, name=body.name, parent_id=body.parent_id)
    except svc.TemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/folders/{folder_id}")
def delete_folder(folder_id: str, db: Annotated[Session, Depends(get_db)]) -> dict[str, bool]:
    """폴더와 그 하위(폴더·양식)를 삭제한다."""
    return {"deleted": svc.delete_folder(db, folder_id)}


@router.post("", response_model=TemplateOut, status_code=201)
async def upload_template(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(description="양식 파일 (.xlsx/.docx/.pptx)")],
    kind: Annotated[str, Form()],
    name: Annotated[str, Form()] = "",
    folder_id: Annotated[str, Form()] = "",
) -> Template:
    """양식을 업로드한다 (기본 양식과 구조 호환 검증 후 저장)."""
    content = await file.read()
    try:
        return svc.save_template(
            db,
            name=name,
            kind=kind,
            folder_id=folder_id or None,
            filename=file.filename or "template",
            data=content,
        )
    except svc.TemplateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except svc.TemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Annotated[Session, Depends(get_db)]) -> dict[str, bool]:
    """업로드된 양식을 삭제한다."""
    return {"deleted": svc.delete_template(db, template_id)}


@router.get("/default/{kind}")
def download_default(kind: str) -> FileResponse:
    """종류별 기본(번들) 양식을 내려받는다 (사용자가 서식만 수정해 재업로드하도록)."""
    if kind not in svc.DEFAULT_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"알 수 없는 양식 종류: {kind}")
    path = svc.DEFAULT_TEMPLATES[kind]
    ext = svc.KIND_EXT[kind]
    return FileResponse(
        path,
        filename=f"{kind}{ext}",
        media_type=MEDIA_TYPES.get(ext, "application/octet-stream"),
    )
