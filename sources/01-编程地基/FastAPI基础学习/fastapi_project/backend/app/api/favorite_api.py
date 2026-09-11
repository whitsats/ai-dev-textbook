from fastapi import APIRouter, Depends

from app.dependencies.current_user import get_current_user
from app.dependencies.api_dp import FavoriteServiceDep
from app.schemas.req.favorite import FavoriteUpdateReq
from app.common.result import Result

router = APIRouter(prefix="/api/favorite", tags=["收藏"])


@router.post("/update_status")
async def update_favorite_status(
    service: FavoriteServiceDep,
    req: FavoriteUpdateReq,
    current_user: dict = Depends(get_current_user),
) -> Result:
    r = service.update_status(
        user_id=current_user["user_id"],
        article_id=req.article_id,
        canceled=req.canceled,
    )
    return Result(code=r["code"], msg=r["msg"], data=r.get("data"))
