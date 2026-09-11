from sqlalchemy.orm import Session

from app.dao.favorite_dao import FavoriteDao
from app.services.favorite_service import FavoriteService


def get_favorite_service(db: Session) -> FavoriteService:
    return FavoriteService(db=db, dao=FavoriteDao(db))
