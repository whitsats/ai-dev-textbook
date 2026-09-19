"""在线观测：**日志、指标、追踪三件东西各管什么**。

3.9 已经建过一层（span 树、四类指标、按工具与角色分维度、只读 `/metrics` 端点）。
那一层量的是**一次运行**；这一章要量的是**一直跑着的服务**，差别有三处：

1. **日志要能被机器筛**。3.9 的日志是给人读的句子；在线的日志必须是
   「事件名 ＋ 键值对」——想查「哪几个请求慢」时，`grep 慢` 是没有用的。
   本模块的 `JsonLog` 就是这一版：一行一个 JSON，事件名在前，字段跟在后面；
2. **指标的命名有官方规则**（Prometheus 的指标与标签命名文档）：
   累加计数用 `_total` 后缀、单位用基本单位（秒而不是毫秒）并写进名字、
   **标签不能是用户 ID 这类无界取值**。最后这一条在本树里落成了**会抛异常的代码**；
3. **追踪要把请求内部串起来**：一次请求一个 `trace_id`，
   检索／重排／生成各段各一行，`sum(各段) ≈ 总耗时` 是一个可断言的不变量。

## 为什么「不许高基数标签」要写成代码

Prometheus 的文档原话是：**每个键值组合都是一条新的时间序列**，
所以「不要用标签存高基数维度（用户 ID、邮箱地址这类无界集合）」。
这条规矩写进文档没人看，写进代码就一定会被看见：本树的 `Counter.inc()`
只接受白名单里的标签名，传 `user_id=` 直接报错。

代价是「按用户统计」这件事在指标层做不了——**这正是重点**：
它本来就该在日志或追踪里做（那里按条付费、可采样、能删）。
把两者混在一起的典型后果是：指标基数爆炸，Prometheus 内存打满，
而**最先挂掉的往往是监控本身**，于是故障时你看不到故障。
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Iterable

__all__ = ["ALLOWED_LABELS", "Counter", "Gauge", "Histogram", "JsonLog", "MetricError",
           "NAMESPACE", "Registry", "Trace", "sanitize_name"]

#: 指标名的命名空间（Prometheus 文档：指标名应带一个与领域相关的单词前缀）。
NAMESPACE = "zhizhou_rag"

#: 允许当标签的维度——**有限取值**的那些。加一个键就是一次决策：
#: 它的取值集合有界吗？（`layer` 只有三层，`kind` 只有三档，都属于有界。）
#: 不在表里的标签名会**抛错而不是被静默丢掉**：静默丢掉会让人以为「统计过了」。
ALLOWED_LABELS = frozenset({"status", "layer", "kind", "phase", "outcome"})

_NAME = re.compile(r"[^a-zA-Z0-9_:]")


class MetricError(ValueError):
    """指标用法错误（高基数标签、非法名字）。**它是错误而不是警告**，理由见模块开头。"""


def sanitize_name(name: str) -> str:
    """把任意字符串折成合法的指标名片段（Prometheus 只允许 `[a-zA-Z0-9_:]`）。"""
    return _NAME.sub("_", name)


@dataclass
class Trace:
    """一次请求的追踪。**`sum(各段) ≈ 总耗时` 是它唯一要保证的不变量。**"""

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    started: float = field(default_factory=time.time)
    spans: list[tuple[str, float, dict]] = field(default_factory=list)
    fields: dict = field(default_factory=dict)

    def span(self, name: str, seconds: float, **kv) -> float:
        self.spans.append((name, round(seconds, 6), kv))
        return seconds

    def measure(self, name: str, **kv):
        """上下文管理器：`with trace.measure("retrieve"): ...`。"""
        return _Span(self, name, kv)

    @property
    def total(self) -> float:
        return round(sum(s[1] for s in self.spans), 6)

    def as_dict(self) -> dict:
        return {"trace_id": self.trace_id, "spans": [{"name": n, "seconds": s, **k}
                                                      for n, s, k in self.spans],
                "total": self.total, **self.fields}


class _Span:
    def __init__(self, trace: Trace, name: str, kv: dict) -> None:
        self.trace, self.name, self.kv = trace, name, kv

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc) -> bool:
        self.trace.span(self.name, time.perf_counter() - self.t0, **self.kv)
        return False


class JsonLog:
    """一行一个 JSON 的结构化日志。**`sink` 可换**（本树默认收在内存里，便于断言）。

    两个约定：事件名用 `领域_动作_状态`（`rag_query_done`），
    以及**异常一律带 `error_type`**：只有 `error` 字符串的话，
    「超时」与「解析失败」在日志里长得一样，而它们的处置完全不同。
    """

    def __init__(self, sink: list | None = None, *, clock: Callable[[], float] = time.time,
                 namespace: str = "rag") -> None:
        self.sink = sink if sink is not None else []
        self.clock = clock
        self.namespace = namespace

    def emit(self, event: str, **fields) -> dict:
        record = {"ts": round(self.clock(), 3), "event": f"{self.namespace}_{event}"}
        record.update(fields)
        self.sink.append(record)
        return record

    def lines(self) -> list[str]:
        return [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in self.sink]

    def find(self, event: str) -> list[dict]:
        return [r for r in self.sink if r["event"].endswith(event)]


class _Metric:
    kind = "untyped"

    def __init__(self, name: str, help_: str, labels: Iterable[str] = ()) -> None:
        self.name = sanitize_name(name)
        self.labels = tuple(labels)
        for key in self.labels:
            if key not in ALLOWED_LABELS:
                raise MetricError(f"{self.name} 的标签 {key!r} 不在白名单里——"
                                  f"高基数标签会把监控自己打挂（可用：{sorted(ALLOWED_LABELS)}）")
        self.help = help_
        self.values: dict[tuple, float] = {}

    def _row(self, labels: dict) -> tuple:
        if set(labels) != set(self.labels):
            raise MetricError(f"{self.name} 的标签必须正好是 {self.labels}，收到 {tuple(labels)}")
        for key in labels:
            if key not in ALLOWED_LABELS:
                raise MetricError(f"标签 {key!r} 不在白名单里")
        return tuple(labels[k] for k in self.labels)

    def render(self) -> list[str]:
        head = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} {self.kind}"]
        return head


class Counter(_Metric):
    """只增不减的累加计数。**名字必须带 `_total`**（Prometheus 命名文档）。"""

    kind = "counter"

    def __init__(self, name: str, help_: str, labels: Iterable[str] = ()) -> None:
        if not name.endswith("_total"):
            raise MetricError(f"计数指标要带 _total 后缀：{name}")
        super().__init__(name, help_, labels)

    def inc(self, value: float = 1.0, **labels) -> None:
        row = self._row(labels)
        self.values[row] = self.values.get(row, 0.0) + value


class Gauge(_Metric):
    """可增可减的瞬时值（在线连接数、队列长度）。"""

    kind = "gauge"

    def set(self, value: float, **labels) -> None:
        self.values[self._row(labels)] = float(value)


class Histogram(_Metric):
    """分桶计数。**桶是契约的一部分**：改了桶就等于改了所有历史分位数的口径。

    本树的桶按「秒」给（0.01 到 30），因为单位必须是基本单位——
    写毫秒的名字（`_ms`）在 Prometheus 里就等着哪天有人把它和秒混着画。
    """

    kind = "histogram"

    def __init__(self, name: str, help_: str, *, buckets: Iterable[float] = (),
                 labels: Iterable[str] = ()) -> None:
        super().__init__(name, help_, labels)
        self.buckets = tuple(sorted(buckets)) or (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
        if not name.endswith("_seconds"):
            raise MetricError(f"按时间分的直方图要带 _seconds 单位后缀：{name}")

    def observe(self, value: float, **labels) -> None:
        row = self._row(labels)
        self.values.setdefault(("_count",) + row, 0.0)
        self.values[("_count",) + row] += 1.0
        self.values[("_sum",) + row] = self.values.get(("_sum",) + row, 0.0) + value
        for b in self.buckets:
            if value <= b:
                self.values.setdefault((b,) + row, 0.0)
                self.values[(b,) + row] += 1.0

    def quantile(self, q: float, **labels) -> float | None:
        """从桶里读一个近似分位（Prometheus 的 `histogram_quantile` 同样只能近似）。

        返回 `None` 表示「落在最后一个桶之外」——**不许外推**。
        这一条与 5.6 的「可检测最小差异」是同一族：分辨率之外的事不要报数。
        """
        row = self._row(labels)
        total = self.values.get(("_count",) + row, 0.0)
        if not total:
            return None
        want = total * q
        prev_b = 0.0
        for b in self.buckets:
            got = self.values.get((b,) + row, 0.0)
            if got >= want:
                return round(prev_b + (b - prev_b) * (want / max(got, 1e-9)), 6)
            prev_b = b
        return None


class Registry:
    """一堆指标 ＋ 一个文本导出（Prometheus 的 `text/plain` 格式）。

    本树不引 `prometheus_client`：这一层要读者看懂的是**格式与命名**，
    而格式本身只有 `# HELP` / `# TYPE` / `名字{标签} 值` 三种行。
    """

    def __init__(self, namespace: str = NAMESPACE) -> None:
        self.namespace = namespace
        self.metrics: dict[str, _Metric] = {}

    def register(self, metric: _Metric) -> _Metric:
        self.metrics[metric.name] = metric
        return metric

    def counter(self, name: str, help_: str, labels: Iterable[str] = ()) -> Counter:
        return self.register(Counter(f"{self.namespace}_{name}", help_, labels))

    def gauge(self, name: str, help_: str, labels: Iterable[str] = ()) -> Gauge:
        return self.register(Gauge(f"{self.namespace}_{name}", help_, labels))

    def histogram(self, name: str, help_: str, **kw) -> Histogram:
        return self.register(Histogram(f"{self.namespace}_{name}", help_, **kw))

    def render(self) -> str:
        out: list[str] = []
        for metric in self.metrics.values():
            out.extend(metric.render())
            if isinstance(metric, Histogram):
                for row, value in sorted(metric.values.items(), key=lambda kv: str(kv[0])):
                    if row[0] == "_count" or row[0] == "_sum":
                        suffix = row[0]
                        labels = metric.labels
                        values = row[1:]
                    else:
                        suffix = "_bucket"
                        labels = ("le",) + metric.labels
                        values = (metric.buckets and row[0],) + row[1:]
                    out.append(_line(metric.name + suffix, labels, values, value))
                continue
            for row, value in sorted(metric.values.items(), key=lambda kv: str(kv[0])):
                out.append(_line(metric.name, metric.labels, row, value))
        return "\n".join(out) + ("\n" if out else "")


def _line(name: str, labels, values, value) -> str:
    if not labels:
        return f"{name} {value:g}"
    pairs = ",".join(f'{k}="{v}"' for k, v in zip(labels, values))
    return f"{name}{{{pairs}}} {value:g}"
