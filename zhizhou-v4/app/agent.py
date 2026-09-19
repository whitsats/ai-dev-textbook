"""v4 的代理层：`create_agent` 一个函数装下循环，外加一份**手写循环**做对照。

两条路径做的事完全相同——同一个模型、同一批工具、同一份系统提示、同一套预算。
不一样的是**循环归谁**：

| | 手写版（`run_handwritten`） | 框架版（`create_zhizhou`） |
| --- | --- | --- |
| 循环在哪 | 本文件的一个 `while True` | 一个编译好的 LangGraph 图 |
| 终止由谁决定 | 预算（模型调用数、词元数、墙钟）＋ 卡死检测 | `recursion_limit`（**数的是 super-step**）＋ 中间件 |
| 工具错误 | 循环里 `except` 收成文本 | 默认**抛穿整轮**，要中间件接 |
| 记账 | 循环自己数 | 从返回的消息里读 |
| 加一个新能力 | 改循环（所有路径都受影响） | 加一个中间件（改动可加不可改） |

这一节要证明的不是「框架更好」，而是**框架替代的是编排，不是判断**：
四条护栏规则（异常、幂等、审批、审计）在两条路径上**一字不差**，
改的只是它们住在哪一层。所以本文件与 `middleware.py` 里各有一份 `idem_key` 的调用点，
而**只有一份** `idem_key` 的实现。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.middleware import bucket_error, guard_tools, idem_key
from app.prompts import AGENT_SYSTEM
from app.tools import WRITE_TOOLS

# 本书显式给出的图递归上限。**框架默认是 9999**（langgraph 1.2.2 实测），
# 而 recursion_limit 数的是 super-step：实测一次「模型 + 工具」占 2 步，
# 所以 9999 约等于 5,000 次模型调用——那不是预算，是没有预算。见 4.3.4。
DEFAULT_RECURSION_LIMIT = 8

# 与 v3 `AgentService.chat` 的默认值逐项对齐（v3 的 3.10 验收就是按这组数跑的）。
DEFAULT_MAX_STEPS = 8
DEFAULT_MAX_TOKENS = 8000


@dataclass
class Budget:
    """手写版的三条上限。**预算不是越小越好**：太小会让循环在读到东西之前就收口。"""

    max_steps: int = DEFAULT_MAX_STEPS
    max_tokens: int = DEFAULT_MAX_TOKENS
    steps: int = 0
    tokens: int = 0

    def exhausted(self) -> str:
        if self.steps >= self.max_steps:
            return f"步数上限 {self.max_steps}"
        if self.tokens >= self.max_tokens:
            return f"词元上限 {self.max_tokens}"
        return ""


@dataclass
class RunStats:
    """一条路径跑完之后的读数。两张表的每一格都取自这里，别手写。"""

    path: str
    stop: str
    model_calls: int = 0
    super_steps: int = 0
    tool_calls: int = 0
    tokens: int = 0
    tools_used: list[str] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    answer: str = ""
    crashed: str = ""

    def row(self) -> dict:
        return {"路径": self.path, "终止原因": self.stop, "模型调用": self.model_calls,
                "super-step": self.super_steps, "工具调用": self.tool_calls,
                "词元": self.tokens, "用过的工具": "、".join(self.tools_used) or "（没有）"}


def agent_config(*, thread_id: str | None = None,
                 recursion_limit: int = DEFAULT_RECURSION_LIMIT) -> dict:
    """一条运行配置。**上限必须写在这**——`create_agent` 自己不收这个参数。"""
    config: dict[str, Any] = {"recursion_limit": recursion_limit}
    if thread_id is not None:
        config["configurable"] = {"thread_id": thread_id}
    return config


def create_zhizhou(model: BaseChatModel, tools: list[BaseTool], *,
                   middleware: list[Any] | None = None,
                   checkpointer: Any = None,
                   system_prompt: str = AGENT_SYSTEM,
                   name: str = "zhizhou-v4"):
    """框架版：**一行装配**。循环、工具节点、路由、消息归并全在图里。

    这里能一行装完，是因为「循环长什么样」已经是一个约定：
    模型节点 → 有工具调用就去工具节点 → 再回模型节点 → 没有就结束。
    手写版把这个约定写成了一个 `while True`；框架版把它编译成了一张图。
    代价是：**想改那个约定，得改中间件**，不能顺手在循环里插一行（那正是它的价值）。
    """
    return create_agent(model, tools=tools, system_prompt=system_prompt,
                        middleware=list(middleware or []), checkpointer=checkpointer,
                        name=name)


def describe_agent(agent) -> dict:
    """把图读出来：有哪些节点、边怎么连。**是读的不是猜的**，版本升级也能自查。"""
    graph = agent.get_graph()
    return {
        "节点": sorted(graph.nodes),
        "边": sorted(f"{e.source}→{e.target}{'（条件）' if e.conditional else ''}"
                     for e in graph.edges),
    }


def sum_tokens(message: AIMessage) -> int:
    """从一条 AI 消息里读用量。框架把账挂在消息上，**不挂在循环的局部变量上**。"""
    meta = getattr(message, "usage_metadata", None) or {}
    return int(meta.get("total_tokens", 0) or 0)


def run_agent(agent, task: str, *, config: dict | None = None) -> RunStats:
    """跑框架版并**从状态里**把读数数出来。

    用 `stream_mode="values"` 而不是 `invoke`：每一步的快照都要，因为
    「框架走了几步」这件事只有流能看见（`invoke` 只给你最后一帧）。
    `super_steps` 就是 `recursion_limit` 数的那件事——两者必须在同一把尺子上，
    否则「我设了 8 步」和「它跑了 8 步」永远对不上账。
    """
    cfg = config or agent_config()
    stats = RunStats(path="create_agent", stop="")
    frames: list[dict] = []
    try:
        for snapshot in agent.stream({"messages": [{"role": "user", "content": task}]},
                                    config=cfg, stream_mode="values"):
            frames.append(snapshot)
    except Exception as exc:                     # GraphRecursionError 也会走到这里
        stats.crashed = f"{type(exc).__name__}: {str(exc)[:60]}"
        stats.stop = f"异常中断（{type(exc).__name__}）"
    stats.super_steps = max(0, len(frames) - 1)   # 第一帧是入口状态，不算一步
    if not frames:
        return stats
    messages = list(frames[-1].get("messages", []))
    stats.model_calls = sum(1 for m in messages if isinstance(m, AIMessage))
    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    stats.tool_calls = len(tool_messages)
    stats.tokens = sum(sum_tokens(m) for m in messages if isinstance(m, AIMessage))
    stats.tools_used = [m.name or "" for m in tool_messages]
    stats.tool_results = [{"name": m.name or "", "status": m.status or "success",
                           "content": m.content if isinstance(m.content, str) else str(m.content)}
                          for m in tool_messages]
    last = messages[-1] if messages else None
    stats.answer = (last.content if isinstance(last, AIMessage) else "") or ""
    if not stats.stop:
        stats.stop = "模型给出最终答案"
    return stats


def run_handwritten(model: BaseChatModel, tools: list[BaseTool], task: str, *,
                    budget: Budget | None = None,
                    approve: Callable[[str, dict], bool] | None = None,
                    require_approval: tuple[str, ...] = ("publish_article",),
                    run_id: str = "loop",
                    stall_limit: int = 3) -> RunStats:
    """手写版：决策 → 执行 → 回填 → 再问。**四条护栏规则与中间件一字不差。**

    这么写是为了让对照成立：如果手写版少一条规则，4.3.6 的表就成了
    「有护栏的框架版 vs 没护栏的手写版」，读出来的是我自己造的差。
    """
    bound = model.bind_tools(tools)
    by_name = {t.name: t for t in tools}
    budget = budget or Budget()
    stats = RunStats(path="手写循环", stop="")
    messages: list[Any] = [SystemMessage(AGENT_SYSTEM), HumanMessage(task)]
    seen: dict[str, str] = {}
    recent: list[str] = []

    def model_call(extra: str = "") -> AIMessage:
        budget.steps += 1
        stats.model_calls += 1
        # super-step 的算法必须与图一致：一次模型调用占 1 步；**只有当它带工具调用时**
        # 后面才跟一个工具节点，再占 1 步。按「模型调用 × 2」算会多算最后那一轮无工具调用的步，
        # 于是「手写 8 步 vs 框架 7 步」这种假差异会被自己造出来。
        stats.super_steps += 1
        if extra:
            messages.append(HumanMessage(extra))
        reply = bound.invoke(messages)
        messages.append(reply)
        budget.tokens += sum_tokens(reply)
        stats.tokens += sum_tokens(reply)
        if reply.tool_calls:
            stats.super_steps += 1
        return reply

    def wrap_up(reason: str) -> RunStats:
        """强制收口：不再探索，只要一个「基于已有信息的最佳答案」。

        这是**手写版有、框架版没有**的一步（框架的 `ModelCallLimitMiddleware`
        是停下并留一句「上限到了」，不追一句结论，见 4.3.6 的读数）。
        """
        reply = model_call("信息足够或时间不多时，请直接用现有信息给出结论，不要再调用工具。")
        stats.answer = reply.content or ""
        stats.stop = f"{reason} → 收口"
        return stats

    while True:
        why = budget.exhausted()
        if why:
            return wrap_up(why)
        reply = model_call()
        calls = list(reply.tool_calls or [])
        if not calls:
            stats.answer = reply.content or ""
            stats.stop = "模型给出最终答案"
            return stats
        for call in calls:
            name, args = call["name"], call.get("args") or {}
            call_id = call["id"]
            # ---- 规则一：审批闸（默认拒绝）----
            if call.get("type") == "tool_call" and name in require_approval and \
                    not (approve and approve(name, args)):
                text = f"[等待人工确认] {name} 未获批准，本轮不执行。请向用户说明并停下。"
                messages.append(ToolMessage(content=text, tool_call_id=call_id, status="error",
                                            name=name))
                stats.tool_calls += 1
                stats.tools_used.append(name)
                stats.tool_results.append({"name": name, "status": "error", "content": text})
                continue
            # ---- 规则二：幂等键（只对写操作）----
            key = idem_key(run_id, name, args) if name in WRITE_TOOLS else ""
            if key and key in seen:
                text = seen[key] + "\n（幂等键命中，本次未重复执行）"
                messages.append(ToolMessage(content=text, tool_call_id=call_id, name=name))
                stats.tool_calls += 1
                stats.tools_used.append(name)
                stats.tool_results.append({"name": name, "status": "success", "content": text})
                continue
            # ---- 规则三：异常收成可读文本，不拖垮循环 ----
            tool = by_name.get(name)
            if tool is None:
                text = f"[工具失败] 不存在的工具：{name}"
            else:
                try:
                    out = tool.invoke(args)
                    text = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
                except Exception as exc:
                    text = f"[工具失败] {type(exc).__name__}: {exc}"
            if key:
                seen[key] = text
            stats.tool_calls += 1
            stats.tools_used.append(name)
            stats.tool_results.append({"name": name, "status": "success", "content": text})
            messages.append(ToolMessage(content=text, tool_call_id=call_id, name=name))
            # ---- 规则四：卡死检测（同动作同参数连续出现）----
            recent.append(f"{name}:{json.dumps(args, sort_keys=True, ensure_ascii=False)}")
            if recent.count(recent[-1]) >= stall_limit:
                return wrap_up(f"卡死：连续 {stall_limit} 次相同动作")


def compare(model: BaseChatModel, tools: list[BaseTool], task: str, *,
            recursion_limit: int = DEFAULT_RECURSION_LIMIT,
            approve: Callable[[str, dict], bool] | None = None,
            run_id: str = "cmp") -> list[RunStats]:
    """同一个任务跑两条路径，返回两份读数。**先跑、再写**，表里的数不许手填。"""
    handwritten = run_handwritten(model, tools, task, approve=approve, run_id=run_id)
    agent = create_zhizhou(model, tools,
                           middleware=[guard_tools(run_id=run_id, approve=approve)])
    framework = run_agent(agent, task, config=agent_config(recursion_limit=recursion_limit))
    return [handwritten, framework]
