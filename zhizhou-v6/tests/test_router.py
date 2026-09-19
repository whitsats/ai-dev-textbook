# tests/test_router.py —— 名单上只有名字，能不能走要看这一次请求的形状
"""七组断言。这一份测的是**路由**（`app/router.py`），与网关那一份分开。

三组最值钱：

1. **名单写死一种方言时，带工具的请求会被排掉一半**——而「排掉」这件事必须报出来，
   否则名单上一半是摆设这件事，要等到前两个一起挂的那天才有人知道；
2. **超窗的候选必须窗口严格更大**：排一个窗口更小的，是把同一面墙再撞一次；
3. **同一批成员只换顺序，「末跳比首跳贵几倍」从 48.5 变成 0.10**——
   降级链的方向是一个价钱决定，不是一个能力决定。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.registry import BY_NAME  # noqa: E402
from app.router import (bigger_window, default_dialect, ladder_jump, plan,  # noqa: E402
                        price_ladder, shape_of, usable)
from app.select import BY_PROFILE  # noqa: E402

#: 按「能力从高到低」排的名单——配置里最常见的写法。
ROSTER = ["claude-fable-5-1", "gpt-6-astra", "claude-opus-5", "gpt-5.6-sol",
          "claude-sonnet-5", "gpt-5.6-terra", "gpt-5.6-luna", "claude-haiku-4-5"]


def test_形状只有两种而名字由网关配() -> None:
    assert shape_of(True) == "tools" and shape_of(False) == "plain"
    assert default_dialect("claude-opus-5") == "messages"
    assert default_dialect("gpt-6-astra") == "responses"
    assert default_dialect("gpt-5.6-luna") == "responses"


def test_名单只有名字时八模型两种形状全都能走() -> None:
    for tools in (True, False):
        p = plan(ROSTER[0], "messages", ROSTER[1:], tools=tools)
        assert len(p.chain) == len(ROSTER) - 1, f"tools={tools} 排掉了不该排的"
        assert p.excluded == []


def test_名单写死兼容层时带工具的请求被排掉一半() -> None:
    plain = plan(ROSTER[0], "messages", ROSTER[1:], tools=False, pin="chat")
    tools = plan(ROSTER[0], "messages", ROSTER[1:], tools=True, pin="chat")
    assert len(plain.chain) == 7 and plain.excluded == []
    assert len(tools.chain) == 3 and len(tools.excluded) == 4
    reasons = {why for _, why in tools.excluded}
    assert reasons == {"这一家在兼容层的图纸上没有这个形状"}


def test_同一个模型不带工具能走带工具不能() -> None:
    """**「谁能降级」不是模型的属性**，是「模型 × 方言 × 这一次的形状」的属性。"""
    assert usable("gpt-6-astra", "chat", tools=False)[0]
    ok, why = usable("gpt-6-astra", "chat", tools=True)
    assert not ok and why


def test_重复的候选不算降级() -> None:
    p = plan("gpt-5.6-terra", "responses", ["gpt-5.6-terra", "gpt-5.6-luna"])
    assert [c.model for c in p.chain] == ["gpt-5.6-luna"]
    assert p.excluded == [("gpt-5.6-terra/responses",
                           "与前面某一个重复——同一个候选试两遍不是降级")]


def test_不在登记表里的名字排掉而不是猜一个方言() -> None:
    p = plan("gpt-5.6-terra", "responses", ["不存在的模型"])
    assert p.chain == [] and p.excluded == [("不存在的模型/messages", "不在 6.1 的登记表里")]


def test_超窗的候选必须窗口严格更大() -> None:
    up = bigger_window("claude-haiku-4-5", same_price_or_cheaper=False)
    assert "claude-haiku-4-5" not in up
    assert len(up) == 7, "比 200K 大的有 7 个（含两家的一百万上下）"
    assert "gpt-5.6-terra" in up, "过线的那一家在名单里"
    assert all(BY_NAME[m].context > 200_000 for m in up)


def test_超窗候选再要求不比它贵只剩一个() -> None:
    assert bigger_window("claude-haiku-4-5") == ["gpt-5.6-luna"]
    assert bigger_window("gpt-5.6-luna") == [], "窗口最大的邻居没有「更大」可言"


def test_同一批成员只换顺序阶梯的方向就反了() -> None:
    profile = "单轮只读问答"
    rows = sorted(ROSTER, key=lambda m: _cost(m, profile))
    cheap = plan(rows[0], default_dialect(rows[0], True), rows[1:], tools=True)
    cap = plan(ROSTER[0], "messages", ROSTER[1:], tools=True)
    assert abs(ladder_jump(cheap, profile) - 48.55) < 0.5
    assert abs(ladder_jump(cap, profile) - 0.10) < 0.02
    assert sum(1 for x, y in zip(_steps(cap, profile), _steps(cap, profile)[1:]) if y > x) == 2


def test_阶梯的首跳是主候选不能漏() -> None:
    """第一版只算了降级那几跳——**漏掉首跳的阶梯看着也像阶梯**。"""
    rows = sorted(ROSTER, key=lambda m: _cost(m, "单轮只读问答"))
    p = plan(rows[0], default_dialect(rows[0], True), rows[1:], tools=True)
    ladder = price_ladder(p, "单轮只读问答")
    assert ladder[0][0].startswith(rows[0]), "第一行必须是主候选"
    assert len(ladder) == len(ROSTER)


def _cost(model: str, profile: str) -> float:
    from app.select import call_cost
    return call_cost(BY_NAME[model], BY_PROFILE[profile])["total"]


def _steps(p, profile: str) -> list[float]:
    return [v for _, v in price_ladder(p, profile)]
