"""指标注册表：一个指标要说清四件事。

1. **它需要哪些输入**（`needs`）——一个需要参考答案的指标，在一条没有参考答案的题上
   就是**算不出来**；
2. **它朝哪边好**（`direction`）——「越大越好」与「越小越好」搞反，门就变成反的：
   一切正常时报警，真退步时放行；
3. **算不出来时返回什么**（`None`）——这是本章最重的一条口径：
   **`None` 不是 0**。「这一条没测」与「这一条得了 0 分」是两件事，
   而把它们合成一个数只要一行代码（`.get(x, 0)`），后果是**分数的分母悄悄变了**；
4. **重名要报错**——注册表里两个同名指标，先注册的那个会被静默替换掉
   （`dict` 的语义），而报表上仍然是「一个指标」。

聚合口径也在这里，因为它同样会悄悄改分母：

- `aggregate(as_zero=False)`：**宏平均**，分母只数算得出来的那些格。它回答的是
  「在能测的那些上表现如何」；
- `aggregate(as_zero=True)`：把测不了的记成 0。它回答的是「测不了就算失败」。
  两个数在一张报表上长得几乎一样，而它们说的不是一件事——所以它是一个**参数**，
  不是一个默认值。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

HIGHER = "higher"
LOWER = "lower"
DIRECTIONS = (HIGHER, LOWER)


@dataclass(frozen=True)
class Metric:
    """一个指标：名字、方向、需要的输入、算它的函数。"""

    name: str
    direction: str
    needs: tuple[str, ...]
    fn: Callable[[dict], float]

    def applicable(self, row: dict) -> bool:
        """这条数据够不够算它。**不够就是 `None`，不许补 0。**"""
        return all(row.get(k) is not None for k in self.needs)


REGISTRY: dict[str, Metric] = {}


def register(metric: Metric) -> Metric:
    if metric.direction not in DIRECTIONS:
        raise ValueError(f"{metric.name} 的方向不合法：{metric.direction}")
    if metric.name in REGISTRY:
        # 静默覆盖是这一族里最早的一种「两个东西变成一个」。
        raise ValueError(f"指标重名：{metric.name}")
    REGISTRY[metric.name] = metric
    return metric


@dataclass(frozen=True)
class Cell:
    """一格读数：某条题上的某个指标。`value=None` ＝ 测不了。"""

    cid: str
    metric: str
    value: float | None


def _norm(text: str) -> str:
    return " ".join(str(text).strip().lower().split())


def _exact(row: dict) -> float:
    return 1.0 if _norm(row["output"]) == _norm(row["reference"]) else 0.0


def _contains(row: dict) -> float:
    return 1.0 if _norm(row["reference"]) in _norm(row["output"]) else 0.0


def _refusal(row: dict) -> float:
    """拒答题的两头都对才算：该拒的拒了，不该拒的没拒。"""
    should = _norm(row["reference"]) == _norm("（无法回答）")
    did = "无法回答" in str(row["output"])
    return 1.0 if should == did else 0.0


def _has_citation(row: dict) -> float:
    return 1.0 if row.get("contexts") else 0.0


def _length_ok(row: dict) -> float:
    """篇幅合规：≤ 120 字。它只需要输出——**不需要参考答案**。"""
    return 1.0 if len(str(row["output"])) <= 120 else 0.0


def build_registry() -> dict[str, Metric]:
    """建表。**顺序也是口径**：它决定输出块里那几列从左到右怎么排。"""
    REGISTRY.clear()
    register(Metric("exact_match", HIGHER, ("output", "reference"), _exact))
    register(Metric("contains", HIGHER, ("output", "reference"), _contains))
    register(Metric("refusal", HIGHER, ("output", "reference"), _refusal))
    register(Metric("has_citation", HIGHER, ("output", "contexts"), _has_citation))
    register(Metric("length_ok", HIGHER, ("output",), _length_ok))
    return dict(REGISTRY)


def evaluate(suite, rows: dict[str, dict]) -> list[Cell]:
    """把一批跑记录算成一格格读数。

    `rows`：`{cid: {"output":…, "contexts":…}}`——它模拟的是**跑了一遍之后留下的记录**。
    本树里这份记录是**造出来的**（离线、不要密钥），所以它能量指标体系与门，
    **量不了模型质量**——这一条写在正文的边界里，不写成结论。
    """
    cells: list[Cell] = []
    for case in sorted(suite.cases, key=lambda c: c.cid):
        row = dict(rows.get(case.cid, {}))
        row.setdefault("reference", case.reference)
        for metric in REGISTRY.values():
            cells.append(Cell(case.cid, metric.name,
                              metric.fn(row) if metric.applicable(row) else None))
    return cells


def measured(cells: list[Cell], metric: str) -> list[Cell]:
    return [c for c in cells if c.metric == metric and c.value is not None]


def aggregate(cells: list[Cell], *, as_zero: bool = False) -> dict[str, float | None]:
    """按指标聚合。

    `as_zero=True` 时把「测不了」当成 0：分母变成**全部格数**，分数因此变低——
    而低多少完全取决于「有多少格测不了」，与系统好坏无关。
    """
    out: dict[str, float | None] = {}
    for metric in REGISTRY.values():
        mine = [c for c in cells if c.metric == metric.name]
        if as_zero:
            values = [0.0 if c.value is None else c.value for c in mine]
        else:
            values = [c.value for c in mine if c.value is not None]
        out[metric.name] = (sum(values) / len(values)) if values else None
    return out


def coverage(cells: list[Cell]) -> dict[str, dict[str, int]]:
    """每个指标：算出来几格、测不了几格。**这两个数要一起报。**"""
    out: dict[str, dict[str, int]] = {}
    for metric in REGISTRY.values():
        mine = [c for c in cells if c.metric == metric.name]
        done = sum(1 for c in mine if c.value is not None)
        out[metric.name] = {"measured": done, "unmeasured": len(mine) - done}
    return out
