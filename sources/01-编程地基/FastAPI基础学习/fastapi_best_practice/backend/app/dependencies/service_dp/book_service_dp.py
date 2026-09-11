from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dao.book_dao import BookDAO
from app.services.book_service import BookService


def get_book_svc(db: Session = Depends(get_db)) -> BookService:
    book_dao = BookDAO(db)
    return BookService(book_dao)
