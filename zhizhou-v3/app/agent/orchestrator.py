"""知舟的编排器：一个主管 + 若干并行的子代理，以及它们之间唯一的接口——交接单。

三件事分开放，因为它们各自会坏：

- **规划**（把目标拆成几份交接单）——坏的样子是「一份太笼统的交接单」，子代理会重复劳动或漏掉整块；
- **执行**（每个子代理在自己的上下文里跑到收敛）——坏的样子是单个子代理失控，把总预算吃光；
- **汇聚**（合并、去重、报缺口）——坏的样子是「看起来汇总了」，其实三份结论是同一件事。

**子代理默认只读。** 写操作的授权、幂等与人工确认（3.5）是**主管**的权利：子代理并行跑的时候，
没有人在旁边确认，让它自己写就是让并行度直接乘以风险。需要写的时候，由主管把某个角色显式提权。

**预算按份切。** 每个子代理拿到一份**硬上限**，而不是大家抢一个池子：
抢池子的结果是先跑完的那个把预算吃光，后面的子代理在「预算耗尽」里收口，
而它的收口结论会被当成「这个方向没东西」——一次资源调度错误伪装成了一次调研结论。
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.agent.loop import bind_tools, run_agent
from app.agent.policy import EMPTY_REPLY, ModelPolicy
from app.agent.runtime import Budget

# 交接触的四件：少一件，子代理就会自己去猜——而它猜的方向由提示的措辞决定，不由你的意图决定。
REQUIRED_FIELDS = ("objective", "deliverable", "tools", "boundaries")

# 官方给的三条档位（Anthropic 多 Agent 研究系统）：把「该花多少力气」写进提示，而不是让模型自己判。
EFFORT_LADDER: tuple[tuple[str, int, int], ...] = (
    ("simple", 1, 3),        # 单点事实：1 个代理，3–10 次工具调用
    ("compare", 3, 10),      # 直接对比：2–4 个子代理，每个 10–15 次
    ("complex", 6, 15),      # 复杂调研：>10 个子代理，职责必须划清
)


class HandoffError(ValueError):
    """交接单不合规：宁可在这里当场报错，也不要把它发给子代理。"""


@dataclass(frozen=True)
class Handoff:
    """交给一个子代理的全部信息。**它是数据，不是提示片段**——所以能被校验、被测试、被日志化。

    `boundaries` 是最容易被省掉的一条，也是最能省事的一条：没有它，
    两个子代理会去查同一件事（实测里最常见的一种浪费），而你付了两份钱买到一份结论。
    """

    role: str
    objective: str
    deliverable: str
    tools: tuple[str, ...]
    boundaries: str
    max_steps: int = 6
    max_tokens: int = 4_000
    allow_write: bool = False

    def validate(self) -> None:
        for name in REQUIRED_FIELDS:
            if not str(getattr(self, name)).strip():
                raise HandoffError(f"交接单缺了「{name}」：子代理会自己猜，而它猜的方向不由你决定")
        if not self.tools:
            raise HandoffError(f"交接单的「tools」是空的：子代理只能干看着（角色 {self.role}）")
        if self.allow_write and not self.boundaries.startswith("写"):
            # 提权必须**写在交接单里**，不能靠调用方记得：否则一次重构就会把写权限漏下去。
            raise HandoffError(f"角色 {self.role} 拿到了写权限，但 boundaries 没有说明写什么")

    def fingerprint(self) -> str:
        """交接单的指纹：用来发现「两份交接单其实是同一件事」。"""
        payload = f"{self.objective}|{self.deliverable}|{'/'.join(sorted(self.tools))}|{self.boundaries}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


@dataclass
class SubResult:
    """一个子代理的产出与账。`status` 有四种，**别把它们合成一句「失败」**。"""

    handoff: Handoff
    answer: str = ""
    status: str = "ok"            # ok ｜ empty（没找到）｜ failed（跑挂了）｜ timeout（被预算收口）
    steps: int = 0
    calls: int = 0
    tokens: int = 0
    reason: str = ""

    @property
    def role(self) -> str:
        return self.handoff.role

    def digest(self) -> str:
        return hashlib.sha256(self.answer.strip().encode("utf-8")).hexdigest()[:12]


@dataclass
class Orchestration:
    """一次编排的全部账。主管与子代理的账**分开记**，因为它们的失败方式不一样。"""

    goal: str
    handoffs: list[Handoff] = field(default_factory=list)
    results: list[SubResult] = field(default_factory=list)
    answer: str = ""
    lead_tokens: int = 0
    lead_steps: int = 0
    lead_error: str = ""              # 主管汇总那一步失败的原因（空字符串 = 没失败）
    wall_seconds: float = 0.0

    @property
    def tokens(self) -> int:
        return self.lead_tokens + sum(r.tokens for r in self.results)

    @property
    def sub_tokens(self) -> int:
        return sum(r.tokens for r in self.results)

    def duplicates(self) -> list[tuple[str, str]]:
        """内容重复的子代理对：**并行不是免费的，重复才是最常见的浪费**。"""
        seen: dict[str, str] = {}
        dups: list[tuple[str, str]] = []
        for r in self.results:
            if not r.answer.strip():
                continue
            key = r.digest()
            if key in seen:
                dups.append((seen[key], r.role))
            else:
                seen[key] = r.role
        return dups

    def gaps(self) -> list[str]:
        """**没有交回可用东西的角色**：它不是失败，而是「这一块还没人看」。两种处置完全不同：
        缺口要补一份新的交接单，失败要查那个子代理为什么炸。"""
        return [r.role for r in self.results if r.status in ("empty", "failed")]

    def degraded(self) -> list[str]:
        """被预算/步数提前收口的角色：**它交了东西，但那东西可能不完整**。

        把它归进「缺口」会让人重跑一遍白花一份钱；把它当成正常结论，
        汇总里就混进了一段「我只看到一半但我不知道」。所以它单独一档。"""
        return [r.role for r in self.results if r.status == "timeout"]

    def report(self) -> dict:
        return {
            "goal": self.goal,
            "roles": [h.role for h in self.handoffs],
            "status": {r.role: r.status for r in self.results},
            "tokens": {"lead": self.lead_tokens, "sub": self.sub_tokens, "total": self.tokens},
            "steps": {"lead": self.lead_steps, "sub": sum(r.steps for r in self.results)},
            "duplicates": self.duplicates(),
            "gaps": self.gaps(),
            "degraded": self.degraded(),
            "lead_error": self.lead_error,
            "wall_seconds": round(self.wall_seconds, 2),
        }


def split_budget(handoffs: Sequence[Handoff], *, total: int, lead_share: float = 0.25
                 ) -> tuple[Budget, list[Budget]]:
    """把总预算切成「主管一份 + 每份交接单一门」的**硬上限**。

    两件事必须成立，而且都能被算术验证：
      · 各份之和 ≤ 总预算（超了就是超支，不是「估算偏保守」）；
      · 每份都 ≥ 一次调用所需（切得太碎会让子代理在读到东西之前就收口——那是假阴性）。
    主管那一份单独留出（默认 25%）：它是**唯一**能看到全部子代理结论的角色，
    把它的预算分光，等于让汇总在最有信息量的一步上没预算可用。
    """
    if not handoffs:
        raise HandoffError("一份交接单都没有：编排退化成了一次普通调用（那就不需要编排器）")
    lead = Budget(max_steps=4, max_tokens=max(int(total * lead_share), 500))
    rest = total - lead.max_tokens
    if rest < len(handoffs) * 500:
        raise HandoffError(f"预算不够切：{total} 词元要分给 1 个主管 + {len(handoffs)} 个子代理")
    each = rest // len(handoffs)
    return lead, [Budget(max_steps=h.max_steps, max_tokens=min(h.max_tokens, each))
                  for h in handoffs]


def ladder_for(complexity: str) -> tuple[int, int]:
    """任务复杂度 → (子代理数, 每个的工具调用上限)。**让规则决定资源，不让模型自己判。**"""
    for name, agents, calls in EFFORT_LADDER:
        if name == complexity:
            return agents, calls
    raise HandoffError(f"未知的复杂度档位：{complexity!r}（可选 {[n for n, _, _ in EFFORT_LADDER]}）")


def run_subagent(handoff: Handoff, *, config, registry_factory, system: str, budget: Budget,
                 chat_fn: Callable[..., object] | None = None,
                 on_call: Callable[[dict], None] | None = None) -> SubResult:
    """一个子代理：**自己的上下文、自己的工具子集、自己的预算**。跑挂了也不往外抛。

    `on_call` 是 3.9 的追踪回呼（可选）：子代理的模型调用也记进同一棵 span 树，
    并在属性里带上 `gen_ai.agent.name`＝角色名——**不然「哪个角色在花钱」只能靠猜**。
    """
    handoff.validate()
    registry = registry_factory(handoff.tools)          # 工具子集：它看不到别人的工具
    prompt = (f"你是「{handoff.role}」。\n目标：{handoff.objective}\n"
              f"交付格式：{handoff.deliverable}\n边界（必须遵守）：{handoff.boundaries}")
    policy = ModelPolicy(config=config, system=system, tool_specs=registry.specs_openai(),
                         **(dict(chat_fn=chat_fn) if chat_fn else {}), on_call=on_call)
    tools = bind_tools(registry, run_id=f"sub:{handoff.role}", allow_write=handoff.allow_write)
    try:
        result = run_agent(prompt, policy, tools, budget)
    except Exception as exc:                              # noqa: BLE001 —— 一个子代理不能拖垮整次编排
        # `calls` 从预算里读，**不能写 0**：它炸之前花掉的那几次调用是真的花掉了，
        # 写成 0 会让「这次编排一共花了多少」少记一笔，而且与同一行的词元自相矛盾。
        return SubResult(handoff, "", "failed", budget.steps, budget.calls, budget.tokens,
                         f"{type(exc).__name__}: {exc}")
    # 占位文本不是内容：策略层在模型没给内容时会填一句占位话，而循环把 `thought` 当答案带回。
    # 不认它，一个空回答就会以 `ok` 混进汇总，而缺口清单会是空的——那比报错更难发现。
    text = (result.answer or "").strip()
    if text == EMPTY_REPLY:
        text = ""
    if "收口" in result.reason:
        # 「被预算收口」与「确实没有」是两种结论：前者要重新分预算，后者要改交接单。
        # 注意收口的那一份**不是空的**（策略层会给一段已有观察的摘要），所以顺序不能反。
        status = "timeout"
    else:
        status = "ok" if text else "empty"
    return SubResult(handoff, text, status, result.steps, result.calls,
                     result.tokens, result.reason)


def orchestrate(goal: str, handoffs: Sequence[Handoff], *, config, registry_factory, system: str,
                total_tokens: int = 20_000, max_workers: int = 4,
                synthesize: Callable[[str, list[SubResult]], str] | None = None,
                clock: Callable[[], float] | None = None,
                chat_fn: Callable[..., object] | None = None,
                on_call_for: Callable[[str], Callable[[dict], None]] | None = None
                ) -> Orchestration:
    """跑一次编排：切预算 → 并行执行 → 汇聚。

    **并行的是子代理，不是工具调用**：一次响应里的多个工具调用在 3.5 已经处理了；
    这里并行的是「独立的上下文窗口」，也就是官方说的那种并行——它们各自探索，再压缩成结论。
    """
    import time

    now = clock or time.monotonic
    started = now()
    seen: set[str] = set()
    for h in handoffs:
        h.validate()
        if h.fingerprint() in seen:
            raise HandoffError(f"交接单重复：{h.role} 的目标/交付/工具与前面某一份相同——"
                               f"那就是同一件事做两遍，你付两份钱买一份结论")
        seen.add(h.fingerprint())

    lead_budget, sub_budgets = split_budget(handoffs, total=total_tokens)
    out = Orchestration(goal=goal, handoffs=list(handoffs))
    with ThreadPoolExecutor(max_workers=min(max_workers, len(handoffs))) as pool:
        futures = [pool.submit(run_subagent, h, config=config, registry_factory=registry_factory,
                               system=system, budget=b, chat_fn=chat_fn,
                               on_call=on_call_for(h.role) if on_call_for else None)
                   for h, b in zip(handoffs, sub_budgets)]
        out.results = [f.result() for f in futures]

    if synthesize is None:
        out.answer = default_synthesis(goal, out.results)
        out.lead_tokens = 0
    else:
        # 子代理有隔离，**主管那一步也要有**。它是最后一步：它炸了，前面几份子代理的钱
        # 就白花了，而调用方拿不到任何东西——实测里那一炸是服务商限流（429）。
        # 降级办法是现成的：退回拼接汇总，并把失败原因记在账上（不假装成功）。
        try:
            out.answer = synthesize(goal, out.results)
        except Exception as exc:                          # noqa: BLE001
            out.lead_error = f"{type(exc).__name__}: {exc}"
            out.answer = (f"（汇总那一步失败了：{out.lead_error}）\n\n"
                          + default_synthesis(goal, out.results))
        out.lead_tokens = getattr(synthesize, "spent", 0) or 0
    out.lead_steps = len(out.results) + 1
    out.wall_seconds = now() - started
    return out


def default_synthesis(goal: str, results: Sequence[SubResult]) -> str:
    """不调模型的汇总：拼接 + 标注缺口。**它存在的意义是「编排能离线验收」**。

    真实项目里这一步交给主管再调一次模型（`synthesize` 传进去），
    但**离线也要能跑**：否则「多代理比单代理强在哪」这个问题，在没密钥的机器上永远无法验证。
    """
    blocks = [f"## {r.role}\n{r.answer.strip()}" for r in results if r.answer.strip()]
    gaps = [r.role for r in results if not r.answer.strip()]
    body = "\n\n".join(blocks) or "（没有任何子代理交回内容）"
    if gaps:
        body += f"\n\n> 未交回内容的角色：{'、'.join(gaps)}——它们的方向还没有人看"
    degraded = [r.role for r in results if r.status == "timeout" and r.answer.strip()]
    if degraded:
        body += f"\n\n> 被预算提前收口的角色：{'、'.join(degraded)}——结论可能只覆盖了一部分"
    return f"目标：{goal}\n\n{body}"
