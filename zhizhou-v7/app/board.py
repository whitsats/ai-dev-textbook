"""成本看板：把 6.4 的四栏账挂到 trace 上之后，多出三件只有「按 trace 看」才有的错。

**① 算不出来 ≠ 0**（与 7.1 的 `None` 不是 0 是同一条纪律）。看板上的每一格钱都由
属性算出来：缺 usage 那两项、或者模型名不在价表里，这一格是**算不出来**——
而它在报表上与「这一格花了 0 元」长得一模一样，于是**看板会显得比真实更便宜**。
所以这张板子上必须同时报两个数：一共多少 span、其中多少格的账**算得出来**。

**② 重试也要付钱，但只能付一次。** 6.3 说重试是「重发」、6.4 算过失败率 20% 会让
一笔账平均贵 24.80%。trace 上这件事有两种记法（`gen_ai.*` 的约定是「一根逻辑 span
覆盖含全部重试的时长」，而网关那一层按物理尝试记）：

| 层 | 它记的是什么 | 谁需要它 |
| --- | --- | --- |
| `attempts` | **每一次物理尝试**各一根 span，各自带 usage | 想回答「失败那几次花了多少」 |
| `logical` | **一次逻辑调用**一根 span，usage 是几次之和 | 想回答「这一次调用一共花了多少」 |

两种都对——**但账单只认一层**。两层都记的树上一个 `sum`（也就是任何一张「把所有 span
加起来」的看板）会把重试那一段算两遍，而报表上看不出任何异常：`layers` 因此是必填参数
而不是默认值。

**③ 口径要先声明。** `gen_ai.usage.input_tokens` 里**含不含**缓存读，两家的写法不同。
本层按「含」处理：未命中输入 ＝ 输入 − 缓存读 − 缓存写；并且对
「缓存读 + 缓存写 > 输入」这种自相矛盾**报错**——报错比静默取绝对值好，
因为取绝对值之后那张表仍然是自洽的。

`alerts()` 也在这一块：看板报数、告警叫人，而**报得准不等于叫得对**——
同一个阈值，判据从「一个窗口越线」改成「连续三个窗口越线」，告警从 3 次变成 1 次，
代价是晚两个窗口。那两件事要一起写在口径里。
"""
from __future__ import annotations

from dataclasses import dataclass

from .trace import Span

#: 两家供应商自己写下的乘法关系（与 6.1 的价表同一组数）。
CACHE_WRITE_X = 1.25
CACHE_READ_X = 0.10

#: 四栏。它们的名字不是随便起的：**四栏之和就是这一格的账**（6.4 那条口径断言）。
COLUMNS = ("uncached", "write", "read", "out")
COLUMN_LABEL = {"uncached": "未命中输入", "write": "缓存写", "read": "缓存读", "out": "输出"}

#: 记录 usage 的两层。看板必须声明它认哪一层（见模块开头第 ② 条）。
LAYERS = ("attempts", "logical")


@dataclass(frozen=True)
class Model:
    """价表里的一行。价是**每百万词元（MTok）的美元数**。"""

    name: str
    input_price: float
    output_price: float
    cache_read: float
    cache_write: float

    def columns(self, usage: dict) -> dict[str, float]:
        """四栏各自的美元数。**四栏之和就是这一格的账。**"""
        return {
            "uncached": usage["uncached"] * self.input_price / 1_000_000,
            "write": usage["write"] * self.cache_write / 1_000_000,
            "read": usage["read"] * self.cache_read / 1_000_000,
            "out": usage["out"] * self.output_price / 1_000_000,
        }


def _row(name: str, inp: float, out: float, cached: float) -> Model:
    """按官方定价页的乘法关系推写价：**不手抄四个数，抄一个数加一条关系**。"""
    return Model(name, inp, out, cached, round(CACHE_WRITE_X * inp, 4))


#: 两档：贵的那个与便宜的那个。**只取两档**是为了让看板上的对比一眼能算。
MODELS: tuple[Model, ...] = (
    _row("gpt-5.6-terra", 2.0, 12.0, 0.20),
    _row("gpt-5.6-luna", 0.20, 1.20, 0.02),
)

