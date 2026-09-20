"""告警：**「响了没有」不是判据，「该不该响」才是。**

这一块量的是 8.5 第二个反直觉的事实：**一个按阈值响的告警，对「慢烧」是完全失明的。**
两种形态摆在同一个 SLO 下比一比就清楚了（预算率 ＝ 1 − SLO ＝ 0.05%）：

| 现场 | 按阈值（5 分钟错误率 > 1%） | 按燃尽率（长窗 ＋ 短窗） | 谁对 |
| --- | --- | --- | --- |
| 快烧：5 分钟错误率 10%，十分钟后恢复 | 响 1 次 | 响（1 小时窗口烧掉 2% 预算） | **都对** |
| 慢烧：错误率 0.1% 持续 3 天 | **一次都不响** | 响（燃尽率 2×，3 天烧掉 20% 预算） | 只有燃尽率对 |
| 单点：一条请求 500，5 分钟错误率 0.002% | 不响 | 不响 | **都对**（这是噪声） |

三条官方事实撑起这一块（出处见 `REFERENCES.md` 第 8 篇）：

1. **按症状告警，不按原因**：用户感受到的那件事（请求失败、变慢）才是该叫醒人的东西；
   而「CPU 高」「队列长」是原因——它们更适合进面板与工单。
2. **燃尽率是「预算花的速率」**：燃尽率 14.4 的意思是「按这个速度，1 小时烧掉 2% 的预算」；
   官方那套工作法给的三档是 **14.4（1 小时／5 分钟）／6（6 小时／30 分钟）／1（3 天／6 小时）**，
   对应 2%／5%／10% 的预算，而它们的处置**不一样**（立刻叫醒／开单／进排期）。
3. **每一条告警都在花一个班的注意力**：叫醒人的那一条必须可行动——
   「不可行动也要响」是告警系统最常见的退化成噪声的方式。

**这一块还要结一笔旧账**：5.7 台账里「连接管理：活跃连接集合 ＋ 广播 ＋ 断开清理 ＋ 当前连接数」
在 8.3 定稿时**一半领走（断开清理与当前连接数）、广播改指 8.5**——
它落在这一段的最后一小节：**状态页的广播**。四个数就是 5.7 那一行点名的四个：
活跃连接集合、广播的出口字节、断开清理、当前连接数。
"""

from __future__ import annotations

from dataclasses import dataclass

#: 三档多窗口多燃尽率（官方那套工作法的形状）：长窗 ＋ 短窗 ＋ 燃尽率 ＋ 处置。
BURN_WINDOWS: tuple[tuple[str, str, float, str, str], ...] = (
    ("1 小时", "5 分钟", 14.4, "2% 的预算在这 1 小时里烧掉", "**立刻叫醒值班**——这是「快烧」"),
    ("6 小时", "30 分钟", 6.0, "5% 在 6 小时里烧掉", "开一张工单，白天处理"),
    ("3 天", "6 小时", 1.0, "10% 在 3 天里烧掉", "进排期；它抓的是**慢慢变坏**"),
)

#: 三个现场 × 两种形态。**这张表是这一节的主读数**：只有第二行把它们分开。
SCENARIOS: tuple[tuple[str, float, str, str, str], ...] = (
    ("快烧：5 分钟错误率 10%，十分钟后恢复", 0.10, "响 1 次", "响（1 小时窗口烧掉 2% 预算）", "都对"),
    ("慢烧：错误率 0.1% 持续 3 天", 0.001, "**一次都不响**（0.1% 没到 1% 那条线）",
     "响（燃尽率 2×，3 天烧掉 20% 预算）", "**只有燃尽率对**"),
    ("单点：一条 500，5 分钟错误率 0.002%", 0.00002, "不响", "不响", "都对——这是噪声"),
)

#: 预算率（1 − SLO）。燃尽率 ＝ 错误率 ÷ 这一条。
BUDGET_RATE = 0.0005


def burn_rate(error_rate: float) -> float:
    """燃尽率：**「按这个速度，多久烧完一个月的预算」**。错误率 1% 时是 20×。"""
    return round(error_rate / BUDGET_RATE, 1)


def shown_burn(error_rate: float) -> str:
    """燃尽率写成能印的样子：**比 0.1× 还慢的不给它一个数**（那是噪声，不是速率）。"""
    b = burn_rate(error_rate)
    return f"{b:g}×" if b >= 0.1 else "< 0.1×（噪声）"


def burn_table() -> tuple[tuple[str, str, str, str, str, str], ...]:
    """三个现场 × 五栏：错误率、燃尽率、两种形态各答什么、谁对。"""
    out = []
    for name, rate, threshold, burn, verdict in SCENARIOS:
        out.append((name, f"{rate * 100:.3f}%", shown_burn(rate), threshold, burn, verdict))
    return tuple(out)


