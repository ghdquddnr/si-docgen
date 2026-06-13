"""잡 진행 상태 SSE 스트림.

DB 의 잡 상태/진행 단계를 폴링해 변경 시 이벤트로 푸시하고, 종료 상태에서 스트림을 닫는다.
백그라운드 워커(run_job)와 프로세스 메모리를 공유하지 않으므로 DB 를 단일 진실원으로 쓴다.
"""

import asyncio
import json
import logging

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.db.models import Job, JobStatus
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

TERMINAL = {JobStatus.SUCCEEDED, JobStatus.FAILED}


def read_job_state(job_id: str) -> dict | None:
    """잡의 현재 상태 스냅샷을 새 세션으로 읽는다 (없으면 None)."""
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            return None
        return {
            "status": job.status.value,
            "progress": job.progress,
            "error": job.error,
            "terminal": job.status in TERMINAL,
        }


@router.get("/{job_id}/events")
async def job_events(job_id: str) -> EventSourceResponse:
    """잡 진행 상태를 Server-Sent Events 로 스트리밍한다."""
    interval = get_settings().sse_poll_interval

    async def event_generator():  # type: ignore[no-untyped-def]
        last: object = object()  # 첫 비교가 항상 성립하도록 센티넬
        while True:
            state = read_job_state(job_id)
            if state is None:
                yield {"event": "error", "data": json.dumps({"detail": "잡을 찾을 수 없습니다"})}
                return
            if state != last:
                last = state
                yield {"event": "progress", "data": json.dumps(state, ensure_ascii=False)}
            if state["terminal"]:
                return
            await asyncio.sleep(interval)

    return EventSourceResponse(event_generator())
