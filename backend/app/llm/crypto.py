"""API 키 대칭 암호화 — 설정의 SIDOCGEN_SECRET_KEY 에서 파생한 키로 Fernet 암복호화.

저장된 상용 LLM API 키는 평문이 아니라 이 모듈로 암호화해 DB 에 보관한다.
마스터 키(SIDOCGEN_SECRET_KEY)는 .env 로만 관리하며 DB·코드에 두지 않는다.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings
from app.exceptions import SiDocgenError


class EncryptionNotConfiguredError(SiDocgenError):
    """SIDOCGEN_SECRET_KEY 미설정 상태에서 암복호화를 시도할 때 발생 (API 400)."""


class DecryptionError(SiDocgenError):
    """저장된 키를 복호화할 수 없을 때 발생 (마스터 키 변경 등)."""


def is_configured() -> bool:
    """마스터 키가 설정되어 키 저장/복호화가 가능한지 여부."""
    return bool(get_settings().secret_key)


def _fernet() -> Fernet:
    secret = get_settings().secret_key
    if not secret:
        raise EncryptionNotConfiguredError(
            "SIDOCGEN_SECRET_KEY 가 설정되지 않았습니다. "
            "API 키 암호화를 위해 .env 에 임의의 비밀 문자열을 설정하세요."
        )
    # 임의 길이 비밀 문자열을 Fernet 키(32바이트 urlsafe base64)로 결정론적 파생
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """평문을 암호화 토큰 문자열로 변환한다."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """암호화 토큰을 평문으로 복원한다. 실패 시 DecryptionError."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise DecryptionError(
            "저장된 API 키를 복호화할 수 없습니다 (SIDOCGEN_SECRET_KEY 가 변경되었을 수 있습니다)."
        ) from exc


def mask(plaintext: str) -> str:
    """키 미리보기용 마스킹 — 끝 4자리만 노출 (예: ••••••1234)."""
    tail = plaintext[-4:] if len(plaintext) >= 4 else plaintext
    return f"••••••{tail}"