BY_NAME: dict[str, Model] = {m.name: m for m in MODELS}

BY_MODEL = lambda span: span.attrs.get("gen_ai.request.model")            # noqa: E731
BY_ROUTE = lambda span: span.attrs.get("zhizhou.route", "（没有这一栏）")   # noqa: E731


def violations(models: tuple[Model, ...] = MODELS) -> list[str]:
    """把表里能算出来的关系全算一遍。**空列表才是正常**（与 6.1 那张表同一条路）。"""
    bad: list[str] = []
    for m in models:
        if abs(m.cache_write - round(CACHE_WRITE_X * m.input_price, 4)) > 1e-9:
            bad.append(f"{m.name}：缓存写价 {m.cache_write} 与「输入 × {CACHE_WRITE_X}」不符")
        if abs(m.cache_read - round(CACHE_READ_X * m.input_price, 4)) > 1e-9:
            bad.append(f"{m.name}：缓存读价 {m.cache_read} 与「输入 × {CACHE_READ_X}」不符")
        if m.cache_read >= m.input_price:
            bad.append(f"{m.name}：缓存读价不低于输入价——命中越多账越大，这一栏必须便宜")
    return bad


def usage_of(span: Span) -> dict | None:
    """从 span 的属性里读出四栏。**读不出来返回 `None`，不是四栏全 0。**

    返回 `None` 的两种情形（都必须在看板上与「花了 0 元」分开）：
    · 缺 `gen_ai.usage.input_tokens` 或 `gen_ai.usage.output_tokens`；
    · 缓存那两栏自相矛盾（读 + 写 > 输入）——这不是「值得怀疑」，这是算不出来。
    """
    attrs = span.attrs
    inp, out = attrs.get("gen_ai.usage.input_tokens"), attrs.get("gen_ai.usage.output_tokens")
    if inp is None or out is None:
        return None
    read = attrs.get("gen_ai.usage.cache_read.input_tokens") or 0
    write = attrs.get("gen_ai.usage.cache_write.input_tokens") or 0
    if read + write > inp:
        return None
    return {"uncached": inp - read - write, "write": write, "read": read, "out": out}


def usage_notes(span: Span) -> list[str]:
    """这一根 span 的 usage 有哪些「没法核」的地方。空列表才是正常。"""
    notes: list[str] = []
    attrs = span.attrs
    if attrs.get("gen_ai.usage.input_tokens") is None or \
            attrs.get("gen_ai.usage.output_tokens") is None:
        notes.append("usage 缺项：这一格的账算不出来")
        return notes
    if attrs.get("gen_ai.usage.cache_read.input_tokens") is None and \
            attrs.get("gen_ai.usage.cache_write.input_tokens") is None:
        # 官方把缓存两栏写成「When applicable」：没报不等于报了 0——
        # 这两件事在「未命中输入」那一栏上给出同一个数，所以只能**标出来**。
        notes.append("缓存两栏都没报（官方是「适用时才有」）：未命中输入那一栏按「全未命中」算")
    read = attrs.get("gen_ai.usage.cache_read.input_tokens") or 0
    write = attrs.get("gen_ai.usage.cache_write.input_tokens") or 0
    if read + write > (attrs.get("gen_ai.usage.input_tokens") or 0):
        notes.append("缓存读+写 > 输入：两家对「input_tokens 含不含缓存」的写法不同，口径要先声明")
    return notes


def layer_of(span: Span) -> str:
    """这根 span 记在哪一层。没写就按 `attempts` 算（物理尝试是默认那一层）。"""
    return span.attrs.get("zhizhou.layer", "attempts")


def span_cost(span: Span, models: dict[str, Model] | None = None) -> float | None:
    """一根 span 的账。**模型不在价表里时返回 `None`**——那同样是「算不出来」。"""
    usage = usage_of(span)
    if usage is None:
        return None
    model = (models or BY_NAME).get(span.attrs.get("gen_ai.request.model"))
    if model is None:
        return None
    return round(sum(model.columns(usage).values()), 10)


