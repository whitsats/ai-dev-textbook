from typing import Any

from sqlalchemy.orm import Session

from app.dao.article_dao import ArticleDao
from app.dao.user_dao import UserDao
from app.dao.comment_dao import CommentDao
from app.config.app_config import settings


class PersonalService:
    def __init__(
        self,
        db: Session,
        article_dao: ArticleDao,
        user_dao: UserDao,
        comment_dao: CommentDao,
    ):
        self.db = db
        self.article_dao = article_dao
        self.user_dao = user_dao
        self.comment_dao = comment_dao

    def _normalize_article_image(self, raw: Any) -> str:
        if not raw:
            return ""
        img = str(raw).lstrip("/")
        if "/" not in img:
            img = f"article/header/{img}"
        return settings.article_header_image_path + img

    def get_article_list(self, user_id: int, drafted: int = 1) -> list[dict[str, Any]]:
        articles = self.article_dao.get_article_by_userid(user_id, drafted=drafted)
        return self._enrich_articles(articles)

    def get_favorite_list(self, user_id: int) -> list[dict[str, Any]]:
        articles = self.article_dao.get_favorite_article_by_userid(user_id)
        return self._enrich_articles(articles)

    def get_comment_list(self, user_id: int) -> list[dict[str, Any]]:
        comments = self.comment_dao.get_user_comments(user_id)
        result = []
        for c in comments:
            item = {}
            item["id"] = c.id
            item["article_id"] = c.article_id
            item["content"] = c.content
            item["floor_number"] = c.floor_number
            item["reply_id"] = c.reply_id
            item["create_time"] = (
                c.create_time.strftime("%Y-%m-%d %H:%M:%S") if c.create_time else ""
            )
            # 通过 article_id 查文章标题
            article = self.article_dao.get_article_detail(c.article_id)
            item["article_title"] = article.title if article else "（文章已删除）"
            result.append(item)
        return result

    def _enrich_articles(self, articles) -> list[dict[str, Any]]:
        result = []
        for a in articles:
            item = self.article_dao.model_to_dict(a)
            if item.get("article_image"):
                item["article_image"] = self._normalize_article_image(item.get("article_image"))
            result.append(item)
        return result
