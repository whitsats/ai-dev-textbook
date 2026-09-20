"""SLO：**它不是一句「我们保证 99.9%」，而是四个数加一条「怎么花」的规矩。**

这一块量的是 8.5 第一个反直觉的事实：**SLO 的难点不在定那个数，在数不出来。**
四个数是：**SLI**（拿什么量）、**SLO**（量到多少算合格）、**错误预算**（1 − SLO 那一段能花多少）、
**达成率**（这一段时间实际是多少）。而四者里最容易坏的是第一个——一个数不出来的 SLI
会让后面三个数全部退化成一句口号：

| 常见的 SLI | 它数的是 | **它抓不到什么** |
| --- | --- | --- |
| 可用性（非 5xx 的比例） | 服务端自己报的错 | **超时**（客户端放弃了，服务端还在慢慢算）、**返回 200 而内容是错的** |
| 延迟（P95 < 2 秒的比例） | 快的那 95% | 慢的那 5% 有多慢；而用户正好落在那 5% 里时他体会到的就是「挂了」 |
| 正确性（答案对不对） | 业务结果（下单成功、引用确实出自那篇文档） | 它通常要另一套数据源，所以最容易被跳过 |
| 新鲜度（数据多旧） | 索引与缓存的时间 | 它不在请求链路上，所以任何可用性 SLO 都看不见它 |

三条纪律（与前四段同源）：

1. **SLI 必须数「用户感受到的那件事」**：服务端 200 不等于用户拿到东西（超时、空结果、
   答非所问都是失败）；反过来，一条后台任务的告警不该进这个数。
2. **两个数必须一起报**：预算用了多少与还剩多少、达成率与它覆盖的窗口、
   事故条数与事故时长——只报一个，另一半就会变成一句听起来对的话。
3. **SLO 是产品决定，不是技术参数**：四个 9 与五个 9 之间不是「更努力」，
   而是「每次发布要多停多久」——它决定的是**错误预算怎么花**，所以它必须在 8.5.2 那张表上谈。

这一块与 `alert` 的分界：**它算「这一段时间花了多少预算」，`alert` 管「烧得快不快、
要不要叫醒人」**；与 `capacity` 的分界：它量「服务得好不好」，`capacity` 量「装得下多少」。
"""

from __future__ import annotations

from dataclasses import dataclass

#: 四个 9 的档位与它们各自的月度停机时长（30 天 ＝ 43,200 分钟）。
#: 第三列是**按「允许的累计不可用」算出来的**，不是抄的——它是「预算」这个词的口语版。
NINES: tuple[tuple[str, float, str], ...] = (
    ("三个 9", 0.999, "43.2 分钟／月"),
    ("三个半 9", 0.9995, "21.6 分钟／月"),
    ("四个 9", 0.9999, "4.32 分钟／月"),
    ("五个 9", 0.99999, "26 秒／月"),
)

#: 四种 SLI × 三问。第三列是**它抓不到什么**——四种里没有一种能单独把「用户没事」这件事说全。
SLIS: tuple[tuple[str, str, str, str], ...] = (
    ("可用性", "非 5xx 的比例",
     "**超时**与**返回 200 而内容错**",
     "最快能上、最容易自动化；**代价是它只看得见服务端自己承认的错误**"),
    ("延迟", "P95 低于某个值的比例",
     "慢的那 5% 有多慢（而用户就可能在那 5% 里）",
     "它与可用性**不同向**：加了重试能救可用性，却把延迟推高"),
    ("正确性", "业务结果的比例（下单成功、引用确实出自那篇文档）",
     "它要另一套数据源，所以**最容易被跳过**",
     "它才是用户真正在意的那个；而它通常不能在网关那一层数出来"),
    ("新鲜度", "索引／缓存数据的时间",
     "它不在请求链路上",
     "RAG 类系统特有的一种：一条**全绿**的接口可以整晚答旧文档"),
)

#: 一个月：总请求、四次事故各自贡献的失败数。**第三列是「监控能不能看见它」**。
MONTH_REQUESTS = 10_000_000
SLO = 0.9995                      # 三个半 9
INCIDENTS: tuple[tuple[str, int, str], ...] = (
    ("全站 5xx 12 分钟（200 rps）", 2_400, "看得见：它就是 5xx"),
    ("上游 30 秒超时、客户端 10 秒放弃", 1_600, "**多数可用性 SLI 看不见它**——连接是被客户端关掉的，服务端还没报错"),
    ("检索返回旧文档（200、延迟正常）", 0, "**任何可用性 SLO 都看不见它**：它是正确性／新鲜度那一档的事"),
    ("零散失败（重试用尽）", 321, "看得见：它就是 5xx"),
)

#: 一次事故的四个时刻：它在做什么、时长（分钟）、这一段的错误率。
#: **这一张表量的是「事故期间烧掉多少预算」**，而它的算法只有一行：失败数 ÷ 允许失败数。
INCIDENT_TIMELINE: tuple[tuple[str, str, int, float], ...] = (
    ("① 发现（告警响之前）", "用户在撞，而没人知道", 6, 1.00),
    ("② 确认（哪一层坏了）", "面板与手册找那一层", 4, 1.00),
    ("③ 缓解（回滚金丝雀）", "错误率开始降下来", 9, 0.30),
    ("④ 复原（补数据、重建缓存）", "错误率回到常态", 11, 0.02),
)

