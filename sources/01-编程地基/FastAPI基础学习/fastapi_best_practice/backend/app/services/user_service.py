from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserCreate


class UserService:
    def __init__(self, user_dao) -> None:
        self.user_dao = user_dao

    def create_user(self, data: UserCreate) -> User:
        return self.user_dao.create_user(data)

    def list_users(self) -> list[User]:
        return self.user_dao.list_users()
