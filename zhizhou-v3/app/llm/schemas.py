"""提示的契约：既是发给服务端的 schema，也是回来之后的校验器（3.2.4）。"""
from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, Field, ValidationError

Tag = Literal["后端", "前端", "数据库", "AI", "运维"]
TAGS = list(get_args(Tag))       # 清单与 enum 同一处定义，不会有第二份


class ArticleSummary(BaseModel):
    """摘要与标签。字段上限写在模型里，同时就是这个 schema 的约束。"""

    summary: str = Field(max_length=120)
    tags: list[Tag] = Field(max_length=3)

    @classmethod
    def json_schema_strict(cls) -> dict:
        """OpenAI 兼容方言的严格模式：必须 additionalProperties=False 且所有字段必填。"""
        schema = cls.model_json_schema()
        schema["additionalProperties"] = False
        for field in schema.get("properties", {}).values():
            if isinstance(field, dict) and "items" in field:
                field["items"] = {**field["items"], "additionalProperties": False} \
                    if field["items"].get("type") == "object" else field["items"]
        schema.pop("title", None)
        return schema


class PlanStep(BaseModel):
    """计划的一步。计划是纯数据，所以它也能被静态校验（3.4.3）。"""

    id: str
    action: str
    accept: str = ""
    deps: list[str] = Field(default_factory=list)


class DraftPlan(BaseModel):
    goal: str
    steps: list[PlanStep]
    max_steps: int = 12


def validate(data: dict) -> ArticleSummary:
    """服务端已保证格式，这一层是防自己：schema 漂移、缓存串号、假实现。"""
    try:
        return ArticleSummary.model_validate(data)
    except ValidationError as exc:
        raise ValueError(exc.errors()[0]["msg"]) from exc
