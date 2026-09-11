from typing import Optional, List

from pydantic import BaseModel


class ArticleListItem(BaseModel):
    id: int
    label_name: Optional[str] = None
    article_image: Optional[str] = None
    title: str
    article_tag: Optional[str] = None
    user_id: Optional[int] = None
    browse_num: int = 0
    drafted: Optional[int] = None
    article_type: Optional[str] = None
    create_time: Optional[str] = None
    nickname: Optional[str] = None


class ArticleDetail(BaseModel):
    id: int
    label_name: Optional[str] = None
    article_image: Optional[str] = None
    title: str
    article_content: str
    article_tag: Optional[str] = None
    user_id: Optional[int] = None
    browse_num: int = 0
    drafted: Optional[int] = None
    article_type: Optional[str] = None
    create_time: Optional[str] = None
