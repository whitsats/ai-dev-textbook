# tests/test_wiring.py —— 不需要密钥：装配、并行调用、人工确认、幂等、收口
"""这一份测的是**接线**，不是零件：真注册表 + 真策略 + 真循环，只把模型传输换成剧本。

它回答的问题与 3.10 的验收标准同源：没有凭据时，三条演示路径的骨架能不能跑完。
"""
from app.agent.loop import Budget, bind_tools, run_agent
from app.agent.policy import ModelPolicy
from app.agent.tools import zhizhou
from app.llm.client import Config, RawChat, ToolCall, chat


def call(*pairs: tuple[str, str]) -> RawChat:
    """造一个「模型响应」：一次响应里带一个或多个工具调用。"""
    return RawChat("", [ToolCall(f"c{i}", n, a) for i, (n, a) in enumerate(pairs)])


def fake_chat(*replies):
    """剧本传输层；剧本用完后重复最后一条。"""
    seq = list(replies)

    def transport(messages, cfg, **kw):
        got = seq.pop(0) if len(seq) > 1 else seq[0]
        return RawChat(got, [], 7) if isinstance(got, str) else got

    def chat_fn(messages, **kw):
        return chat(messages, transport=transport, **kw)
    return chat_fn


def run_with(replies, *, allow_write=False, approve=lambda n, a: False, max_steps=8,
             store=None, registry=None):
    reg = registry if registry is not None else zhizhou.build(7, store if store is not None else {})
    policy = ModelPolicy(config=Config(api_key="x"), system="s",
                         tool_specs=reg.specs_openai(), chat_fn=fake_chat(*replies))
    tools = bind_tools(reg, run_id="t1", allow_write=allow_write, approve=approve)
    return run_agent("任务", policy, tools, Budget(max_steps=max_steps)), reg


def test_模型给出最终答案就收口():
    r, _ = run_with([call(("read_article", '{"article_id": 42}')), "答案是……", "兜底"])
    assert r.reason == "模型给出最终答案" and r.answer == "答案是……"


def test_一次响应里的两个调用都执行且只问模型一次():
    r, reg = run_with([call(("get_tags", "{}"), ("articles", '{"mode":"count"}')), "答案", "兜底"])
    assert reg.executed == ["get_tags", "articles"]      # 两个都真的执行了
    assert r.calls == 2                                  # 但只问了模型两次（批次 + 收口）
    assert r.trace.entries[1].tokens == 0                # 第二个调用没有花词元
    assert "不再问模型" in r.trace.entries[1].thought


def test_坏参数变成一条结果而不是异常():
    r, _ = run_with([call(("read_article", "{oops")), "答案", "兜底"])
    assert "参数不是合法 JSON" in r.trace.entries[0].observation


def test_只读会话里写工具被权限档拦住():
    r, reg = run_with([call(("create_draft", '{"article_id":42,"body":"x"}')), "答案", "兜底"])
    assert reg.executed == [] and "权限不足" in r.trace.entries[0].observation


def test_发布必须人工确认且默认不批():
    asked: list[str] = []
    store: dict = {}
    r, reg = run_with([call(("create_draft", '{"article_id":42,"body":"x"}')),
                       call(("publish_article", '{"article_id":42}')), "答案", "兜底"],
                      allow_write=True, approve=lambda n, a: asked.append(n) or False,
                      registry=zhizhou.build(7, store))
    assert reg.executed == ["create_draft"]              # 发布没执行
    assert asked == ["publish_article"] and store["draft"]["status"] == "draft"
    assert "等待人工确认" in r.trace.entries[1].observation


def test_同一参数的写只执行一次():
    r, reg = run_with([call(("create_draft", '{"article_id":42,"body":"x"}')),
                       call(("create_draft", '{"article_id":42,"body":"x"}')), "答案", "兜底"],
                      allow_write=True)
    assert reg.executed == ["create_draft"]              # 第二次同参数被幂等键挡住


def test_收口时工具被收走():
    """收口那一次必须带 tool_choice=none，否则模型可以继续调工具、把上限绕过去。"""
    seen: list[str | None] = []
    reg = zhizhou.build(7, {})
    inner = fake_chat(call(("get_tags", "{}")), "兜底答案")

    def chat_fn(messages, **kw):
        seen.append(kw.get("tool_choice"))
        return inner(messages, **kw)

    policy = ModelPolicy(config=Config(api_key="x"), system="s",
                         tool_specs=reg.specs_openai(), chat_fn=chat_fn)
    r = run_agent("任务", policy, bind_tools(reg, run_id="t1"), Budget(max_steps=1))
    assert r.reason.startswith("步数上限") and seen == ["auto", "none"]
