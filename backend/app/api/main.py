"""FastAPI 애플리케이션 진입점.

개발 실행: uv run uvicorn app.api.main:app --reload
"""

from fastapi import FastAPI

from app.api.routers import events, health, jobs

app = FastAPI(
    title="si-docgen API",
    description="한국 SI 표준 산출물 생성 API",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(events.router)
