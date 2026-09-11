from pydantic import BaseModel, Field


class CommentAddReq(BaseModel):
    article_id: int = Field(..., description="文章 ID")
    content: str = Field(..., min_length=5, max_length=1000, description="评论内容")


class CommentReplyReq(BaseModel):
    article_id: int = Field(..., description="文章 ID")
    content: str = Field(..., min_length=5, max_length=1000, description="回复内容")
    reply_id: int = Field(..., description="被回复的评论 ID")
    base_reply_id: int = Field(..., description="所属一级评论 ID")
