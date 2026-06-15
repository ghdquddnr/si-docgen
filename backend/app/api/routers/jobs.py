"""생성 잡 라우터 — 업로드/생성, 상태 조회."""

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.schemas import JobOut, RenderOut
from app.db.models import Job
from app.db.session import get_db
from app.schemas.requirement_spec import RequirementSpecDocument
from app.schemas.screen_spec import ScreenSpecDocument
from app.schemas.test_scenario import TestScenarioDocument
from app.schemas.user_manual import UserManualDocument
from app.services import job_service
from app.services.job_service import (
    UnknownScreenRefError,
    UnsupportedImageError,
    UnsupportedSourceError,
)

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# 다운로드 종류 → MIME 타입 (기본은 xlsx)
DOWNLOAD_MEDIA_TYPES = {
    "screen_spec": PPTX_MEDIA_TYPE,
    "requirement_spec": DOCX_MEDIA_TYPE,
    "user_manual": DOCX_MEDIA_TYPE,
}

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
    with_screens: Annotated[bool, Form()] = False,
    with_requirements: Annotated[bool, Form()] = False,
    with_wbs: Annotated[bool, Form()] = False,
    with_table_spec: Annotated[bool, Form()] = False,
    with_interface_spec: Annotated[bool, Form()] = False,
    with_user_manual: Annotated[bool, Form()] = False,
    start_date: Annotated[str, Form()] = "",
    requirement_spec_model: Annotated[str, Form()] = "",
    scenario_model: Annotated[str, Form()] = "",
    screen_spec_model: Annotated[str, Form()] = "",
    wbs_model: Annotated[str, Form()] = "",
    table_spec_model: Annotated[str, Form()] = "",
    interface_spec_model: Annotated[str, Form()] = "",
    user_manual_model: Annotated[str, Form()] = "",
) -> Job:
    """원천 문서를 업로드하고 백그라운드 생성 잡을 시작한다.

    with_requirements=True 면 요구사항정의서를 머리로 둔 4종 체인을, with_screens=True 면
    화면정의서까지의 3종 체인을 실행한다. *_model 은 단계별 모델 오버라이드.
    """
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
            with_screens=with_screens,
            with_requirements=with_requirements,
            with_wbs=with_wbs,
            with_table_spec=with_table_spec,
            with_interface_spec=with_interface_spec,
            with_user_manual=with_user_manual,
            start_date=start_date,
            requirement_spec_model=requirement_spec_model,
            scenario_model=scenario_model,
            screen_spec_model=screen_spec_model,
            wbs_model=wbs_model,
            table_spec_model=table_spec_model,
            interface_spec_model=interface_spec_model,
            user_manual_model=user_manual_model,
        )
    except UnsupportedSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background.add_task(job_service.run_job, job.id)
    return job


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Annotated[Session, Depends(get_db)]) -> Job:
    """잡 상태를 조회한다."""
    return _require_job(db, job_id)


