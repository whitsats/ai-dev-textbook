"""知舟的追踪与指标层：一步一棵 span，多次运行一组读数。

三件事放在同一个文件里，因为它们共用同一份数据：

    记录  一次任务一棵 span 树（`invoke_agent` → `chat` / `execute_tool`）
    导出  属性名对齐 OpenTelemetry 的 GenAI 语义约定（`gen_ai.*`），但不引 OTel 依赖
    聚合  从一棵棵树算出「成功率 / 平均步数 / 每任务成本 / 失败分布 / 延迟分位」

三条设计决定都是官方语义约定里写明的，也都很容易做错：

1. **一次逻辑操作一棵 span，重试不另起一棵。** 原文是 span SHOULD cover the duration
   of the logical operation with all retries。另起一棵的话，「重试了 3 次」会在图上
   长成「调用了 3 次」，而按次计费的服务商账单不这么算。
2. **内容默认不记。** 官方明确：默认不捕获提示与工具参数，因为它们可能含敏感数据，
   只有元数据（模型名、词元数、时长）默认带上；要显式打开内容捕获才有正文。
   这条与 3.8 的脱敏是同一条边界，所以默认值必须是「关」。
3. **指标从 span 树算，不从日志里 grep。** 一笔账只有一处来源，才不会出现
   「服务端账单说 4,590、日志里加起来 6,000」这种两个数都对不上的局面。

不做的事（留给后面的篇）：不导出到 OTLP、不接后端、不引任何框架（第 3 篇的硬约定），
也不采样——本地这几百次运行还没到需要采样的量级。什么时候需要，见 3.9.3。
"""
from __future__ import annotations

import hashlib
import time
from collections import Counter, deque
from collections.abc import Callable
from dataclasses import dataclass, field

# span 的 `gen_ai.operation.name`。取值来自官方语义约定的枚举，不自己造名字。
INVOKE_AGENT = "invoke_agent"
CHAT = "chat"
EXECUTE_TOOL = "execute_tool"

# 失败分布的口径：**它必须是有限档**。把终止原因的原话当键，会得到一个每次都不同的
# 直方图（原话里带步数和工具名），那样读完什么也看不出来。六档是按「下一步该改什么」分的：
# 改预算、改提示、补工具、查服务商、查网络——它们的修法完全不同，所以不能合成一句「失败 3 次」。
#
# 最后一档是**真机跑出来的**：9 次试验因「连接断开」中断，全被归进「模型失败」——
# 而模型的错与服务商的错修法相反（前者改提示，后者加重试）。没有这一档时，一张
# 90% 是网络抖动的失败分布看起来像「这个模型不行」。
KINDS = ("成功", "预算收口", "卡死", "工具不可用", "模型失败", "运行中断")


def classify(reason: str) -> str:
    """把一次运行的终止原因收进有限档。**外部中断不能记成「模型失败」**。"""
    if reason.startswith("运行中断"):
        return "运行中断"
    if reason.startswith("模型给出最终答案"):
        return "成功"
    if any(k in reason for k in ("预算耗尽", "步数上限", "墙钟超时")):
        return "预算收口"
    if any(k in reason for k in ("卡死", "无新事实")):
        return "卡死"
    if "不存在" in reason:
        return "工具不可用"
    return "模型失败"


