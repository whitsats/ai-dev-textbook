from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import User


class UserDao:
    def __init__(self, db: Session):
        self.db = db

    def find_by_username(self, username: str) -> List[User]:
        return self.db.query(User).filter(User.username == username).all()

    def find_by_userid(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.user_id == user_id).first()

    def create_user(
        self,
        username: str,
        password: str,
        nickname: str,
        picture: str,
        job: str = "未定义",
    ) -> User:
        user = User(
            username=username,
            password=password,
            nickname=nickname,
            picture=picture,
            job=job,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def model_to_dict(self, user: User) -> dict:
        result = {}
        for k, v in user.__dict__.items():
            if not k.startswith("_"):
                if isinstance(v, datetime):
                    v = v.strftime("%Y-%m-%d %H:%M:%S")
                result[k] = v
        return result
