from pydantic import BaseModel, Field


class FavoriteUpdateReq(BaseModel):
    article_id: int = Field(..., description="文章 ID")
    canceled: int = Field(..., description="0=收藏 1=取消收藏")
