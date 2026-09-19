"""v4 的配置：**与 v3 读同一套环境变量名**。

这不是巧合，是有意设定的对照条件。第 4 篇要比的是「同一件事用框架做会变成什么样」，
如果连配置方式都换了，比出来的差异里就混进了无关变量。所以 `LLM_API_KEY` /
`LLM_BASE_URL` / `LLM_MODEL` 三个名字沿用 v3 的 `app/llm/client.py`——
同一份 `.env`，两个版本都能跑。

v3 里这一块是自己写的（`Config.from_env` ＋ `redacted()` ＋ 方言枚举）；
v4 只保留「读环境变量」这一件事，其余交给框架——**但有一件事仍然要自己写：
把密钥从日志里挡掉**。框架不认识你的日志。
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
        """缺密钥要**在装配时**就报错，而不是等到第一次调用（v3 同一条纪律）。"""
        key = getenv("LLM_API_KEY", "")
        if not key:
            raise RuntimeError("缺少 LLM_API_KEY——v4 与 v3 读同一套变量，见 .env.example")
        return cls(
            api_key=key,
            base_url=getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=float(getenv("LLM_TEMPERATURE", "0") or 0),
        )

    def redacted(self) -> dict:
        """唯一能进日志的形态：密钥只留尾四位，其余抹掉。"""
        return {"base_url": self.base_url, "model": self.model,
                "temperature": self.temperature,
                "api_key": f"***{self.api_key[-4:]}" if self.api_key else "(未设置)"}
