"""知舟的 Agent 端点。外壳沿用 `Result`，错误也不换形状。

**人工确认怎么落在这个端点上**：`approve` 由调用方传入（真实项目里是前端二次确认后的回调，
或一个「待确认」表 + 轮询）。这里默认**一律不批**——不接受任何默认放行的发布路径。

`/chat` 是无记忆的一次性调用，`/session/chat` 才有会话与长期记忆。分成两个端点是有意的：
**「要不要带历史」是调用方的选择，不是服务端的默认**。默认带上历史，就会让「探测一条提示」
这类调用莫名其妙地变贵、也变不可复现。

`_SESSIONS` 是进程内的内存替身：重启即清空。换成真库只改这一行的构造
（`SqlMemoryStore(session_factory)`），四个端点一行不改——这正是把存储抽成协议的目的。
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.agent.memory import InMemoryStore
from app.agent.trace import Price, Tracer
from app.core.result import Result
from app.llm.client import Config, LlmError
from app.services.agent_service import AgentService

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

# 进程内一份：同一进程里的多次请求才看得到彼此的会话。真库实现见模块文档。
_SESSIONS = InMemoryStore()

# 追踪器同样是**进程级一份**。每次请求新建一个的话，`/metrics` 只会看到最后一次运行
# ——而指标的意义全在「很多次」上。内容捕获与单价是配置（环境变量），不是代码常量。
_CAPTURE = os.environ.get("LLM_CAPTURE_CONTENT", "") == "1"
_TRACER = Tracer(capture_content=_CAPTURE, price=Price.from_env(os.environ.get))


class AgentChatReq(BaseModel):
    task: str = Field(min_length=1, max_length=2_000)
    allow_write: bool = False          # 只读会话是默认档
    run_id: str | None = None
    max_steps: int = Field(default=8, ge=1, le=20)


class SessionChatReq(AgentChatReq):
    session_id: int | None = None      # 不给就新开一个会话
    policy: str = Field(default="note", pattern="^(full|clean|note|compress)$")
    max_messages: int | None = Field(default=None, ge=2, le=200)


def get_llm_config() -> Config:
    try:
        return Config.from_env()
    except LlmError as exc:
        raise HTTPException(status_code=500, detail=f"模型未配置：{exc}") from exc


def get_agent_service(cfg: Config = Depends(get_llm_config)) -> AgentService:
    return AgentService(cfg, user_id=7, sessions=_SESSIONS, tracer=_TRACER)


def get_memory_service() -> AgentService:
    """读会话、看装配账、删一条记忆——这三件事不该要求模型凭据。

    它们走一条不依赖 `get_llm_config` 的依赖，否则在没配密钥的开发机上，
    「会话存了些什么」会以一个 500 回答你，而那与模型毫无关系。
    """
    return AgentService(Config(api_key=""), user_id=7, sessions=_SESSIONS, tracer=_TRACER)


@router.post("/chat", response_model=Result)
def chat(req: AgentChatReq, svc: AgentService = Depends(get_agent_service)) -> Result:
    try:
        r = svc.chat(req.task, allow_write=req.allow_write, run_id=req.run_id,
                     max_steps=req.max_steps)
    except LlmError as exc:
        # 模型侧的失败按统一外壳返回：code 非 0，data 里给出失败分类与已花掉的词元
        return Result.fail(f"模型调用失败：{exc.kind}",
                           code=2, data={"kind": exc.kind, "spent": exc.spent})
    return Result.success(AgentService.to_payload(r))


@router.post("/session/chat", response_model=Result)
def session_chat(req: SessionChatReq, svc: AgentService = Depends(get_agent_service)) -> Result:
    """带记忆的一轮。响应里的 `data.memory` 就是这一次装配的账——**账属于响应体，不属于日志**。"""
    try:
        payload = svc.session_chat(req.task, session_id=req.session_id, policy=req.policy,
                                   allow_write=req.allow_write, max_steps=req.max_steps)
    except KeyError as exc:                       # 会话不存在：这是客户端的问题，不是服务端的
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LlmError as exc:
        return Result.fail(f"模型调用失败：{exc.kind}",
                           code=2, data={"kind": exc.kind, "spent": exc.spent})
    return Result.success(payload)


@router.get("/session/{session_id}", response_model=Result)
def get_session(session_id: int, svc: AgentService = Depends(get_memory_service)) -> Result:
    """可回放的会话：存的是正文，所以拿得到的是真的历史，不是一串哈希。"""
    try:
        return Result.success(svc.transcript(session_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/session/{session_id}/context", response_model=Result)
def get_context(session_id: int, policy: str = "note", max_messages: int | None = None,
                svc: AgentService = Depends(get_memory_service)) -> Result:
    """只读诊断：**这一次装进去多少、省了多少、丢了什么**。不写库、不调模型。"""
    try:
        return Result.success(svc.memory_of(session_id, policy=policy, max_messages=max_messages))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/metrics", response_model=Result)
def metrics(window: int = Query(default=50, ge=1, le=200),
            svc: AgentService = Depends(get_memory_service)) -> Result:
    """四类指标：成功率 / 平均步数 / 每任务词元 / 失败分布（再给延迟分位与分维度）。

    它挂在**不需要模型凭据**那条依赖上：看账不该要求密钥，否则没配模型的开发机上
    「刚才那几次到底跑成什么样」会以一个 500 回答你（3.6 踩过同一个坑）。
    参数 `window` 是看最近多少次运行——取有界的滑动窗口，而不是「从进程启动至今」。
    """
    return Result.success(svc.metrics(window=window))


@router.delete("/memory/{key}", response_model=Result)
def forget(key: str, svc: AgentService = Depends(get_memory_service)) -> Result:
    """删掉一条长期记忆。用户能删，才谈得上「可脱敏、可保留期」。"""
    return Result.success({"key": key, "deleted": svc.forget(key)})
