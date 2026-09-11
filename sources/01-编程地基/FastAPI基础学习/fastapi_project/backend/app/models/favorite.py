from datetime import datetime

from sqlalchemy import Column, Integer, DateTime

from app.models.base import Base


class Favorite(Base):
    __tablename__ = "favorite"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    article_id = Column(Integer, nullable=False)
    canceled = Column(Integer, default=0, comment="0=收藏 1=取消收藏")
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Favorite(id={self.id}, user_id={self.user_id}, article_id={self.article_id}, canceled={self.canceled})>"
