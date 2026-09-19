# tests/agent/test_tools.py —— 不需要模型凭据，也不需要数据库
import json

from app.agent.tools.zhizhou import build

DRAFT = {"article_id": 42, "body": "改后的正文"}


def test_六个工具里两个是写操作():
    reg = build(user_id=7)
    assert [s["name"] for s in reg.specs()] == [
        "search_article", "read_article", "articles", "get_tags", "create_draft", "publish_article"]
    assert sum(1 for t in reg.tools.values() if t.access == "write") == 2


def test_每个定义都关得住多余字段():
    """严格工具调用的前提：additionalProperties=False，且必填项齐全。"""
    for spec in build(user_id=7).specs():
        schema = spec["input_schema"]
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) <= set(schema["properties"])


def test_越权读在取数据之前被拒():
    reg = build(user_id=7)
    r = reg.call("read_article", {"article_id": 43})      # 43 的作者是 9
    assert not r.ok and "无权" in r.error and reg.executed == []


def test_非法参数在调用之前被拒():
    reg = build(user_id=7)
    for args, kind in [
        ({"article_id": 0}, "范围越界"),
        ({"article_id": "42"}, "类型错"),
        ({"article_id": 42, "extra": 1}, "多出字段"),
    ]:
        r = reg.call("read_article", args)
        assert not r.ok and kind in r.error and reg.executed == []


def test_写操作没有幂等键就不执行():
    reg = build(user_id=7)
    r = reg.call("create_draft", DRAFT, allow_write=True)
    assert not r.ok and "幂等键" in r.error and reg.executed == []


def test_同一幂等键重跑只写一次():
    reg = build(user_id=7)
    first = reg.call("create_draft", DRAFT, idem="s3-create", allow_write=True)
    again = reg.call("create_draft", DRAFT, idem="s3-create", allow_write=True)
    assert first.ok and again.ok and reg.executed == ["create_draft"]


def test_结果超上限时截断并注明原文长度():
    reg = build(user_id=7)
    r = reg.call("read_article", {"article_id": 42})
    raw = len(json.dumps(r.data, ensure_ascii=False))
    assert len(r.payload()) < raw and "已截断" in r.payload() and str(raw) in r.payload()


def test_工具错误带可重试标记():
    reg = build(user_id=7)
    r = reg.call("publish_article", {"article_id": 42}, idem="s1", allow_write=True)
    assert not r.ok and r.retryable is False and "先调 create_draft" in r.error


def test_检索词像整句任务时给出可执行的建议():
    reg = build(user_id=7)
    r = reg.call("search_article", {"q": "帮我找一篇讲刷新令牌的文章"})
    assert not r.ok and "关键词" in r.error


def test_两方言用的是同一份定义():
    """规范形 `input_schema` 与 OpenAI 形 `parameters` 必须同源，否则一边改了另一边没改。"""
    reg = build(user_id=7)
    canon, oai = reg.specs(), reg.specs_openai()
    assert [s["name"] for s in canon] == [t["name"] for t in oai]
    assert all(c["input_schema"] == t["parameters"] for c, t in zip(canon, oai))
    assert all(t["parameters"]["additionalProperties"] is False for t in oai)