def digest(text: str) -> str:
    """内容指纹：默认模式下用它代替正文——**能比对相等，不能还原内容**。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def percentile(values: list[float], p: float) -> float:
    """线性插值分位。**延迟必须给分位，不给均值**：均值会被长尾藏住（3.9.4）。"""
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


@dataclass(frozen=True)
class Price:
    """单价（每百万词元）。**输入与输出分开**——它们是两笔钱，而且输入的重复付费才是大头。"""

    input_per_mtok: float
    output_per_mtok: float
    currency: str = "元"

    @staticmethod
    def from_env(getenv: Callable[[str, str], str]) -> Price | None:
        """从环境变量读；两个都没配就是「没有单价」，此时只报词元、不报钱。"""
        raw = (getenv("LLM_PRICE_IN", ""), getenv("LLM_PRICE_OUT", ""))
        if not any(v.strip() for v in raw):
            return None
        try:
            return Price(float(raw[0] or 0), float(raw[1] or 0),
                         getenv("LLM_PRICE_CURRENCY", "元"))
        except ValueError:                      # 配错了不要炸整个服务：只当没有单价
            return None

    def of(self, in_tokens: int, out_tokens: int) -> float:
        return (in_tokens * self.input_per_mtok + out_tokens * self.output_per_mtok) / 1_000_000


@dataclass
class Span:
    """一个操作。`attributes` 里的键按官方语义约定命名（`gen_ai.*` / `error.type`）。"""

    name: str
    operation: str
    trace_id: str
    span_id: str
    parent_id: str | None = None
    kind: str = "INTERNAL"                  # CLIENT（跨进程调用）｜ INTERNAL
    started_ms: float = 0.0
    duration_ms: float = 0.0
    attributes: dict = field(default_factory=dict)
    status: str = "ok"                      # ok ｜ error
    error_type: str = ""

    def to_otel(self) -> dict:
        """导出成 OTLP 形状的最小投影：名字、类型、时长、属性、状态。

        真实项目里这一步交给 SDK（第 7 篇），这里手写是为了**说清哪几个字段是约定**。
        注意 `status` 与 `error.type` 是两件事：前者是 0/1，后者是「错在哪一类」。
        """
        attrs = dict(self.attributes)
        if self.status == "error":
            attrs["error.type"] = self.error_type or "unknown"
        elif "error.type" in attrs:
            attrs.pop("error.type")            # 成功的那一次不该留着上一次的空字段
        return {"name": self.name, "kind": self.kind, "trace_id": self.trace_id,
                "span_id": self.span_id, "parent_span_id": self.parent_id,
                "duration_ms": round(self.duration_ms, 2), "attributes": attrs,
                "status": "ERROR" if self.status == "error" else "OK"}


@dataclass
class RunRecord:
    """一次运行：根 span ＋ 它下面那棵树。指标全部从它算出来。"""

    trace_id: str
    task: str
    reason: str
    kind: str
    steps: int
    calls: int
    tokens: int
    in_tokens: int
    out_tokens: int
    duration_ms: float
    spans: list[Span] = field(default_factory=list)
    answer_chars: int = 0
    error_type: str = ""

    def spans_of(self, operation: str) -> list[Span]:
        return [s for s in self.spans if s.operation == operation]

    def roles(self) -> list[str]:
        return sorted({s.attributes.get("gen_ai.agent.name", "") for s in self.spans
                       if s.attributes.get("gen_ai.agent.name")})


class Run:
    """一棵 span 树。根 span 是 `invoke_agent`，子 span 挂在同一层（本项目的操作没有嵌套）。"""

    def __init__(self, tracer: Tracer, task: str, *, conversation_id: str = "",
                 run_id: str = "", agent_name: str = "知舟") -> None:
        self._tracer = tracer
        self.task = task
        self.spans: list[Span] = []
        trace_id = tracer.new_id("trace")
        root_attrs = {"gen_ai.operation.name": INVOKE_AGENT,
                      "gen_ai.agent.name": agent_name,
                      "zhizhou.run_id": run_id,
                      "zhizhou.task.digest": digest(task),
                      "zhizhou.task.chars": len(task)}
        if conversation_id:
            # 会话 id 进属性：这样「同一会话跨几次运行」在追踪里是连得上的（官方同名属性）
            root_attrs["gen_ai.conversation.id"] = conversation_id
        if tracer.capture_content:
            root_attrs["gen_ai.input.messages"] = task
        self.root = Span(f"{INVOKE_AGENT} {agent_name}", INVOKE_AGENT, trace_id,
                         tracer.new_id("span"), attributes=root_attrs)
        self.spans.append(self.root)

    def add(self, span: Span) -> Span:
        span.trace_id = self.root.trace_id
        span.parent_id = self.root.span_id
        self.spans.append(span)
        return span

    def spans_of(self, operation: str) -> list[Span]:
        """按操作取一类 span。与 `RunRecord.spans_of` 同名同义：
        运行中与运行完拿到的应该是同一组答案，不然“边跑边看”与“跑完再看”会给出两个数。"""
        return [s for s in self.spans if s.operation == operation]


class Tracer:
    """记录器 ＋ 指标源。**有界**：只留最近 `max_runs` 次，否则进程活久了内存只涨不落。"""

    def __init__(self, *, capture_content: bool = False,
                 clock: Callable[[], float] = time.perf_counter,
                 max_runs: int = 200, provider: str = "openai",
                 price: Price | None = None) -> None:
        self.capture_content = capture_content
        self.clock = clock
        self.provider = provider
        self.price = price
        self.runs: deque[RunRecord] = deque(maxlen=max_runs)
        self._n = 0

    # ---------------------------------------------------------------- 记录

    def new_id(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}-{self._n:06d}"

    def start_trace(self, task: str, *, conversation_id: str = "", run_id: str = "",
                    agent_name: str = "知舟") -> Run:
        return Run(self, task, conversation_id=conversation_id, run_id=run_id,
                   agent_name=agent_name)

    def record_model_call(self, run: Run, *, model: str, duration_ms: float, tokens: int = 0,
                          in_tokens: int = 0, out_tokens: int = 0, attempts: int = 1,
                          tools: tuple[str, ...] = (), agent_name: str = "知舟",
                          content: str = "", wrap_up: bool = False) -> Span:
        """一次模型调用。`attempts` 是**这一棵 span 里的重试次数**，不是新 span。"""
        attrs = {"gen_ai.operation.name": CHAT, "gen_ai.provider.name": self.provider,
                 "gen_ai.request.model": model, "gen_ai.agent.name": agent_name,
                 "gen_ai.usage.input_tokens": in_tokens,
                 "gen_ai.usage.output_tokens": out_tokens,
                 "zhizhou.attempts": attempts}
        if tools:
            attrs["gen_ai.response.finish_reasons"] = ["tool_calls"]
            attrs["zhizhou.tools.requested"] = list(tools)
        else:
            attrs["gen_ai.response.finish_reasons"] = ["stop"]
        if wrap_up:
            # 「收口那一次」单独标出来：它是预算被用满的证据，而它自己的调费往往最大
            attrs["zhizhou.wrap_up"] = True
        if self.capture_content:
            attrs["gen_ai.output.messages"] = content
        else:
            attrs["zhizhou.content.digest"] = digest(content)
            attrs["zhizhou.content.chars"] = len(content)
        span = Span(f"{CHAT} {model}", CHAT, run.root.trace_id, self.new_id("span"),
                    kind="CLIENT", duration_ms=duration_ms, attributes=attrs)
        return run.add(span)

    def record_tool_call(self, run: Run, *, tool: str, duration_ms: float, ok: bool = True,
                         error_type: str = "", arguments: str = "", result: str = "",
                         idem: str = "") -> Span:
        """一次工具执行。工具名进 span 名（`execute_tool search_article`），失败进 `error.type`。"""
        attrs = {"gen_ai.operation.name": EXECUTE_TOOL, "gen_ai.tool.name": tool,
                 "zhizhou.tool.idem": idem}
        if self.capture_content:
            attrs["gen_ai.tool.call.arguments"] = arguments
            attrs["gen_ai.tool.call.result"] = result
        else:
            attrs["zhizhou.args.digest"] = digest(arguments)
            attrs["zhizhou.result.digest"] = digest(result)
            attrs["zhizhou.result.chars"] = len(result)
        if not ok:
            # `error.type` 是 span **属性**（不只是导出时才拼的字段）：它一进属性，
            # 「按错误类型分组」在本地就能算，不必等后端。
            attrs["error.type"] = error_type or "工具执行失败"
        span = Span(f"{EXECUTE_TOOL} {tool}", EXECUTE_TOOL, run.root.trace_id,
                    self.new_id("span"), duration_ms=duration_ms, attributes=attrs,
                    status="ok" if ok else "error", error_type=attrs.get("error.type", ""))
        return run.add(span)

    def finish(self, run: Run, *, reason: str, steps: int, calls: int, tokens: int,
               in_tokens: int = 0, out_tokens: int = 0, answer_chars: int = 0,
               duration_ms: float = 0.0, error_type: str = "") -> RunRecord:
        """收尾：给出根 span 的时长与状态，并把这一次存进有界的账本。"""
        failed = classify(reason) != "成功"
        run.root.duration_ms = duration_ms
        run.root.status = "error" if failed else "ok"
        run.root.error_type = error_type or ("" if not failed else "运行未完成")
        if failed:
            run.root.attributes["error.type"] = run.root.error_type
        run.root.attributes["zhizhou.termination"] = reason
        run.root.attributes["zhizhou.result"] = classify(reason)
        rec = RunRecord(trace_id=run.root.trace_id, task=run.task[:80], reason=reason,
                        kind=classify(reason), steps=steps, calls=calls, tokens=tokens,
                        in_tokens=in_tokens, out_tokens=out_tokens, duration_ms=duration_ms,
                        spans=run.spans, answer_chars=answer_chars, error_type=error_type)
        self.runs.append(rec)
        return rec

    # ---------------------------------------------------------------- 聚合

    def metrics(self, window: int | None = None, price: Price | None = None) -> dict:
        return summarize(list(self.runs)[-(window or len(self.runs)):], price=price or self.price)


def summarize(records: list[RunRecord], *, price: Price | None = None) -> dict:
    """四类指标一次算完：成功率、步数与调用、每任务成本、失败分布（外加延迟分位）。

    分维度（按工具、按角色）不是为了好看：**「哪个工具在拖」与「哪个角色在花钱」
    是两种不同的修法**——前者改工具或参数，后者改交接单与预算切法。
    """
    n = len(records)
    if n == 0:
        return {"runs": 0, "note": "还没有运行记录：指标要有样本才有意义"}
    ok = sum(1 for r in records if r.kind == "成功")
    in_tokens = sum(r.in_tokens for r in records)
    out_tokens = sum(r.out_tokens for r in records)
    out: dict = {
        "runs": n,
        "success_rate": round(ok / n, 4),
        "steps": {"avg": round(sum(r.steps for r in records) / n, 2),
                  "max": max(r.steps for r in records)},
        "calls": {"avg": round(sum(r.calls for r in records) / n, 2),
                  "total": sum(r.calls for r in records)},
        "tokens": {"avg": round(sum(r.tokens for r in records) / n, 1),
                   "input": in_tokens, "output": out_tokens,
                   # 输入占比是**最该看的一个数**：每轮把历史重发一次，输入会随步数平方增长。
                   # 服务商没分开报时为 None——**“没这个数”与“这个数是 0”是两件事**。
                   "input_share": round(in_tokens / (in_tokens + out_tokens), 4)
                   if (in_tokens + out_tokens) else None},
        "latency_ms": {"p50": round(percentile([r.duration_ms for r in records], 0.5), 1),
                       "p95": round(percentile([r.duration_ms for r in records], 0.95), 1)},
        "failure_distribution": dict(Counter(r.kind for r in records)),
        "by_tool": _by_tool(records),
        "by_role": _by_role(records),
    }
    if price is not None:
        out["cost"] = {"currency": price.currency,
                       "per_task": round(price.of(in_tokens, out_tokens) / n, 6),
                       "total": round(price.of(in_tokens, out_tokens), 6)}
    else:
        out["cost"] = None                     # 没配单价就只报词元，**不要编一个价**
    return out


def _by_tool(records: list[RunRecord]) -> dict:
    """每个工具：调用次数、失败次数、平均耗时。**失败率高的那个就是最该改的一个。**"""
    acc: dict[str, dict] = {}
    for r in records:
        for s in r.spans_of(EXECUTE_TOOL):
            name = s.attributes.get("gen_ai.tool.name", "?")
            row = acc.setdefault(name, {"calls": 0, "failed": 0, "ms": []})
            row["calls"] += 1
            row["failed"] += 1 if s.status == "error" else 0
            row["ms"].append(s.duration_ms)
    return {k: {"calls": v["calls"], "failed": v["failed"],
                "avg_ms": round(sum(v["ms"]) / len(v["ms"]), 1) if v["ms"] else 0.0}
            for k, v in sorted(acc.items())}


def _by_role(records: list[RunRecord]) -> dict:
    """每个角色（`gen_ai.agent.name`）：模型调用次数与平均耗时。多 Agent 时它才非空。"""
    acc: dict[str, dict] = {}
    for r in records:
        for s in r.spans_of(CHAT):
            role = s.attributes.get("gen_ai.agent.name", "?")
            row = acc.setdefault(role, {"calls": 0, "ms": []})
            row["calls"] += 1
            row["ms"].append(s.duration_ms)
    return {k: {"calls": v["calls"],
                "avg_ms": round(sum(v["ms"]) / len(v["ms"]), 1) if v["ms"] else 0.0}
            for k, v in sorted(acc.items())}


__all__ = ["Tracer", "Run", "RunRecord", "Span", "Price", "summarize", "classify",
           "percentile", "digest", "KINDS", "INVOKE_AGENT", "CHAT", "EXECUTE_TOOL"]
