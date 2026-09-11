from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime

from app.models.base import Base


class Comment(Base):
    __tablename__ = "comment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    article_id = Column(Integer, nullable=False)
    ipaddr = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    reply_id = Column(Integer, default=0, comment="回复目标评论id，一级评论为0")
    floor_number = Column(Integer, default=0, comment="一级评论楼层号")
    base_reply_id = Column(Integer, default=None, comment="所属一级评论id，一级评论为0")
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Comment(id={self.id}, article_id={self.article_id}, user_id={self.user_id})>"
