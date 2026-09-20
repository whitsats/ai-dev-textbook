"""配额：**「能用多少」有五种量法，而它们给出的答案差两个数量级。**

这一块量的是 8.4 第二个反直觉的事实：**「按请求数限流」是最省事的一种，
也是最容易被绕开的一种**——官方风险清单里那条被绕开的示例就是**一次 HTTP 请求装 999 个操作**
（GraphQL 批处理），而它按请求数只算作「一次」。所以真正的问题不是「要不要限」，
而是**限什么量**：

| 量 | 它抓住什么 | 它漏掉什么 |
| --- | --- | --- |
| 请求数 / 秒 | 脚本刷接口（最常见的那一类） | 一次请求里的贵操作 |
| 并发（同时在进行中） | CPU 密集型端点的资源争抢 | 便宜而高频的调用 |
| 词元（进 ＋ 出） | 「长回答」这一类 | 短而密的调用、失败重试 |
| 成本 | **唯一与账单同名的那个量** | 它滞后——要等用量出来才知道 |

四条官方事实撑起这一块（出处见 `REFERENCES.md` 第 8 篇）：

1. **限流器与负载卸载是两件事**：限流器按**用户**决策，负载卸载按**系统整体状态**决策
   （事故中保住核心请求）；而**并发限制器**那一句原文说得很直白——它管的是
   「同一时刻最多 20 条在进行中」，用来治 CPU 密集型端点的资源争抢，
   且「把它调得比速率限制器更常拒绝是完全合理的」。
2. **超限的答复有标准形状**：429 ＋ `Retry-After`（单位秒），
   而「通常按 IP，但认证过之后可以按用户或按应用」——**所以「按租户限」这件事
   只有在认得出调用者之后才成立**（那一步是 `tenant` 与 8.4.1 的事）。
3. **滑动窗口与固定窗口的差别不是精度，是边界**：固定窗口在两条窗口的交界处
   可以放行近两倍的量，而**它在曲线上看起来完全正常**（每一秒都没超）。
4. **缺上限本身就是一类风险**（官方把它列在第四位）：判据是「缺任一条上限即脆弱」，
   而那份清单里既有「单页返回条数」也有「第三方服务商的预算上限」
   ——**预算上限是配额表里唯一直接对应钱的格子**。

这一块与 `tenant` 的分界：`tenant` 管「看得到什么」，它管「能用多少」；
与 `billing` 的分界更细：**它管「让不让这次调用进来」，`billing` 管「这次调用花了多少」**
——两者共享同一份用量，但一个在**调用之前**说话，一个在**调用之后**说话。
"""

from __future__ import annotations

from dataclasses import dataclass

#: 一批 12 条调用（夹具）。字段：id、到达时刻（秒）、耗时（秒）、输入词元、输出词元、命中缓存词元。
CALLS: tuple[tuple[str, float, float, int, int, int], ...] = (
    ("c01", 0.0, 2.0, 120, 300, 2_000),
    ("c02", 0.2, 6.0, 350, 1_200, 2_000),
    ("c03", 0.5, 1.0, 80, 60, 0),
    ("c04", 0.9, 4.5, 900, 900, 8_000),
    ("c05", 1.1, 0.8, 40, 25, 0),
    ("c06", 1.4, 7.5, 260, 2_600, 2_000),
    ("c07", 1.8, 1.5, 150, 200, 0),
    ("c08", 2.2, 3.0, 600, 700, 6_000),
    ("c09", 2.5, 0.6, 30, 18, 0),
    ("c10", 2.9, 5.5, 420, 1_500, 2_000),
    ("c11", 3.2, 1.1, 90, 70, 0),
    ("c12", 3.5, 2.4, 200, 350, 2_000),
)

#: 一个租户在一个窗口内的四档上限。**四档给的是同一个租户**——所以「谁先触顶」是可比的问题。
CAPS: dict[str, float] = {
    "并发": 8,          # 同时在进行中的条数
    "请求速率": 5,      # 每秒钟几条
    "词元": 20_000,     # 一个窗口内的进 + 出
    "成本": 0.25,       # 美元，按 `billing.PRICE` 算
}

