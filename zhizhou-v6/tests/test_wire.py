# tests/test_wire.py —— 不需要密钥、不需要网络：这张翻译表自己能不能核
"""八组断言，测的都是**表自身**：落点数、形状层、正程与回程、以及三条校验。

两组最值钱：**把回程改错一处就红**（正程表自己看不出来）与
**把空的那格的原因抹掉就红**（抹掉之后，空看起来像漏填）。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.wire import (DIALECTS, FIELD_MAP, SHAPE_MAP, SOURCES, STOP_BACK,  # noqa: E402
                      STOP_LOSSY, STOP_MAP, WIRE_AS_OF, Block, Message, Request,
                      Tool, distinct_landings, shape_landings, stop_cells,
                      table_violations, validate)


def _req(**changes) -> Request:
    """一个模板请求：一轮问答 ＋ 一次已经回来的工具调用。"""
    base = dict(model="gpt-5.6-terra", system="你是知舟。",
                messages=(Message("user", (Block("text", text="查一下北京"),)),
                          Message("assistant", (Block("tool_call", call_id="c1",
                                                      name="search",
                                                      arguments={"q": "北京"}),)),
                          Message("user", (Block("tool_result", call_id="c1",
                                                 text="晴"),))),
                tools=(Tool("search", "查资料",
                            {"type": "object", "properties": {"q": {"type": "string"}}}),),
                max_output_tokens=1_024, dialect="chat")
    base.update(changes)
    return Request(**base)


# ---------------------------------------------------------------- 一、落点数

def test_八个字段三家各说各的没有一栏同名() -> None:
    assert len(FIELD_MAP) == 8 and all(len(v) == 3 for v in FIELD_MAP.values())
    assert set(distinct_landings().values()) == {3}, distinct_landings()


def test_形状层分三堆而不是八堆() -> None:
    """**名字全不同，而形状其实分三堆**——改代码要看的正是这一堆。"""
    land, shape = distinct_landings(), shape_landings()
    assert sorted(k for k, v in shape.items() if v == 3) == \
        sorted(["messages", "tools[].schema", "tool_result", "口径/版本"])
    assert sorted(k for k, v in land.items() if v == 3) == sorted(FIELD_MAP)
    assert WIRE_AS_OF == "2026-09-17", "抄协议的那一天是本章的一个读数，不许悄悄变"


def test_每一格都指得到一页官方文档() -> None:
    assert len(SOURCES) == 6, f"口径出处应当是 6 页官方文档，实得 {len(SOURCES)}"
    assert all(u.startswith("https://") for u in SOURCES.values())


# ---------------------------------------------------------------- 二、正程与回程

def test_真表上正程与回程逐格对得上() -> None:
    assert table_violations() == [], f"翻译表不符：{table_violations()}"
    assert len(stop_cells()) == 15, f"五档 × 三方 = 15 格，实得 {len(stop_cells())}"


def test_把回程改错一处只红那一条() -> None:
    """**正程表自己看不出来**：`length` 在两个表里各自都写得很整齐。"""
    broken = {d: dict(m) for d, m in STOP_BACK.items()}
    broken["chat"]["length"] = "end_turn"
    bad = table_violations(stop_back=broken)
    assert len(bad) == 1, f"只该报一处，实得 {len(bad)}：{bad}"
    assert "length" in bad[0] and "chat" in bad[0]


def test_把空的那些格的原因抹掉也会红() -> None:
    """空的那两格如果不写原因，读的人会以为是漏填——而漏填与「这一家说不出来」是两件事。"""
    bad = table_violations(lossy={})
    assert len([m for m in bad if "却没有登记原因" in m]) == 2, bad
    assert any("stop_sequence" in m for m in bad) and any("refusal" in m for m in bad)


# ---------------------------------------------------------------- 三、三条校验

def test_规范请求缺系统提示会被拦() -> None:
    bad = validate(_req(system="   "))
    assert len(bad) == 1 and "系统提示" in bad[0], bad


def test_工具结果指向一次不存在的调用会被拦() -> None:
    orphan = _req(messages=(Message("user", (Block("tool_result", call_id="c9",
                                                   text="晴"),)),))
    bad = validate(orphan)
    assert any("没有这一次调用" in m for m in bad), bad


def test_工具的结构不是对象会被拦() -> None:
    bad = validate(_req(tools=(Tool("search", "查资料",
                                    {"type": "string", "properties": {}}),)))
    assert any("不是对象" in m for m in bad), bad


def test_方言名写错会被拦() -> None:
    bad = validate(_req(dialect="chatgpt"))
    assert any("未知方言" in m for m in bad), bad
    assert STOP_MAP["tool_call"]["responses"] == "completed", \
        "这一格是本章最重的一条读数：它读不出「要调工具」"
    assert set(STOP_LOSSY) and all("/" in k for k in STOP_LOSSY), \
        "每条缺失都要写成「方言/规范档」，否则读数组数不出空与撞车各几格"
    assert set(STOP_BACK) == set(DIALECTS)
