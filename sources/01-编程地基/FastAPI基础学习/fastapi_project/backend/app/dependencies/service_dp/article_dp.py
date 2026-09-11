from sqlalchemy.orm import Session

from app.dao.article_dao import ArticleDao
from app.dao.user_dao import UserDao
from app.dao.comment_dao import CommentDao
from app.dao.favorite_dao import FavoriteDao
from app.services.article_service import ArticleService


def get_article_service(db: Session) -> ArticleService:
    return ArticleService(
        db=db,
        article_dao=ArticleDao(db),
        user_dao=UserDao(db),
        comment_dao=CommentDao(db),
        favorite_dao=FavoriteDao(db),
    )
