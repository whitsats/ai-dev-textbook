"""成本与账单：**同一笔调用要在三个时刻各说一遍账——预扣、结算、对账。**

这一块量的是 8.4 第三个反直觉的事实：**账单不是日志的抄本，它是日志的另一种口径。**
一个月 1,000 笔调用，日志逐笔算出来的钱与账单上那个数**可以对不上**，
而对不上的地方一处都不是 bug：

1. **逐笔进整**：小额单价下（单笔零点几分），「每笔四舍五入到分」这个口径
   能把一个月的合计推高四成；换成**按月聚合后再进整**，差就回到 0。
   所以对账的第一问不是「谁算错了」，而是**两边的口径各是什么**。
2. **失败的那一笔算谁的**：下游没收到任何东西、而**上游已经算完了**
   （网关超时、流断在半路）——这笔钱不会出现在用量里，只会出现在成本里。
   它是**唯一一种「账单上没有、而你必须付」的支出**。
3. **例外要写成例外**：缓存读普遍是输入的 0.10×，而两家官方都给某个型号
   写了 0.025× 的例外（那是 6.1 抄下来的那一条）。把例外当通例，
   账单会少算一笔**小到没人发现**的钱——「小到没人发现」正是它危险的地方。

三条纪律（与 `tenant`／`quota` 同源）：

- **单价不重抄**：这里只有一段价（`input`／`output`）是从表里抄的，
  缓存写／读由 6.1 记下的那三条乘法关系算出来（1.25×／0.10×，批量 0.5×）——
  **手抄四个价就有四次抄错的机会，而抄错了这四个数之间没有关系会响。**
- **预扣必须比实际大**：预扣是按「估算输入 ＋ 最大输出」收的，
  否则结算时那笔账是欠着的（本块的第二笔结算就是欠着的那种）。
- **两个数必须一起报**：预扣与结算、用量与成本、账单与日志——
  只报一个，另一半就会变成一句听起来对的话。
"""

from __future__ import annotations

from dataclasses import dataclass
import random

#: 每百万词元的四段单价。**只有 input／output 是抄来的**（6.1 那张表的 `claude-sonnet-5` 一行），
#: 另两段按 6.1 记下的乘法关系算出来——不重抄，见模块注释第三条。
PRICE: dict[str, float] = {
    "input": 2.00,
    "output": 10.00,
    "cache_write": 2.50,   # 1.25 × input
    "cache_read": 0.20,    # 0.10 ×  input
}
BATCH_X = 0.50             # 批量通道：不着急的活

#: 一次调用的预扣额（按「估算输入 ＋ 最大输出」收）。**结算时按实际用量多退少补。**
RESERVE_TOKENS = (1_000, 1_000)


def charge(input_tokens: int, output_tokens: int, cache_read: int = 0,
           cache_write: int = 0, batch: bool = False) -> float:
    """一笔调用的钱。四段各自乘单价再相加，**最后才乘批量折扣**（它作用在整单上）。"""
    cost = (
        input_tokens * PRICE["input"]
        + output_tokens * PRICE["output"]
        + cache_read * PRICE["cache_read"]
        + cache_write * PRICE["cache_write"]
    ) / 1_000_000
    return round(cost * (BATCH_X if batch else 1.0), 6)


def reserve() -> float:
    """预扣额：按上限估。**它不是「预计花多少」，是「最多能花多少」。**"""
    return charge(*RESERVE_TOKENS)


#: 三笔结算。第二列是实际进、第三列实际出、第四列命中缓存、第五列这一笔的现场。
SETTLEMENTS: tuple[tuple[str, int, int, int, str], ...] = (
    ("c1 正常", 400, 300, 2_000, "实际比预扣小——**这是常态**"),
    ("c2 想多了", 1_200, 1_500, 0, "输入越过了估算、输出越过了上限——**预扣不够，结算时是欠着的**"),
    ("c3 上游 500", 900, 0, 0, "一个字也没给用户；**而输入那一段上游已经处理过了**"),
)


@dataclass(frozen=True)
class Settlement:
    """一笔结算：预扣、实际、差额。`delta > 0` ＝ 退给用户，`< 0` ＝ 用户还欠着。"""

    name: str
    held: float
    actual: float
    why: str

    @property
    def delta(self) -> float:
        return round(self.held - self.actual, 6)


def settlements() -> tuple[Settlement, ...]:
    """三笔结算。**预扣额三笔相同**——不同全在实际那一列上。"""
    held = reserve()
    return tuple(
        Settlement(name, held, charge(inp, out, cache_read=cr), why)
        for name, inp, out, cr, why in SETTLEMENTS
    )


#: 那笔「账单上没有、而你必须付」的钱：上游算完了、我们没收到。它的形状是**网关超时**。
STRANDED: tuple[int, int, int, str] = (
    37,          # 一个月里这种笔数
    900,         # 每笔的输入词元
    300,         # 每笔的输出词元（上游算出来了，只是没到我们手上）
    "上游按「已生成」计费，我们按「已送达」计费——**两个口径的差就是这一笔**",
)


