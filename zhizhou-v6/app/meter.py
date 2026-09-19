"""计量：把「一次调用」变成「一页账」，再把一页账变成「一个能盯住的数」。

6.1 回答的是「这一单多少钱」——它算的是**一笔账**；这一章回答另外两个问题：
**钱花在哪一栏**、**怎么把它降下来**。两件事合起来才是成本工程：只会算账的人
看得到 42.8 美元，看得到「哪一栏该动手」的人才知道下周能把它变成 30。

这一层有四样东西，**顺序不能换**（换掉就会出现两种很常见的假结论）：

1. **先立口径**（`Usage` / `bill` / `violations`）：一次调用在账单上是**四个数**，
   不是「一次调用的钱」；四栏之和必须等于总价，**这条能断言**；
2. **再看顺序**（`breakpoints`）：缓存能不能命中，取决于**会变的那一段排在第几位**——
   同一批提示词段，**只改排列**，可缓存的词元数就能掉四分之三，而差异在 diff 里看不见；
3. **再算三招的账**（`batch_plan` / `shunt` / 叠加）：批量用**延迟**换 0.5×、
   分流用**一致性**换单价、缓存不花钱但要先花力气把前缀拼稳；
4. **最后才是看板**（`board` / `guard`）：一页指标 ＋ 三道闸——而闸要看的是
   「已花 ＋ 在飞」，不是「已结算」（账单比调用晚，见 `guard()`）。

三处刻意的口径，都写在函数名旁边，因为它们都会改变结论：

- **思考块是输出**，不是第六栏。账单上「输出」这个词比「答复」大，
  一次 1,200 词元的输出里可能有 900 是读者看不到的那部分；
- **长档的判据是输入规模，不是「没命中缓存的那部分」**——所以**缓存救不了长档**：
  300,000 词元的请求命中 96.7% 之后，输入仍然过 272,000 那条线，整单照旧 ×2。
  唯一的出口是**把它裁到线以下**（或换一个不分档的模型）；
- **失败的尝试也计费**。输入已经被处理过，输出可能算了一半——`Event.ok=False`
  的那些钱必须算进账里，否则看板会把「省钱」读成「降级率上升」。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from app.registry import BATCH_X, BY_NAME, MODELS
from app.select import PROFILES, call_cost, feasible, unit_prices

#: 抄这几页的那一天。折扣倍数与承诺窗口与价格一样会变。
AS_OF = "2026-09-19"

#: 口径出处。这一章的两条新口径（批量通道、数据留存）各指得到一行。
SOURCES: dict[str, str] = {
    "claude_pricing": "https://platform.claude.com/docs/en/about-claude/pricing",
    "openai_pricing": "https://developers.openai.com/api/docs/pricing",
    "claude_batch": "https://platform.claude.com/docs/en/build-with-claude/batch-processing",
    "openai_batch": "https://developers.openai.com/api/docs/guides/batch",
    "openai_data": "https://developers.openai.com/api/docs/guides/your-data",
}

#: 批量通道的**承诺窗口**（两家同一句话：50% off、up to 24 hours）。
#: 它是这一章唯一一条「用钱买不到」的东西——省下来的 0.5× 是拿**最多 24 小时**换的，
#: 所以「多少比例可以挪」不是技术问题，是产品问题（见 `batch_plan()`）。
BATCH_WINDOW_H = 24.0

#: 看板上的两道线。80% 告警（不拦）、100% 分流到便宜链（**不是拒服务**）。
WARN_AT = 0.80
SHUNT_AT = 1.00


# ----------------------------------------------------------------- 口径：四栏

@dataclass(frozen=True)
class Usage:
    """一次调用在账单上的**四个**词元数。**它是这一章的地基。**

    | 栏 | 它是什么 | 单价（相对输入价） |
    | --- | --- | --- |
    | `uncached` | 按原价计的输入（没被任何缓存覆盖的那部分） | 1.0 |
    | `write` | 写进缓存的词元 | 1.25（1 小时档 2.0） |
    | `read` | 读到缓存的词元 | 0.1（一家是 0.025） |
    | `out` | 输出词元 —— **思考块也算在这里** | 输出价 |

    `thinking` 是 `out` 的**子集**，不是第五栏：官方把它算在输出词元里，
    而它值钱的地方在于**它常常占掉一半以上的输出**（见 `thinking_share()`）。
    """

    uncached: int
    write: int
    read: int
    out: int
    thinking: int = 0

    @property
    def tokens(self) -> int:
        """账单上出现的词元总数（四栏之和）。"""
        return self.uncached + self.write + self.read + self.out

    @property
    def input_tokens(self) -> int:
        """**长档的判据是这一个数**：它包含命中的那部分。"""
        return self.uncached + self.write + self.read


def tier_x(spec, input_tokens: int) -> tuple[float, float]:
    """长档的**两个倍数**（不是两个价）。

    `select.unit_prices()` 返回的是**价**（已经乘过 2.0 与 1.5），而这一层要的是
    **倍数**——它要分别乘到四栏各自的价上（写价与读价也要跟着进长档）。
    把两者搞混的后果是把价再乘一遍：420 千词元的账会算成 2.04 美元，
    而它看起来只是「贵一点」，没人会去查。
    """
    pin, pout = unit_prices(spec, input_tokens)
    return pin / spec.input_price, pout / spec.output_price


def bill(spec, usage: Usage, *, ttl: str = "5m", batch: bool = False) -> dict:
    """一次调用的一页账。**四栏分开报**，因为它们的修法完全不同。

    | 栏 | 它变大的原因 | 修法 |
    | --- | --- | --- |
    | `uncached` | 每次都在变的那些段 | 把静态的提到前面（缓存）、裁剪 |
    | `write` | 前缀换了（断点打错） | **只改排列**（6.4.3） |
    | `read` | 命中得多 | 这是**好的**那一栏：它越大，账越小 |
    | `out` | 话长、思考块多 | 约束篇幅、降档、换输出价便宜的候选 |

    长档加成乘在**四栏各自**的价上（官方那句 `for the full request` 说的是整单）。
    **这个乘法的位置很重要**：把它只乘在 `uncached` 上，会让「命中缓存的那些词元
    不算进长档」——而它们算。
    """
    x_in, x_out = tier_x(spec, usage.input_tokens)
    lines = {
        "uncached": usage.uncached * spec.input_price * x_in / 1_000_000,
        "write": usage.write * spec.write_price(ttl) * x_in / 1_000_000,
        "read": usage.read * spec.cache_read * x_in / 1_000_000,
        "out": usage.out * spec.output_price * x_out / 1_000_000,
    }
    full = sum(lines.values())
    paid = full * (BATCH_X if batch else 1.0)
    return {
        **lines,
        "total": paid,
        "full": full,
        "batch_saving": full - paid,
        "input_x": x_in,
        "output_x": x_out,
        "tokens": usage.tokens,
    }


def violations(spec, usage: Usage, page: dict | None = None) -> list[str]:
    """这一页账自己**说得通**吗。空列表才是正常。

    四条，每一条都对应一种「看起来正常」的错账：

    1. 四栏之和 ≠ 总价——差额只可能来自一个**没报出来的加数**；
    2. `thinking > out`——思考块不是输出的子集了，那它就不该在这张表里；
    3. 命中缓存的读价**不低于**原价：这一栏越大账越大，缓存就成了反的；
    4. 用了 1 小时档而这家**没有**这一档——`write_price()` 会报错，这里兜一层。
    """
    page = page if page is not None else bill(spec, usage)
    bad: list[str] = []
    four = page["uncached"] + page["write"] + page["read"] + page["out"]
    if abs(four - page["full"]) > 1e-9:
        bad.append(f"四栏之和 {four!r} 与总价 {page['full']!r} 不等——有一栏没报出来")
    if usage.thinking > usage.out:
        bad.append(f"思考块 {usage.thinking} 大于输出 {usage.out}——它只能是输出的子集")
    if spec.cache_read >= spec.input_price:
        bad.append(f"{spec.name}：缓存读价 {spec.cache_read} 不低于输入价 "
                   f"{spec.input_price}——命中越多账越大，这一栏必须便宜")
    return bad


def thinking_share(usage: Usage) -> float:
    """**输出里有多少钱花在读者看不到的地方。**一个字都没有的时候返回 0.0。"""
    return usage.thinking / usage.out if usage.out else 0.0


def attribution(a: dict, b: dict) -> dict:
    """两页账的差**落在哪一栏**。`a` 是现在，`b` 是之前。

    这是「为什么这一单贵了」的可计算形式。只报「贵了 3.2 倍」是不够的——
    贵 3.2 倍可能与模型无关（是 `read` 那一栏塌了，也就是前缀换了），
    而这两件事的修法一个是**换模型**、另一个是**只改排列**。
    """
    diff = {k: a[k] - b[k] for k in ("uncached", "write", "read", "out")}
    raised = {k: v for k, v in diff.items() if v > 0}
    top = max(raised, key=raised.get) if raised else ""
    total = sum(raised.values())
    return {"diff": diff, "total": total, "top": top,
            "top_share": (raised[top] / total) if (top and total) else 0.0,
            "ratio": (a["total"] / b["total"]) if b["total"] else 0.0}


# ----------------------------------------------------------------- 顺序：断点

@dataclass(frozen=True)
class Segment:
    """提示词里的一段，以及**它多久变一次**。

    `changes` 只有三种取值，它们是这一章最省事的一个判据：

    | 取值 | 意思 | 能不能进缓存前缀 |
    | --- | --- | --- |
    | `never` | 每次调用都一样（系统提示、工具定义、固定示例） | 能 |
    | `session` | 一个会话内不变，会话之间会变（租户配置、用户档案） | 能 |
    | `call` | 每次调用都在变（检索到的资料、用户这一句、当前时间） | **不能** |
    """

    name: str
    tokens: int
    changes: str


CHANGES = ("never", "session", "call")

#: 一份真实的提示词结构（知舟的问答链）。**顺序就是它的全部内容**：
#: 下面三个排列用的是**同一批段**，只把 `docs`（每次都在变的检索资料）挪了位置。
CANONICAL: tuple[Segment, ...] = (
    Segment("系统提示", 800, "never"),
    Segment("工具定义", 2_600, "never"),
    Segment("检索资料", 1_500, "call"),
    Segment("用户这一句", 120, "call"),
)

#: 错法甲：把每次都会变的那一段插在中间。**提示词逐字相同，只是排列不同。**
MIDDLE_VARIABLE: tuple[Segment, ...] = (
    Segment("系统提示", 800, "never"),
    Segment("检索资料", 1_500, "call"),
    Segment("工具定义", 2_600, "never"),
    Segment("用户这一句", 120, "call"),
)

#: 错法乙：把「当前时间」放在最前面（很多人写提示词的第一行就是这个）。
STAMP_FIRST: tuple[Segment, ...] = (
    Segment("当前时间", 20, "call"),
    Segment("系统提示", 800, "never"),
    Segment("工具定义", 2_600, "never"),
    Segment("检索资料", 1_500, "call"),
    Segment("用户这一句", 120, "call"),
)


def breakpoints(segments: tuple[Segment, ...]) -> dict:
    """这份结构**能缓存多少词元**、断点该打在哪一段之后。

    规则只有一条，而它来自 6.1 的口径 2（「只有前缀能缓存」）：

    > 从第一段开始累加，**遇到第一段 `call` 就停**——那一段与它后面的所有段
    > 都不再可缓存，因为缓存的前缀必须**连续**。

    所以「哪些段该放前面」不是一个风格问题：**一个会变的段放得越靠前，
    它后面那些不会变的段就越亏**。错法乙（多一个 20 词元的时间戳）的代价
    不是那 20 个词元，是**它后面 3,400 个词元全部落空**。
    """
    total = 0
    cut = ""
    for seg in segments:
        if seg.changes == "call":
            break
        total += seg.tokens
        cut = seg.name
    return {
        "cacheable": total,
        "cut_after": cut,
        "prompt_tokens": sum(s.tokens for s in segments),
        "share": total / sum(s.tokens for s in segments),
        "order": [s.name for s in segments],
    }


# ----------------------------------------------------------------- 三招：批量

@dataclass(frozen=True)
class Event:
    """看板的最小单位：一次**真的发出去**的调用。

    ⚠️ 它数的是**尝试**，不是**请求**：一次请求重试两次就是三条 `Event`
    （6.3 的 `CallResult.network_calls`）。`ok=False` 的那些**也要入账**——
    输入已经被处理过，失败的钱不是没花，是花在了没结果的地方。

    `by_batch` 是「这一次的活能不能等 24 小时」。它是**产品给的信息**，
    不是一个默认值：把它默认成 `True`，看板上就会多出一次「省了一半」的幻觉。
    """

    model: str
    profile: str
    usage: Usage
    ok: bool = True
    tried: int = 1
    ttl: str = "5m"
    by_batch: bool = False


def batch_plan(events: list[Event]) -> dict:
    """把「能等的那部分」挪到批量通道：**省多少、以及有多少能挪**。

    两条口径：①刷量 **0.5×**（两家同一句话）；②它与缓存**叠加**
    （6.1 的口径 3：这两个倍数作用在整笔账上）——所以一条已经命中缓存的调用
    挪过去，省的**不是**它的一半原价，而是**它那一份的一半**（已经很小了）。

    这个函数真正的输出不是那个百分比，而是**两个百分比的差**：
    按次数算能挪多少、按钱算能挪多少。它们不一致的时候，
    「挪哪一批」这件事就不能交给「量最大的那一批」来做。
    """
    total = sum(bill(BY_NAME[e.model], e.usage, ttl=e.ttl)[ "total"] for e in events)
    movable = [e for e in events if e.by_batch]
    movable_money = sum(bill(BY_NAME[e.model], e.usage, ttl=e.ttl)["total"] for e in movable)
    saving = movable_money * (1 - BATCH_X)
    return {
        "calls": len(events),
        "movable_calls": len(movable),
        "calls_pct": len(movable) / len(events) if events else 0.0,
        "total": total,
        "movable_money": movable_money,
        "money_pct": movable_money / total if total else 0.0,
        "saving": saving,
        "saving_pct": saving / total if total else 0.0,
    }


def stacked(spec, usage: Usage, *, ttl: str = "5m") -> dict:
    """**三招叠在一笔账上**：不缓存 / 只缓存 / 只批量 / 两个都要。

    最后一行是这一节的收尾：**叠加的省不是相加**。缓存把这一笔从 1.00 压到 0.14，
    再叠上批量是 0.07——比「只批量」的 0.50 小得多，但它省下来的**绝对数**
    只有缓存那一半的一半。预算该按**还剩多少可省**来分，不是按招式数。
    """
    plain = bill(spec, usage)
    cached = bill(spec, Usage(uncached=0, write=usage.write, read=usage.read,
                              out=usage.out, thinking=usage.thinking), ttl=ttl)
    batched = bill(spec, usage, ttl=ttl, batch=True)
    both = bill(spec, Usage(uncached=0, write=usage.write, read=usage.read,
                            out=usage.out, thinking=usage.thinking),
                ttl=ttl, batch=True)
    return {"plain": plain["total"], "cached": cached["total"],
            "batched": batched["total"], "both": both["total"],
            "cache_saving": plain["total"] - cached["total"],
            "batch_saving": plain["total"] - batched["total"],
            "both_saving": plain["total"] - both["total"]}


# ----------------------------------------------------------------- 三招：分流

#: 一批真实比例的流量：四个画像各占多少。**这张混合表是产品给的**，不是模型给的。
MIX: tuple[tuple[str, int], ...] = (
    ("单轮只读问答", 700),
    ("最长的那条链", 200),
    ("长稿压力画像", 80),
    ("整本书问答", 20),
)


def shunt(mix: tuple[tuple[str, int], ...] = MIX, *, pinned: str = "claude-fable-5-1") -> dict:
    """按画像把流量分开：**每一档只买它装得下的那一档能力**。

    它省下来的钱来自一个很朴素的事实：`claude-fable-5-1` 与 `gpt-5.6-luna`
    的输出价差 **41.7 倍**，而「单轮只读问答」这一类活并不需要那 41.7 倍。
    但它换来的代价不在账上，在**一致性**上：同一个问题在不同用户那里由不同模型回答，
    「同一个问题两种答案」这件事只有 A/B 能量出来（见 `bucket()`）。

    `feasible()` 是这里唯一的硬约束（装不下的一律出局），
    **长档是软约束**：它不过滤候选，但它会让一个候选**变贵**——
    于是「第二便宜的那个」可能在这一张画像上变成最贵的（读数里真的发生了）。
    """
    rows: list[dict] = []
    total = 0.0
    pinned_total = 0.0
    for name, calls in mix:
        profile = {p.name: p for p in PROFILES}[name]
        best: dict | None = None
        for m in sorted(MODELS, key=lambda s: call_cost(s, profile)["total"]):
            ok, why = feasible(m, profile)
            if not ok:
                continue
            cost = call_cost(m, profile)["total"]
            if best is None:
                best = {"model": m.name, "cost": cost}
            elif m.long_context_over is not None and \
                    profile.input_tokens > m.long_context_over:
                # 「长档把谁顶到了后面」——它的前提是**价目表上它更便宜**，
                # 所以要先算一个不含长档的价，不能只看排序结果。
                plain = (profile.input_tokens * m.input_price
                         + profile.output_tokens * m.output_price) / 1_000_000
                if plain < best["cost"]:
                    best.setdefault("lifted", []).append(m.name)
        assert best is not None, f"{name} 没有可行候选——画像或表有问题"
        tier_free = (profile.input_tokens * BY_NAME[best["model"]].input_price
                     + profile.output_tokens * BY_NAME[best["model"]].output_price) / 1_000_000
        pinned_row = call_cost(BY_NAME[pinned], profile)
        rows.append({"profile": name, "calls": calls, "model": best["model"],
                     "per_call": best["cost"], "money": best["cost"] * calls,
                     "lift": best["cost"] / tier_free - 1.0 if tier_free else 0.0,
                     "lifted": best.get("lifted", []),
                     "pinned_per_call": pinned_row["total"],
                     "pinned_money": pinned_row["total"] * calls})
        total += best["cost"] * calls
        pinned_total += pinned_row["total"] * calls
    calls = sum(c for _, c in mix)
    chosen = {r["model"] for r in rows}
    return {"rows": rows, "calls": calls, "total": total, "pinned_total": pinned_total,
            "saving": pinned_total - total,
            "saving_pct": (pinned_total - total) / pinned_total if pinned_total else 0.0,
            "per_1k_routed": total / calls * 1000,
            "per_1k_pinned": pinned_total / calls * 1000,
            "distinct": len(chosen), "chosen": sorted(chosen),
            "lifted": sorted({n for r in rows for n in r["lifted"]})}


# ----------------------------------------------------------------- 三招：分桶

def bucket(key: str, *, salt: str, buckets: int = 2) -> int:
    """**稳定的**分桶：同一个键每次都进同一个桶。

    键必须是**用户**，不是请求、也不是会话——用会话做键的实现，会让同一个人
    在换设备之后落进另一边，于是「A 组出了个问题」这句话里混着 B 组的样本。
    `salt` 让同一个用户在两组实验里独立分桶（换了盐就不在同一个桶里了）。
    """
    digest = hashlib.sha256(f"{salt}:{key}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % buckets


def cross_users(users: list[str], *, calls_per_user: int, salt: str,
                by: str = "user") -> dict:
    """有多少用户在这一次实验里**落进了两边**（按 `by` 决定怎么分）。

    - `by="user"`：哈希分桶（同一个人每次都在同一边）→ 跨池 **0 个**；
    - `by="call"`：每次请求各自随机 → 每人 n 次全在同一边的概率是 `2·0.5ⁿ`，
      于是跨池的用户数是 `N × (1 − 2·0.5ⁿ)`（n ＝ 6 时是 968.75／1000）。

    这是「分流要不要分组」这句话的算术版：**不按用户分，A 组与 B 组之间就没有
    「人」这个单位**——两边的用户是同一批人，指标只能按请求比，而按请求比
    会把「同一个人量了六次」当成六个样本。
    """
    size = {0: 0, 1: 0}
    crossed = 0
    for i, user in enumerate(users):
        if by == "user":
            side = bucket(user, salt=salt)
            size[side] += 1
            continue
        sides = {bucket(f"{user}:{k}", salt=salt) for k in range(calls_per_user)}
        if len(sides) > 1:
            crossed += 1
        else:
            size[next(iter(sides))] += 1
    return {"crossed": crossed, "users": len(users), "by": by,
            "crossed_pct": crossed / len(users) if users else 0.0,
            "uncrossed_split": (size[0], size[1])}


# ----------------------------------------------------------------- 看板与闸

def board(events: list[Event]) -> dict:
    """一页指标。**每一个数都有它自己的修法**，所以它们才要摆在同一页上。

    | 指标 | 它变坏时该动哪一处 |
    | --- | --- |
    | 每千次成本 | 整体（分流与候选） |
    | 前缀命中率（**按词元**） | 前缀排列（6.4.3） |
    | 命中率（按调用） | 缓存有没有开 |
    | 思考块占比 | 输出那一栏（模型与篇幅） |
    | 重试倍数 | 候选的稳定性（6.3） |
    | 失败的钱 | 同上，但它是「花了却什么都没拿到」的那一份 |

    **命中率报两个**，因为它们的差就是问题本身：按调用算很好看（大部分调用
    都命中过），按词元算很难看（没命中的那几次恰好是最长的那些）——
    只报一个数，看板会替你做决定。
    """
    money = 0.0
    failed = 0.0
    saved = 0.0
    out = 0
    thinking = 0
    read = write = 0
    fed = 0            # 全部输入词元（含未命中的那些）——按词元的命中率要它当分母
    per_model: dict[str, dict] = {}
    hit_calls = 0
    for e in events:
        spec = BY_NAME[e.model]
        page = bill(spec, e.usage, ttl=e.ttl)
        money += page["total"]
        if not e.ok:
            failed += page["total"]
        x_in, _ = tier_x(spec, e.usage.input_tokens)
        # 缓存**净**省下来的钱：命中读的那部分省下「原价 − 读价」，
        # 再减去为写它多付的溢价（写价高于原价的那一部分）——两个都要算，
        # 只加不减会把一个「每次都写、从不命中」的前缀读成省了钱。
        saved += (e.usage.read * (spec.input_price - spec.cache_read)
                  - e.usage.write * (spec.write_price(e.ttl) - spec.input_price)) \
            * x_in / 1_000_000
        out += e.usage.out
        thinking += e.usage.thinking
        read += e.usage.read
        write += e.usage.write
        fed += e.usage.input_tokens
        if e.usage.read > 0:
            hit_calls += 1
        row = per_model.setdefault(e.model, {"calls": 0, "money": 0.0})
        row["calls"] += 1
        row["money"] += page["total"]
    calls = len(events)
    return {
        "calls": calls,
        "money": money,
        "per_1k": money / calls * 1000 if calls else 0.0,
        "hit_calls": hit_calls / calls if calls else 0.0,
        #: 按词元的命中率：**分母是全部输入词元**（含没命中的那些）。
        #: 写成 `read / (read + write)` 会得到 100%——未命中的那部分压根不在分母里，
        #: 而这个假数正好是最容易让人放心的那一个。
        "hit_tokens": read / fed if fed else 0.0,
        "cache_saving": saved,
        "cache_saving_share": saved / (money + saved) if (money + saved) else 0.0,
        "thinking_share": thinking / out if out else 0.0,
        "retry_x": sum(e.tried for e in events) / calls if calls else 0.0,
        "failed_money": failed,
        "failed_pct": failed / money if money else 0.0,
        "by_model": per_model,
    }


def guard(spent: float, inflight: float, budget: float) -> tuple[str, str]:
    """三道闸：**正常 / 告警 / 分流**。返回 `(动作, 理由)`。

    判据是 `spent + inflight`，而不是 `spent`——**这是这一节唯一容易漏的地方**：
    账单比调用晚（批量通道可以晚 24 小时），所以「已结算」永远小于「已经花掉」，
    照它做闸的话，闸会在超支之后才响。`inflight` 是「已经发出去、还没结算」的预估。

    第三道闸的动作是**分流**（换便宜链），不是**拒服务**：
    预算控制的目标是「这件事还能继续做，但用更便宜的做法」——
    拒服务把一次成本问题变成了可用性问题，而可用性问题更贵。
    """
    used = (spent + inflight) / budget if budget else 0.0
    if used >= SHUNT_AT:
        return "shunt", f"已用 {used:.1%}（含在飞 {inflight:.4f}）——转到便宜链"
    if used >= WARN_AT:
        return "warn", f"已用 {used:.1%}——告警，同时把不急的活挪到批量通道"
    return "ok", f"已用 {used:.1%}"


# ----------------------------------------------------------------- 夹具用的小工具

def users_of(n: int) -> list[str]:
    """`n` 个稳定的用户键。**看板上的人必须是同一批人**，不能每次现造。"""
    return [f"u{i:04d}" for i in range(n)]


def on_this_day(events: list[Event]) -> dict:
    """把一批事件按「一批账」汇总——看板与对账都要它的四栏合计。"""
    sums = {"uncached": 0, "write": 0, "read": 0, "out": 0, "thinking": 0}
    total = 0.0
    for e in events:
        sums["uncached"] += e.usage.uncached
        sums["write"] += e.usage.write
        sums["read"] += e.usage.read
        sums["out"] += e.usage.out
        sums["thinking"] += e.usage.thinking
        total += bill(BY_NAME[e.model], e.usage, ttl=e.ttl)["total"]
    return {**sums, "total": total}
