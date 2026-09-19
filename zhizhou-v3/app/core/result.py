"""统一响应外壳，沿用第 1 篇的 `Result{code, msg, data}`。

第 3 篇新增的端点也必须穿同一件外衣：客户端不该因为「这是 AI 接口」而换一套解析代码。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Result(BaseModel):
    code: int = 0
    msg: str = "ok"
    data: Any = None

    @classmethod
    def success(cls, data: Any = None, msg: str = "ok") -> "Result":
        return cls(code=0, msg=msg, data=data)

    @classmethod
    def fail(cls, msg: str, code: int = 1, data: Any = None) -> "Result":
        return cls(code=code, msg=msg, data=data)