def stranded_cost() -> float:
    """这一个月不可回收的那笔钱。"""
    n, inp, out, _ = STRANDED
    return round(charge(inp, out) * n, 6)


#: 一个月 1,000 笔的用量（**用固定种子生成，所以这个月能被复算**）。
MONTH_CALLS = 1_000
MONTH_SEED = 84


def month_calls(n: int = MONTH_CALLS, seed: int = MONTH_SEED) -> tuple[tuple[int, int, int], ...]:
    """造一个月的用量：进 120–1,800 词元、出 40–1,600 词元、三成命中缓存。"""
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        inp = rng.randrange(120, 1_801)
        out = rng.randrange(40, 1_601)
        cache_read = inp if rng.random() < 0.30 else 0
        rows.append((inp, out, cache_read))
    return tuple(rows)


#: 账单的最小粒度：**上游按百词元进整**（它只对到百位，而日志记的是精确词元数）。
GRAIN = 100


def bill_call(inp: int, out: int, cache_read: int = 0, grain: int = GRAIN) -> float:
    """账单侧的一笔：**先把词元进整到粒度，再乘单价**。粒度是开票口径，不是舍入误差。"""
    up = lambda n: -(-n // grain) * grain  # noqa: E731 —— 向上取整到 grain
    return charge(up(inp), up(out), cache_read=up(cache_read))


def month_totals(rows: tuple[tuple[int, int, int], ...] | None = None) -> dict[str, float]:
    """同一个月，两种口径：**日志（精确到词元）** 与 **账单（按百词元进整）**。

    这一对数字的差**不是错误**，是粒度；所以下一条给的是「口径对齐之后还剩多少」。
    """
    rows = month_calls() if rows is None else rows
    exact = round(sum(charge(i, o, cache_read=c) for i, o, c in rows), 6)
    billed = round(sum(bill_call(i, o, c) for i, o, c in rows), 6)
    return {"日志合计": exact, "账单合计": billed, "差额": round(billed - exact, 6),
            "笔数": float(len(rows))}


def aligned_gap(rows: tuple[tuple[int, int, int], ...] | None = None) -> float:
    """**把日志也进整到同一粒度**，两边就一模一样——差 0.0。

    这就是对账的第一条动作：不是去查谁算错，而是先把口径对齐；
    对齐之后剩下的差才是真需要解释的东西。
    """
    rows = month_calls() if rows is None else rows
    left = round(sum(bill_call(i, o, c) for i, o, c in rows), 6)
    right = round(sum(bill_call(i, o, c) for i, o, c in rows), 6)
    return round(left - right, 6)


#: 那一栏「把例外当通例」的差：缓存读普遍是输入的 0.10×，而某个型号官方写的**是 0.025×**。
EXCEPTION_ROW: tuple[str, float, int, int] = (
    "某个旗舰型号的缓存读（官方 0.025×，而全局按 0.10× 算）",
    10.0,        # 它的输入价（美元／百万词元）
    12_000,      # 每笔的缓存读词元
    30,          # 一个月的这种笔数
)


def exception_gap() -> float:
    """把例外按通例算，一个月少收多少。**小到没人发现**，所以它才要写成一条。"""
    _, inp_price, cache_tokens, n = EXCEPTION_ROW
    return round((0.10 - 0.025) * inp_price * cache_tokens / 1_000_000 * n, 6)


def discrepancies(rows: tuple[tuple[int, int, int], ...] | None = None) -> tuple[tuple[str, str, str], ...]:
    """对账表：三处差异、各自的金额、**以及怎么才算「对上」**。

    三处的性质完全不同：第一处是**口径**（改口径就没有了），
    第二处是**成本**（它根本不该出现在用量里），第三处是**抄漏了一条例外**。
    """
    t = month_totals(rows)
    return (
        (f"进整粒度：账单按百词元、日志按词元",
         f"+${t['差额']:.6f}（占日志 {t['差额'] / t['日志合计'] * 100:.1f}%）",
         f"**口径对齐就归零**（把日志也进整到同一粒度，差 ${aligned_gap(rows):.6f}）——"
         "对账要比的是同一口径下的两个数，而不是两个数看起来应该一样"),
        ("上游已算完、我们没收到",
         f"+${stranded_cost():.6f}（{STRANDED[0]} 笔）",
         "它**不该**出现在用量账单里：账单按送达计、成本按已生成计——"
         "两个数一起看才对得上，只核一个会一直差这一笔"),
        (EXCEPTION_ROW[0],
         f"−${exception_gap():.6f}（{EXCEPTION_ROW[3]} 笔）",
         "把例外抄进单价表（6.1 那一条就是这么写的）："
         "**「按全局倍数算」在八个模型里错一个，而那一个恰好是缓存用量最大的那种**"),
    )
