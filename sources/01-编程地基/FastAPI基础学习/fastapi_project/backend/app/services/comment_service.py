from typing import Any

from sqlalchemy.orm import Session

from app.dao.comment_dao import CommentDao


class CommentService:
    def __init__(self, db: Session, dao: CommentDao):
        self.db = db
        self.dao = dao

    def add_comment(
        self, user_id: int, article_id: int, content: str, ipaddr: str
    ) -> dict[str, Any]:
        content = content.strip()
        if len(content) < 5 or len(content) > 1000:
            return {"code": 400, "msg": "内容长度不符"}
        try:
            self.dao.insert_comment(user_id, article_id, content, ipaddr)
            return {"code": 200, "msg": "评论成功"}
        except Exception as e:
            return {"code": 500, "msg": f"评论失败: {str(e)}"}

    def add_reply(
        self,
        user_id: int,
        article_id: int,
        content: str,
        ipaddr: str,
        reply_id: int,
        base_reply_id: int,
    ) -> dict[str, Any]:
        content = content.strip()
        if len(content) < 5 or len(content) > 1000:
            return {"code": 400, "msg": "内容长度不符"}
        try:
            row = self.dao.insert_reply(
                article_id, user_id, content, ipaddr, reply_id, base_reply_id
            )
            return {"code": 200, "msg": "回复成功", "data": {"id": row.id, "user_id": row.user_id}}
        except Exception as e:
            return {"code": 500, "msg": f"回复失败: {str(e)}"}

    def get_comment_list(self, article_id: int) -> dict[str, Any]:
        data = self.dao.get_comment_user_list(article_id)
        count = self.dao.get_article_comment_count(article_id)
        return {"list": data, "count": count}
