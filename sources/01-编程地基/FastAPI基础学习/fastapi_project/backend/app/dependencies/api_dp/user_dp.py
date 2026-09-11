from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies.service_dp.user_dp import get_user_service
from app.services.user_service import UserService


def get_user_service_dep(
    db: Session = Depends(get_db),
) -> UserService:
    return get_user_service(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service_dep)]
