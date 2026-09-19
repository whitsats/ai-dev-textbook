"""知舟的 Agent 运行时：预算、追踪、终止判定。

终止永远由运行时负责，不由模型负责——模型只提「下一步做什么」。
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Budget:
    """一次任务的三类上限。时钟可注入，否则「超时」这条永远测不了。"""

    max_steps: int = 8
    max_tokens: int = 1200
    max_seconds: float = 30.0
    clock: Callable[[], float] = time.monotonic
    started: float = field(init=False, default=0.0)
    steps: int = 0
    tokens: int = 0
    calls: int = 0

    def __post_init__(self) -> None:
        self.started = self.clock()

    def charge(self, tokens: int) -> None:
        self.tokens += tokens

    def count_call(self) -> None:
        """记一次模型调用。**它记在预算上，而不是调用方的一个局部变量里**：

        子代理抛异常时，那个局部变量随栈一起消失，而「它花掉的几次调用」必须留下——
        否则一次失败在账上变成 0 次调用（3.7 实测里真的出现过：状态 failed、0 次调用、
        396 词元，两个数字互相矛盾）。预算本来就是这一份的账本，调用数也该记在这里。
        """
        self.calls += 1

    def begin_step(self) -> None:
        self.steps += 1

    def exhausted(self) -> str | None:
        if self.steps >= self.max_steps:
            return "步数上限"
        if self.tokens >= self.max_tokens:
            return "预算耗尽"
        return "墙钟超时" if self.clock() - self.started >= self.max_seconds else None


@dataclass
class TraceEntry:
    n: int
    thought: str
    action: str | None = None
    arg: str | None = None
    observation: str | None = None
    tokens: int = 0
    final: bool = False
    failed: bool = False          # 工具调用被拒 / 报错：真实运行时里，这类步骤不该重复计费


@dataclass
class Trace:
    """每一步都记。两种卡死口径都留痕：动作序列 ＋ 观察集合。"""

    task: str
    entries: list[TraceEntry] = field(default_factory=list)
    calls_seen: list[tuple[str, str]] = field(default_factory=list)
    facts_seen: set[str] = field(default_factory=set)
    repeat_limit: int = 3

    def add(self, e: TraceEntry) -> None:
        self.entries.append(e)

    def stalled_by_action(self, action: str, arg: str) -> bool:
        """口径一：连续 N 次完全相同的动作（参数也一样）。"""
        self.calls_seen.append((action, arg))
        if len(self.calls_seen) < self.repeat_limit:
            return False
        return len(set(self.calls_seen[-self.repeat_limit:])) == 1

    # 空结果不算「事实」：两次不同的检索都返回空，是「这条线索也没有」，
    # 而不是「它在原地打转」。判成卡死会把一个正常的「找不到」结论记成失败——
    # 3.9 的评测集第一轮真机跑就是这样：反向题两条试验全被这条口径收了口。
    # 同一动作的重复由口径一负责（它管的是「原封不动地再来一次」）。
    EMPTY_OBSERVATIONS = frozenset({"", "[]", "{}", "null", "None"})

    def stalled_by_fact(self, observation: str) -> bool:
        """口径二：没有新事实。参数每次都不同、结果却一样时只有它拦得住。"""
        if observation.strip() in self.EMPTY_OBSERVATIONS:
            return False
        if observation in self.facts_seen:
            return True
        self.facts_seen.add(observation)
        return False


@dataclass
class LoopResult:
    answer: str | None
    steps: int
    calls: int
    tokens: int
    reason: str
    trace: Trace
