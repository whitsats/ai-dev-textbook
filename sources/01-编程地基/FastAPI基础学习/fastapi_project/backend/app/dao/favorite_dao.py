from typing import Optional

from sqlalchemy.orm import Session

from app.models.favorite import Favorite


class FavoriteDao:
    def __init__(self, db: Session):
        self.db = db

    def update_status(self, article_id: int, user_id: int, canceled: int = 0):
        existing = (
            self.db.query(Favorite)
            .filter(Favorite.article_id == article_id, Favorite.user_id == user_id)
            .first()
        )
        if existing is None:
            fav = Favorite(article_id=article_id, user_id=user_id, canceled=canceled)
            self.db.add(fav)
        else:
            existing.canceled = canceled
        self.db.commit()

    def user_if_favorite(self, user_id: int, article_id: int) -> int:
        result = (
            self.db.query(Favorite.canceled)
            .filter(Favorite.user_id == user_id, Favorite.article_id == article_id)
            .first()
        )
        if result is None:
            return 1
        return result[0]
