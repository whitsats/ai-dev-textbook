"""选择器：把「一张表」变成「一次决定」。

这一层要做四件事，顺序不能换：**先过滤（装不下的一律出局）→ 再算单笔账 →
再算缓存与批量那两笔可选的账 → 最后才排序**。顺序换掉就会出现两种很常见的假结论：
「最便宜的那个」其实装不下这次上下文；「贵三倍的那个」在命中缓存之后反而更便宜。

三处刻意的口径，都写在函数名旁边，因为它们都会改变结论：

1. **长档按整单算**（官方原话 `for the full request`）——不是超出部分加价，
   所以 272,000 与 272,001 词元是两笔**不同形状**的账（见 `long_tier()`）；
2. **缓存按「前缀 ＋ 变量」算**：前缀是每次都在的那一段（系统提示、工具定义、资料），
   变量是这一次的问题。**只有前缀能缓存**——这是官方那句「断点要打在
   最后一次都不变的那一块上」的可计算形式；
3. **批量与缓存都作用在整笔账上**（官方说这两档倍数与其它修饰符叠加）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.registry import BATCH_X, LONG_INPUT_X, LONG_OUTPUT_X


@dataclass(frozen=True)
class TaskProfile:
    """一次调用长什么样。

    `input_tokens` / `output_tokens` 这两个数是**词元**，不是汉字——
    它们是前几章在真机上量出来的（`source` 写着是哪一章），本树不重新量：
    本树没有分词器（那需要联网或模型侧的编码器），**拿别的章量到的数来算钱是诚实的，
    自己编一个数是骗人的**。
    """

    name: str
    input_tokens: int
    output_tokens: int
    source: str


#: 三张画像：两张量出来的、一张是专为「长档」造的合成画像。
#: `source` 里那句「合成」必须留着——它一旦被去掉，这张画像就会看起来像量出来的。
PROFILES: tuple[TaskProfile, ...] = (
    TaskProfile("单轮只读问答", 3_730, 131,
                "3.10 真机：一轮 2 步 3,861 词元、输入占 96.6%（3,861 × 0.966 ≈ 3,730）"),
    TaskProfile("最长的那条链", 365, 105,
                "4.2 真机：并行两条链合成一次调用，365 ＋ 105 ＝ 470 词元"),
    TaskProfile("长稿压力画像", 272_001, 8_000,
                "合成：专为「长档悬崖」造的一张画像，**不是量出来的**"),
    TaskProfile("整本书问答", 300_000, 8_000,
                "合成：用来演示「装不下」那一档——它比其中一家的窗口还大，并且把另一家推过长档线"),
)

BY_PROFILE: dict[str, TaskProfile] = {p.name: p for p in PROFILES}


def unit_prices(spec, input_tokens: int) -> tuple[float, float]:
    """这一次调用的**实际**输入/输出单价（已把长档算进去）。

    判据是**输入词元数**，而加成落在**整单**上——两件事都要写出来，
    因为它们一起造成那个悬崖：多一个词元，整单翻倍。
    """
    x_in = x_out = 1.0
    if spec.long_context_over is not None and input_tokens > spec.long_context_over:
        x_in, x_out = LONG_INPUT_X, LONG_OUTPUT_X
    return spec.input_price * x_in, spec.output_price * x_out


def call_cost(spec, profile: TaskProfile, *, batch: bool = False) -> dict:
    """一次调用的一笔账。**四栏分开报**，因为它们各自的修法不同：

    | 栏 | 它变大的原因 | 修法 |
    | --- | --- | --- |
    | 输入 | 历史每轮重发 | 裁剪、缓存、把静态部分提到前面 |
    | 输出 | 话长、思考 token 也算输出 | 约束篇幅、降档、换便宜的输出价 |
    | 长档加成 | 输入过了那一条线 | **切成两单**（这是唯一能在整单翻倍下省钱的修法） |
    | 批量折扣 | 这笔可以等 | 不着急的活全走批量 |
    """
    pin, pout = unit_prices(spec, profile.input_tokens)
    base = (profile.input_tokens * spec.input_price
            + profile.output_tokens * spec.output_price) / 1_000_000
    grown = (profile.input_tokens * pin + profile.output_tokens * pout) / 1_000_000
    total = grown * (BATCH_X if batch else 1.0)
    return {
        "input": profile.input_tokens * pin / 1_000_000,
        "output": profile.output_tokens * pout / 1_000_000,
        "long_surcharge": grown - base,
        "batch_saving": grown - total,
        "total": total,
        "input_x": pin / spec.input_price,
        "output_x": pout / spec.output_price,
    }


def cache_ledger(spec, prefix_tokens: int, calls: int, ttl: str = "5m",
                 hit_rate: float = 1.0) -> dict:
    """缓存 n 次调用的账：**写几次、读几次、省了多少**。

    `hit_rate` 是**前缀命中率**：`1.0` 表示这 n 次里前缀那次次都一样；
    `0.0` 表示断点打在了每次都变的那一块上——官方文档点名的那个常见错误，
    此时**每一次都在付写价**（比不缓存还贵 25%）。

    ⚠️ **第一次调用一定要写**（缓存本来空着），所以能命中的只有后面 `calls − 1` 次。
    写成 `writes = calls × (1−h)` 会算出一个「100% 命中时一次都不写」的假账——
    而那个假账比真账好看，于是没人会去查它。
    """
    w = spec.write_price(ttl)
    reads = round((calls - 1) * hit_rate)
    writes = calls - reads
    cached = (writes * w + reads * spec.cache_read) * prefix_tokens / 1_000_000
    plain = calls * prefix_tokens * spec.input_price / 1_000_000
    return {
        "writes": writes, "reads": reads,
        "cached": cached, "plain": plain,
        "saving": plain - cached,
        "saving_pct": (plain - cached) / plain * 100 if plain else 0.0,
    }


def cache_breakeven_calls(spec, ttl: str = "5m") -> int:
    """**第几次调用开始，缓存才比不缓存便宜。**

    解 `1.25 + 0.1 (n−1) < n`（写一次 ＋ 读 n−1 次 ＜ 读 n 次）：
    标准档是 `n > 1.2778` → **第 2 次**；1 小时档是 `n > 2.1111` → **第 3 次**。
    官方把这两句话写在了定价页上（「pays off after one cache read for the
    5-minute duration... after two cache reads for the 1-hour duration」），
    所以它同时是一条**能对账的读数**：我们的解与它那句话必须一致。

    ⚠️ 三个价必须**先除以输入价**：式子里的 `1.0` 是「原价那一份」，
    拿绝对美元数去减它（用 2.5 减 1）会得到一个看起来很像真的错答案。
    """
    w = spec.write_price(ttl) / spec.input_price
    c = spec.cache_read / spec.input_price
    return math.floor((w - c) / (1.0 - c)) + 1



def cache_breakeven_hit_rate(spec, ttl: str = "5m") -> float:
    """**命中率要高过多少，缓存才不亏。**

    解 `(1−h)·1.25 + h·0.1 < 1` → `h > (w − 1) / (w − c)`：
    标准档 `0.25 / 1.15 ≈ 21.74%`、1 小时档 `1 / 1.9 ≈ 52.63%`。
    这条比拐点更有用：拐点假设的是「连着调」，而线上常常是「二十次里命中几次」。

    这条是**不依赖调用次数**的粗线：它没算「第一次总要写」（有限次数下真分界会略高，
    100 次时是 21.7% 而不是 21.74%——差 0.0 几个百分点，所以正文报两位小数）。
    """
    w = spec.write_price(ttl) / spec.input_price
    c = spec.cache_read / spec.input_price
    return (w - 1.0) / (w - c)


def long_tier(spec, input_tokens: int, output_tokens: int = 8_000) -> dict:
    """这条线在哪、过线要多付多少、**以及为什么「切两单」是唯一省法**。"""
    over = spec.long_context_over
    if over is None:
        return {"applies": False, "at": None, "input_x": 1.0, "output_x": 1.0,
                "cliff": 0.0, "cliff_pct": 0.0}
    probe = TaskProfile("边界探针", over, output_tokens, "临时：只为量出这条线两侧的差")
    before = call_cost(spec, probe)["total"]
    after = call_cost(spec, TaskProfile("边界探针", over + 1, output_tokens,
                                       probe.source))["total"]
    return {"applies": input_tokens > over, "at": over,
            "input_x": LONG_INPUT_X, "output_x": LONG_OUTPUT_X,
            "cliff": after - before,
            "cliff_pct": (after - before) / before * 100}


def feasible(spec, profile: TaskProfile) -> tuple[bool, str]:
    """装得下吗。**三条都判，报第一条不满足的**——它们的修法完全不同。

    第三条（输入 ＋ 输出 ≤ 窗口）最容易漏：只看「输入没超窗」就下单，
    会得到一个跑到一半被截断的答复。
    """
    if profile.input_tokens > spec.context:
        return False, f"输入 {profile.input_tokens:,} 超窗 {spec.context:,}"
    if profile.output_tokens > spec.max_output:
        return False, f"要输出 {profile.output_tokens:,}，最大输出 {spec.max_output:,}"
    if profile.input_tokens + profile.output_tokens > spec.context:
        return False, (f"输入 ＋ 输出 {profile.input_tokens + profile.output_tokens:,} "
                       f"超窗 {spec.context:,}")
    return True, "可行"


def rank(specs, profile: TaskProfile, *, batch: bool = False) -> list[dict]:
    """按钱排序，**但先把装不下的挑出去**。

    每一行都带上「每美元买到的输出词元」——选型时真正要比的是它，
    不是单价：一个输出价便宜但话痨的模型，单位成本反而更高。
    """
    rows: list[dict] = []
    for m in specs:
        ok, why = feasible(m, profile)
        cost = call_cost(m, profile, batch=batch)["total"]
        rows.append({
            "name": m.name, "vendor": m.vendor, "ok": ok, "why": why,
            "total": cost,
            "output_per_dollar": (profile.output_tokens / cost) if (ok and cost) else 0.0,
        })
    rows.sort(key=lambda r: (not r["ok"], r["total"]))
    return rows
