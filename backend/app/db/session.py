"""DB 엔진·세션 관리.

엔진은 설정의 database_url 로 생성한다. SQLite 는 다중 스레드(FastAPI 백그라운드)
접근을 위해 check_same_thread=False 가 필요하다. 테스트는 rebind_engine 으로 교체한다.
"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def _make_engine(database_url: str) -> Engine:
    connect_args: dict = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        # 파일 기반 SQLite 면 상위 디렉토리를 보장한다 (sqlite:///./data/x.db)
        prefix = "sqlite:///"
        if database_url.startswith(prefix) and ":memory:" not in database_url:
            db_path = Path(database_url[len(prefix) :])
            db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, connect_args=connect_args, future=True)


engine: Engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def rebind_engine(database_url: str) -> Engine:
    """엔진과 세션 팩토리를 새 URL 로 교체한다 (테스트에서 임시 DB 주입용)."""
    global engine, SessionLocal
    engine = _make_engine(database_url)
    SessionLocal.configure(bind=engine)
    return engine


def get_db() -> Iterator[Session]:
    """FastAPI 의존성: 요청 범위 DB 세션을 제공하고 종료 시 닫는다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
