"""`app/metrics.py` 的用例。这一组里最重的是「`None` 不是 0」那一族。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.metrics import (HIGHER, LOWER, REGISTRY, Cell, Metric, aggregate,  # noqa: E402
                         build_registry, coverage, evaluate, register)
from app.suite import Case, Suite  # noqa: E402


def test_注册表建成五条指标():
    reg = build_registry()
    assert list(reg) == ["exact_match", "contains", "refusal", "has_citation", "length_ok"]


def test_两个方向都合法():
    build_registry()
    assert all(m.direction in (HIGHER, LOWER) for m in REGISTRY.values())


def test_需要的输入缺一项就测不了():
    build_registry()
    assert REGISTRY["exact_match"].applicable({"output": "x"}) is False
    assert REGISTRY["exact_match"].applicable({"output": "x", "reference": "x"}) is True
    assert REGISTRY["has_citation"].applicable({"output": "x", "contexts": None}) is False
    # 空列表是「检索了、没检索到」——那是一个读数，不是没有读数
    assert REGISTRY["has_citation"].applicable({"output": "x", "contexts": []}) is True


def test_测不了的格子写的是None而不是0():
    build_registry()
    suite = Suite([Case("a", "问", reference=None)])
    cells = evaluate(suite, {"a": {"output": "答"}})
    assert [c.value for c in cells if c.metric == "exact_match"] == [None]


def test_宏平均的分母只数算得出的():
    build_registry()
    cells = [Cell("a", "length_ok", 1.0), Cell("b", "length_ok", None)]
    assert aggregate(cells)["length_ok"] == 1.0


def test_记零的口径会把它算进分母():
    build_registry()
    cells = [Cell("a", "length_ok", 1.0), Cell("b", "length_ok", None)]
    assert abs(aggregate(cells, as_zero=True)["length_ok"] - 0.5) < 1e-12


def test_覆盖率把两个数一起报():
    build_registry()
    suite = Suite([Case("a", "问", reference="答")])
    cells = evaluate(suite, {"a": {"output": "答", "contexts": ["片"]}})
    cov = coverage(cells)
    assert cov["exact_match"] == {"measured": 1, "unmeasured": 0}
    assert cov["has_citation"] == {"measured": 1, "unmeasured": 0}


def test_指标重名要报错():
    build_registry()
    try:
        register(Metric("exact_match", HIGHER, ("output",), lambda r: 0.0))
    except ValueError as exc:
        assert "重名" in str(exc)
    else:
        raise AssertionError("同名指标应当报错——静默覆盖会把两个指标变成一个")


def test_方向不合法要报错():
    build_registry()
    try:
        register(Metric("乱七八糟", "up", ("output",), lambda r: 0.0))
    except ValueError as exc:
        assert "方向" in str(exc)
    else:
        raise AssertionError("方向不合法应当报错")


def test_拒答指标两头都算():
    build_registry()
    fn = REGISTRY["refusal"].fn
    assert fn({"output": "无法回答", "reference": "（无法回答）"}) == 1.0
    assert fn({"output": "随便答", "reference": "（无法回答）"}) == 0.0
    assert fn({"output": "comments", "reference": "comments"}) == 1.0
    # 不该拒而拒了，同样算错
    assert fn({"output": "无法回答这个问题", "reference": "comments"}) == 0.0


def test_只缺参考答案时长度指标照算():
    build_registry()
    cells = evaluate(Suite([Case("a", "问", reference=None)]),
                     {"a": {"output": "短"}})
    assert [c.value for c in cells if c.metric == "length_ok"] == [1.0]
