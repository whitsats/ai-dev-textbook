"""知舟 v3 的应用入口。

第 1 篇的博客路由（article / comment / favorite / user）在这里省略——参考实现只装**第 3 篇新增的部分**，
这样「第 3 篇加了什么」一眼可见，也让这份代码不需要数据库就能起。

    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI

from app.api import agent as agent_api
from app.api import llm as llm_api

app = FastAPI(title="知舟 v3 · Agent 版", version="3.0")
app.include_router(agent_api.router)

# 诊断端点默认只在开发环境挂载：它会把提示结构原样报出来，不该出现在线上。
if os.environ.get("APP_ENV", "dev") == "dev":
    app.include_router(llm_api.router)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "env": os.environ.get("APP_ENV", "dev"),
            "model": os.environ.get("LLM_MODEL", "(未设置)")}
