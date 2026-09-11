from fastapi import APIRouter, Depends, Query

from app.dependencies.current_user import get_current_user
from app.dependencies.api_dp import PersonalServiceDep
from app.common.result import Result

router = APIRouter(prefix="/api/personal", tags=["个人中心"])


@router.get("/")
async def get_personal_center(
    service: PersonalServiceDep,
    type_name: str = Query(default="article", description="article / favorite / comment"),
    drafted: int = Query(default=1, description="仅 type_name=article 有效：1=已发布 0=草稿"),
    current_user: dict = Depends(get_current_user),
) -> Result:
    if type_name == "article":
        r = service.get_article_list(current_user["user_id"], drafted=drafted)
    elif type_name == "favorite":
        r = service.get_favorite_list(current_user["user_id"])
    elif type_name == "comment":
        r = service.get_comment_list(current_user["user_id"])
    else:
        r = service.get_article_list(current_user["user_id"], drafted=drafted)
    return Result.success(data=r)
