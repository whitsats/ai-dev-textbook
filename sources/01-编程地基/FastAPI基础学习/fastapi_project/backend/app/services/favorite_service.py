from typing import Any

from sqlalchemy.orm import Session

from app.dao.favorite_dao import FavoriteDao


class FavoriteService:
    def __init__(self, db: Session, dao: FavoriteDao):
        self.db = db
        self.dao = dao

    def update_status(self, user_id: int, article_id: int, canceled: int) -> dict[str, Any]:
        try:
            self.dao.update_status(article_id, user_id, canceled)
            return {
                "code": 200,
                "msg": "收藏成功" if canceled == 0 else "取消收藏成功",
            }
        except Exception as e:
            return {
                "code": 500,
                "msg": f"操作失败: {str(e)}",
            }
