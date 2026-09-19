"""v4 的唯一模型出口：**一次 `init_chat_model` 调用**。

对照点先摆在这里。v3 的 `app/llm/client.py` 自己写了 468 行（非空 396 行）：两方言传输、
有界超时、重试与退避、工具调用解析、受约束解码、`finish_reason == "length"` 的识别。
v4 把这些交给框架，本文件只剩两件事：

1. **给出一个模型对象**（`build_model`）——这是「框架替你做了什么」的那一半；
2. **报出框架的默认值**（`describe_defaults`）——这是框架**不告诉你**的那一半。

第二件事是本节的要点。`init_chat_model(...)` 看起来什么都没配就返回一个能用的模型，
但「能用」不等于「有界」：不显式传 `timeout`／`max_retries` 时，落到的是底层
`openai` SDK 的默认值。实测（`openai` 2.36.0）读到的是
`Timeout(connect=5.0, read=600, write=600, pool=600)` 与 `max_retries=2`——
**读超时是 600 秒**，而 v3 手写的是 30 秒。两次重试乘上十分钟，一次卡住的请求
可以占住一次会话很久。所以本模块把这两个值做成显式参数，并在 `describe_defaults` 里
把「你没写时它会是多少」打印出来：**框架有默认值，不等于你有边界。**
"""
from __future__ import annotations

from langchain.chat_models import init_chat_model

from app.config import Config

# 与 v3 对齐的边界（v3 的 `client.py`：连接 5s、读 30s、重试 2 次）。
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2


def build_model(cfg: Config | None = None, *, timeout: float = DEFAULT_TIMEOUT,
                max_retries: int = DEFAULT_MAX_RETRIES, temperature: float | None = None,
                **overrides):
    """唯一入口。**每一次模型调用都从这里拿对象**，别处不得直接构造 ChatOpenAI。

    `overrides` 是留给后面几章的（工具绑定、结构化输出、流式），
    但它有一个纪律：**只能加参数，不能改这里的默认值**。
    """
    cfg = cfg or Config.from_env()
    return init_chat_model(
        cfg.model,
        model_provider="openai",          # 本地服务商是 OpenAI 兼容端点，所以走这一支
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        temperature=cfg.temperature if temperature is None else temperature,
        timeout=timeout,                  # 显式给出，不用 SDK 的 600 秒
        max_retries=max_retries,
        **overrides,
    )


def describe_defaults(model) -> dict:
    """把「框架这一层写了什么、没写什么」读出来。

    **这里踩过一个坑，所以它是现在这样写的。** 第一版读的是内部 HTTP 客户端的
    `.timeout`，两种情况下读到的都是 `None`——因为框架把超时**按请求**传下去
    （`root_client.chat.completions.create(..., timeout=...)`），而不是在构造客户端时传。
    只看客户端就会得出「没设超时」的错误结论，而那正是本函数要回答的问题。

    所以现在读两层，并把「没设时兜底成多少」也算出来：
      · 框架层：`request_timeout` / `max_retries`，为 `None` 就是没给值；
      · 下游兜底：`openai` SDK 的常量（实测 2.36.0：read 600s、重试 2 次）。
    后一项读写的是 SDK 的私有常量——诊断函数里可以接受，但要注明：
    **它是「此刻这个版本」的事实，不是稳定契约。**
    """
    from openai import _constants as sdk          # noqa: PLC0415 —— 只有诊断这里需要它

    floor = sdk.DEFAULT_TIMEOUT
    timeout = getattr(model, "request_timeout", None)
    retries = getattr(model, "max_retries", None)
    return {
        "类型": type(model).__name__,
        "model": getattr(model, "model_name", ""),
        "框架层 request_timeout": timeout,
        "框架层 max_retries": retries,
        "未设时下游兜底的 read 超时（秒）": getattr(floor, "read", None),
        "未设时下游兜底的重试次数": sdk.DEFAULT_MAX_RETRIES,
        "实际生效的 read 超时（秒）": getattr(floor, "read", None) if timeout is None else timeout,
        "实际生效的重试次数": sdk.DEFAULT_MAX_RETRIES if retries is None else retries,
    }
