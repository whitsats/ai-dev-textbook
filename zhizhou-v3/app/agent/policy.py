"""真模型策略：循环注入的那个 `policy`，落到一次真实的模型调用上。

三个决定值得说清，它们都是「跑起来才看得见」的那一类：

1. **上下文每轮从 trace 重建，而不是自己维护一份历史。**
   真相只有一份：trace 是状态，消息是它的投影。取消/收口时不会出现
   「assistant 说要调工具、但结果永远不来」这种让下一次请求非法的历史。
2. **一次响应里的多个工具调用（并行）按顺序执行，但不再问模型。**
   Agnes / OpenAI / Anthropic 都会在一次响应里给多个 `tool_calls`；
   循环一步只执行一个动作，所以后一个先排队、下一步直接取用（`tokens=0`）。
   步数会多，模型调用不会多——这正是 3.5.8 说的「一次响应里的多个调用」。
3. **收口时把工具收走**（`tool_choice="none"`），而不是只在提示里请求它别调工具。
   请求是概率，参数是约束。
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.llm.client import Config, chat
from app.llm.schemas import DraftPlan

WRAP_UP_HINT = ("已达到步数或预算上限。现在**不要再调用任何工具**，"
                "只用上面已经拿到的信息，给出一段完整、可直接给用户看的答案；"
                "信息不足就明确说明缺什么。")

# 模型没给内容时的占位文本。**它是一个常量，因为下游要能认出它**：
# 多代理编排（3.7）里「占位文本」必须被当成「什么都没交回」，
# 否则一个空回答会以 status=ok 混进汇总，而缺口清单是空的。
EMPTY_REPLY = "（模型没有给出内容）"


@dataclass
class ModelPolicy:
    """一次任务一个实例：它持有并行调用的队列。

    `chat_fn` 可注入：测试里换成剧本就能把「接线」单测完，不必联网
    ——「唯一模型入口」指的是**生产代码**只有一条路径，不是让测试也去发请求。
    """

    config: Config
    system: str
    tool_specs: list[dict] = field(default_factory=list)
    chat_fn: Callable[..., object] = chat
    # 上一次会话的装配结果（`memory.to_openai(assembly.messages)`）：只读前缀，插在
    # system 与本次任务之间。它由记忆层给，**策略层不自己攒历史**——真相只有 trace 一份，
    # 而这里是「以前说过什么」，两件事分开放才不会一改就乱。
    history: list[dict[str, object]] = field(default_factory=list)
    queued: list[tuple[str, str]] = field(default_factory=list)
    calls: int = 0
    tokens: int = 0
    in_tokens: int = 0                     # 3.9：输入与输出分开累积，比例才是可看的数
    out_tokens: int = 0
    # 调用完成后的回呼（3.9）。**在调用点计时**，因为只有这里知道「这一次」花了多久；
    # 事后从别处推的时间会把排队与重试算错。默认 None：没有追踪层时一行代码都不多跑。
    on_call: Callable[[dict], None] | None = None

    def __call__(self, task: str, trace, wrap_up: bool = False) -> dict:
        if self.queued:                       # 上一响应里没执行完的调用：不再问模型
            name, arg = self.queued.pop(0)
            return {"thought": f"（同一响应里的第 {len(self.queued) + 1} 个调用，不再问模型）",
                    "action": name, "arg": arg, "tokens": 0, "model_call": False}
        messages = self.render(task, trace, wrap_up)
        self.calls += 1
        started = time.perf_counter()
        reply = self.chat_fn(messages, config=self.config,
                             tools=self.tool_specs or None,
                             tool_choice="none" if wrap_up else ("auto" if self.tool_specs else None))
        self.tokens += reply.tokens
        # `getattr` 的默认值不是“防御性编程”：测试与离线剧本用的是轻量回复对象，
        # 它们本来就没有这几个字段——追踪层不因为“看不到就炸”而把主流程带下水。
        self.in_tokens += int(getattr(reply, "in_tokens", 0) or 0)
        self.out_tokens += int(getattr(reply, "out_tokens", 0) or 0)
        if self.on_call is not None:
            self.on_call({
                "model": getattr(reply, "model", "") or self.config.model,
                "duration_ms": (time.perf_counter() - started) * 1000,
                "tokens": reply.tokens,
                "in_tokens": int(getattr(reply, "in_tokens", 0) or 0),
                "out_tokens": int(getattr(reply, "out_tokens", 0) or 0),
                "attempts": int(getattr(reply, "attempts", 1) or 1),
                "tools": tuple(getattr(c, "name", "") for c in (reply.tool_calls or ())),
                "content": reply.content or "",
                "wrap_up": wrap_up})
        if wrap_up:
            text = reply.content.strip() or "（收口时模型没有给出内容，以下为已获得的观察摘要）\n" + \
                "\n".join(f"- {e.action}: {str(e.observation)[:120]}"
                          for e in trace.entries if e.observation)
            return {"thought": text, "final": True, "tokens": reply.tokens, "final_text": text}
        if reply.tool_calls:
            head, rest = reply.tool_calls[0], reply.tool_calls[1:]
            self.queued.extend((c.name, c.arguments) for c in rest)
            return {"thought": reply.content.strip() or f"调用 {head.name}", "action": head.name,
                    "arg": head.arguments, "tokens": reply.tokens}
        text = reply.content.strip()
        return {"thought": text or EMPTY_REPLY, "final": True,
                "tokens": reply.tokens, "final_text": text}

    def render(self, task: str, trace, wrap_up: bool) -> list[dict]:
        """trace → 消息列表。工具结果紧跟它对应的 assistant 调用，形状必须是合法的。"""
        msgs: list[dict] = [{"role": "system", "content": self.system}]
        msgs.extend(self.history)                       # 历史在前、本次任务在后：前缀可被缓存
        msgs.append({"role": "user", "content": task})
        for e in trace.entries:
            if e.final or not e.action:
                continue
            msgs.append({"role": "assistant", "content": e.thought or "",
                         "tool_calls": [{"id": f"call_{e.n}", "type": "function",
                                         "function": {"name": e.action,
                                                      "arguments": e.arg or "{}"}}]})
            msgs.append({"role": "tool", "tool_call_id": f"call_{e.n}",
                         "content": e.observation or ""})
        if wrap_up:
            msgs.append({"role": "user", "content": WRAP_UP_HINT})
        return msgs


PLAN_HINT = ("把目标拆成 3–6 步。每步必须有可验证的验收标准（accept），"
             "有先后依赖的用 deps 指明步骤 id；只做只读动作，不要安排发布。")


def draft_plan_with_model(config: Config, goal: str, tools_hint: str = "",
                          max_tokens: int = 2_048) -> dict:
    """让真模型给一份计划。形状由 schema 保证，内容由 plan.validate 判定。

    `max_tokens` 默认比对话大：计划是一段长 JSON，按对话的默认上限会被截断；
    截断不是「格式不对」而是「没写完」，所以 client 层把它单独认出来（3.2 的坑）。
    """
    schema = {"type": "json_schema", "json_schema": {
        "name": "DraftPlan", "strict": True,
        "schema": {**DraftPlan.model_json_schema(), "additionalProperties": False}}}
    messages = [{"role": "system", "content": PLAN_HINT},
                {"role": "user", "content": goal + (f"\n可用动作：{tools_hint}" if tools_hint else "")}]
    reply = chat(messages, config=config, response_format=schema, max_tokens=max_tokens)
    import json

    return {"reply": json.loads(reply.content or "{}"), "tokens": reply.tokens}
