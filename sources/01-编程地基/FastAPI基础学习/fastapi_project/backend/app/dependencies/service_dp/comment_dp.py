from sqlalchemy.orm import Session

from app.dao.comment_dao import CommentDao
from app.services.comment_service import CommentService


def get_comment_service(db: Session) -> CommentService:
    return CommentService(db=db, dao=CommentDao(db))
