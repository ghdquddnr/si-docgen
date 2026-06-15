"""모델 레지스트리 기반 인증 해석 — 저장된 모델·키로 LiteLLM 호출 인자를 만든다.

LLM 호출 래퍼(client.py)가 모델 식별자만으로 적절한 API 키(상용)·엔드포인트(Ollama)를
주입할 수 있도록, DB 의 LlmModel·ApiCredential 을 조회해 completion 인자를 돌려준다.
레지스트리에 없는 모델은 빈 결과를 반환해 기존 설정(.env·환경변수) 기반 동작으로 폴백한다.
"""

import logging

from sqlalchemy import select

from app.config import get_settings

logger = logging.getLogger(__name__)


def resolve_model_auth(model: str) -> dict[str, str]:
    """모델 식별자로 LiteLLM completion 인증 인자(api_key/api_base)를 해석한다.

    - Ollama: 설정의 ollama_base_url 을 api_base 로 사용.
    - 상용: 모델에 연결된(또는 같은 provider 의) 저장 키를 복호화해 api_key 로 사용.
    - 레지스트리에 없으면 {} 반환 → 호출부가 기존 설정값으로 폴백.
    """
    from app.db.models import ApiCredential, LlmModel
    from app.db.session import SessionLocal
    from app.llm import crypto

    with SessionLocal() as db:
        row = db.scalar(select(LlmModel).where(LlmModel.model == model))
        if row is None:
            return {}
        if row.provider == "ollama":
            base = get_settings().ollama_base_url or get_settings().llm_api_base
            return {"api_base": base} if base else {}
        cred = None
        if row.credential_id:
            cred = db.get(ApiCredential, row.credential_id)
        if cred is None:
            cred = db.scalar(select(ApiCredential).where(ApiCredential.provider == row.provider))
        if cred is None:
            logger.warning("모델 %s 에 사용할 API 키가 없습니다 (provider=%s)", model, row.provider)
            return {}
        return {"api_key": crypto.decrypt(cred.encrypted_key)}
