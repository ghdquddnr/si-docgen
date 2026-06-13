"""SQLAlchemy Declarative Base.

모든 ORM 모델은 이 Base 를 상속한다. Alembic env.py 는 Base.metadata 를
마이그레이션 대상으로 참조하므로, 새 모델은 반드시 import 되어 metadata 에 등록되어야 한다.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """프로젝트 전역 ORM Declarative Base."""
