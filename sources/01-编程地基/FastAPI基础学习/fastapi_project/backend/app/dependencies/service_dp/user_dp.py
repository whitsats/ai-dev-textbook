from sqlalchemy.orm import Session

from app.dao.user_dao import UserDao
from app.services.user_service import UserService


def get_user_service(db: Session) -> UserService:
    return UserService(db=db, dao=UserDao(db))
