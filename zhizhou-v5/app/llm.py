"""真机出口：**一个 `(messages) -> str` 的闭包**，别的什么都不做。

为什么这一层这么薄？因为第 5 篇要比的是「有没有知识层」，不是「怎么写模型客户端」——
那是 3.2 与 4.1 的活。本树沿用 v4 的那一条纪律：显式给出 `timeout` 与 `max_retries`，
**不落到下游 SDK 的 600 秒读超时**上（4.1 实测：不显式传时，框架层是 `None`，
真正生效的是 `openai` SDK 的常量）。

`make_call()` 返回的那个函数，签名与 `app.scripted.ScriptedModel` 完全一致。
所以 `app.rag.answer(call, ...)` 里那一行字，离线与真机走的是同一个位置——
3.10 起全书用的「离线当门、真机报数」，靠的就是这个形状。
"""
from __future__ import annotations

from app.config import Config

#: 与 v3／v4 对齐的边界：读 30 秒、重试 2 次。
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2


def build_model(cfg: Config | None = None, *, timeout: float = DEFAULT_TIMEOUT,
                max_retries: int = DEFAULT_MAX_RETRIES):
    """建一个模型对象。**只有 `make_call` 该调它。**"""
    from langchain.chat_models import init_chat_model  # noqa: PLC0415

    cfg = cfg or Config.from_env()
    return init_chat_model(
        cfg.model,
        model_provider="openai",       # 本地服务商是 OpenAI 兼容端点
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        temperature=cfg.temperature,
        timeout=timeout,               # 显式给出，不用 SDK 的 600 秒
        max_retries=max_retries,
    )


def make_call(cfg: Config | None = None, *, timeout: float = DEFAULT_TIMEOUT,
              max_retries: int = DEFAULT_MAX_RETRIES):
    """把模型包成 `call(messages) -> str`。`messages` 是 `[{"role","content"}, ...]`。"""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: PLC0415

    cfg = cfg or Config.from_env()
    model = build_model(cfg, timeout=timeout, max_retries=max_retries)
    roles = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}

    def call(messages: list[dict]) -> str:
        msgs = [roles[m["role"]](content=m["content"]) for m in messages]
        out = model.invoke(msgs)
        content = getattr(out, "content", out)
        return content if isinstance(content, str) else str(content)

    call.cfg = cfg          # 让调用方能打印「用的是哪个服务商、哪个模型」（只打脱敏形态）
    return call
