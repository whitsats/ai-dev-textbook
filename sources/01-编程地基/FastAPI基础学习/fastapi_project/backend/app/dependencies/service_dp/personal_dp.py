from sqlalchemy.orm import Session

from app.dao.article_dao import ArticleDao
from app.dao.user_dao import UserDao
from app.dao.comment_dao import CommentDao
from app.services.personal_service import PersonalService


def get_personal_service(db: Session) -> PersonalService:
    return PersonalService(
        db=db,
        article_dao=ArticleDao(db),
        user_dao=UserDao(db),
        comment_dao=CommentDao(db),
    )