#: 事故场景的流量：**均值 2 rps**（一个月的请求数由它算出）。
INCIDENT_RPS = 2.0


@dataclass(frozen=True)
class Budget:
    """一个窗口的错误预算：总量、已用、剩余、达成率。**四个数一起报**。"""

    total_requests: int
    failures: int

    @property
    def allowed(self) -> int:
        """允许的失败数 ＝ (1 − SLO) × 总请求。**它是「能坏几次」，不是「坏了百分之几」**。"""
        return int(round((1 - SLO) * self.total_requests))

    @property
    def used(self) -> float:
        return round(self.failures / self.allowed * 100, 2)

    @property
    def remaining(self) -> int:
        return max(0, self.allowed - self.failures)

    @property
    def availability(self) -> float:
        return round(1 - self.failures / self.total_requests, 6)


def timeline_table() -> tuple[tuple[str, str, str, str, str, str, str], ...]:
    """事故四个时刻 × 六栏。**这是「值班那半小时烧掉多少」的算法**，不是一段叙述。"""
    b = month_window()
    out = []
    for name, what, minutes, rate in INCIDENT_TIMELINE:
        reqs = int(round(minutes * 60 * INCIDENT_RPS))
        fails = int(round(reqs * rate))
        out.append((name, what, f"{minutes} 分钟", f"{rate * 100:.0f}%",
                    f"{reqs:,}", f"{fails:,}", f"{fails / b.allowed * 100:.1f}%"))
    return tuple(out)


def timeline_totals() -> tuple[int, int, float, str]:
    """`(总分钟, 总失败数, 占预算, 一句话)`。

    **前三段（发现 ＋ 确认）占了一半预算，而它们一条请求都没救回来**——
    这就是「先把告警调准、把面板做对」比「把回滚做快」更值钱的那个数。
    """
    b = month_window()
    fails = sum(int(round(m * 60 * INCIDENT_RPS * r)) for _, _, m, r in INCIDENT_TIMELINE)
    head = sum(int(round(m * 60 * INCIDENT_RPS * r)) for _, _, m, r in INCIDENT_TIMELINE[:2])
    minutes = sum(m for _, _, m, _ in INCIDENT_TIMELINE)
    why = (f"头两段（发现 ＋ 确认）占 {head / b.allowed * 100:.1f}% 的预算，"
           "而它们**一条请求都没救回来**——这就是「先把告警调准、把面板做对」值钱的地方")
    return minutes, fails, round(fails / b.allowed * 100, 1), why


def slow_burn_same_traffic(days: int = 3, rate: float = 0.001) -> tuple[int, float]:
    """同一份流量下的慢烧：`(失败数, 占预算)`。**它和上面那半小时是可比的。**"""
    b = month_window()
    fails = int(round(days * 24 * 3600 * INCIDENT_RPS * rate))
    return fails, round(fails / b.allowed * 100, 1)


def budget(failures: int | None = None) -> Budget:
    """本月的预算。不传失败数就用 `INCIDENTS` 那四次相加。"""
    if failures is None:
        failures = sum(n for _, n, _ in INCIDENTS)
    return Budget(MONTH_REQUESTS, failures)


def month_window(rps: float = INCIDENT_RPS) -> Budget:
    """按 `rps` 算一个月的请求数与允许失败数。

    **同一个 SLO，流量不同，预算的绝对值就不同**：同一个 99.95%，一个月 518 万条请求
    允许失败 2,592 条，而 1,000 万条允许 5,000 条（`MONTH_REQUESTS` 那一档）。
    所以「错误预算」不是一句话，它是**流量 × 时间 × (1 − SLO)**。
    """
    return Budget(int(round(rps * 30 * 24 * 3600)), 0)


def incident_table() -> tuple[tuple[str, str, str, str], ...]:
    """四次事故 × 四栏：失败数、占预算、**这一格监控看不看得见**。"""
    b = budget()
    out = []
    for name, n, seen in INCIDENTS:
        out.append((
            name,
            f"{n:,}",
            f"{n / b.allowed * 100:.1f}%",
            seen,
        ))
    return tuple(out)


#: 预算烧完的三种处置。第三列是判据，第四列是代价——**没有免费的那一种**。
DECISIONS: tuple[tuple[str, str, str], ...] = (
    ("冻结发布（只修问题，不加功能）",
     "预算烧到 100% 时唯一能「还债」的动作：**它把「少改」写成了规矩**",
     "它会让一条已经排好的发布线停下来，而这件事要在事前就跟业务方谈好"),
    ("降级非关键功能（先保住核心链路）",
     "有明确「非关键功能」清单时最划算：**它把不可用换成了「少一点」**",
     "它要那张清单真的存在、且真的能单独关——没有清单的降级会在事故当天现场发明"),
    ("接受风险并写下来（不改判据）",
     "**有时是对的**：预算是拿来花的，不是拿来零的（花在「这次值得」上）",
     "代价是它必须**被写下来**（谁决定、为什么、什么时候复看）——否则它退化成「忽略」"),
)