@router.get("/{job_id}/scenario")
def get_scenario(job_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """생성·검수된 테스트시나리오 JSON 을 반환한다 (검수 화면용)."""
    job = _require_job(db, job_id)
    if job.scenario_json is None:
        raise HTTPException(status_code=409, detail="아직 생성된 시나리오가 없습니다")
    return job.scenario_json


@router.put("/{job_id}/scenario", response_model=JobOut)
def update_scenario(
    job_id: str,
    scenario: TestScenarioDocument,
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    """검수 화면에서 편집한 시나리오를 재검증 후 저장한다.

    본문은 TestScenarioDocument 로 자동 검증되므로 스키마 위반·TC ID 중복은 422 로 거부된다.
    RTM 정합성은 시나리오에서 결정론적으로 파생되므로 구조적으로 보장된다.
    """
    job = _require_job(db, job_id)
    job.scenario_json = scenario.model_dump(mode="json")
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}/screen-spec")
def get_screen_spec(job_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """생성된 화면정의서 JSON 을 반환한다 (체인 잡)."""
    job = _require_job(db, job_id)
    if job.screen_spec_json is None:
        raise HTTPException(status_code=409, detail="화면정의서가 없습니다 (체인 잡이 아님)")
    return job.screen_spec_json


@router.put("/{job_id}/screen-spec", response_model=JobOut)
def update_screen_spec(
    job_id: str,
    screen_spec: ScreenSpecDocument,
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    """검수 화면에서 편집한 화면정의서를 재검증 후 저장한다.

    본문은 ScreenSpecDocument 로 자동 검증되므로 스키마 위반(SCR ID 형식 등)은 422 로 거부된다.
    요건↔화면 추적성(REQ 참조)은 render 시점에 교차 검증된다.
    """
    job = _require_job(db, job_id)
    if job.screen_spec_json is None:
        raise HTTPException(status_code=409, detail="화면정의서가 없습니다 (체인 잡이 아님)")
    job.screen_spec_json = screen_spec.model_dump(mode="json")
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}/requirement-spec")
def get_requirement_spec(job_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """생성된 요구사항정의서 JSON 을 반환한다 (요건 머리 체인 잡)."""
    job = _require_job(db, job_id)
    if job.requirement_spec_json is None:
        raise HTTPException(status_code=409, detail="요구사항정의서가 없습니다 (요건 체인 잡 아님)")
    return job.requirement_spec_json


@router.put("/{job_id}/requirement-spec", response_model=JobOut)
def update_requirement_spec(
    job_id: str,
    requirement_spec: RequirementSpecDocument,
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    """검수 화면에서 편집한 요구사항정의서를 재검증 후 저장한다.

    본문은 RequirementSpecDocument 로 자동 검증되므로 스키마 위반(REQ ID 형식·요건 0건 등)은
    422 로 거부된다. 요건↔시나리오/화면 추적성은 render 시점에 교차 검증된다.
    """
    job = _require_job(db, job_id)
    if job.requirement_spec_json is None:
        raise HTTPException(status_code=409, detail="요구사항정의서가 없습니다 (요건 체인 잡 아님)")
    job.requirement_spec_json = requirement_spec.model_dump(mode="json")
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}/wbs")
def get_wbs(job_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """생성된 WBS JSON 을 반환한다 (with_wbs 잡)."""
    job = _require_job(db, job_id)
    if job.wbs_json is None:
        raise HTTPException(status_code=409, detail="WBS 가 없습니다 (WBS 생성 잡이 아님)")
    return job.wbs_json


@router.get("/{job_id}/table-spec")
def get_table_spec(job_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """생성된 테이블정의서 JSON 을 반환한다 (with_table_spec 잡)."""
    job = _require_job(db, job_id)
    if job.table_spec_json is None:
        raise HTTPException(status_code=409, detail="테이블정의서가 없습니다 (생성 잡이 아님)")
    return job.table_spec_json


@router.get("/{job_id}/interface-spec")
def get_interface_spec(job_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """생성된 인터페이스정의서 JSON 을 반환한다 (with_interface_spec 잡)."""
    job = _require_job(db, job_id)
    if job.interface_spec_json is None:
        raise HTTPException(status_code=409, detail="인터페이스정의서가 없습니다 (생성 잡이 아님)")
    return job.interface_spec_json


@router.get("/{job_id}/user-manual")
def get_user_manual(job_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """생성된 사용자 매뉴얼 JSON 을 반환한다 (with_user_manual 잡)."""
    job = _require_job(db, job_id)
    if job.user_manual_json is None:
        raise HTTPException(status_code=409, detail="사용자 매뉴얼이 없습니다 (생성 잡이 아님)")
    return job.user_manual_json


@router.put("/{job_id}/user-manual", response_model=JobOut)
def update_user_manual(
    job_id: str,
    user_manual: UserManualDocument,
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    """검수 화면에서 편집한 사용자 매뉴얼을 재검증 후 저장한다.

    본문은 UserManualDocument 로 자동 검증되므로 스키마 위반(섹션/단계 0건 등)은 422 로 거부된다.
    """
    job = _require_job(db, job_id)
    if job.user_manual_json is None:
        raise HTTPException(status_code=409, detail="사용자 매뉴얼이 없습니다 (생성 잡이 아님)")
    job.user_manual_json = user_manual.model_dump(mode="json")
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}/manual-images")
def list_manual_images(job_id: str, db: Annotated[Session, Depends(get_db)]) -> dict[str, bool]:
    """매뉴얼의 screen_ref 별 화면 캡처 업로드 여부를 반환한다 (검수 UI 표시용)."""
    job = _require_job(db, job_id)
    if job.user_manual_json is None:
        raise HTTPException(status_code=409, detail="사용자 매뉴얼이 없습니다 (생성 잡이 아님)")
    return job_service.list_manual_images(job_id, job.user_manual_json)


@router.post("/{job_id}/manual-images/{screen_ref}", status_code=201)
async def upload_manual_image(
    job_id: str,
    screen_ref: str,
    file: Annotated[UploadFile, File(description="화면 캡처 이미지 (.png/.jpg 등)")],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """특정 screen_ref 에 대응하는 화면 캡처 이미지를 업로드한다."""
    job = _require_job(db, job_id)
    if job.user_manual_json is None:
        raise HTTPException(status_code=409, detail="사용자 매뉴얼이 없습니다 (생성 잡이 아님)")
    content = await file.read()
    try:
        job_service.save_manual_image(
            job_id,
            job.user_manual_json,
            screen_ref,
            filename=file.filename or "image",
            data=content,
        )
    except UnknownScreenRefError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"screen_ref": screen_ref, "status": "uploaded"}


@router.delete("/{job_id}/manual-images/{screen_ref}")
def delete_manual_image(
    job_id: str, screen_ref: str, db: Annotated[Session, Depends(get_db)]
) -> dict[str, bool]:
    """업로드된 화면 캡처를 삭제한다."""
    _require_job(db, job_id)
    return {"deleted": job_service.delete_manual_image(job_id, screen_ref)}


@router.post("/{job_id}/render", response_model=RenderOut)
def render_job(job_id: str, db: Annotated[Session, Depends(get_db)]) -> RenderOut:
    """검수된 시나리오(+화면/요구사항/WBS/테이블/인터페이스/매뉴얼)를 재렌더링한다 (동기)."""
    job = _require_job(db, job_id)
    if job.scenario_json is None:
        raise HTTPException(status_code=409, detail="렌더링할 시나리오가 없습니다")
    result = job_service.render_job_outputs(
        job_id,
        job.scenario_json,
        job.screen_spec_json,
        job.requirement_spec_json,
        job.wbs_json,
        job.table_spec_json,
        job.interface_spec_json,
        job.user_manual_json,
    )
    return RenderOut(
        unit_count=result.unit_count,
        integration_count=result.integration_count,
        requirement_count=result.requirement_count,
        screen_count=result.screen_count,
        downloads={kind: f"/jobs/{job_id}/download/{kind}" for kind in result.kinds},
    )


@router.get("/{job_id}/download/{kind}")
def download(job_id: str, kind: str, db: Annotated[Session, Depends(get_db)]) -> FileResponse:
    """렌더링된 산출물을 다운로드한다 (kind: requirement_spec|test_scenario|rtm|screen_spec)."""
    _require_job(db, job_id)
    filename = job_service.OUTPUT_FILES.get(kind)
    if filename is None:
        raise HTTPException(status_code=404, detail=f"알 수 없는 산출물 종류: {kind}")
    path = job_service.output_dir(job_id) / filename
    if not path.is_file():
        raise HTTPException(status_code=409, detail="먼저 렌더링을 수행하세요")
    media_type = DOWNLOAD_MEDIA_TYPES.get(kind, XLSX_MEDIA_TYPE)
    return FileResponse(path, filename=filename, media_type=media_type)


def _require_job(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"잡을 찾을 수 없습니다: {job_id}")
    return job
