"""容量：**排队不是线性的——利用率从七成到九成，等待从 3 倍涨到 10 倍。**

这一块量的是 8.5 第四个反直觉的事实：**「再加一点流量就崩」这个感觉是对的，
而它不是「多 10% 流量」，是「利用率过了一条线」。** 一个单服务台的近似足够说明它：

    wait_factor(ρ) ≈ 1 / (1 − ρ)

ρ ＝ 0.5 时等待是服务时间的 2 倍，ρ ＝ 0.9 时是 10 倍，ρ ＝ 0.95 时是 20 倍——
**后两档之间只差 5 个百分点的利用率，等待涨了一倍。** 这条曲线就是「按均值买机器」的代价：
均值那一档看起来余量很大，而**峰值那一天它落在曲线的陡坡上**。

四条公认事实撑起这一块（出处见 `REFERENCES.md` 第 8 篇）：

1. **可观测性有三个信号，而容量要的是它们的「绝对值」**：指标（数字、全量）、
   日志（事件）、链路（因果、采样）——那一套把三者的分工写得很清楚；
   而容量规划要的是「峰值那一刻有多少个数字同时在涨」，所以它要的是**采样策略与保留窗口**，
   不是一个面板。
2. **压测要压过拐点**：延迟与错误率在某个并发处开始非线性上升，**那一点才是容量**——
   压测停在拐点之前，量到的是「还没用上」。
3. **预留买的是时间**：N+1 与「一条经验线」都不是物理量，它们买的是
   「一台机器挂了之后，剩下的还能不能撑到有人接手」。
4. **增长按月看，不要按年看**：年化在小基数上会放大误差，而容量是季度决定。

这一块与 `slo` 的分界：**它量「装得下多少」，`slo` 量「服务得好不好」**；
而两者的接口是那张排队表——**`slo` 里的 P95 会在利用率过线之后自己变坏，
不用等错误率上升**（这是 8.5 的一条边界）。
"""

from __future__ import annotations

import math

#: 利用率 × 排队放大 × 这一档的现实形态。**第二列是模型，第三列是它的意思**。
UTILIZATION: tuple[tuple[float, float, str], ...] = (
    (0.50, 2.0, "余量充足，扩容窗口很宽"),
    (0.70, 3.3, "**经验线附近**：再往上，等待时间开始跑得比流量快"),
    (0.80, 5.0, "余量只剩一倍：一次热点或一台机器挂掉就越线"),
    (0.90, 10.0, "**峰值形态**：多 10% 流量，等待翻一倍"),
    (0.95, 20.0, "几乎只能靠限流保命（配额那一套在这里生效）"),
)

#: 流量形状：日峰值／均值比、月度增长。**两个数都要报**——只报一个会得出相反的结论。
PEAK_RATIO = 3.2
MONTHLY_GROWTH = 0.12
#: 单机能扛的请求速率（每秒）与日均速率。
PER_NODE_RPS = 100
MEAN_RPS = 120


def wait_factor(rho: float) -> float:
    """单服务台近似的等待放大。**它是一个模型，不是承诺**——它量的是形状（陡坡在哪）。"""
    if rho >= 1.0:
        return float("inf")
    return round(1 / (1 - rho), 1)


def shown_wait(rho: float) -> str:
    """把等待放大写成能印在表里的样子：**过载就是过载，不给它一个数**。"""
    return "过载（∞）" if math.isinf(wait_factor(rho)) else f"{wait_factor(rho):g}×"


def utilization_table() -> tuple[tuple[str, str, str], ...]:
    return tuple((f"{rho * 100:.0f}%", shown_wait(rho), note) for rho, _, note in UTILIZATION)


def nodes_for(rps: float, headroom: float = 0.0, per_node: int = PER_NODE_RPS) -> int:
    """按 `rps` 加 `headroom` 买几台。**向上取整**——「3.2 台」在采购单上不存在。"""
    return math.ceil(rps * (1 + headroom) / per_node)


def rho(rps: float, nodes: int) -> float:
    return rps / (nodes * PER_NODE_RPS)


def plan_table() -> tuple[tuple[str, str, str, str, str], ...]:
    """三种买法 × 五栏。**第四、五列才是这张表要讲的事**。

    三种买法的差别不在成本，而在**峰值那一天落在排队曲线的哪一档**；
    而第五列（挂掉一台之后）是「预留」这个词的全部内容。
    """
    peak = MEAN_RPS * PEAK_RATIO
    rows = (
        ("按日均买", nodes_for(MEAN_RPS), "**峰值那天直接过载（ρ > 1）：队列无上限地涨**"),
        ("按峰值买（不留余量）", nodes_for(peak), "峰值刚好装得下；**而一台机器挂掉就过载**"),
        ("按峰值 ＋ 50% 预留", nodes_for(peak, 0.50), "峰值仍在经验线以内；**一台挂掉也还在线上**"),
    )
    out = []
    for name, nodes, note in rows:
        out.append((
            name,
            f"{nodes} 台",
            f"{rho(peak, nodes) * 100:.0f}%",
            shown_wait(rho(peak, nodes)),
            f"挂一台后 {rho(peak, nodes - 1) * 100:.0f}%／"
            f"{shown_wait(rho(peak, nodes - 1))}——{note}",
        ))
    return tuple(out)


def peak_rps() -> float:
    """日峰值那一天的速率（日均 × 峰值比）。"""
    return MEAN_RPS * PEAK_RATIO


#: 压测的四个档：并发、P95、错误率、这一段说明什么。
LOAD_TEST: tuple[tuple[int, float, float, str], ...] = (
    (50, 120, 0.0, "线性段：**延迟几乎不动**，加并发就加吞吐"),
    (200, 180, 0.1, "仍然线性，但斜率开始变了"),
    (400, 620, 0.8, "**拐点在这一档附近**：延迟涨 3 倍而错误率开始出现"),
    (800, 2_900, 14.0, "过载段：**再加并发只会让错误率涨**，吞吐反而掉"),
)


def load_test_table() -> tuple[tuple[str, str, str, str], ...]:
    """压测三个数 ＋ 一句「这一段说明什么」。**判据是「压过拐点」**，不是「压到多少并发」。"""
    return tuple(
        (f"{conc}", f"{p95:.0f} ms", f"{err:.1f}%", note)
        for conc, p95, err, note in LOAD_TEST
    )


def quarters_to_grow(times: float = 2.0, monthly: float = MONTHLY_GROWTH) -> int:
    """按月度增长率，多久需要翻倍（**用来定下一次评估容量的时间点**）。"""
    q = 0
    while (1 + monthly) ** (q * 3) < times:
        q += 1
    return q
