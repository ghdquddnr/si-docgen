"""LLM 설정 — API 키(암호화 저장)·생성 모델 레지스트리 CRUD 및 Ollama 모델 조회.

상용 키는 crypto 모듈로 암호화해 저장하고, 응답에는 평문 대신 마스킹 미리보기만 노출한다.
모델 목록은 각 문서 생성 화면의 '생성 모델' 셀렉트박스를 채운다.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import ApiCredential, LlmModel
from app.exceptions import SiDocgenError
from app.llm import crypto

logger = logging.getLogger(__name__)

# 지원 제공자: key=식별자, label=표시명, needs_key=API 키 필요 여부, prefix=LiteLLM 모델 접두사
PROVIDERS: dict[str, dict] = {
    "ollama": {"label": "Ollama (로컬)", "needs_key": False, "prefix": "ollama/"},
    "openai": {"label": "OpenAI", "needs_key": True, "prefix": "openai/"},
    "gemini": {"label": "Google Gemini", "needs_key": True, "prefix": "gemini/"},
    "anthropic": {"label": "Anthropic", "needs_key": True, "prefix": "anthropic/"},
    "xai": {"label": "xAI (Grok)", "needs_key": True, "prefix": "xai/"},
}


class LlmSettingsError(SiDocgenError):
    """LLM 설정 관련 잘못된 요청 (API 400)."""


class LlmSettingsNotFoundError(SiDocgenError):
    """존재하지 않는 키/모델 참조 (API 404)."""


def _require_provider(provider: str) -> dict:
    info = PROVIDERS.get(provider)
    if info is None:
        raise LlmSettingsError(f"지원하지 않는 제공자: {provider} (지원: {', '.join(PROVIDERS)})")
    return info


# ── API 키 ────────────────────────────────────────────────────────────────


def create_credential(db: Session, *, provider: str, label: str, api_key: str) -> ApiCredential:
    """상용 LLM API 키를 암호화해 저장한다 (provider 별 다중 저장 가능)."""
    info = _require_provider(provider)
    if not info["needs_key"]:
        raise LlmSettingsError(f"{info['label']} 는 API 키가 필요하지 않습니다")
    if not api_key.strip():
        raise LlmSettingsError("API 키가 비어 있습니다")
    if not crypto.is_configured():
        raise LlmSettingsError(
            "API 키 암호화 마스터 키(SIDOCGEN_SECRET_KEY)가 설정되지 않았습니다. "
            ".env 에 설정 후 다시 시도하세요."
        )
    cred = ApiCredential(
        id=uuid.uuid4().hex,
        provider=provider,
        label=label or f"{info['label']} 키",
        encrypted_key=crypto.encrypt(api_key.strip()),
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    logger.info("API 키 저장: id=%s provider=%s", cred.id, provider)
    return cred


def list_credentials(db: Session) -> list[ApiCredential]:
    return list(db.scalars(select(ApiCredential).order_by(ApiCredential.created_at.desc())).all())


def delete_credential(db: Session, credential_id: str) -> bool:
    """키를 삭제하고, 이 키를 참조하던 모델의 연결을 해제한다."""
    cred = db.get(ApiCredential, credential_id)
    if cred is None:
        return False
    for m in db.scalars(select(LlmModel).where(LlmModel.credential_id == credential_id)).all():
        m.credential_id = None
    db.delete(cred)
    db.commit()
    return True


def credential_preview(cred: ApiCredential) -> str:
    """저장된 키를 복호화해 마스킹 미리보기를 만든다. 복호화 실패 시 안내 문자열."""
    try:
        return crypto.mask(crypto.decrypt(cred.encrypted_key))
    except SiDocgenError:
        return "(복호화 불가)"


# ── 모델 레지스트리 ─────────────────────────────────────────────────────────


def create_model(
    db: Session,
    *,
    label: str,
    provider: str,
    model: str,
    credential_id: str | None = None,
) -> LlmModel:
    """생성 모델을 레지스트리에 등록한다. 상용 제공자는 키 연결을 검증한다."""
    info = _require_provider(provider)
    model = model.strip()
    if not model:
        raise LlmSettingsError("모델 식별자가 비어 있습니다")
    if info["needs_key"]:
        if credential_id:
            cred = db.get(ApiCredential, credential_id)
            if cred is None or cred.provider != provider:
                raise LlmSettingsError("선택한 API 키가 제공자와 일치하지 않습니다")
        elif not db.scalar(select(ApiCredential).where(ApiCredential.provider == provider)):
            raise LlmSettingsError(
                f"{info['label']} 모델을 추가하려면 먼저 {info['label']} API 키를 등록하세요"
            )
    entry = LlmModel(
        id=uuid.uuid4().hex,
        label=label or model,
        provider=provider,
        model=model,
        credential_id=credential_id or None,
        enabled=True,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info("모델 등록: id=%s model=%s", entry.id, model)
    return entry


def list_models(db: Session, *, enabled_only: bool = False) -> list[LlmModel]:
    stmt = select(LlmModel).order_by(LlmModel.created_at.desc())
    if enabled_only:
        stmt = stmt.where(LlmModel.enabled.is_(True))
    return list(db.scalars(stmt).all())


def set_model_enabled(db: Session, model_id: str, enabled: bool) -> LlmModel:
    entry = db.get(LlmModel, model_id)
    if entry is None:
        raise LlmSettingsNotFoundError(f"모델을 찾을 수 없습니다: {model_id}")
    entry.enabled = enabled
    db.commit()
    db.refresh(entry)
    return entry


def delete_model(db: Session, model_id: str) -> bool:
    entry = db.get(LlmModel, model_id)
    if entry is None:
        return False
    db.delete(entry)
    db.commit()
    return True


# ── Ollama 모델 조회 ────────────────────────────────────────────────────────


def ollama_tags() -> list[str]:
    """실행 중인 Ollama 서버에서 설치된 모델 이름 목록을 조회한다 (실패 시 빈 목록)."""
    import httpx

    base = get_settings().ollama_base_url
    try:
        resp = httpx.get(f"{base.rstrip('/')}/api/tags", timeout=3.0)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", []) if m.get("name")]
    except Exception as exc:  # 서버 미실행 등 — 조회 실패는 빈 목록으로 처리
        logger.info("Ollama 모델 조회 실패 (%s): %s", base, exc)
        return []