#: 四种量 × 三问。第一列是量，后三列：它抓住什么／它漏掉什么／超限的答复。
METERS: tuple[tuple[str, str, str, str], ...] = (
    ("请求数 / 秒",
     "脚本刷接口——**官方那条被绕开的示例里，攻击者正是靠它漏过去的**",
     "一次请求里的贵操作；批处理；重试",
     "429 ＋ `Retry-After`（这一档最常拒人，而它拒得最便宜）"),
    ("并发（同一时刻在进行中）",
     "CPU 密集型端点的资源争抢（**长回答占着 worker 不放**）",
     "便宜而高频的调用（它们单个不占资源，加起来才占）",
     "通常**排队**而不是拒：并发这一档说得出「等多久」"),
    ("词元（进 ＋ 出）",
     "「长回答」这一类——**同样一条请求，输出差 40 倍的量**",
     "短而密的调用；失败重试；被缓存吃掉的前缀（那些不该算）",
     "429，而 `Retry-After` 只能按「平均用量的倒数」估"),
    ("成本",
     "**唯一与账单同名的量**——它是租户、财务、销售唯一都认的那一栏",
     "它滞后：要等这一批用完才知道；且它把「贵」和「多」混在一起",
     "**在这里拒人等于拒钱**：好的做法是「到 80% 就告警、到 100% 降级」"),
)


@dataclass(frozen=True)
class Call:
    """一条调用。五个数：到达、耗时、进、出、命中缓存。"""

    id: str
    at: float
    secs: float
    inp: int
    out: int
    cache_read: int

    @property
    def ends(self) -> float:
        return self.at + self.secs


def peak_concurrency(calls: tuple[Call, ...]) -> tuple[int, float]:
    """并发峰值与它的时刻。**注意它数的是「同时在跑」**——一条 7.5 秒的长回答会横跨七条短调用。"""
    events = []
    for c in calls:
        events.append((c.at, 1))
        events.append((c.ends, -1))
    events.sort()
    now = best = 0
    at = 0.0
    for t, delta in events:
        now += delta
        if now > best:
            best, at = now, t
    return best, at


def peak_rate(calls: tuple[Call, ...], window: float = 1.0) -> tuple[int, float]:
    """速率峰值：最密的那 1 秒里有几条（**按到达时刻数**，与耗时无关）。"""
    best, at = 0, 0.0
    for c in calls:
        n = sum(1 for o in calls if c.at <= o.at < c.at + window)
        if n > best:
            best, at = n, c.at
    return best, at


def tokens(calls: tuple[Call, ...]) -> tuple[int, int]:
    """整批的进与出。**两个数必须分开报**——它们的单价差 5 倍。"""
    return sum(c.inp for c in calls), sum(c.out for c in calls)


def usage(calls: tuple[Call, ...]) -> dict[str, float]:
    """同一批调用按四种量各算一遍。**这是这一块的核心读数**：四个数来自同一份现场。"""
    from . import billing

    inp, out = tokens(calls)
    conc, _ = peak_concurrency(calls)
    rate, _ = peak_rate(calls)
    cost = sum(
        billing.charge(c.inp, c.out, cache_read=c.cache_read) for c in calls
    )
    return {"并发": conc, "请求速率": rate, "词元": inp + out, "成本": round(cost, 6)}


def cap_table(calls: tuple[Call, ...]) -> tuple[tuple[str, str, str, str], ...]:
    """四档上限 × 这批用量：用掉多少、**还剩几条**（按这一批的平均用量的倒数算）。

    「还剩几条」这一栏比「用掉多少」有用：**它把两种量放在同一个单位上比**。
    """
    used = usage(calls)
    out = []
    for name, cap in CAPS.items():
        u = used[name]
        pct = u / cap * 100
        per_call = u / len(calls)
        left = int((cap - u) / per_call) if per_call else 0
        out.append((
            name,
            f"{u:g}" if name != "成本" else f"${u:.6f}",
            f"{pct:.1f}%",
            f"{left:,} 条",
        ))
    return tuple(out)


#: 两条长回答（c02 6.0 秒、c06 7.5 秒）。**它们只改一个量**——把并发峰值抬起来。
LONG_CALLS = ("c02", "c06")


def shorten(seconds: float = 2.0) -> tuple[Call, ...]:
    """把两条长回答压到 `seconds` 秒，然后重算四个量。

    **这是这一块最干净的一组对照**：四条读数里只有「并发」会动——
    请求数、词元、成本一个数都不变（因为**词元是与时长无关的**，
    而时长正是并发那一档唯一被乘进去的东西）。
    """
    return tuple(
        Call(c.id, c.at, seconds, c.inp, c.out, c.cache_read)
        if c.id in LONG_CALLS else c
        for c in all_calls()
    )


