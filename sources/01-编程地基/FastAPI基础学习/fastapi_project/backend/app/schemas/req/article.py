from typing import Optional, List

from pydantic import BaseModel, Field


class ArticleSaveReq(BaseModel):
    article_id: int = Field(..., description="-1=首次保存草稿，其他=更新已有文章")
    title: str = Field(default="", description="文章标题")
    article_content: str = Field(default="", description="文章正文 HTML")
    drafted: int = Field(..., description="0=草稿 1=发布")
    label_name: Optional[str] = Field(None, description="栏目名称 key")
    article_tag: Optional[str] = Field(None, description="标签，逗号分隔")
    article_type: Optional[str] = Field(None, description="文章类型")
    article_image: Optional[str] = Field(None, description="头图相对路径，例如 article/header/xxx.jpg")


class DraftedDetailReq(BaseModel):
    id: int = Field(..., description="草稿文章 ID")


class ArticleListReq(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    article_type: str = Field(default="recommend", description="栏目类型")
    keyword: Optional[str] = Field(None, description="搜索关键字")
