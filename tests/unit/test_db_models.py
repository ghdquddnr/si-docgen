"""Job ORM 모델 CRUD 테스트 (임시 SQLite).

엔진은 테스트마다 임시 파일 DB 로 생성하고 Base.metadata 로 스키마를 만든다.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Job, JobStatus


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_job_생성_및_조회(session: Session) -> None:
    job = Job(id="job-1", input_filename="req.docx", status=JobStatus.PENDING)
    session.add(job)
    session.commit()

    got = session.get(Job, "job-1")
    assert got is not None
    assert got.status is JobStatus.PENDING
    assert got.project_name == "프로젝트"  # 기본값
    assert got.scenario_json is None
    assert got.created_at is not None
    assert got.updated_at is not None


def test_job_상태_전이_및_json_저장(session: Session) -> None:
    session.add(Job(id="job-2", input_filename="req.md"))
    session.commit()

    job = session.get(Job, "job-2")
    assert job is not None
    job.status = JobStatus.SUCCEEDED
    job.scenario_json = {"unit_test_cases": [{"tc_id": "TC-001"}]}
    session.commit()

    reloaded = session.get(Job, "job-2")
    assert reloaded.status is JobStatus.SUCCEEDED
    assert reloaded.scenario_json == {"unit_test_cases": [{"tc_id": "TC-001"}]}


def test_job_기본_상태는_pending(session: Session) -> None:
    session.add(Job(id="job-3", input_filename="req.txt"))
    session.commit()
    assert session.get(Job, "job-3").status is JobStatus.PENDING
