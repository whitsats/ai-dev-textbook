from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime

from app.models.base import Base


class Article(Base):
    __tablename__ = "article"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label_name = Column(String(100), nullable=True, comment="文章类别名称")
    article_image = Column(String(256), nullable=True, comment="文章缩略图")
    title = Column(String(256), nullable=False)
    article_content = Column(Text, nullable=False, comment="文章正文内容")
    article_tag = Column(String(64), nullable=True, comment="文章标签，逗号分隔")
    user_id = Column(Integer, nullable=True)
    browse_num = Column(Integer, default=0)
    drafted = Column(Integer, default=None, comment="是否草稿，0是草稿 1是发布")
    article_type = Column(String(255), nullable=True, comment="原创、首发、其它")
    create_time = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title}, drafted={self.drafted})>"
