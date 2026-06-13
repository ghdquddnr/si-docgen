"""헬스체크 라우터."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """애플리케이션 가용성 확인."""
    return {"status": "ok"}
