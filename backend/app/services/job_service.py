"""생성 잡 오케스트레이션 — 업로드 파일 저장, 잡 생성, 백그라운드 파이프라인 실행.

생성 단계는 검증된 테스트시나리오 JSON 까지만 만들어 DB 에 저장한다 (렌더링은 검수 후 단계).
"""

import logging
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Job, JobStatus
from app.db.session import SessionLocal
from app.exceptions import SiDocgenError
from app.pipelines.generate_test_scenario import generate_scenario

logger = logging.getLogger(__name__)

# 원천 문서로 허용하는 확장자 (source_loader 지원 범위와 일치)
SUPPORTED_SUFFIXES = {".docx", ".pdf", ".md", ".markdown", ".txt"}


class UnsupportedSourceError(SiDocgenError):
    """업로드된 원천 문서 형식이 지원 범위를 벗어났을 때 발생 (API 에서 400 으로 매핑)."""


def job_dir(job_id: str) -> Path:
    """잡별 저장 디렉토리 경로."""
    return Path(get_settings().storage_dir) / job_id


def source_path(job_id: str, original_filename: str) -> Path:
    """잡의 원천 파일 저장 경로 (원본 확장자 유지)."""
    return job_dir(job_id) / f"source{Path(original_filename).suffix.lower()}"


def create_job(
    db: Session,
    *,
    filename: str,
    file_bytes: bytes,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
) -> Job:
    """업로드 파일을 저장하고 대기 상태 잡을 생성한다."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedSourceError(
            f"지원하지 않는 원천 문서 형식입니다: {suffix or '(확장자 없음)'} "
            f"(지원: {', '.join(sorted(SUPPORTED_SUFFIXES))})"
        )

    written_date = written_date or date.today().isoformat()  # 빈 값이면 오늘로 보정
    job_id = uuid.uuid4().hex
    target = source_path(job_id, filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(file_bytes)

    job = Job(
        id=job_id,
        status=JobStatus.PENDING,
        input_filename=filename,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("잡 생성: id=%s file=%s", job_id, filename)
    return job


def run_job(job_id: str) -> None:
    """백그라운드 실행: 원천 파싱 → LLM 생성 → scenario_json 저장. 자체 DB 세션을 연다."""
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("실행할 잡을 찾을 수 없음: %s", job_id)
            return
        job.status = JobStatus.RUNNING
        db.commit()

        try:
            scenario = generate_scenario(
                source_path(job_id, job.input_filename),
                project_name=job.project_name,
                system_name=job.system_name,
                author=job.author,
                written_date=job.written_date or "",
            )
            job.scenario_json = scenario.model_dump(mode="json")
            job.status = JobStatus.SUCCEEDED
            job.error = None
            logger.info("잡 완료: id=%s", job_id)
        except Exception as exc:  # 백그라운드라 모든 예외를 잡아 잡 상태로 기록한다
            job.status = JobStatus.FAILED
            job.error = str(exc)
            logger.exception("잡 실패: id=%s", job_id)
        db.commit()
