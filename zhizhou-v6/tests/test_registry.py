# tests/test_registry.py —— 不需要密钥、不需要网络：这张表自己能不能核
"""六组断言，测的都是**表自身**：条数、乘法关系、例外、口径字段。

这一份里最重要的一组是第三组：**把表改坏一个数，检查会不会红**。
一张「永远绿」的检查与「没有检查」在输出上长得一样（`STYLE` 8.5），
所以每条断言都要有一条反例陪着。
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.registry import (AS_OF, BY_NAME, CACHE_READ_X, MODELS, SOURCES,  # noqa: E402
                          table_row, violations)


def _with(name: str, **changes):
    """拿真表做一份「只改了一处」的副本——检查要能指认出这一处。"""
    return tuple(replace(m, **changes) if m.name == name else m for m in MODELS)


# ---------------------------------------------------------------- 一、表本身

def test_表里有八个模型两家供应商() -> None:
    assert len(MODELS) == 8, f"八个模型，实际 {len(MODELS)}"
    assert {m.vendor for m in MODELS} == {"Anthropic", "OpenAI"}
    assert len(BY_NAME) == 8, "按名字取的那张索引必须与表一样长"
    assert AS_OF == "2026-09-17", "抄表日期是这一章的一个读数，不许悄悄变"


# ---------------------------------------------------------------- 二、乘法关系

def test_真表上的乘法关系一处不差() -> None:
    assert violations() == [], f"真表不符：{violations()}"


def test_每行都有出处与截止日期() -> None:
    for m in MODELS:
        assert m.source in SOURCES, f"{m.name} 的出处 {m.source!r} 不在 SOURCES 里"
        assert m.cutoff, f"{m.name} 没有知识截止日期——它是选型的一栏，不是装饰"


# ---------------------------------------------------------------- 三、改一个数就红

def test_改一个数检查就红而且只红那一条() -> None:
    bad = violations(_with("claude-sonnet-5", cache_read=0.30))
    assert len(bad) == 1, f"只该报一处，实得 {len(bad)}：{bad}"
    assert "claude-sonnet-5" in bad[0] and "缓存读价" in bad[0]


def test_把例外统一掉也会红() -> None:
    """Fable 5.1 的读价是 **0.025×**（官方脚注的例外）。

    如果有人为了「表更整齐」把它改成通用的 0.1×，检查必须说话——
    否则那条例外只是一句注释，而注释不拦截任何人。
    """
    bad = violations(_with("claude-fable-5-1",
                           cache_read=round(CACHE_READ_X * 10.0, 4)))
    assert any("claude-fable-5-1" in b and "缓存读价" in b for b in bad), \
        f"统一掉例外竟然没报：{bad}"


# ---------------------------------------------------------------- 四、档与例外

def test_一小时档只有一家有并且要不到会报错() -> None:
    assert BY_NAME["claude-opus-5"].write_price("1h") == 10.0
    assert BY_NAME["claude-opus-5"].write_price("5m") == 6.25
    try:
        BY_NAME["gpt-5.6-terra"].write_price("1h")
    except ValueError as exc:
        assert "没有 1 小时档" in str(exc), str(exc)
    else:
        raise AssertionError("另一方没有 1 小时档，要不到时必须报错，不许退回标准档")


def test_扁平行不留需要再解释一次的字段() -> None:
    row = table_row(BY_NAME["gpt-5.6-luna"])
    assert row["input"] == 0.20 and row["output"] == 1.20
    assert row["long_over"] == 272_000, "长档那条线是这一章的一个读数，必须在行里"
    assert table_row(BY_NAME["claude-haiku-4-5"])["long_over"] is None, \
        "另一家不分档，None 是「没有这一档」而不是「漏抄」"
