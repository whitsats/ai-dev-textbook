from fastapi import APIRouter

from app.common.result import Result

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> Result:
    return Result.success({"status": "ok"})
