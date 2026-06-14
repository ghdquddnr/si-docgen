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

    # LiteLLM 모델 식별자 (예: ollama/gemma4:12b, anthropic/claude-sonnet-4-6)
    # 기본값은 개발 PC에 설치된 로컬 모델 기준이며 .env 로 전환한다
    llm_model: str = "ollama/gemma4:12b"
    # 단계별 모델 오버라이드 (미지정 시 llm_model 사용). 산출물별로 다른 모델을 쓸 때
    requirement_spec_model: str | None = None
    scenario_model: str | None = None
    screen_spec_model: str | None = None
    wbs_model: str | None = None
    table_spec_model: str | None = None
    # OpenAI 호환 게이트웨이 등 별도 엔드포인트 사용 시 지정 (Ollama 는 미지정 시 localhost:11434)
    llm_api_base: str | None = None
    # LLM 호출 1회 타임아웃 (초)
    llm_timeout: float = 120.0
    # 검증 실패 시 총 시도 횟수 (절대 원칙: 최대 3회)
    llm_max_attempts: int = 3

    # DB 연결 URL (SQLAlchemy 형식). 기본은 로컬 SQLite 이며,
    # SIDOCGEN_DATABASE_URL 로 PostgreSQL/MySQL 등으로 전환한다
    # (예: postgresql+psycopg://user:pw@host/db). 스키마는 Alembic 으로 관리.
    database_url: str = "sqlite:///./data/si_docgen.db"

    # 잡별 업로드 원천 파일·산출물 저장 루트 디렉토리
    storage_dir: str = "./data/jobs"

    # SSE 진행 상태 스트림의 DB 폴링 간격(초). 테스트에서는 0 으로 낮춘다
    sse_poll_interval: float = 0.3

    # CORS 허용 오리진 (프론트엔드 개발 서버). 쉼표 구분 문자열로도 주입 가능
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴. 테스트에서는 get_settings.cache_clear() 후 환경 변수로 재구성한다."""
    return Settings()
