"""门：一个判据要说清五件事，缺一件它就会变成装饰。

1. **方向**——越大越好还是越小越好。方向写反，门就变成反向的：一切正常时报警，
   真退步时放行（`Gate.direction`）；
2. **基线**——「比谁」的那一个数（`Gate.baseline`）；
3. **抖动带**——**基线本身在抖**：同一份配置跑两遍就不是同一个数。
   所以容差不是 0，是**多跑几遍量出来的极差**（`noise_band()`）；
4. **分辨率**——n 条样本上看得见的最小差异是 `1/n`（`resolution()`）。
   n=24 时它是 0.0417：比它小的变化**不是「变好了」，是「看不见」**；
5. **0 条怎么办**——这一条最容易被漏。空集跑完，一次失败都没有，
   于是一个只看「有没有失败」的脚本会**绿**。所以门有三档「不下结论」：

   | 判定 | 什么时候 | 它是不是「通过」 |
   | --- | --- | --- |
   | `empty` | 一条都没跑 | **不是**——这是故障，不是通过 |
   | `underpowered` | 跑的条数少于 `min_cases` | 不是——样本不够，说什么都是运气 |
   | `too_coarse` | 变化真的存在，但小于 `1/n` | 不是——看不见不等于没变 |

   pytest 自己把这件事写成了退出码：`5` 是「一条测试都没收集到」，
   而它是一个**非零**退出码——「没跑」与「跑了且全过」在它那里是两件事。

`diff()` 是另一件必须分开做的事：**聚合级的 diff 会互相抵消**。
三条翻好、三条翻坏，总分一模一样，而报表上写着「无变化」。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .metrics import HIGHER, LOWER

PASS = "pass"
REGRESS = "regress"
EMPTY = "empty"
UNDERPOWERED = "underpowered"
TOO_COARSE = "too_coarse"

#: 三档「不下结论」＋ 一档退步——它们都不是「通过」。
NOT_PASS = (REGRESS, EMPTY, UNDERPOWERED, TOO_COARSE)


def resolution(n: int) -> float:
    """n 条样本上的最小可分辨差异：1/n。

    它是**读数的一部分**，不是注释：「0.02 的退步」在 24 条上根本不存在。
    """
    if n <= 0:
        raise ValueError("n 必须为正（0 条的分辨率没有定义——那正是 empty 那一档）")
    return 1.0 / n


def detectable(n: int, delta: float) -> bool:
    """这个变化量在 n 条上看得见吗（边界算看得见）。"""
    return abs(delta) >= resolution(n) - 1e-12


def noise_band(runs: list[float]) -> float:
    """抖动带：同一份配置多跑几遍的**极差**。

    为什么不是标准差：门的判据是「这一趟比基线差」——一次比较的对手是**极值**，
    所以容差要用极差量。用标准差会得到一个「理论上一半的时候会误报」的门。
    """
    if not runs:
        raise ValueError("没有跑记录，量不出抖动")
    return max(runs) - min(runs)


@dataclass(frozen=True)
class Gate:
    """一道门。"""

    metric: str
    direction: str
    baseline: float | None
    noise: float = 0.0
    min_cases: int = 8

    def __post_init__(self) -> None:
        if self.direction not in (HIGHER, LOWER):
            raise ValueError(f"{self.metric} 的方向不合法：{self.direction}")
        if self.noise < 0:
            raise ValueError("抖动带不能是负数")

    def margin(self) -> float:
        """判据的门槛＝抖动带（不是 0）：比它小的差是噪声，不是退步。"""
        return self.noise


def judge(gate: Gate, value: float | None, n: int) -> str:
    """判一档。`n` 是**这一趟真跑了几条**，不是数据集有几条。"""
    if n <= 0:
        return EMPTY
    if value is None:
        # 指标本身都没算出来（比如全部缺参考答案）——它同样不是「通过」。
        return EMPTY
    if n < gate.min_cases:
        return UNDERPOWERED
    if gate.baseline is None:
        return PASS                    # 第一次跑，只立基线，不下结论
    raw = value - gate.baseline
    delta = raw if gate.direction == HIGHER else -raw
    if delta < -gate.margin() and abs(delta) > 1e-12:
        return REGRESS if detectable(n, delta) else TOO_COARSE
    if abs(delta) > 1e-12 and not detectable(n, delta):
        return TOO_COARSE
    return PASS


@dataclass(frozen=True)
class Report:
    """一次跑的记录：条目 → 过没过。**聚合的那个数由它算出来，不单独存。**"""

    run_id: str
    verdicts: dict[str, int] = field(default_factory=dict)

    def total(self) -> float:
        if not self.verdicts:
            return 0.0
        return sum(self.verdicts.values()) / len(self.verdicts)


def diff(before: Report, after: Report) -> dict[str, list[str]]:
    """**条目级** diff。

    为什么必须有它：聚合级的 diff 会在两条相反的改动上抵消——
    三条翻好、三条翻坏，总分一模一样。所以「总分没动」这句话不能由总分自己来说。
    """
    improved = sorted(c for c, v in before.verdicts.items()
                      if v == 0 and after.verdicts.get(c) == 1)
    regressed = sorted(c for c, v in before.verdicts.items()
                       if v == 1 and after.verdicts.get(c) == 0)
    return {
        "improved": improved,
        "regressed": regressed,
        "added": sorted(c for c in after.verdicts if c not in before.verdicts),
        "removed": sorted(c for c in before.verdicts if c not in after.verdicts),
    }


def offsetting(before: Report, after: Report, *, tol: float = 1e-12) -> bool:
    """总分一样，而条目**真的翻面了**——聚合级 diff 看不见的那一种变化。"""
    same = abs(after.total() - before.total()) <= tol
    flips = diff(before, after)
    return same and bool(flips["improved"] or flips["regressed"])


def ci_cost(n: int, per_case_usd: float, *, attempts: int = 1) -> dict[str, float]:
    """CI 里跑一次评测的账。

    它有两个用途，而第二个才是重点：**用条数换分辨率是有价格的**——
    `1/n` 每好一格，账单就跟着涨一格。所以「多跑几条」不是免费的谨慎，
    它是一个要跟别的改动比价的改动。
    """
    if attempts < 1:
        raise ValueError("attempts 至少是 1")
    return {"cases": float(n), "attempts": float(attempts),
            "usd": n * per_case_usd * attempts,
            "resolution": resolution(n)}
