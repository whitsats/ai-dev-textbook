"""追踪：一条 trace 上「谁调了谁」这件事，要说清四件事。

1. **形状**——span 是一棵**树**，不是一列。所以有三样东西只有树上才读得出来：
   一根 span 的**自耗时**（`self_ms`：自己的时长减掉所有子 span，回答「时间花在这一层
   还是下一层」）、根的**缺口**（`gap_ms`：根的总时长减掉子 span **覆盖过的并集**，
   回答「有多少毫秒不在任何 span 里」），以及**挂空**（父 span 不在这一条 trace 里）。
   缺口永远不是 0——那不是 bug，那是**没被埋点的那段代码**，而它在报表上是隐身的。
   并集与加法的区别只在并行时出现：两个子 span 重叠的那一段，加法算两次、并集算一次，
   于是「缺口」比「自耗时」小——**两个数都对，问的不是同一个问题**；
2. **语义约定**（`REQUIRED` / `CONDITIONAL`）——`gen_ai.*` 那些名字不是随便起的：
   看板、评估器、过滤器都按名字取数，所以**名字是接口**。官方把属性分成
   Required／Conditionally Required／Recommended 三档，而「缺了要报出来」这一条
   没有任何运行时在守：缺 `gen_ai.request.model` 看板就分不成组，缺 usage 两项
   **这一格的账算不出来**——而它长得和「这一格花了 0 元」一模一样；
3. **关联**——`trace_id` 是把三层账串起来的那根线：6.3 的 `attempts`（一次逻辑调用
   重试了几次）、7.1 的跑记录（这一条题是哪一次跑）。官方在 GenAI span 那一节写得很
   清楚：**一次被自动重试的调用，那一根 span 覆盖的是「含全部重试」的逻辑时长**——
   于是「物理 span」与「逻辑 span」是两种记法，而混用会让看板重复计费（见 `board`）；
4. **采样**——抽多少、抽谁。头部采样**在知道结果之前**就决定了，所以它抽掉的恰恰是
   最该留的那一类（出错、超长）；尾部采样等结果出来再决定，代价是要先把整条 trace
   缓在内存里。还有第三种写法最省事也最像坏掉：**每一根 span 各自掷骰子**——
   于是同一条 trace 里留下了没有父的子 span，而那看起来和「链路断了」一模一样。

`percentile()` 也在这里，因为它同属「读数怎么算」：同一个分位有两种算法，
同一批数会给出两个不同的 p95，所以**报分位必须连算法一起报**。
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

#: span 的类型。前四种是应用层的，`gateway` 是 6.3 那一层（一次逻辑调用）。
KINDS = ("chain", "retriever", "llm", "tool", "gateway")

#: 每个类型**必须**带的属性。这张表是官方语义约定的可执行形式——
#: 名字取自 OpenTelemetry 的 GenAI 约定（`gen_ai.*`）。注意 `gen_ai.provider.name`
#: 本身是改过名的（旧写法 `gen_ai.system`）：**属性名会变，看板按名字取数**，
#: 所以改名是一件要跟看板一起改的事，不是一次重命名。
REQUIRED: dict[str, tuple[str, ...]] = {
    "llm": ("gen_ai.operation.name", "gen_ai.provider.name", "gen_ai.request.model",
            "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"),
    "gateway": ("gen_ai.operation.name", "gen_ai.provider.name", "gen_ai.request.model"),
    "retriever": ("db.system", "db.collection.name"),
    "tool": ("gen_ai.tool.name",),
    "chain": (),
}

#: 条件必填：**条件成立时**缺了才报。（条件属性, 它带出来的那个必填属性）
CONDITIONAL: dict[str, tuple[tuple[str, str], ...]] = {
    "llm": (("error", "error.type"),),          # 出错的那一趟必须写清错误类型
    "gateway": (("error", "error.type"),),
}


@dataclass(frozen=True)
class Span:
    """一根 span。时间是**相对这一次请求开始的毫秒数**（不是绝对时钟）。"""

    span_id: str
    trace_id: str
    name: str
    kind: str
    start_ms: float
    end_ms: float
    parent_id: str | None = None
    attrs: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"{self.span_id} 的类型不合法：{self.kind}（可选 {KINDS}）")
        if self.end_ms < self.start_ms:
            raise ValueError(f"{self.span_id} 结束早于开始：{self.start_ms} → {self.end_ms}")

    def duration(self) -> float:
        return self.end_ms - self.start_ms

    def missing(self) -> list[str]:
        """这一根缺了哪些语义约定要求带的属性。**空列表才是正常。**"""
        out = [k for k in REQUIRED[self.kind] if self.attrs.get(k) is None]
        for cond, key in CONDITIONAL.get(self.kind, ()):
            if self.attrs.get(cond) and self.attrs.get(key) is None:
                out.append(key)
        return out


@dataclass(frozen=True)
class Trace:
    """一条 trace：一棵树 ＋ 一次逻辑请求（Langfuse 的数据模型里它就是这个粒度）。"""

    trace_id: str
    spans: tuple[Span, ...]

    def by_id(self) -> dict[str, Span]:
        return {s.span_id: s for s in self.spans}

    def orphans(self) -> list[Span]:
        """父 span 不在这一条 trace 里——**逐 span 独立抽样的断口长这样**。"""
        ids = set(self.by_id())
        return [s for s in self.spans if s.parent_id is not None and s.parent_id not in ids]

    def roots(self) -> list[Span]:
        return [s for s in self.spans if s.parent_id is None] or self.orphans()

    def children(self, span_id: str) -> list[Span]:
        return sorted([s for s in self.spans if s.parent_id == span_id],
                      key=lambda s: (s.start_ms, s.span_id))

    def root(self) -> Span | None:
        """根：那一个没有父的 span。多于一个时取开始最早的那一个（并且会被报出来）。"""
        roots = self.roots()
        return min(roots, key=lambda s: (s.start_ms, s.span_id)) if roots else None

    def self_ms(self, span: Span) -> float:
        """自耗时 ＝ 自己的时长 − 所有子 span 的时长之和（负数会被截到 0 并报出来）。

        它是**树才有的读数**：一次请求变慢时它回答「是这一层慢了，还是它调的那一层慢了」。
        """
        return max(0.0, span.duration() - sum(c.duration() for c in self.children(span.span_id)))

    def covered_ms(self) -> float:
        """根的直接子 span **覆盖过的并集**（重叠只算一次）。

        「加法」与「并集」在串行时相等，在并行时不等——这就是并发为什么让
        「自耗时」与「缺口」变成两个数：两个各 300ms 的重叠子 span，加法给 600ms、
        并集给一段 300ms 的区间，而根只等了 300ms。
        """
        root = self.root()
        if root is None:
            return 0.0
        spans = [(max(c.start_ms, root.start_ms), min(c.end_ms, root.end_ms))
                 for c in self.children(root.span_id)]
        spans = sorted((a, b) for a, b in spans if b > a)
        total, cur_a, cur_b = 0.0, None, None
        for a, b in spans:
            if cur_b is None or a > cur_b:
                if cur_b is not None:
                    total += cur_b - cur_a
                cur_a, cur_b = a, b
            else:
                cur_b = max(cur_b, b)
        if cur_b is not None:
            total += cur_b - cur_a
        return total

    def gap_ms(self) -> float:
        """根窗口里**没有任何子 span 覆盖**的毫秒数（＝没被埋点的那一段）。"""
        root = self.root()
        return root.duration() - self.covered_ms() if root else 0.0

    def violations(self) -> list[str]:
        """这一条 trace 自身的断言（也是**树能不能信**的断言）。空列表才是正常。"""
        bad: list[str] = []
        if not self.spans:
            return ["一条 span 都没有：空 trace 不是「一切正常」"]
        ids = [s.span_id for s in self.spans]
        seen: set[str] = set()
        for sid in ids:
            if sid in seen:
                bad.append(f"span_id 有重复：{sid}（覆盖会让两根 span 变成一根）")
            seen.add(sid)
        for s in self.spans:
            if s.trace_id != self.trace_id:
                bad.append(f"{s.span_id} 的 trace_id 不是这一条的：{s.trace_id}")
        for s in self.orphans():
            bad.append(f"{s.span_id}（{s.name}）的父 span {s.parent_id} 不在这一条 trace 里"
                       f"——挂空；逐 span 抽样留下的断口就长这样")
        roots = [s for s in self.spans if s.parent_id is None]
        if len(roots) > 1:
            bad.append(f"有 {len(roots)} 个根（{', '.join(s.name for s in roots)}）"
                       f"——同一条 trace 只该有一个根")
        for s in self.spans:
            if s.parent_id is None:
                continue
            parent = self.by_id().get(s.parent_id)
            if parent is None:
                continue
            if s.end_ms > parent.end_ms + 1e-9 or s.start_ms < parent.start_ms - 1e-9:
                bad.append(f"{s.span_id} 的时间区间超出了父 {parent.span_id}："
                           f"{s.start_ms}→{s.end_ms} 不在 {parent.start_ms}→{parent.end_ms} 内")
            if s.duration() > parent.duration() + 1e-9:
                bad.append(f"{s.span_id} 比它的父还长（{s.duration()} > {parent.duration()}）"
                           f"——自耗时会被截到 0，而报表上看不出来")
        return bad

    def missing_attrs(self) -> list[tuple[str, str, list[str]]]:
        """整条 trace 的语义约定缺口：`(span_id, kind, 缺的属性)`。"""
        return [(s.span_id, s.kind, s.missing()) for s in self.spans if s.missing()]

    def depth(self, span: Span) -> int:
        """层级：根是 0。父不在时按 1 算（它是那个断口的挂点）。"""
        d, cur = 0, span
        while cur.parent_id is not None:
            parent = self.by_id().get(cur.parent_id)
            if parent is None:
                return d + 1
            d, cur = d + 1, parent
        return d

    def tree_lines(self) -> list[str]:
        """把树画成行：**按父子关系递归地画**（按时间排序会把子 span 排在别人底下）。

        `×` 是断口（父不在这一条 trace 里）——它画在根那一层，因为它没有父可挂。
        """
        ids = self.by_id()
        lines: list[str] = []

        def walk(span: Span, depth: int) -> None:
            mark = "×" if span.parent_id is not None and span.parent_id not in ids else "·"
            lines.append(f"{'  ' * depth}{mark} {span.name:<30} "
                         f"{span.kind:<9} {span.duration():>7.0f}ms  "
                         f"自 {self.self_ms(span):>7.0f}ms")
            for child in self.children(span.span_id):
                walk(child, depth + 1)

        for root in sorted([s for s in self.spans if s.parent_id is None],
                           key=lambda s: (s.start_ms, s.span_id)):
            walk(root, 0)
        for orphan in sorted(self.orphans(), key=lambda s: (s.start_ms, s.span_id)):
            walk(orphan, 0)
        return lines


# --------------------------------------------------------------------------- 样本
# 离线树没有真流量，所以下面这些「现场记录」是**造出来的**：它们的用途是让埋点、
# 语义约定、采样与看板**自己的性质**能被算出来。它量不了真实延迟，也量不了模型质量。

#: 200 条现场记录：路线决定模型，每隔 20 条有一个 `/export`，每隔 33 条有一次出错。
ROUTES = ("/ask", "/export")
MODEL_FOR_ROUTE = {"/ask": "gpt-5.6-luna", "/export": "gpt-5.6-terra"}
#: 六条「慢得离谱」的 trace——第 4／70／110 条是孤立的单点，135/144/153 是连着的那一次。
SLOW_AT: dict[int, float] = {4: 1500.0, 70: 1600.0, 110: 1520.0,
                             135: 3050.0, 144: 3200.0, 153: 2980.0}
#: 告警那一节每窗多少条：20 个窗口正好覆盖 200 条。
WINDOW = 10


def sample_trace() -> Trace:
    """知舟回答一个问题的那一条 trace：8 根 span。

    它**故意留了三处缺口**（属性那一侧），而结构那一侧是干净的：
    「树没问题」与「属性齐了」是两条断言，一条绿不代表另一条绿。
    网关那一层按 `logical` 记（含两次尝试），两次尝试按 `attempts` 各记一根——
    这就是「重试也有账、但只能算一次」那条口径的现场。
    """
    tr = "tr-0000"
    root = Span("s-root", tr, "invoke_agent 知舟", "chain", 0, 1240)
    guard = Span("s-guard", tr, "check-injection", "tool", 10, 30, "s-root",
                 {"gen_ai.tool.name": None})          # 缺：手工埋点最容易漏的那一个
    retr = Span("s-retr", tr, "retrieve-context", "retriever", 40, 240, "s-root",
                {"db.system": "sqlite"})              # 缺：db.collection.name
    gw = Span("s-gw", tr, "chat gpt-5.6-terra", "gateway", 260, 900, "s-root",
              {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
               "gen_ai.request.model": "gpt-5.6-terra", "zhizhou.layer": "logical",
               "gen_ai.usage.input_tokens": 9200, "gen_ai.usage.output_tokens": 900,
               "gen_ai.usage.cache_read.input_tokens": 1000,
               "gen_ai.usage.cache_write.input_tokens": 200,
               "zhizhou.attempts": 2})
    att1 = Span("s-att1", tr, "attempt 1", "llm", 260, 520, "s-gw",
                {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
                 "gen_ai.request.model": "gpt-5.6-terra", "zhizhou.layer": "attempts",
                 "error": True, "error.type": "429",
                 "gen_ai.usage.input_tokens": 4000, "gen_ai.usage.output_tokens": 0})
    att2 = Span("s-att2", tr, "attempt 2", "llm", 540, 900, "s-gw",
                {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
                 "gen_ai.request.model": "gpt-5.6-terra", "zhizhou.layer": "attempts",
                 "gen_ai.usage.input_tokens": 5200, "gen_ai.usage.output_tokens": 900,
                 "gen_ai.usage.cache_read.input_tokens": 1000,
                 "gen_ai.usage.cache_write.input_tokens": 200})
    tool = Span("s-tool", tr, "execute_tool get_table_schema", "tool", 920, 1040, "s-root",
                {"gen_ai.tool.name": "get_table_schema"})
    summ = Span("s-sum", tr, "chat gpt-5.6-luna", "llm", 1060, 1200, "s-root",
                {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
                 "gen_ai.request.model": "gpt-5.6-luna", "zhizhou.layer": "attempts",
                 "gen_ai.usage.input_tokens": 900})   # 缺 output_tokens → 这一格算不出钱
    return Trace(tr, (root, guard, retr, gw, att1, att2, tool, summ))


def fanout_trace() -> Trace:
    """两路并发的那一条：`自耗时` 与 `缺口` 在这一种树上**不是同一个数**。"""
    tr = "tr-fan"
    root = Span("f-root", tr, "invoke_agent 知舟", "chain", 0, 600)
    a = Span("f-a", tr, "retrieve-context", "retriever", 100, 400, "f-root",
             {"db.system": "sqlite", "db.collection.name": "chunks"})
    b = Span("f-b", tr, "expand-query", "llm", 100, 400, "f-root",
             {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
              "gen_ai.request.model": "gpt-5.6-luna",
              "gen_ai.usage.input_tokens": 800, "gen_ai.usage.output_tokens": 200})
    return Trace(tr, (root, a, b))


def workload(n: int = 200, seed: int = 7) -> list[Trace]:
    """200 条现场记录。慢的那六条按 `SLOW_AT` 摆好，其余按种子生成。"""
    import random

    rng = random.Random(seed)
    out: list[Trace] = []
    for i in range(n):
        route = "/export" if i % 20 == 3 else "/ask"
        model = MODEL_FOR_ROUTE[route]
        total = SLOW_AT.get(i, rng.uniform(320, 560))
        attrs = {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
                 "gen_ai.request.model": model, "zhizhou.layer": "attempts",
                 "zhizhou.route": route,
                 "gen_ai.usage.input_tokens": rng.randint(1200, 5000),
                 "gen_ai.usage.cache_read.input_tokens": 400,
                 "gen_ai.usage.cache_write.input_tokens": 100,
                 "gen_ai.usage.output_tokens": rng.randint(300, 900)}
        if i % 33 == 7:
            attrs |= {"error": True, "error.type": "500"}
        tr = f"tr-{i:04d}"
        out.append(Trace(tr, (
            Span(f"t{i}-root", tr, "invoke_agent 知舟", "chain", 0, total),
            Span(f"t{i}-retr", tr, "retrieve-context", "retriever", 20, 220, f"t{i}-root",
                 {"db.system": "sqlite", "db.collection.name": "chunks"}),
            Span(f"t{i}-llm", tr, f"chat {model}", "llm", 240, total * 0.9, f"t{i}-root",
                 attrs),
        )))
    return out


def window_p95(traces: list[Trace]) -> list[float]:
    """每 `WINDOW` 条一窗，取这一窗的 p95。**10 个样本时 p95 就是这一窗的最大值。**"""
    out: list[float] = []
    for start in range(0, len(traces), WINDOW):
        roots = [t.root().duration() for t in traces[start:start + WINDOW]]
        if len(roots) < WINDOW:
            break
        out.append(round(percentile(roots, 0.95), 4))
    return out


def head_keep(trace_id: str, rate: float, *, seed: str = "zhizhou") -> bool:
    """头部采样：只看 `trace_id` 掷一次骰子，**结果出来之前就定了**。

    确定性哈希，不是随机数：同一个 `trace_id` 在网关、检索、生成三处必须得到
    **同一个**决定，否则一条 trace 会被抽成半条（见 `sample_spans`）。
    """
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"采样率必须在 [0, 1]：{rate}")
    digest = hashlib.sha256(f"{seed}:{trace_id}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0x1_0000_0000 < rate


def is_error(trace: Trace) -> bool:
    """这一条里有没有出错的 span（`error` 标记或状态码 ≥ 500）。"""
    for s in trace.spans:
        if s.attrs.get("error"):
            return True
        if isinstance(s.attrs.get("http.status_code"), int) and s.attrs["http.status_code"] >= 500:
            return True
    return False


def tail_keep(trace: Trace, *, rate: float, slow_ms: float) -> bool:
    """尾部采样：**等这一条跑完再决定**。出错的和慢的一律留，其余按比例抽。

    代价是那份「先缓存住整条 trace」的内存——它换来的是：真正想看的那些一条不少。
    """
    if is_error(trace) or trace.root() is not None and trace.root().duration() >= slow_ms:
        return True
    return head_keep(trace.trace_id, rate)


def sample_spans(trace: Trace, rate: float) -> Trace:
    """**每一根 span 各自掷骰子**——最省事的那种写法，也是最像坏掉的那种。

    它留下的树里有「父不在的子 span」：断口与真正的链路断裂在报表上长得一样。
    """
    kept = [s for s in trace.spans if head_keep(s.span_id, rate)]
    return Trace(trace.trace_id, tuple(kept))


#: 分位的两种算法。**同一批数会给出两个不同的 p95**，所以报分位必须连算法一起报。
QUANTILE_METHODS = ("nearest_rank", "linear")


def percentile(values: list[float], q: float, *, method: str = "nearest_rank") -> float:
    """分位数。

    - `nearest_rank`：第 `ceil(q·n)` 个（监控系统的常见口径——**报的是「实际某一个值」**）；
    - `linear`：在 `q·(n−1)` 处线性插值（统计软件的常见口径——**可能报出没人经历过的值**）。

    两种都不算错。错的是**换了一个算法而没说**：昨天 p95 是 3,150、今天是 3,240，
    差的完全是算法。
    """
    if method not in QUANTILE_METHODS:
        raise ValueError(f"未知的分位算法：{method}（可选 {QUANTILE_METHODS}）")
    if not values:
        raise ValueError("没有样本，算不出分位")
    if not 0.0 < q <= 1.0:
        raise ValueError(f"分位必须在 (0, 1]：{q}")
    xs = sorted(values)
    n = len(xs)
    if method == "nearest_rank":
        return xs[min(n - 1, max(0, math.ceil(q * n) - 1))]
    pos = q * (n - 1)
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


def p95_gap(values: list[float]) -> float:
    """两种算法在这批数上差多少（**差值本身就是一条读数**）。"""
    a = percentile(values, 0.95, method="nearest_rank")
    b = percentile(values, 0.95, method="linear")
    return round(a - b, 4)
