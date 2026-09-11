from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies.service_dp.book_service_dp import get_book_svc as _get_book_svc
from app.services.book_service import BookService


def get_book_svc(db: Session = Depends(get_db)) -> BookService:
    return _get_book_svc(db)
