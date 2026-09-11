from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.favorite import Favorite
from app.models.comment import Comment
from app.models.user import User


class ArticleDao:
    def __init__(self, db: Session):
        self.db = db

    def find_article(
        self, page: int, article_type: str = "recommend"
    ) -> List[Tuple[Article, str]]:
        if page < 1:
            page = 1
        count = page * 10
        query = (
            self.db.query(Article, User.nickname)
            .join(User, User.user_id == Article.user_id)
            .filter(Article.drafted == 1)
        )
        if article_type != "recommend":
            query = query.filter(Article.label_name == article_type)
        return (
            query.order_by(Article.browse_num.desc())
            .limit(count)
            .all()
        )

    def search_article(self, page: int, keyword: str) -> List[Tuple[Article, str]]:
        if page < 1:
            page = 1
        count = page * 10
        return (
            self.db.query(Article, User.nickname)
            .join(User, User.user_id == Article.user_id)
            .filter(
                (Article.title.like(f"%{keyword}%"))
                | (Article.article_content.like(f"%{keyword}%"))
            )
            .filter(Article.drafted == 1)
            .order_by(Article.browse_num.desc())
            .limit(count)
            .all()
        )

    def get_article_detail(self, article_id: int) -> Optional[Article]:
        article = self.db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.browse_num += 1
            self.db.commit()
            self.db.refresh(article)
        return article

    def find_about_article(self, label_name: str) -> List[Article]:
        return (
            self.db.query(Article)
            .filter(Article.label_name == label_name)
            .filter(Article.drafted == 1)
            .order_by(Article.browse_num.desc())
            .limit(5)
            .all()
        )

    def insert_article(
        self,
        user_id: int,
        title: str,
        article_content: str,
        drafted: int,
        label_name: str = "",
        article_tag: str = "",
        article_type: str = "",
        article_image: str = "",
    ) -> Article:
        article = Article(
            user_id=user_id,
            title=title,
            article_content=article_content,
            drafted=drafted,
            label_name=label_name or "",
            article_tag=article_tag or "",
            article_type=article_type or "",
            article_image=article_image or "",
        )
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)
        return article

    def update_article(
        self,
        article_id: int,
        title: str,
        article_content: str,
        drafted: int,
        label_name: str = "",
        article_tag: str = "",
        article_type: str = "",
        article_image: str = "",
    ) -> int:
        row = self.db.query(Article).filter(Article.id == article_id).first()
        if row:
            row.title = title
            row.article_content = article_content
            row.drafted = drafted
            if label_name:
                row.label_name = label_name
            if article_tag:
                row.article_tag = article_tag
            if article_type:
                row.article_type = article_type
            if article_image:
                row.article_image = article_image
            self.db.commit()
        return article_id

    def update_article_header_image(self, article_id: int, article_image: str) -> int:
        row = self.db.query(Article).filter(Article.id == article_id).first()
        if row:
            row.article_image = article_image
            self.db.commit()
        return article_id

    def get_article_owner_id(self, article_id: int) -> Optional[int]:
        row = self.db.query(Article.user_id).filter(Article.id == article_id).first()
        return row[0] if row else None

    def get_all_article_drafted(self, user_id: int) -> List[Article]:
        return (
            self.db.query(Article)
            .filter(Article.user_id == user_id, Article.drafted == 0)
            .all()
        )

    def get_one_article_drafted(self, article_id: int) -> Optional[Article]:
        return (
            self.db.query(Article)
            .filter(Article.id == article_id, Article.drafted == 0)
            .first()
        )

    def get_article_by_userid(self, user_id: int, drafted: int = 1) -> List[Article]:
        return (
            self.db.query(Article)
            .filter(Article.user_id == user_id, Article.drafted == drafted)
            .all()
        )

    def get_favorite_article_by_userid(self, user_id: int) -> List[Article]:
        return (
            self.db.query(Article)
            .join(Favorite, Favorite.article_id == Article.id)
            .filter(Favorite.user_id == user_id)
            .order_by(Favorite.create_time.desc())
            .all()
        )

    def get_comment_article_by_userid(self, user_id: int) -> List[Article]:
        subquery = (
            self.db.query(func.distinct(Comment.article_id))
            .filter(Comment.user_id == user_id)
            .subquery()
        )
        return self.db.query(Article).filter(Article.id.in_(subquery)).all()

    def model_to_dict(self, article: Article) -> dict:
        result = {}
        for k, v in article.__dict__.items():
            if not k.startswith("_"):
                if isinstance(v, datetime):
                    v = v.strftime("%Y-%m-%d %H:%M:%S")
                result[k] = v
        return result
