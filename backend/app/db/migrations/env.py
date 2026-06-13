"""Alembic 마이그레이션 환경.

DB URL 과 대상 metadata 는 애플리케이션 설정·모델에서 가져온다
(alembic.ini 에 URL 을 적지 않는다 — 설정 단일 진실 공급원 원칙).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db import models  # noqa: F401  (Base.metadata 에 테이블 등록을 위해 import)
from app.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 설정의 DB URL 을 주입한다
config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """DBAPI 없이 SQL 스크립트만 생성하는 오프라인 모드."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """엔진에 연결해 실제 DB 에 마이그레이션을 적용하는 온라인 모드."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # render_as_batch: SQLite 의 제한된 ALTER 를 배치 모드로 우회 (이식성)
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