def trace_cost(trace, *, layers: tuple[str, ...], models: dict[str, Model] | None = None):
    """一条 trace 的账：**只累加指定的那一层**。

    返回值是 `(账, 算得出来的格数, 算不出来的格数)`——后两个数必须一起报，
    否则「看板便宜了」这件事永远没人会说出口。
    """
    for name in layers:
        if name not in LAYERS:
            raise ValueError(f"未知的层：{name}（可选 {LAYERS}）")
    total, done, missing = 0.0, 0, 0
    for span in trace.spans:
        if layer_of(span) not in layers:
            continue
        if span.attrs.get("gen_ai.usage.input_tokens") is None:
            continue                      # 本来就没有 usage 的 span（检索、工具）不算格
        cost = span_cost(span, models)
        if cost is None:
            missing += 1
        else:
            total, done = total + cost, done + 1
    return round(total, 10), done, missing


def board(traces, *, layers: tuple[str, ...] = ("attempts",),
          models: dict[str, Model] | None = None, key_of=BY_MODEL) -> dict:
    """看板：按 `key_of` 分组，每组四栏 ＋ 总额 ＋ **格数与覆盖率**。

    覆盖率那一栏是这张板子存在的理由：只报钱数的看板，在「一半 span 算不出来」时
    会显得比真实便宜，而**它和「真的很便宜」长得一样**。
    """
    models = models or BY_NAME
    rows: dict[str, dict] = {}
    priced, unpriced = 0, 0
    models_seen: set[str] = set()
    for trace in traces:
        for span in trace.spans:
            if layer_of(span) not in layers:
                continue
            if span.attrs.get("gen_ai.usage.input_tokens") is None:
                continue                  # 本来就没有 usage 的 span（检索、工具）：不算账的一格
            key = key_of(span) or ("（没有这一栏）" if key_of is BY_MODEL else "（未分组）")
            row = rows.setdefault(key, {"traces": set(), **{c: 0.0 for c in COLUMNS},
                                        "grid": 0, "unknown": 0})
            row["traces"].add(trace.trace_id)
            usage = usage_of(span)
            if usage is None:
                # 有 usage 而算不出来（缺项或自相矛盾）：进不了钱，但**必须被数出来**。
                row["unknown"] += 1
                unpriced += 1
                continue
            model = models.get(span.attrs.get("gen_ai.request.model"))
            if model is None:
                row["unknown"] += 1
                unpriced += 1
                continue
            models_seen.add(model.name)
            for c, usd in model.columns(usage).items():
                row[c] += usd
            row["grid"] += 1
            priced += 1
    for key, row in rows.items():
        row["total"] = sum(row[c] for c in COLUMNS)
        row["traces"] = len(row["traces"])
    return {"rows": rows, "priced": priced, "unpriced": unpriced,
            "models": sorted(models_seen),
            "coverage": (priced / (priced + unpriced)) if priced + unpriced else None}


def alert_events(series: list[float], threshold: float, *,
                 window: int = 1, direction: str = "higher") -> list[tuple[int, int]]:
    """告警：返回**事件**（`1` 起的窗口号）`(fire, clear)` 列表。

    `window` 是「连续几个窗口都越线才算」——也就是告警规则里那个 `for`。
    它同时买到两样东西：**假报变少**与**真报变晚**，而这两样必须一起写在口径里。
    """
    if window < 1:
        raise ValueError("window 至少是 1")
    if direction not in ("higher", "lower"):
        raise ValueError(f"方向不合法：{direction}")

    def over(i: int) -> bool:
        return series[i] > threshold if direction == "higher" else series[i] < threshold

    events: list[tuple[int, int]] = []
    firing = False
    for i in range(len(series)):
        now = all(over(j) for j in range(max(0, i - window + 1), i + 1)) and i + 1 >= window
        if now and not firing:
            events.append((i + 1, i + 1))
            firing = True
        elif now:
            events[-1] = (events[-1][0], i + 1)
        else:
            firing = False
    return events
