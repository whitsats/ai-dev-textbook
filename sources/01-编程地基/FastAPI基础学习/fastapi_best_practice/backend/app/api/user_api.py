from fastapi import APIRouter, Depends

from app.common.result import Result
from app.dependencies.api_dp.user_api_dp import get_user_svc
from app.schemas import UserCreate, UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/api", tags=["user"])


@router.post("/users")
def create_user(
    data: UserCreate,
    svc: UserService = Depends(get_user_svc),
) -> Result:
    user = svc.create_user(data)
    return Result.success(UserOut.model_validate(user))


@router.get("/users")
def list_users(
    svc: UserService = Depends(get_user_svc),
) -> Result:
    users = svc.list_users()
    return Result.success([UserOut.model_validate(u) for u in users])
