from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dao.user_dao import UserDAO
from app.services.user_service import UserService


def get_user_svc(db: Session = Depends(get_db)) -> UserService:
    user_dao = UserDAO(db)
    return UserService(user_dao)
