"""si-docgen 설정.

모델명 등 LLM 관련 설정은 반드시 이 모듈을 통해서만 관리한다 (코드 내 하드코딩 금지).
환경 변수 또는 프로젝트 루트의 .env 파일에서 읽으며, 접두사는 SIDOCGEN_ 이다.
예: SIDOCGEN_LLM_MODEL=ollama/gemma4:e4b
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 전역 설정."""

    model_config = SettingsConfigDict(env_prefix="SIDOCGEN_", env_file=".env", extra="ignore")

    # LiteLLM 모델 식별자 (예: ollama/gemma4:e4b, anthropic/claude-sonnet-4-6)
    llm_model: str = "ollama/gemma4:e4b"
    # OpenAI 호환 게이트웨이 등 별도 엔드포인트 사용 시 지정 (Ollama 는 미지정 시 localhost:11434)
    llm_api_base: str | None = None
    # LLM 호출 1회 타임아웃 (초)
    llm_timeout: float = 120.0
    # 검증 실패 시 총 시도 횟수 (절대 원칙: 최대 3회)
    llm_max_attempts: int = 3


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴. 테스트에서는 get_settings.cache_clear() 후 환경 변수로 재구성한다."""
    return Settings()
