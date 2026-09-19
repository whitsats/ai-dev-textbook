"""v4 的调用层护栏：v3 `bind_tools` 里那四条规则，换个地方落。

v3 的 `bind_tools(registry, ...)` 把四件事全塞进一个「参数文本 → 结果文本」的闭包里：
坏参数收成可读失败、写操作按 `run_id` 生成幂等键、需要确认的动作先问 `approve`、
每次调用上报追踪回呼。它写得对，但**位置不对**——那些规则管的是「一次调用」，
却被塞进了「怎么装配循环」里，于是任何绕过 `bind_tools` 的调用路径都没有护栏。
4.3 的实测里有一条正是这么来的：`create_agent` 默认**不**接住工具异常，
一份照抄 v3 逻辑的工具集在框架里第一次失败就是整轮崩掉。

v4 把这四条搬到中间件上，因为它们遵守的正是同一个契约：

    一次工具调用 = 判断（谁、能不能、做没做过）→ 执行 → 记账

四条规则：

| 规则 | v3 的位置 | v4 的位置 | 为什么 |
| --- | --- | --- | --- |
| 异常收成可读文本 | 循环里 `except` | `wrap_tool_call` | 循环不知道是哪一步坏的，中间件知道 |
| 幂等键 | `bind_tools` 闭包 | `wrap_tool_call` | 同上：键要由**运行**生成，不由模型提供 |
| 人工确认 | `approve` 回调 | `wrap_tool_call`（或框架的中断） | 两种做法的代价见 4.3.7 |
| 审计与耗时 | 追踪回呼 | `wrap_tool_call` | 同一次调用只有一个地方看得全 |

**它不替代 `HumanInTheLoopMiddleware`。** 那个用 LangGraph 的中断把「等人」变成
可以跨进程暂停的状态（4.3.7 有实测），代价是需要检查点与一条 `Command(resume=...)`；
这里的回调是进程内的一个函数，便宜，但进程一停就问不到了。
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable

from langchain.agents.middleware import AgentMiddleware, wrap_tool_call
from langchain_core.messages import ToolMessage

from app.tools import WRITE_TOOLS


def idem_key(run_id: str, name: str, args: dict) -> str:
    """一次写操作的幂等键：**由运行生成，不由模型提供**（3.5.5 的结论在这里照用）。

    键里必须带 `run_id`：同一任务内重复的写只执行一次，跨任务换一个 `run_id`，
    于是「重放」不会被静默吞掉，也**不会**重复写。
    """
    digest = hashlib.sha1(json.dumps(args, sort_keys=True, ensure_ascii=False)
                          .encode("utf-8")).hexdigest()[:12]
    return f"{run_id}:{name}:{digest}"


def bucket_error(message: str) -> str:
    """把失败消息收进有限档（与 v3 的 `error_kind` 同一张表）。

    取值集合必须小：按 `error.type` 分组时，只出现一次的柱子读不出东西。
    收档的依据是「下一步该改什么」——改 schema / 改权限 / 改提示词 / 查工具实现。
    """
    for key, bucket in (("权限不足", "权限不足"), ("缺少幂等键", "缺幂等键"),
                        ("越权", "越权"), ("不属于你", "越权"),
                        ("不存在", "目标不存在"),
                        ("多出字段", "参数不合 schema"),
                        ("不是合法", "参数不合 schema"), ("类型", "参数不合 schema"),
                        ("必填", "参数不合 schema")):
        if key in message:
            return bucket
    return "工具执行失败"


def guard_tools(*, run_id: str, approve: Callable[[str, dict], bool] | None = None,
                require_approval: tuple[str, ...] = ("publish_article",),
                audit: list[dict] | None = None) -> AgentMiddleware:
    """把四条规则装成一个中间件。`run_id` 是幂等键的命名空间，`audit` 是审计出口。

    `approve(name, args) -> bool`：返回 `False` 就是「这轮不执行」。
    没给 `approve` 时，`require_approval` 里的动作一律不执行——**默认拒绝**，
    而不是默认放行（3.8 的档位表里「没配」等于哪一档，这里给了明确答案）。
    """
    seen: dict[str, str] = {}          # 幂等键 → 第一次的返回文本

    @wrap_tool_call
    def guard(request, handler):       # noqa: ANN001 —— 框架给的签名
        call = request.tool_call
        name, args, call_id = call["name"], call.get("args") or {}, call["id"]
        started = time.perf_counter()

        def emit(**kw: Any) -> None:
            if audit is not None:
                audit.append({"tool": name, "run_id": run_id,
                              "ms": round((time.perf_counter() - started) * 1000, 1), **kw})

        if name in require_approval and not (approve and approve(name, args)):
            text = f"[等待人工确认] {name} 未获批准，本轮不执行。请向用户说明并停下。"
            emit(ok=False, error_type="未获人工确认", arguments=json.dumps(args, ensure_ascii=False))
            # `name` 要自己填：框架自己的工具节点会填，替它合成的消息不填的话
            # 下游按 `message.name` 分组的统计会把这两类失败归成一个空名字。
            return ToolMessage(content=text, tool_call_id=call_id, status="error", name=name)

        key = idem_key(run_id, name, args) if name in WRITE_TOOLS else ""
        if key and key in seen:
            # 命中不等于「没发生」：这次调用真实发生过、被拦下了，所以要留痕。
            emit(ok=True, idem=key, repeated=True,
                 arguments=json.dumps(args, ensure_ascii=False))
            return ToolMessage(content=seen[key] + "\n（幂等键命中，本次未重复执行）",
                               tool_call_id=call_id, name=name)

        try:
            message = handler(request)
        except Exception as exc:        # 框架默认会把异常抛穿整轮（4.3.5 实测）
            text = f"[工具失败] {type(exc).__name__}: {exc}"
            emit(ok=False, error_type=bucket_error(str(exc)),
                 arguments=json.dumps(args, ensure_ascii=False), result=text)
            return ToolMessage(content=text, tool_call_id=call_id, status="error", name=name)

        content = message.content if isinstance(message.content, str) else str(message.content)
        if key:
            seen[key] = content
        emit(ok=True, idem=key, arguments=json.dumps(args, ensure_ascii=False),
             result=content[:60])
        return message

    return guard
