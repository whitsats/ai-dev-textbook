"""`app/gate.py` 的用例。这一组的重点是**「不是通过」的那几档**。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.gate import (EMPTY, PASS, REGRESS, TOO_COARSE, UNDERPOWERED, Gate,  # noqa: E402
                      Report, ci_cost, detectable, diff, judge, noise_band, offsetting,
                      resolution)
from app.metrics import HIGHER, LOWER  # noqa: E402


def test_分辨率就是n分之一():
    assert abs(resolution(18) - 1 / 18) < 1e-12
    assert abs(resolution(24) - 1 / 24) < 1e-12


def test_分辨率对零条没有定义():
    try:
        resolution(0)
    except ValueError:
        return
    raise AssertionError("0 条上的分辨率没有定义，应当报错")


def test_同一批题上看得见与看不见的边界():
    assert detectable(18, 0.0556) is True
    assert detectable(18, 0.0417) is False
    # 边界算看得见：1/18 正好落在线上
    assert detectable(18, 1 / 18) is True


def test_零条判empty而不是pass():
    gate = Gate("m", HIGHER, 0.5)
    assert judge(gate, 0.9, 0) == EMPTY
    assert EMPTY != PASS


def test_样本不够判underpowered():
    gate = Gate("m", HIGHER, 0.5, min_cases=8)
    assert judge(gate, 0.9, 6) == UNDERPOWERED


def test_小于分辨率的变化判看不见():
    gate = Gate("m", HIGHER, 0.6, min_cases=8)
    assert judge(gate, 0.6111, 18) == TOO_COARSE


def test_超过抖动带且可分辨才判退步():
    gate = Gate("m", HIGHER, 0.6, noise=0.1111, min_cases=8)
    assert judge(gate, 0.4444, 18) == REGRESS


def test_落在抖动带里的一格变化不算退步():
    gate = Gate("m", HIGHER, 0.6, noise=0.1111, min_cases=8)
    assert judge(gate, 0.5444, 18) == PASS


def test_容差为零会把噪声当成退步():
    strict = Gate("m", HIGHER, 0.6, min_cases=8)
    assert judge(strict, 0.5444, 18) == REGRESS


def test_方向写反门就是反的():
    value, n = 0.4444, 18
    assert judge(Gate("m", HIGHER, 0.6, noise=0.1111, min_cases=8), value, n) == REGRESS
    assert judge(Gate("m", LOWER, 0.6, noise=0.1111, min_cases=8), value, n) == PASS


def test_方向不合法要报错():
    try:
        Gate("m", "up", 0.5)
    except ValueError:
        return
    raise AssertionError("方向只允许 higher / lower")


def test_抖动带是极差():
    assert abs(noise_band([0.4444, 0.3889, 0.3333]) - 0.1111) < 1e-4


def test_没有跑记录量不出抖动():
    try:
        noise_band([])
    except ValueError:
        return
    raise AssertionError("没有记录就量不出抖动，应当报错")


def test_总分一样而条目翻面会被认出来():
    before = Report("b", {"c1": 1, "c2": 0, "c3": 1, "c4": 0})
    after = Report("a", {"c1": 0, "c2": 1, "c3": 0, "c4": 1})
    assert offsetting(before, after) is True
    flips = diff(before, after)
    assert flips["improved"] == ["c2", "c4"]
    assert flips["regressed"] == ["c1", "c3"]


def test_总分真变了就不是抵消():
    before = Report("b", {"c1": 1, "c2": 0})
    after = Report("a", {"c1": 0, "c2": 0})
    assert offsetting(before, after) is False


def test_加了题与删了题都记得下来():
    before = Report("b", {"c1": 1, "c2": 0})
    after = Report("a", {"c1": 1, "c3": 1})
    flips = diff(before, after)
    assert flips["added"] == ["c3"] and flips["removed"] == ["c2"]


def test_空报告的总分是零():
    assert Report("e", {}).total() == 0.0


def test_ci的账随条数线性涨():
    a = ci_cost(18, 0.000903)
    b = ci_cost(36, 0.000903)
    assert abs(b["usd"] - 2 * a["usd"]) < 1e-9
    assert b["resolution"] < a["resolution"]


def test_尝试次数至少一次():
    try:
        ci_cost(18, 0.000903, attempts=0)
    except ValueError:
        return
    raise AssertionError("一次都没跑的账没有意义")
