from typing import Any, Optional

from sqlalchemy.orm import Session

from app.dao.article_dao import ArticleDao
from app.dao.user_dao import UserDao
from app.dao.comment_dao import CommentDao
from app.dao.favorite_dao import FavoriteDao
from app.config.app_config import settings


class ArticleService:
    def __init__(
        self,
        db: Session,
        article_dao: ArticleDao,
        user_dao: UserDao,
        comment_dao: CommentDao,
        favorite_dao: FavoriteDao,
    ):
        self.db = db
        self.article_dao = article_dao
        self.user_dao = user_dao
        self.comment_dao = comment_dao
        self.favorite_dao = favorite_dao

    def _normalize_article_image(self, raw: Optional[str]) -> str:
        if not raw:
            return ""
        img = (raw or "").lstrip("/")

        # 兼容旧数据：数据库里可能只存了 "article_001.jpg" 这类文件名
        if "/" not in img:
            img = f"article/header/{img}"

        return settings.article_header_image_path + img

    def get_list(self, page: int, article_type: str, keyword: Optional[str] = None) -> list[dict[str, Any]]:
        if keyword:
            rows = self.article_dao.search_article(page, keyword)
        else:
            rows = self.article_dao.find_article(page, article_type)
        result = []
        for article, nickname in rows:
            item = self.article_dao.model_to_dict(article)
            item["nickname"] = nickname
            if item.get("article_image"):
                item["article_image"] = self._normalize_article_image(item.get("article_image"))
            if item.get("article_tag"):
                item["article_tag"] = item["article_tag"].replace(",", " · ")
            result.append(item)
        return result

    def get_detail(
        self, article_id: int, current_user: Optional[dict] = None
    ) -> dict[str, Any]:
        article = self.article_dao.get_article_detail(article_id)
        if not article:
            return {"code": 400, "msg": "文章不存在"}
        article_dict = self.article_dao.model_to_dict(article)
        author = self.user_dao.find_by_userid(article.user_id)
        author_dict = {}
        if author:
            author_dict["nickname"] = self.user_dao.model_to_dict(author).get("nickname", "")
        comment_list = self.comment_dao.get_comment_user_list(article_id)
        comment_count = self.comment_dao.get_article_comment_count(article_id)
        is_favorite = 1
        if current_user:
            is_favorite = self.favorite_dao.user_if_favorite(
                current_user.get("user_id"), article_id
            )
        tag_list = (
            article_dict.get("article_tag", "").split(",")
            if article_dict.get("article_tag")
            else []
        )
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "id": article_dict.get("id"),
                "user_id": article_dict.get("user_id"),
                "title": article_dict.get("title"),
                "article_content": article_dict.get("article_content"),
                "browse_num": article_dict.get("browse_num"),
                "label_name": article_dict.get("label_name"),
                "article_type": article_dict.get("article_type"),
                "drafted": article_dict.get("drafted"),
                "article_image": self._normalize_article_image(article_dict.get("article_image")),
                "article_tag": article_dict.get("article_tag") or "",
                "author": author_dict,
                "comment_list": comment_list,
                "comment_count": comment_count,
                "is_favorite": is_favorite,
                "tag_list": tag_list,
            },
        }

    def get_new_page_data(self, user_id: int) -> dict[str, Any]:
        all_drafted = self.article_dao.get_all_article_drafted(user_id)
        drafted_list = [self.article_dao.model_to_dict(d) for d in all_drafted]
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "drafted_list": drafted_list,
                "label_types": settings.label_types,
                "article_types": settings.article_types,
                "article_tags": settings.article_tags,
            },
        }

    def get_drafted_detail(self, article_id: int) -> dict[str, Any]:
        article = self.article_dao.get_one_article_drafted(article_id)
        if not article:
            return {"code": 400, "msg": "草稿不存在"}
        return self.article_dao.model_to_dict(article)

    def save_article(
        self,
        user_id: int,
        article_id: int,
        title: str,
        article_content: str,
        drafted: int,
        label_name: Optional[str] = None,
        article_tag: Optional[str] = None,
        article_type: Optional[str] = None,
        article_image: Optional[str] = None,
    ) -> dict[str, Any]:
        title_str = (title or "").strip()
        content_str = (article_content or "").strip()

        # 归属校验：article_id > 0 时必须是本人才能操作
        self._check_ownership(article_id, user_id)

        # 后端兜底校验：发布必须有标题；草稿至少要有标题或内容
        if drafted == 1:
            if not title_str:
                return {"code": 400, "msg": "请输入文章标题"}
            if not content_str:
                return {"code": 400, "msg": "请输入文章内容"}
        else:
            if not title_str and not content_str:
                return {"code": 400, "msg": "草稿至少需要填写标题或内容"}

        # article_image 只允许存相对路径，blob: / 绝对 URL / 空值 都过滤掉
        safe_image = ""
        if article_image and isinstance(article_image, str):
            s = article_image.strip()
            if not s.startswith("blob:") and not s.startswith("http") and not s.startswith("//"):
                safe_image = s

        if article_id == -1:
            new_article = self.article_dao.insert_article(
                user_id,
                title,
                article_content,
                drafted,
                label_name or "",
                article_tag or "",
                article_type or "",
                safe_image,
            )
            return {
                "code": 200,
                "msg": "发布成功" if drafted == 1 else "草稿存储成功",
                "data": {"article_id": new_article.id},
            }
        elif article_id > -1:
            self.article_dao.update_article(
                article_id,
                title,
                article_content,
                drafted,
                label_name or "",
                article_tag or "",
                article_type or "",
                safe_image,
            )
            return {"code": 200, "msg": "发布成功", "data": {"article_id": article_id}}

    def _check_ownership(self, article_id: int, user_id: int) -> None:
        """如果 article_id > 0 则校验是否属于当前用户，否则抛异常"""
        if article_id <= -1:
            return
        owner_id = self.article_dao.get_article_owner_id(article_id)
        if owner_id is None:
            raise PermissionError("文章不存在")
        if owner_id != user_id:
            raise PermissionError("无权操作此文章")

    def upload_header_image(self, article_id: int, rel_path: str, user_id: int) -> dict[str, str]:
        self._check_ownership(article_id, user_id)
        self.article_dao.update_article_header_image(article_id, rel_path)
        return {
            "state": "SUCCESS",
            "url": f"/images/{rel_path}",
            "title": rel_path,
            "original": rel_path,
        }

