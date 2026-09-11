from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.user import User


class CommentDao:
    def __init__(self, db: Session):
        self.db = db

    def model_to_dict(self, obj) -> dict:
        result = {}
        for k, v in obj.__dict__.items():
            if not k.startswith("_"):
                if isinstance(v, datetime):
                    v = v.strftime("%Y-%m-%d %H:%M:%S")
                result[k] = v
        return result

    def _sanitize_user_dict(self, user_dict: dict) -> dict:
        if not user_dict:
            return {}
        safe = dict(user_dict)
        safe.pop("password", None)
        return safe

    def get_comment_user_list(self, article_id: int) -> List[Dict[str, Any]]:
        final_data_list = []
        comment_list = self.find_comment_by_article_id(article_id)
        for comment in comment_list:
            user = self.db.query(User).filter(User.user_id == comment.user_id).first()
            all_reply = self.find_reply_by_replyid(base_reply_id=comment.id)
            reply_list = []
            for reply in all_reply:
                from_user = (
                    self.db.query(User).filter(User.user_id == reply.user_id).first()
                )
                to_comment_row = (
                    self.db.query(Comment).filter(Comment.id == reply.reply_id).first()
                )
                to_user = None
                if to_comment_row:
                    to_user = (
                        self.db.query(User)
                        .filter(User.user_id == to_comment_row.user_id)
                        .first()
                    )
                reply_item = {
                    "from_user": self._sanitize_user_dict(self.model_to_dict(from_user))
                    if from_user
                    else {},
                    "to_user": self._sanitize_user_dict(self.model_to_dict(to_user)) if to_user else {},
                    "content": self.model_to_dict(reply),
                }
                reply_list.append(reply_item)
            comment_data = self.model_to_dict(comment)
            if user:
                comment_data.update(self._sanitize_user_dict(self.model_to_dict(user)))
            comment_data["reply_list"] = reply_list
            final_data_list.append(comment_data)
        return final_data_list

    def find_comment_by_article_id(self, article_id: int) -> List[Comment]:
        return (
            self.db.query(Comment)
            .filter(
                Comment.article_id == article_id,
                Comment.reply_id == 0,
                Comment.base_reply_id == 0,
            )
            .order_by(Comment.id.desc())
            .all()
        )

    def find_reply_by_replyid(self, base_reply_id: int) -> List[Comment]:
        return (
            self.db.query(Comment)
            .filter(Comment.base_reply_id == base_reply_id)
            .order_by(Comment.id.desc())
            .all()
        )

    def get_user_comments(self, user_id: int) -> List[Comment]:
        return (
            self.db.query(Comment)
            .filter(Comment.user_id == user_id)
            .order_by(Comment.create_time.desc())
            .all()
        )

    def get_article_comment_count(self, article_id: int) -> int:
        return (
            self.db.query(Comment)
            .filter(
                Comment.article_id == article_id,
                Comment.reply_id == 0,
                Comment.base_reply_id == 0,
            )
            .count()
        )

    def insert_comment(
        self,
        user_id: int,
        article_id: int,
        content: str,
        ipaddr: str,
    ) -> Comment:
        max_floor_row = (
            self.db.query(func.max(Comment.floor_number).label("max_floor"))
            .filter(Comment.article_id == article_id)
            .first()
        )
        max_floor = max_floor_row.max_floor or 0
        next_floor = max_floor + 1
        comment = Comment(
            user_id=user_id,
            article_id=article_id,
            content=content,
            ipaddr=ipaddr,
            floor_number=next_floor,
            reply_id=0,
            base_reply_id=0,
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def insert_reply(
        self,
        article_id: int,
        user_id: int,
        content: str,
        ipaddr: str,
        reply_id: int,
        base_reply_id: int,
    ) -> Comment:
        comment = Comment(
            user_id=user_id,
            article_id=article_id,
            content=content,
            ipaddr=ipaddr,
            reply_id=reply_id,
            base_reply_id=base_reply_id,
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment
