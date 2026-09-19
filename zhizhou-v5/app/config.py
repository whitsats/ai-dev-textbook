"""v5 的配置：**与前两棵树读同一套环境变量名**。

这不是顺手抄过来的，是**对照条件**（`PROJECT.md` 第一节的硬约定）：
第 5 篇要量的差是「有没有知识层」，如果连配置方式都换了，差里就混进了无关变量。

三棵树的关系因此是干净的：同一份 `.env`、同一套模型、同一套工具契约，
v5 之前的所有代码都是 v3／v4 里写过的东西——**唯一的新东西是资料**。
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.0

    @classmethod
    def from_env(cls, getenv=os.environ.get) -> "Config":
        """缺密钥**在装配时就报错**，不等到第一次调用（v3 起的一贯纪律）。

        检索这一侧**不需要密钥**：`--offline` 那一路从头到尾不读这个函数。
        所以「知识层能不能被验证」不取决于你有没有服务商——这是本树的一条设计约束。
        """
        key = getenv("LLM_API_KEY", "")
        if not key:
            raise RuntimeError("缺少 LLM_API_KEY——v5 与 v3／v4 读同一套变量，见 .env.example")
        return cls(
            api_key=key,
            base_url=getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=float(getenv("LLM_TEMPERATURE", "0") or 0),
        )

    def redacted(self) -> dict:
        """唯一能进日志的形态：密钥只留尾四位。"""
        tail = self.api_key[-4:] if len(self.api_key) >= 4 else ""
        return {"base_url": self.base_url, "model": self.model,
                "temperature": self.temperature, "api_key": f"***{tail}"}