def burn_window_table() -> tuple[tuple[str, str, str, str, str], ...]:
    """三档窗口 × 四栏。**处置那一栏才是燃尽率的分层所在**：三种速度对应三种打扰方式。"""
    return tuple(
        (long_w, short_w, f"{rate:g}×", budget, action)
        for long_w, short_w, rate, budget, action in BURN_WINDOWS
    )


#: 一个月的告警账。三个数：发出多少、其中多少次不需要动作、每班几次。
ALERTS = (340, 211, 180)          # 发出 ／ 无需动作 ／ 班次


@dataclass(frozen=True)
class Noise:
    """噪声账：**「三次里有一次是狼来了」这句话是可算的**。"""

    sent: int
    no_action: int
    shifts: int

    @property
    def noise_ratio(self) -> float:
        return round(self.no_action / self.sent * 100, 1)

    @property
    def per_shift(self) -> float:
        return round(self.sent / self.shifts, 2)

    @property
    def actionable_per_shift(self) -> float:
        return round((self.sent - self.no_action) / self.shifts, 2)


def noise() -> Noise:
    return Noise(*ALERTS)


#: 状态页广播：四个数就是 5.7 那一行点名的四个（活跃连接集合／广播／断开清理／当前连接数）。
BROADCAST_PAYLOAD = 1_200        # 一条状态更新的字节数
BROADCAST_PER_CONN_MS = 0.02     # 一条连接的写出耗时
#: 连接数 × 三问。第三列与第四列是**断开清理存在的理由**。
CONNECTIONS: tuple[tuple[str, int, str, str], ...] = (
    ("小规模", 1, "一条广播 0.02 ms", "断开就是断开，集合自然变小"),
    ("中规模", 100, "2.0 ms ＋ 120 KB", "要按写超时清理——否则**一条慢连接会拖住整轮广播**"),
    ("大规模", 1_000, "20 ms ＋ 1.2 MB", "**这一轮广播已经值得单独跑一个任务**；而且必须先快照连接集合"),
    ("没清理的那一天", 6_000, "120 ms ＋ 7.2 MB", "1,000 条连接重连 6 次而集合只增不减——**内存事故与广播风暴是同一件事**"),
)


def _size(nbytes: int) -> str:
    """字节数写成能印的样子（十进制的 KB／MB——与正文里那句「1.2 MB」同一口径）。"""
    if nbytes >= 1_000_000:
        return f"{nbytes / 1_000_000:.1f} MB"
    if nbytes >= 10_000:
        return f"{nbytes / 1_000:.0f} KB"
    if nbytes >= 1_000:
        return f"{nbytes / 1_000:.1f} KB"
    return f"{nbytes} B"


def broadcast_table() -> tuple[tuple[str, int, str, str, str], ...]:
    """广播的四栏：连接数、出口字节、一轮耗时、断开清理的判据。"""
    out = []
    for name, conns, _, why in CONNECTIONS:
        size = BROADCAST_PAYLOAD * conns
        ms = BROADCAST_PER_CONN_MS * conns
        out.append((
            name,
            conns,
            _size(size),
            f"{ms:.2f} ms",
            why,
        ))
    return tuple(out)


#: 一轮广播里两种速度的连接：(写一条更新的耗时 ms, 条数)。0.02 是正常；
#: 200 是「对面已经不读了而 TCP 还没告诉内核」——**它只能靠写超时发现**。
CONN_SPEEDS: tuple[tuple[float, int], ...] = ((0.02, 997), (200.0, 3))
WRITE_TIMEOUT_MS = 50.0


def cleanup() -> tuple[int, int, float, str]:
    """断开清理：一轮广播里慢连接占了多少时间、有几条会被清掉。

    返回 `(被清掉的条数, 留下的条数, 那些慢连接占一轮的百分比, 为什么)`。
    **清理的判据是「写」而不是「读」**（对面不读这件事，在内核里可能要下一轮才发现），
    而这条读数的重点在第三个那个百分比：**1,000 条里 3 条慢连接能吃掉一轮广播的时间**。
    """
    slow = sum(n for ms, n in CONN_SPEEDS if ms > WRITE_TIMEOUT_MS)
    kept = sum(n for ms, n in CONN_SPEEDS if ms <= WRITE_TIMEOUT_MS)
    total = sum(ms * n for ms, n in CONN_SPEEDS)
    slow_ms = sum(ms * n for ms, n in CONN_SPEEDS if ms > WRITE_TIMEOUT_MS)
    share = slow_ms / total * 100
    why = (f"慢连接共 {slow} 条、占一轮 {share:.1f}% 的时间——"
           "**不清理的话，整轮广播的耗时由最慢的那几条决定**")
    return slow, kept, round(share, 1), why
