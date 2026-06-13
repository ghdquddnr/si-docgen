"""생성 잡 라우터 — 업로드/생성, 상태 조회."""

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import JobOut
from app.db.models import Job
from app.db.session import get_db
from app.services import job_service
from app.services.job_service import UnsupportedSourceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut, status_code=201)
async def create_job(
    background: BackgroundTasks,
    file: Annotated[UploadFile, File(description="원천 문서 (.docx/.pdf/.md/.txt)")],
    db: Annotated[Session, Depends(get_db)],
    project_name: Annotated[str, Form()] = "프로젝트",
    system_name: Annotated[str, Form()] = "시스템",
    author: Annotated[str, Form()] = "작성자",
    written_date: Annotated[str, Form()] = "",
) -> Job:
    """원천 문서를 업로드하고 백그라운드 생성 잡을 시작한다."""
    content = await file.read()
    try:
        job = job_service.create_job(
            db,
            filename=file.filename or "upload",
            file_bytes=content,
            project_name=project_name,
            system_name=system_name,
            author=author,
            written_date=written_date,
        )
    except UnsupportedSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background.add_task(job_service.run_job, job.id)
    return job


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Annotated[Session, Depends(get_db)]) -> Job:
    """잡 상태를 조회한다."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"잡을 찾을 수 없습니다: {job_id}")
    return job
