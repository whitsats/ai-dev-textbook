# tests/test_select.py —— 不需要密钥、不需要网络：算出来的账能不能复算
"""七组断言，测的是**算账那一层**：四栏自洽、缓存两个拐点、悬崖、装不下、名次翻转。

这一层全是纯算术，所以它有一个好东西：**每个结论都能用手再算一遍**。
测试里因此尽量写「手工算出来的那个数」，而不是「上次跑出来的那个数」——
后者只是把实现抄了一遍，抄错了也一起错。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.registry import BY_NAME, MODELS  # noqa: E402
from app.select import (BY_PROFILE, PROFILES, TaskProfile, cache_breakeven_calls,   # noqa: E402
                        cache_breakeven_hit_rate, cache_ledger, call_cost, feasible,
                        long_tier, rank, unit_prices)


def _approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) < tol


def _p(inp: int, out: int) -> TaskProfile:
    """测试里临时造的画像。`source` 写成「测试用」——**它不该冒充量出来的数据**。"""
    return TaskProfile("测试用", inp, out, "测试用：只在断言里出现，不进任何读数")


# ---------------------------------------------------------------- 一、四笔账

def test_四栏加起来等于总数() -> None:
    p = BY_PROFILE["单轮只读问答"]
    c = call_cost(BY_NAME["claude-sonnet-5"], p)
    assert _approx(c["input"], 3_730 * 2.0 / 1_000_000)
    assert _approx(c["output"], 131 * 10.0 / 1_000_000)
    assert _approx(c["long_surcharge"], 0.0), "这一笔没过线，加成必须是 0"
    assert _approx(c["total"], c["input"] + c["output"]), "不批量时总数就是两栏之和"


def test_批量按整单减半() -> None:
    p = BY_PROFILE["单轮只读问答"]
    m = BY_NAME["gpt-5.6-terra"]
    full = call_cost(m, p)["total"]
    half = call_cost(m, p, batch=True)["total"]
    assert _approx(half, full * 0.5), f"批量该减半：{full} → {half}"


# ---------------------------------------------------------------- 二、长档

def test_长档按整单算并且是悬崖不是斜坡() -> None:
    m = BY_NAME["gpt-5.6-terra"]
    before = call_cost(m, _p(272_000, 8_000))["total"]
    after = call_cost(m, _p(272_001, 8_000))["total"]
    assert _approx(before, 0.64), f"272,000 那一单该是 0.64 美元，实得 {before}"
    assert _approx(after, 1.232004), f"272,001 那一单该是 1.232004，实得 {after}"
    assert (after - before) / before > 0.9, "多一个词元该让整单涨九成以上"
    assert unit_prices(m, 272_000) == (2.0, 12.0)
    assert unit_prices(m, 272_001) == (4.0, 18.0)
    assert unit_prices(BY_NAME["claude-opus-5"], 900_000) == (5.0, 25.0), \
        "另一家的 1M 窗口全程一个价——这正是两家「1M 上下文」不是一回事的地方"


def test_切两单是唯一能在悬崖后省钱的修法() -> None:
    m = BY_NAME["gpt-5.6-terra"]
    one = call_cost(m, _p(272_001, 8_000))["total"]
    two = call_cost(m, _p(136_000, 4_000))["total"] * 2
    assert _approx(two, 0.64), f"两单各 136,000 应与「刚好不过线」同价，实得 {two}"
    assert two < one, "切两单必须比过线的整单便宜"


# ---------------------------------------------------------------- 三、缓存

def test_缓存拐点是第二次与第三次() -> None:
    sonnet = BY_NAME["claude-sonnet-5"]
    assert cache_breakeven_calls(sonnet, "5m") == 2
    assert cache_breakeven_calls(sonnet, "1h") == 3
    fable = BY_NAME["claude-fable-5-1"]
    assert cache_breakeven_calls(fable, "5m") == 2, "低读价那一族仍是第 2 次"


def test_命中率底线与有限次数的粗线之差() -> None:
    sonnet = BY_NAME["claude-sonnet-5"]
    assert _approx(cache_breakeven_hit_rate(sonnet, "5m"), 0.25 / 1.15, 1e-12)
    assert _approx(cache_breakeven_hit_rate(sonnet, "1h"), 1.0 / 1.9, 1e-12)
    hit22 = cache_ledger(sonnet, 2_510, 100, "5m", hit_rate=0.22)
    hit21 = cache_ledger(sonnet, 2_510, 100, "5m", hit_rate=0.21)
    assert hit22["saving"] > 0 > hit21["saving"], \
        f"100 次调用的分界该在 21%–22% 之间：22% → {hit22['saving']}，21% → {hit21['saving']}"


def test_断点打错地方比不缓存还贵四分之一() -> None:
    """命中率 0 就是官方文档点名的那个错误：断点打在每次都会变的那一块上。"""
    led = cache_ledger(BY_NAME["claude-sonnet-5"], 2_510, 100, "5m", hit_rate=0.0)
    assert led["writes"] == 100 and led["reads"] == 0
    assert _approx(led["saving"], -0.25 * led["plain"]), f"该贵 25%：{led}"


# ---------------------------------------------------------------- 四、可行与排序

def test_装不下的被挑出来而不是排到最后() -> None:
    p = BY_PROFILE["整本书问答"]
    ok, why = feasible(BY_NAME["claude-haiku-4-5"], p)
    assert not ok and "超窗" in why, why
    tall = _p(10_000, 70_000)
    ok2, why2 = feasible(BY_NAME["claude-haiku-4-5"], tall)
    assert not ok2 and "最大输出" in why2, why2
    rows = rank(MODELS, p)
    assert [r["ok"] for r in rows] == [True] * 7 + [False], "装得下的排前面，装不下的留名"
    assert sum(1 for r in rows if r["ok"]) == 7, "反向守：不能全被判成装不下"


def test_长档把两家的名次翻了一遍() -> None:
    """本章最重要的一条读数：**同一对模型，换个画像名次就反过来**。

    单轮只读问答（输入占 96.6%）时 sol 更便宜；长稿画像过线之后，
    只是因为它那一档整单 ×2/×1.5，opus5 反而更便宜。
    """
    short = {r["name"]: r["total"] for r in rank(MODELS, BY_PROFILE["单轮只读问答"])}
    long_ = {r["name"]: r["total"] for r in rank(MODELS, BY_PROFILE["长稿压力画像"])}
    assert short["gpt-5.6-sol"] < short["claude-opus-5"]
    assert long_["claude-opus-5"] < long_["gpt-5.6-sol"]
    assert _approx(long_["claude-opus-5"], 1.560005), long_["claude-opus-5"]


def test_画像是量出来的还是合成的必须写在明面上() -> None:
    assert len(PROFILES) == 4
    assert "合成" in BY_PROFILE["长稿压力画像"].source, "合成画像必须自己说是合成的"
    assert "3.10" in BY_PROFILE["单轮只读问答"].source, "量出来的要写清是哪一章量的"
    for p in PROFILES:
        assert p.source, f"{p.name} 没有来源——那就成了一个看着像量出来的数"
