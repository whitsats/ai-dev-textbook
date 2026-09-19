# tests/llm/test_tokens.py —— 不需要模型凭据与数据库
from app.llm.budget import ContextBudget, cacheable_prefix
from app.llm.tokens import Count, Counter, Prompt


def chars(s: str) -> list[int]:
    """按字符切分的假编码器：要断言的是行为，不是真实分词结果。"""
    return [ord(c) for c in s]


def test_逐字相同的段落只计一次():
    asked: list[str] = []
    c = Counter(lambda s: asked.append(s) or len(s), len)
    p = Prompt({"tools": "T" * 10, "system": "S" * 5, "messages": "M"})
    first, second = c.report(p), c.report(p)
    assert len(asked) == 3 and c.hits == 3          # 第二遍一次都没问
    assert first.parts == second.parts


def test_前缀顺序决定可命中的长度():
    a, b = "现在是 21:04。", "现在是 21:05。"
    good = (Prompt({"tools": "T" * 10, "system": "S" * 5 + a, "messages": "M"}),
            Prompt({"tools": "T" * 10, "system": "S" * 5 + b, "messages": "M"}))
    bad_order = ("system", "tools", "messages")
    bad = (Prompt({"system": a + "S" * 5, "tools": "T" * 10, "messages": "M"}, bad_order),
           Prompt({"system": b + "S" * 5, "tools": "T" * 10, "messages": "M"}, bad_order))
    assert cacheable_prefix(chars, *[x.serialize() for x in good]) == 23   # 10＋5＋8
    assert cacheable_prefix(chars, *[x.serialize() for x in bad]) == 8     # 只剩时间戳里相同的 8 个字


def test_输出预留占窗口():
    b = ContextBudget(window=100, max_output=20)
    assert b.check(Count({"messages": 80})).fits is True    # 80＋20 恰好占满
    assert b.check(Count({"messages": 81})).fits is False


def test_水位线按比例触发():
    b = ContextBudget(window=100, max_output=0, water=0.8)
    assert b.check(Count({"messages": 79})).over_water is False
    assert b.check(Count({"messages": 80})).over_water is True


def test_余量可以是负数而不是崩掉():
    v = ContextBudget(window=100, max_output=20).check(Count({"messages": 500}))
    assert v.fits is False and v.remaining == -420


def test_估算值必须标注来源():
    c = Counter(lambda s: 7, lambda s: 3)
    p = Prompt({"messages": "x"})
    assert c.report(p).source == "official" and c.report(p).input_tokens == 7
    assert c.report(p, exact=False).source == "local-estimate"


def test_空请求不崩():
    """没有段落可报的请求（例如全部被截掉）也要能拿到一个结果，而不是除零。"""
    c = Count({})
    assert c.input_tokens == 0 and c.heavy() == []
