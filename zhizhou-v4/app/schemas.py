"""v4 的结构化输出契约：与 v3 的 `app/llm/schemas.py` 是**同一份契约**。

对照点先摆在这里。v3 里同一个东西有三个身份，而且三个都靠自己维护：

    ① 发给服务端的 schema —— 手写 `json_schema_strict()`（加 `additionalProperties: False`、去掉 title）；
    ② 给模型看的字段说明 —— 写在提示文件 `app/llm/prompts/article_summary.md` 的第 2 条规则里；
    ③ 回来之后的校验器 —— 手写 `validate()`，把 `ValidationError` 翻成人话。

v4 里这三个身份是**同一个 `BaseModel`**：字段名与类型进 schema、`description` 进模型能看到的说明、
`Field(max_length=...)` 进约束与校验。**少掉的两处**是 ① 与 ③——
① 由框架做转换（它认识 OpenAI 方言），③ 由返回类型保证（Pydantic 实例就是校验过的）。

但有一件事**没少**：约束写在模型里，而不是散在提示词里。第 4.2.4 节会用两台模型的读数说明
为什么这件事不能靠「提示里写一句」。
"""
from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, Field

# 清单与 enum 同一处定义，不会有第二份（与 v3 同一条纪律）。
Tag = Literal["后端", "前端", "数据库", "AI", "运维"]
TAGS = list(get_args(Tag))


class ArticleSummary(BaseModel):
    """摘要与标签：把一篇文章压成两句话与不超过三个标签。

    两个字段都带 `description`，因为**模型看到的就是它们**：
    v3 把「最多三个」写在提示文件的第 2 条规则里，v4 写在 `Field` 里——
    而 `Field` 的这一份是**同时**给模型的（进 schema）和给自己的（回来校验）。
    """

    summary: str = Field(max_length=120, description="三句话以内的摘要，只陈述正文写过的事实。")
    tags: list[Tag] = Field(max_length=3, description="从清单里选，按正文实际内容选，不要凑数。")


class ToolAction(BaseModel):
    """模型打算调用的那一个工具。

    它比 `JsonOutputParser` 多一层保障：`args` 是**对象**而不是一段 JSON 字符串，
    字段名与类型都被校验过。v3 里这一层是手写的（工具注册表在 3.5 才做），
    而这里它只需要一个 `BaseModel`。
    """

    tool: str = Field(description="要调用的工具名，必须是注册表里有的那一个。")
    args: dict = Field(default_factory=dict, description="这个工具的参数，键名与它的签名一致。")


class DraftMeta(BaseModel):
    """起草一份草稿时需要的元信息：标题、标签、一句话说明为什么选这两个标签。"""

    title: str = Field(max_length=50, description="不超过 50 字的标题。")
    tags: list[Tag] = Field(max_length=3)
    reason: str = Field(max_length=200, description="为什么选这几个标签，指到正文里的具体内容。")
