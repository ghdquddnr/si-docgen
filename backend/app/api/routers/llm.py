"""LLM 설정 라우터 — 제공자 목록, API 키 CRUD, 생성 모델 CRUD, Ollama 조회."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import (
    LlmCredentialCreate,
    LlmCredentialOut,
    LlmModelCreate,
    LlmModelEnabledUpdate,
    LlmModelOut,
    LlmProviderOut,
)
from app.db.models import ApiCredential, LlmModel
from app.db.session import get_db
from app.llm import crypto
from app.services import llm_settings_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/providers", response_model=list[LlmProviderOut])
def list_providers() -> list[LlmProviderOut]:
    """선택 가능한 LLM 제공자 목록."""
    return [
        LlmProviderOut(provider=p, label=info["label"], needs_key=info["needs_key"])
        for p, info in svc.PROVIDERS.items()
    ]


@router.get("/encryption")
def encryption_status() -> dict[str, bool]:
    """마스터 키(SIDOCGEN_SECRET_KEY) 설정 여부 — UI 안내용."""
    return {"configured": crypto.is_configured()}


def _credential_out(cred: ApiCredential) -> LlmCredentialOut:
    return LlmCredentialOut(
        id=cred.id,
        provider=cred.provider,
        label=cred.label,
        key_preview=svc.credential_preview(cred),
        created_at=cred.created_at,
    )


@router.get("/credentials", response_model=list[LlmCredentialOut])
def list_credentials(db: Annotated[Session, Depends(get_db)]) -> list[LlmCredentialOut]:
    """저장된 API 키 목록 (마스킹)."""
    return [_credential_out(c) for c in svc.list_credentials(db)]


@router.post("/credentials", response_model=LlmCredentialOut, status_code=201)
def create_credential(
    body: LlmCredentialCreate, db: Annotated[Session, Depends(get_db)]
) -> LlmCredentialOut:
    """상용 LLM API 키를 암호화해 저장한다."""
    try:
        cred = svc.create_credential(
            db, provider=body.provider, label=body.label, api_key=body.api_key
        )
    except svc.LlmSettingsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _credential_out(cred)


@router.delete("/credentials/{credential_id}")
def delete_credential(
    credential_id: str, db: Annotated[Session, Depends(get_db)]
) -> dict[str, bool]:
    return {"deleted": svc.delete_credential(db, credential_id)}


@router.get("/models", response_model=list[LlmModelOut])
def list_models(
    db: Annotated[Session, Depends(get_db)], enabled_only: bool = False
) -> list[LlmModel]:
    """등록된 생성 모델 목록 (enabled_only=true 면 활성 모델만 — 생성 화면 셀렉트용)."""
    return svc.list_models(db, enabled_only=enabled_only)


@router.post("/models", response_model=LlmModelOut, status_code=201)
def create_model(body: LlmModelCreate, db: Annotated[Session, Depends(get_db)]) -> LlmModel:
    """생성 모델을 레지스트리에 등록한다."""
    try:
        return svc.create_model(
            db,
            label=body.label,
            provider=body.provider,
            model=body.model,
            credential_id=body.credential_id,
        )
    except svc.LlmSettingsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/models/{model_id}", response_model=LlmModelOut)
def update_model_enabled(
    model_id: str, body: LlmModelEnabledUpdate, db: Annotated[Session, Depends(get_db)]
) -> LlmModel:
    try:
        return svc.set_model_enabled(db, model_id, body.enabled)
    except svc.LlmSettingsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/models/{model_id}")
def delete_model(model_id: str, db: Annotated[Session, Depends(get_db)]) -> dict[str, bool]:
    return {"deleted": svc.delete_model(db, model_id)}


@router.get("/ollama/tags")
def ollama_tags() -> dict[str, list[str]]:
    """실행 중인 Ollama 서버의 설치 모델 목록 (미실행 시 빈 목록)."""
    return {"models": svc.ollama_tags()}