def all_calls() -> tuple[Call, ...]:
    """把 `CALLS` 摊成对象。**夹具与正文用同一个来源**。"""
    return tuple(Call(*row) for row in CALLS)


#: 同一串到达时刻（10 条，跨过第 10 秒那条窗口边界）：**三种算法给出三种答案**。
ARRIVALS: tuple[float, ...] = (9.60, 9.70, 9.80, 9.90, 9.95, 10.10, 10.20, 10.30, 10.40, 10.50)

#: 三种算法的参数。**限的是同一个东西**：每 10 秒 5 条。
LIMIT = 5
WINDOW = 10.0


def fixed_window(arrivals: tuple[float, ...] = ARRIVALS,
                 limit: int = LIMIT, window: float = WINDOW) -> tuple[bool, ...]:
    """固定窗口计数：窗口从 0 开始切，每个窗口各数各的。**边界就在这里**。"""
    counts: dict[int, int] = {}
    out = []
    for t in arrivals:
        bucket = int(t // window)
        ok = counts.get(bucket, 0) < limit
        if ok:
            counts[bucket] = counts.get(bucket, 0) + 1
        out.append(ok)
    return tuple(out)


def sliding_window(arrivals: tuple[float, ...] = ARRIVALS,
                   limit: int = LIMIT, window: float = WINDOW) -> tuple[bool, ...]:
    """滑动窗口：**每来一条，回头看它前面那 10 秒**（含自己），够不够。"""
    out = []
    kept: list[float] = []
    for t in arrivals:
        kept = [k for k in kept if k > t - window]
        ok = len(kept) < limit
        if ok:
            kept.append(t)
        out.append(ok)
    return tuple(out)


def token_bucket(arrivals: tuple[float, ...] = ARRIVALS, capacity: int = LIMIT,
                 per_second: float = LIMIT / WINDOW) -> tuple[bool, ...]:
    """令牌桶：桶里有几个就放几条，**按时间匀速补**（每秒 `per_second` 个，封顶 `capacity`）。"""
    tokens = float(capacity)
    last = arrivals[0] if arrivals else 0.0
    out = []
    for t in arrivals:
        tokens = min(float(capacity), tokens + (t - last) * per_second)
        last = t
        ok = tokens >= 1.0
        if ok:
            tokens -= 1.0
        out.append(ok)
    return tuple(out)


#: 超限之后能说的三句话。第三列是**它的代价**——三种各有各的代价，没有免费的那种。
REPLIES: tuple[tuple[str, str, str], ...] = (
    ("429 ＋ `Retry-After`",
     "最诚实的一句：**现在不行，N 秒后再来**（单位是秒）",
     "它要调用方**会重试**；不会重试的客户端把它当成一次失败（于是丢了一次真实需求）"),
    ("排队（把请求挂在队列里）",
     "对并发这一档最合适：**说得出「等多久」**，也不用调用方改代码",
     "队列本身要占内存与 worker；**队列没有上限时它就是 8.3 那个背压事故**"),
    ("降级（换小模型／缩短输出／关掉检索）",
     "把「拒」变成「答得差一点」——**产品上最容易被接受的一种**",
     "它要一条**能降级的路径**（同一件事有便宜做法），而这条路径的成本通常不在这一章、在 6.x"),
)

#: 三层配额 × 四问。**顺序不能反**：租户那一层先于用户，用户先于 key。
LIMIT_LAYERS: tuple[tuple[str, str, str, str], ...] = (
    ("租户",
     "月／日（与账单同窗）",
     "它是**合同上写的那个数**，也是 8.4.6 对账时要对上的那一栏",
     "它太粗：一个租户里一个用户刷爆，整个租户一起被限"),
    ("用户",
     "分／时（与人的手速同窗）",
     "它拦住「一个人写了个脚本」——**这一类占线上超限的绝大多数**",
     "一个人可以有多个 key（前端、脚本、CI），所以它拦不住有意的滥用"),
    ("key（API key）",
     "秒（与机器的速率同窗）",
     "它拦住「一个坏掉的循环」——**这一层最先触顶，也最该先触顶**",
     "key 会被共享；而共享的 key 让「谁在滥用」变成一个查不出来的问题"),
)
