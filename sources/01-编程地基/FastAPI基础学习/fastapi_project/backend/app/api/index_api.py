from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies.current_user import get_current_user_optional
from app.dependencies.api_dp import IndexArticleServiceDep
from app.config.app_config import settings
from app.common.result import Result

router = APIRouter(prefix="/api", tags=["首页"])


@router.get("/")
async def get_index(
    service: IndexArticleServiceDep,
    page: int = Query(default=1, ge=1),
    article_type: str = Query(default="recommend"),
    keyword: Optional[str] = Query(default=None),
) -> Result:
    rows = service.get_list(page, article_type, keyword)
    return Result.success(data={"list": rows, "label_types": settings.label_types})
