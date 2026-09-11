from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies.service_dp.user_service_dp import get_user_svc as _get_user_svc
from app.services.user_service import UserService


def get_user_svc(db: Session = Depends(get_db)) -> UserService:
    return _get_user_svc(db)
