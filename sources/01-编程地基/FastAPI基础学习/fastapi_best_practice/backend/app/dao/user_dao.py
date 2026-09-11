from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserCreate


class UserDAO:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_user(self, data: UserCreate) -> User:
        user = User(username=data.username)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_users(self) -> list[User]:
        return self.db.query(User).order_by(User.id.desc()).all()
