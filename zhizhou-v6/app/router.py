"""路由：把「一张候选名单」变成「一条真的能走的降级链」。

网关（`gateway.py`）管**发生错误之后怎么办**；这一层管**名单上写谁、按什么顺序**。
两件事分开是因为它们的判据不同：网关的判据是错误码，路由的判据是**这一次请求的形状**。

三处刻意的地方：

1. **候选必须带上方言**。`fallbacks=[{"gpt-5.6-terra": ["claude-sonnet-5"]}]` 这样一行
   名单里只有**模型名**，而降级一次就意味着**换一种方言**（6.2 的表：同一个请求
   翻成三家的载荷，key 路径 27／27／28）。所以名单上的名字要先配上方言才谈得上降级；
2. **名单要按请求形状过滤**。6.2 量过：24 个「模型 × 方言」格里只有 11 格能调到工具。
   一个带工具的请求，它的降级链上那些调不到工具的候选**不是「次优」，是坏的**——
   换过去只会拿到一次没有工具调用的答复，而它在外表上完全正常；
3. **超窗降级必须往上走窗口**。这是唯一一个 `fix` 档，它的修法不是「换个人」而是
   「换一个装得下的」：把窗口比当前候选小的模型排进链里，等于再撞一次同一面墙。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.dialects import tool_constraint, tool_dialects
from app.registry import BY_NAME, MODELS
from app.select import PROFILES, call_cost


@dataclass(frozen=True)
class Candidate:
    """名单上的一个候选：**模型名 ＋ 方言**。少了方言，降级这件事就没法谈。"""

    model: str
    dialect: str
    why: str = ""

    @property
    def label(self) -> str:
        return f"{self.model}/{self.dialect}"


@dataclass
class Plan:
    """一条降级链的**全部**结果：能走的、不能走的、以及不能走的理由。

    不能走的那一列必须留下来。只报「能走的三个」的实现在线上有一个很贵的症状：
    第一个候选挂了、第二个候选被静默跳过、第三个成功了，于是**没人知道
    名单上有一半是摆设**——直到某天前两个一起挂。
    """

    primary: Candidate
    chain: list[Candidate] = field(default_factory=list)
    excluded: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return 1 + len(self.chain) + len(self.excluded)


def shape_of(tools: bool) -> str:
    return "tools" if tools else "plain"


def usable(model: str, dialect: str, tools: bool) -> tuple[bool, str]:
    """这个候选能不能接**这一次的请求**。返回 `(能用, 理由)`。"""
    if model not in BY_NAME:
        return False, "不在 6.1 的登记表里"
    if not tools:
        return True, ""
    if dialect not in tool_dialects(model):
        return False, tool_constraint(model, dialect)
    return True, ""


def plan(primary_model: str, primary_dialect: str, names: list[str], *,
         tools: bool = False, pin: str | None = None) -> Plan:
    """把一行**只有模型名**的名单摊成一条带方言、并逐格核过形状的链。

    `names` 是 in-order 的（LiteLLM 的文档原话：`["a", "b", "c"]` 会先试 `a`），
    顺序不改——这一层只做过滤与配方言，不做排序。**顺序是策略，过滤是正确性。**

    `pin` 是「这条名单上所有候选都走同一种方言」（配置里很常见：整个网关都说
    兼容层）。它一开，候选会不会被过滤就取决于**那个模型在那种方言上能不能
    接这一次的形状**——而「名字 → 方言」这一步交给这一层做时，它永远不会失配。
    """
    primary = Candidate(primary_model, primary_dialect)
    out = Plan(primary=primary)
    seen = {f"{primary_model}/{primary_dialect}"}
    for name in names:
        dialect = pin or default_dialect(name, tools)
        key = f"{name}/{dialect}"
        if key in seen:
            out.excluded.append((key, "与前面某一个重复——同一个候选试两遍不是降级"))
            continue
        ok, why = usable(name, dialect, tools)
        if not ok:
            out.excluded.append((key, why))
            continue
        seen.add(key)
        out.chain.append(Candidate(name, dialect))
    return out


def default_dialect(model: str, tools: bool = False) -> str:
    """名单上只写了模型名时，给它配哪一种方言。

    规则是**先看请求形状、再看能力**：带工具时取这家能调工具的那一种
    （`tool_dialects` 的头一个），不带工具时也取它——两种情形都不会配出
    「接不了这一次形状」的候选，**这正是把这一步交给代码而不是交给配置的理由**。
    """
    if model not in BY_NAME:
        return "messages"
    ds = tool_dialects(model)
    return ds[0] if ds else "messages"


def bigger_window(model: str, *, same_price_or_cheaper: bool = True) -> list[str]:
    """窗口**严格更大**的候选，按「窗口升序、价格升序」排。

    超窗（`fix` 档）时的名单只能从这里出：换一个窗口更小的，是把同一面墙再撞一次。
    `same_price_or_cheaper` 默认开着——它是路由的**代价约束**：
    修一次错误顺手把这一单的价钱翻十倍，比报这个错更糟。
    """
    if model not in BY_NAME:
        return []
    me = BY_NAME[model]
    out = []
    for m in MODELS:
        if m.name == model or m.context <= me.context:
            continue
        if same_price_or_cheaper and (
                m.input_price > me.input_price or m.output_price > me.output_price):
            continue
        out.append(m)
    out.sort(key=lambda m: (m.context, m.input_price, m.output_price))
    return [m.name for m in out]


def price_ladder(plan: Plan, profile_name: str) -> list[tuple[str, float]]:
    """一条降级链的**价格阶梯**：每一跳各要多少钱。**首跳是主候选，不能漏。**

    名单在配置里只有名字，**跑起来才知道它是一条价格阶梯**——而且方向常常是反的：
    便宜的候选先试，挂了换贵的，于是「这次请求多花了钱」与「这次请求降级过」
    是同一件事的两种说法。

    ⚠️ 第一版只算了 `chain`（降级那几跳），把主候选落在外面——于是「末跳比首跳
    贵几倍」量的是「最贵的那个替身」而不是「最贵的那个替身相对主候选」，
    48.5 倍被算成 10.0 倍。**漏掉首跳的阶梯看着也像阶梯**，这是它没被当场发现的原因。
    """
    profile = {p.name: p for p in PROFILES}[profile_name]
    steps = [plan.primary, *plan.chain]
    return [(c.label, call_cost(BY_NAME[c.model], profile)["total"]) for c in steps]


def ladder_jump(plan: Plan, profile_name: str) -> float:
    """末跳相对首跳贵几倍。**`1.0` ＝ 这条链是平的。**"""
    rows = price_ladder(plan, profile_name)
    if len(rows) < 2 or not rows[0][1]:
        return 1.0
    return rows[-1][1] / rows[0][1]
