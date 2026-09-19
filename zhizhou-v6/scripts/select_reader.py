#!/usr/bin/env python
"""6.1 的读数脚本：把「选型」变成六组能复算的数。

    python scripts/select_reader.py --offline     # 六组读数（不要密钥、不要网络）
    python scripts/select_reader.py --self-test   # 十套夹具

它**不调模型**。它算的是账单：把登记表上的价乘上前几章量到的词元数，
再把两处分档的边界逐个报出来（缓存的写/读、长上下文的整单加成）。
所以这一章的每一个结论都能用手再算一遍——这是第 5 篇那条纪律在本篇的形态：
**读数要么能复算，要么别写进正文**。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.registry import (AS_OF, BY_NAME, MODELS, SOURCES, table_row, violations)  # noqa: E402
from app.select import (BY_PROFILE, PROFILES, TaskProfile, cache_breakeven_calls,  # noqa: E402
                        cache_breakeven_hit_rate, cache_ledger, call_cost, feasible,
                        long_tier, rank, unit_prices)

#: 缓存那一组用的前缀长度与调用次数。前缀取 3.6 量到的装配账（那一段每次都在），
#: 次数取 100——**不取 2 或 3**：拐点那两个数由公式给，账要有代表性才看得出差别。
CACHE_PREFIX = 2_510
CACHE_CALLS = 100


def _usd(x: float) -> str:
    """钱的打印口径：一律六位小数。**位数是格式，不是精度**——比它更小的差别不报。"""
    return f"${x:.6f}"


def _p(inp: int, out: int) -> TaskProfile:
    """脚本内部临时造的画像。`name` 与 `source` 都写「临时」——
    免得它以后被人当成一张量过的画像引到别处去。"""
    return TaskProfile("临时", inp, out, "临时：只用来算边界，不是一张画像")


# ------------------------------------------------------------------ 一、登记表

def group_table() -> list[str]:
    out = [f"=== 一、登记表：{len(MODELS)} 个模型 / "
           f"{len({m.vendor for m in MODELS})} 家，抄于 {AS_OF} ==="]
    out.append(f"{'模型':<20}{'厂商':<11}{'窗口':>10}{'输出上限':>10}"
               f"  {'输入/输出':>9}  {'缓存写/读':>10}  {'1小时写':>8}  {'长档线':>7}  知识截止")
    for m in MODELS:
        hour = "—" if m.cache_write_hour is None else f"${m.cache_write_hour:g}"
        over = "—" if m.long_context_over is None else f">{m.long_context_over // 1000}K"
        out.append(f"{m.name:<20}{m.vendor:<11}{m.context:>10,}{m.max_output:>10,}"
                   f"  {m.input_price:>4g}/{m.output_price:<4g}"
                   f"  {m.cache_write:>7g}/{m.cache_read:<6g}"
                   f"  {hour:>8}  {over:>7}  {m.cutoff}")
    bad = violations()
    out.append(f"表自身的关系：{len(MODELS)} 行逐行核过，不符 {len(bad)} 处")
    out.append(f"口径出处：{len(SOURCES)} 个官方页面（每条记录的 source 都指得到其中一行）")
    return out


# ------------------------------------------------- 二、同一次调用的账

def group_one_call(profile: TaskProfile) -> list[str]:
    rows = [r for r in rank(MODELS, profile) if r["ok"]]
    out = [f"=== 二、同一次调用的账（画像：{profile.name} "
           f"{profile.input_tokens:,} ＋ {profile.output_tokens:,} 词元）==="]
    for r in rows:
        m = BY_NAME[r["name"]]
        share = m.input_price * profile.input_tokens / 1_000_000 / r["total"] * 100
        out.append(f"{r['name']:<19} {_usd(r['total'])}  "
                   f"输入占 {share:5.1f}%  每美元买到 {r['output_per_dollar']:,.0f} 输出词元")
    cheap, dear = rows[0], rows[-1]
    out.append(f"最便宜 {cheap['name']} {_usd(cheap['total'])} ／ "
               f"最贵 {dear['name']} {_usd(dear['total'])} = "
               f"{dear['total'] / cheap['total']:.1f} 倍")
    return out


# ------------------------------------------------------- 三、缓存

def group_cache() -> list[str]:
    m = BY_NAME["claude-sonnet-5"]
    out = ["=== 三、缓存：写一次 1.25×、读 0.1×，那要读几次才回本 ==="]
    out.append("档      写价×  读价×  第几次回本  命中率底线")
    for ttl in ("5m", "1h"):
        w = m.write_price(ttl)
        out.append(f"{ttl:<6}  {w / m.input_price:>5.2f}  "
                   f"{m.cache_read / m.input_price:>5.2f}  "
                   f"第 {cache_breakeven_calls(m, ttl)} 次      "
                   f"{cache_breakeven_hit_rate(m, ttl) * 100:5.2f}%")
    out.append("（官方原话：5 分钟档「pay off after one cache read」、"
               "1 小时档「after two cache reads」——两条与上表逐个对得上）")
    for hit in (1.0, 0.5, 0.0):
        led = cache_ledger(m, CACHE_PREFIX, CACHE_CALLS, "5m", hit_rate=hit)
        note = "断点打错地方（每次都重写）" if hit == 0.0 else f"命中率 {hit:.0%}"
        out.append(f"{CACHE_CALLS} 次调用、前缀 {CACHE_PREFIX:,} 词元、{note}："
                   f"写 {led['writes']} 读 {led['reads']} → {_usd(led['cached'])}"
                   f"（不缓存 {_usd(led['plain'])}，省 {led['saving_pct']:+.1f}%）")
    return out


# ------------------------------------------------------- 四、长档悬崖

def group_long_tier() -> list[str]:
    m = BY_NAME["gpt-5.6-terra"]
    over = m.long_context_over
    just = call_cost(m, _p(over, 8_000))["total"]
    past = call_cost(m, _p(over + 1, 8_000))["total"]
    tier = long_tier(m, over + 1)
    two = call_cost(m, _p(over // 2, 4_000))["total"] * 2
    flat = unit_prices(BY_NAME["claude-opus-5"], 900_000)
    return [
        f"=== 四、长档悬崖（{m.name}，输出固定 8,000 词元）===",
        f"{over:,} 词元      {_usd(just)}",
        f"{over + 1:,} 词元    {_usd(past)}   ← 多 1 个词元，整单 +{tier['cliff_pct']:.1f}%",
        f"切成两单各 {over // 2:,}  {_usd(two)}   比过线便宜 "
        f"{(past - two) / past * 100:.1f}%",
        f"另一家同一件事：1,000,000 窗口全程一个价（900,000 词元时单价仍是 "
        f"${flat[0]:g}/${flat[1]:g}）——**两家的「1M 上下文」不是一回事**",
    ]


# ------------------------------------------------------- 五、可行与名次

def group_feasible() -> list[str]:
    p = BY_PROFILE["整本书问答"]
    rows = rank(MODELS, p)
    out = [f"=== 五、可行性过滤（画像：{p.name} "
           f"{p.input_tokens:,} ＋ {p.output_tokens:,} 词元）==="]
    for r in rows:
        mark = "✓" if r["ok"] else "✗"
        extra = f"　进长档：整单 ×{long_tier(BY_NAME[r['name']], p.input_tokens)['input_x']:g}/" \
                f"×{long_tier(BY_NAME[r['name']], p.input_tokens)['output_x']:g}" \
                if long_tier(BY_NAME[r["name"]], p.input_tokens)["applies"] else ""
        out.append(f"{mark} {r['name']:<19} {r['why']}{extra}")
    return out


def group_rank_flip() -> list[str]:
    out = ["=== 六、名次翻转：同一对模型，换个画像次序就反了 ==="]
    pair = ("gpt-5.6-sol", "claude-opus-5")
    for p in (BY_PROFILE["单轮只读问答"], BY_PROFILE["长稿压力画像"]):
        got = {r["name"]: r["total"] for r in rank(MODELS, p)}
        cheaper = min(pair, key=lambda n: got[n])
        dearer = max(pair, key=lambda n: got[n])
        out.append(f"{p.name:<10}{p.input_tokens:>9,} ＋ {p.output_tokens:<6,}  "
                   f"更便宜的是 {cheaper}：{_usd(got[cheaper])} ／ "
                   f"{dearer} {_usd(got[dearer])}（贵 {(got[dearer] / got[cheaper] - 1) * 100:.1f}%）")
    out.append("差别只来自一处：过线的那一家是**整单**加成，没过线的那一家全程一个价")
    return out


def readings() -> list[str]:
    lines: list[str] = []
    for part in (group_table(), group_one_call(BY_PROFILE["单轮只读问答"]),
                 group_cache(), group_long_tier(), group_feasible(), group_rank_flip()):
        lines.extend(part)
        lines.append("")
    lines.append("选型读数：六组全过 ｜ 离线自检通过")
    return lines


# ------------------------------------------------------- 夹具

def fixture_cases() -> list[tuple[str, bool]]:
    """十套夹具。**每条断言都要配一条反例**——只测正向会让规则越管越宽。"""
    sonnet = BY_NAME["claude-sonnet-5"]
    fable = BY_NAME["claude-fable-5-1"]
    terra = BY_NAME["gpt-5.6-terra"]
    rows = rank(MODELS, BY_PROFILE["整本书问答"])
    hit22 = cache_ledger(sonnet, CACHE_PREFIX, CACHE_CALLS, "5m", hit_rate=0.22)
    hit21 = cache_ledger(sonnet, CACHE_PREFIX, CACHE_CALLS, "5m", hit_rate=0.21)
    mis = cache_ledger(sonnet, CACHE_PREFIX, CACHE_CALLS, "5m", hit_rate=0.0)
    short = {r["name"]: r["total"] for r in rank(MODELS, BY_PROFILE["单轮只读问答"])}
    long_ = {r["name"]: r["total"] for r in rank(MODELS, BY_PROFILE["长稿压力画像"])}
    one = call_cost(terra, _p(272_001, 8_000))["total"]
    two = call_cost(terra, _p(136_000, 4_000))["total"] * 2
    return [
        ("表非空且两家", len(MODELS) == 8 and len({m.vendor for m in MODELS}) == 2),
        ("真表关系全对", violations() == []),
        ("每行都有出处", all(m.source in SOURCES and m.cutoff for m in MODELS)),
        ("拐点 2 与 3", cache_breakeven_calls(sonnet, "5m") == 2
         and cache_breakeven_calls(sonnet, "1h") == 3),
        ("低读价那族仍第 2 次", cache_breakeven_calls(fable, "5m") == 2),
        ("命中率底线对得上",
         abs(cache_breakeven_hit_rate(sonnet, "5m") - 0.25 / 1.15) < 1e-12
         and abs(cache_breakeven_hit_rate(sonnet, "1h") - 1.0 / 1.9) < 1e-12),
        ("有限次数以 21%/22% 为界", hit22["saving"] > 0 > hit21["saving"]),
        ("断点打错贵 25%", abs(mis["saving"] + 0.25 * mis["plain"]) < 1e-9),
        ("悬崖后切两单更便宜", two < one),
        ("装不下的留名且没全拦", [r["ok"] for r in rows] == [True] * 7 + [False]),
        ("名次翻转", short["gpt-5.6-sol"] < short["claude-opus-5"]
         and long_["claude-opus-5"] < long_["gpt-5.6-sol"]),
    ]


def self_test() -> int:
    cases = fixture_cases()
    bad = 0
    for label, ok in cases:
        print(f"  {'✓' if ok else '✗'} {label}")
        bad += 0 if ok else 1
    print(f"自检 {len(cases) - bad}/{len(cases)} 通过")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    for line in readings():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
