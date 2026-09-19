"""一次 Agent 会话的组装：注册表（工具与权限）+ 策略（真模型）+ 运行时（预算与终止）。

服务层只做三件事：选工具集、定预算、把结果整理成响应体。**它不写循环、不拼提示、不校验参数**——
那三件事分别属于 `loop`、`prompts/` 与 `registry`，混在一起就没法单独测。

3.6 起它多了一件事：**把「以前说过什么」装进这次请求**。三份数据各走各的路，不混在一个字典里：

    长期记忆（跨会话）  recall → 进 system 提示（前缀，可被缓存）
    会话历史（本会话）  assemble → 进 messages 前缀（策略只读它，不改它）
    本次任务            用户这一轮 —— 才是唯一驱动本次推理的入参

**写入时机也是设计的一部分**：用户这一轮在调模型**之前**就落库（进程崩了也不丢用户的话），
助手与工具侧的结果在跑完后一次性落库（半截轨迹落库反而会装出非法请求）。
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from app.agent.loop import bind_tools, run_agent
from app.agent.trace import Price, Tracer
from app.agent.memory import (Assembly, InMemoryStore, MemoryItem, MemoryStore, MemoryWriter,
                              Message, ToolCall, assemble, render_memory, to_openai)
from app.agent.policy import ModelPolicy
from app.agent.runtime import Budget, LoopResult
from app.agent.tools import zhizhou
from app.llm.client import Config, LlmError, prompt_version

PROMPTS = Path(__file__).resolve().parent.parent / "agent" / "prompts"
SYSTEM = (PROMPTS / "agent.md").read_text(encoding="utf-8")

# 需要人工确认的动作：发布不可逆，所以它不在「模型说做就做」的范围内。
NEEDS_APPROVAL = ("publish_article",)


class AgentService:
    def __init__(self, config: Config, *, user_id: int = 7, store: dict | None = None,
                 approve=lambda name, args: False,
                 sessions: MemoryStore | None = None,
                 chat_fn: Callable[..., object] | None = None,
                 memory_policy: str = "note",
                 tracer: Tracer | None = None,
                 registry_factory: Callable[..., object] = zhizhou.build) -> None:
        self.config = config
        self.user_id = user_id
        self.store = store if store is not None else {}          # 工具用的假数据仓库
        self.approve = approve
        # 3.9：追踪器可以注入。**进程里要共用同一个**（默认这个只给单次实例用），
        # 否则「指标」只能看到最后一次运行——真用起来是端点上挂一份进程级实例。
        # 内容捕获与单价都从环境变量读：它们是配置，不是代码里的常量。
        self.tracer = tracer if tracer is not None else Tracer(
            capture_content=os.environ.get("LLM_CAPTURE_CONTENT", "") == "1",
            price=Price.from_env(os.environ.get))
        # 注意两个 store 不是一回事：`store` 是工具读写的假业务数据，`sessions` 是记忆存储。
        # 替身与真库可以互换（`SqlMemoryStore` 有完全相同的接口），装配逻辑一行不改。
        self.sessions: MemoryStore = sessions if sessions is not None else InMemoryStore()
        self.writer = MemoryWriter()
        self.memory_policy = memory_policy
        self.chat_fn = chat_fn
        # 工具集的构造方式也可注入（默认就是 `zhizhou.build`）。评测集用它把某一篇的正文
        # 换成「被投毒的正文」——那是 3.8 那条注入演练的复用，不必另写一份假工具。
        self.registry_factory = registry_factory

    def chat(self, task: str, *, allow_write: bool = False, run_id: str | None = None,
             max_steps: int = 8, max_tokens: int = 8000, max_seconds: float = 120.0,
             history: list[dict] | None = None, conversation_id: str = "",
             agent_name: str = "知舟", trace_run=None) -> LoopResult:
        # 词元预算不是「越小越好」：历史每轮重发，读一篇长文就能花掉一两千词元，
        # 预算太小会让循环在读到东西之前就收口（实跑撞到过，见 3.10 的验收记录）。
        registry = self.registry_factory(self.user_id, self.store)
        run_id = run_id or uuid.uuid4().hex[:12]
        # 一棵 span 树从调模型之前就开：**它要盖住“整个任务”，不只是那几次调用**，
        # 否则「这一次一共花了多久」在图上没有对应的东西。
        run = trace_run if trace_run is not None else self.tracer.start_trace(
            task, conversation_id=conversation_id, run_id=run_id, agent_name=agent_name)
        policy = ModelPolicy(config=self.config, system=self.system_prompt(),
                             tool_specs=registry.specs_openai(), history=history or [],
                             on_call=lambda info: self.tracer.record_model_call(
                                 run, agent_name=agent_name, **info),
                             **({"chat_fn": self.chat_fn} if self.chat_fn else {}))
        tools = bind_tools(registry, run_id=run_id, allow_write=allow_write,
                           approve=self.approve, require_approval=NEEDS_APPROVAL,
                           on_tool=lambda info: self.tracer.record_tool_call(run, **info))
        budget = Budget(max_steps=max_steps, max_tokens=max_tokens, max_seconds=max_seconds)
        started = time.perf_counter()
        try:
            result = run_agent(task, policy, tools, budget)
        except Exception as exc:                                # noqa: BLE001 —— 失败也要留一棵树
            # 没这一手的话，失败的那次在追踪里**根本不存在**——而失败分布恰恰是本章要看的东西。
            kind = getattr(exc, "kind", type(exc).__name__)
            self.tracer.finish(run, reason=f"模型调用失败：{kind}", steps=budget.steps,
                               calls=budget.calls, tokens=budget.tokens,
                               in_tokens=policy.in_tokens, out_tokens=policy.out_tokens,
                               duration_ms=(time.perf_counter() - started) * 1000,
                               error_type=str(kind))
            raise
        record = self.tracer.finish(run, reason=result.reason, steps=result.steps,
                                    calls=result.calls, tokens=result.tokens,
                                    in_tokens=policy.in_tokens, out_tokens=policy.out_tokens,
                                    answer_chars=len(result.answer or ""),
                                    duration_ms=(time.perf_counter() - started) * 1000)
        result.record = record                                  # type: ignore[attr-defined]
        result.trace_id = record.trace_id                       # type: ignore[attr-defined]
        result.run_id = run_id                                  # type: ignore[attr-defined]
        result.prompt_version = prompt_version(PROMPTS / "agent.md")  # type: ignore[attr-defined]
        return result

    # ------------------------------------------------------------------ 会话与记忆

    def open_session(self, title: str) -> int:
        return self.sessions.open_session(self.user_id, title=title)

    def assemble(self, session_id: int, *, policy: str | None = None,
                 max_messages: int | None = None) -> Assembly:
        """把库里那份历史装配成「送进模型的那一段」，**不改库**。"""
        return assemble(self.sessions.history(session_id), policy=policy or self.memory_policy,
                        max_messages=max_messages)

    def session_chat(self, task: str, *, session_id: int | None = None, policy: str | None = None,
                     allow_write: bool = False, max_steps: int = 8, max_tokens: int = 8_000,
                     max_seconds: float = 120.0) -> dict:
        """带记忆的一轮：先装配，再调模型，再回写。返回响应体 + 这一次的账。

        顺序不是随便定的，四步都不能换：
          1. 取历史**快照**（装配要用的是「上一轮以前的历史」，不能把本轮的提问算两遍）；
          2. 把用户这一轮落库（写前日志：进程挂了也不会把用户说的话丢掉）；
          3. 召回长期记忆、装配上下文、跑循环；
          4. 一次性回写轨迹与最终答案，并抽出值得跨会话保留的偏好。
        """
        policy_name = policy or self.memory_policy
        sid = self.open_session(task[:40]) if session_id is None else session_id

        snapshot = self.sessions.history(sid)                   # ①
        assembly = assemble(snapshot, policy=policy_name)
        self.sessions.append(sid, Message("user", task))        # ②

        remembered = self.sessions.recall(self.user_id)          # ③
        history = to_openai(assembly.messages)
        # 会话 id 进 span 属性：这样「同一会话跨几次运行」在追踪里连得上。
        # 它不进提示、不进日志正文——只是一个能对上的编号。
        result = self.chat(task, allow_write=allow_write, history=history,
                           max_steps=max_steps, max_tokens=max_tokens, max_seconds=max_seconds,
                           conversation_id=str(sid))

        for m in self._trace_messages(result):                   # ④
            self.sessions.append(sid, m)
        written = self.writer.from_turn(task, session_id=sid)
        for item in written:
            self.sessions.remember(self.user_id, item)
        self.sessions.remember(self.user_id,
                               self.writer.from_task(task, result.reason, session_id=sid))

        payload = self.to_payload(result)
        payload["session_id"] = sid
        payload["memory"] = {
            "policy": assembly.policy,
            "history_messages": len(snapshot),
            "baseline_tokens": assembly.baseline_tokens,
            "input_tokens": assembly.input_tokens,
            "saved": round(assembly.saved, 3),
            "dropped_tool_results": assembly.dropped_tool_results,
            "dropped_messages": assembly.dropped_messages,
            "recalled": [i.key for i in remembered],
            "remembered": [i.key for i in written] + ["task.last"],
        }
        return payload

    def transcript(self, session_id: int) -> dict:
        """可回放的会话：存的是正文，所以它是真的能装回上下文的那一份（不是一串哈希）。"""
        return self.sessions.transcript(session_id)

    def forget(self, key: str) -> int:
        """用户要有权删掉一条长期记忆——这是「脱敏」能说出口的前提（3.8）。"""
        return self.sessions.forget(self.user_id, key)

    @staticmethod
    def _trace_messages(r: LoopResult) -> list[Message]:
        """轨迹 → 可回放的消息。**工具往返必须成对**：声明一条、结果一条，id 相同。

        只存结果的写法看起来更干净，但下一次会话装不出合法请求——服务商要求
        `tool` 消息紧跟在声明了同一个 id 的 `assistant` 消息之后。
        """
        out: list[Message] = []
        for e in r.trace.entries:
            if e.final or not e.action:
                continue
            cid = f"call_{e.n}"
            out.append(Message("assistant", e.thought or "", e.tokens,
                               tool_calls=(ToolCall(cid, e.action, e.arg or "{}"),)))
            out.append(Message("tool", e.observation or "", tool_call_id=cid))
        if r.answer:
            out.append(Message("assistant", r.answer))
        return out

    def memory_of(self, session_id: int, *, policy: str | None = None,
                  max_messages: int | None = None) -> dict:
        """诊断：这一次会话装配后会发出去多少消息、多少词元、省了多少。

        它存在的理由与 3.1 的只读诊断端点一样：**账要能被单独问，而不是只能从日志里猜**。
        """
        a = self.assemble(session_id, policy=policy, max_messages=max_messages)
        return {"session_id": session_id, "policy": a.policy, "messages": len(a.messages),
                "input_tokens": a.input_tokens, "baseline_tokens": a.baseline_tokens,
                "saved": round(a.saved, 3), "note": bool(a.note),
                "dropped_tool_results": a.dropped_tool_results,
                "dropped_messages": a.dropped_messages,
                "long_term": [i.key for i in self.sessions.recall(self.user_id)]}

    def metrics(self, window: int | None = None) -> dict:
        """这一进程跑过的运行聚成的四类指标。**它是只读的，也不需要模型凭据。**

        只报词元、不编价：成本那一块要调用方给出单价（`LLM_PRICE_IN` / `LLM_PRICE_OUT`）；
        没配时 `cost` 为 `None`——一个编出来的价会让整张表看起来都可疑。
        """
        return self.tracer.metrics(window=window)

    def system_prompt(self) -> str:
        """系统提示 = 固定部分 + 这位用户的长期记忆。**记忆为空时不加空标题**。"""
        tail = render_memory(self.sessions.recall(self.user_id))
        return f"{SYSTEM}\n\n{tail}" if tail else SYSTEM

    @staticmethod
    def digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def to_payload(r: LoopResult) -> dict:
        """响应体：终态、账、以及可回放的轨迹。轨迹只留摘要指纹，不留正文（3.8）。"""
        return {
            "answer": r.answer,
            "steps": r.steps,
            "calls": r.calls,
            "tokens": r.tokens,
            "reason": r.reason,
            "run_id": getattr(r, "run_id", ""),
            "trace_id": getattr(r, "trace_id", ""),
            "prompt_version": getattr(r, "prompt_version", ""),
            "trace": [{"n": e.n, "thought": e.thought[:200], "action": e.action,
                       "arg": (e.arg or "")[:200],
                       "observation_digest": AgentService.digest(e.observation or ""),
                       "observation_head": (e.observation or "")[:120],
                       "tokens": e.tokens, "final": e.final}
                      for e in r.trace.entries],
        }


def build_service(*, user_id: int = 7, approve=lambda name, args: False,
                  sessions: MemoryStore | None = None) -> AgentService:
    """从环境变量装配。密钥缺失在这里就报错，而不是等到第一次调用。"""
    return AgentService(Config.from_env(), user_id=user_id, approve=approve, sessions=sessions)


__all__ = ["AgentService", "build_service", "LlmError", "MemoryItem"]
