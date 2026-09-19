# tests/agent/test_orchestrator.py —— 不需要密钥：交接单校验、预算切分、失败隔离、重复与缺口
"""这一份测的是 3.7 的契约。四组：

1. **交接单**：四件缺一不可、空工具集要被拒、写权限必须写在 boundaries 里、重复的份要被拦；
2. **预算**：切分之和不超总预算、每份都够用、预算不够时当场报错、档位由规则决定；
3. **执行**：一个子代理跑挂不影响其它、工具子集真的只是子集、空回答不算产出；
4. **汇聚**：重复内容能被认出、缺口能被列出。

**并行测试必须按角色分发剧本**：子代理是并行跑的，一个共享的剧本队列会被交错消费，
测试就变成了「有时通过」。所以这里的传输层先看消息里的角色名，再给对应那一份答案
——这也顺手证明了「每个子代理确实在自己的上下文里跑」。
"""
from app.agent import orchestrator as orch
from app.agent.orchestrator import Handoff, HandoffError, ladder_for, orchestrate, split_budget
from app.agent.policy import EMPTY_REPLY
from app.agent.tools import zhizhou
from app.llm.client import Config, RawChat, ToolCall, chat

REGISTRY = lambda names: zhizhou.build_for(7, {}, names)          # noqa: E731
SEARCH = ToolCall("c0", "search_article", '{"q":"刷新令牌"}')


def by_role(answers: dict[str, str], *, tool=SEARCH):
    """按角色分发剧本：角色名在子代理的提示里（「你是「甲」」）。"""
    def transport(messages, cfg, **kw):
        text = "\n".join(str(m.get("content") or "") for m in messages)
        for role, answer in answers.items():
            if f"你是「{role}」" in text:
                used = sum(1 for m in messages if m.get("role") == "tool")
                return RawChat(answer, [], 5) if used else RawChat("", [tool], 5)
        return RawChat(f"（没有匹配到角色的请求：{text[:40]}）", [], 5)
    return transport


def chat_for(answers: dict[str, str], *, tool=SEARCH):
    def chat_fn(messages, **kw):
        return chat(messages, transport=by_role(answers, tool=tool), **kw)
    return chat_fn


def handoff(role: str = "检索者", *, tools=("search_article", "read_article"), **kw) -> Handoff:
    base = dict(objective=f"查清第 {role} 条线索", deliverable="三条要点，每条一行",
                boundaries="不要碰发布；只回答被问到的那一块",
                max_steps=4, max_tokens=3_000)
    base.update(kw)
    return Handoff(role=role, tools=tuple(tools), **base)


def run(handoffs, answers, **kw):
    return orchestrate("目标", handoffs, config=Config(api_key="x"), registry_factory=REGISTRY,
                       system="s", chat_fn=chat_for(answers), **kw)


# ------------------------------------------------------------------ 1. 交接单

def test_交接单四件缺一不可() -> None:
    for field in ("objective", "deliverable", "tools", "boundaries"):
        bad = handoff(**{field: "  " if field != "tools" else ()})
        try:
            bad.validate()
        except HandoffError as exc:
            assert field in str(exc), (field, str(exc))
        else:
            raise AssertionError(f"{field} 空了也必须被拦下")


def test_写权限必须写在边界里() -> None:
    """提权是「写在单子上的一行」，不是调用方记得去做的一件事。"""
    try:
        handoff(allow_write=True).validate()
    except HandoffError as exc:
        assert "boundaries" in str(exc)
    else:
        raise AssertionError("提权必须同时写明写什么")
    handoff(allow_write=True, boundaries="写草稿，但不得发布", tools=("create_draft",)).validate()


def test_两份一样的交接单就是同一件事做两遍() -> None:
    """指纹只看目标/交付/工具/边界——角色名不同不算不同。"""
    same = dict(objective="查清刷新令牌讲了哪几种做法", deliverable="三条要点，每条一行",
                boundaries="不要碰发布", tools=("search_article",))
    a, b = Handoff(role="甲", **same), Handoff(role="乙", **same)
    assert a.fingerprint() == b.fingerprint()
    try:
        run([a, b], {"甲": "x", "乙": "y"})
    except HandoffError as exc:
        assert "重复" in str(exc)
    else:
        raise AssertionError("重复的交接单必须在花钱之前被拦下")


def test_一份交接单都没有就不是编排() -> None:
    try:
        split_budget([], total=10_000)
    except HandoffError as exc:
        assert "退化成" in str(exc)
    else:
        raise AssertionError("空交接单列表必须报错")


# ------------------------------------------------------------------ 2. 预算

def test_预算切分的和不超过总额且每份都够用() -> None:
    lead, subs = split_budget([handoff("甲"), handoff("乙"), handoff("丙")], total=20_000)
    assert lead.max_tokens + sum(b.max_tokens for b in subs) <= 20_000
    assert all(b.max_tokens >= 500 for b in subs)
    assert lead.max_tokens == 5_000                  # 主管默认留 25%


def test_预算不够切时当场报错而不是悄悄少切() -> None:
    hs = [handoff(f"角色{i}") for i in range(10)]
    try:
        split_budget(hs, total=800)
    except HandoffError as exc:
        assert "预算不够切" in str(exc)
    else:
        raise AssertionError("预算不够必须报错，不能偷偷把某一份切到 0")


def test_复杂度档位由规则决定而不是让模型自己判() -> None:
    assert ladder_for("simple") == (1, 3)
    assert ladder_for("compare") == (3, 10)
    assert ladder_for("complex") == (6, 15)
    try:
        ladder_for("看起来挺复杂")
    except HandoffError as exc:
        assert "档位" in str(exc)
    else:
        raise AssertionError("未知档位必须报错")


# ------------------------------------------------------------------ 3. 执行

def test_工具子集真的只是子集() -> None:
    reg = REGISTRY(("search_article",))
    assert sorted(reg.tools) == ["search_article"]
    assert reg.call("read_article", {"article_id": 42}).error       # 没注册就是未知工具
    try:
        REGISTRY(("不存在的工具",))
    except KeyError as exc:
        assert "不存在" in str(exc)
    else:
        raise AssertionError("交接单里写错工具名必须当场报错")


def test_一个子代理跑挂不影响其它() -> None:
    def transport(messages, cfg, **kw):
        text = "\n".join(str(m.get("content") or "") for m in messages)
        if "你是「甲」" in text:
            raise RuntimeError("这个子代理炸了")
        return by_role({"乙": "乙的结论"})(messages, cfg, **kw)

    out = orchestrate("目标", [handoff("甲"), handoff("乙")], config=Config(api_key="x"),
                      registry_factory=REGISTRY, system="s",
                      chat_fn=lambda messages, **kw: chat(messages, transport=transport, **kw))
    status = {r.role: r.status for r in out.results}
    assert status == {"甲": "failed", "乙": "ok"}
    assert out.results[0].reason.startswith("RuntimeError")
    assert out.gaps() == ["甲"] and "乙的结论" in out.answer


def test_占位文本不算产出() -> None:
    """模型没给内容时策略层会填一句占位话；**不认它，空回答就会以 ok 混进汇总**。"""
    out = run([handoff("甲")], {"甲": EMPTY_REPLY})
    assert out.results[0].status == "empty"
    assert out.gaps() == ["甲"] and "未交回内容的角色：甲" in out.answer


def test_被预算收口与确实没找到是两种结论() -> None:
    """"收口"的份**不是空的**（策略层会给一段已有观察的摘要），所以它既不是 ok 也不是缺口。"""
    out = run([handoff("甲", max_steps=1)], {"甲": ""})
    assert out.results[0].status == "timeout"
    assert "收口" in out.results[0].reason
    assert out.degraded() == ["甲"] and out.gaps() == []
    assert "被预算提前收口" in out.answer


def test_预算是子代理的硬上限而不是共享池() -> None:
    """共享池的后果：先跑完的把预算吃光，后面那些在「预算耗尽」里收口——
    一次资源调度错误会被当成一次调研结论。"""
    out = run([handoff("甲"), handoff("乙")], {"甲": "甲找到了三条", "乙": "乙也找到了三条"},
              total_tokens=20_000)
    assert len(out.results) == 2
    assert all(r.tokens <= 8_000 for r in out.results)
    assert all(r.status == "ok" for r in out.results)


# ------------------------------------------------------------------ 4. 汇聚

def test_一个子代理跑挂前的调用也要记账() -> None:
    """状态 failed 的行不能记成 0 次调用——它炸之前花掉的调用是真的花掉了。

    修之前那一行是「failed｜0 次调用｜396 词元」：同一行的两个数互相矛盾，
    而它正好是「这次编排一共花了多少」的加数之一。
    """
    def transport(messages, cfg, **kw):
        text = "\n".join(str(m.get("content") or "") for m in messages)
        if "你是「甲」" in text:
            if any(m.get("role") == "tool" for m in messages):
                raise RuntimeError("第二跳被限流")
            return RawChat("", [SEARCH], 5)
        return by_role({"乙": "乙的结论"})(messages, cfg, **kw)

    out = orchestrate("目标", [handoff("甲"), handoff("乙")], config=Config(api_key="x"),
                      registry_factory=REGISTRY, system="s",
                      chat_fn=lambda messages, **kw: chat(messages, transport=transport, **kw))
    bad = next(r for r in out.results if r.role == "甲")
    assert (bad.status, bad.calls, bad.tokens) == ("failed", 1, 5)
    assert out.tokens == sum(r.tokens for r in out.results) >= 5


def test_主管汇总炸了也要交出子代理的结论() -> None:
    """主管那一步是**最后一步**：它炸了，前面几份子代理的钱就白花了（实测那次是限流 429）。
    降级退到拼接汇总，并把原因记在账上——不假装成功，也不把已有的东西丢掉。"""
    def synth(goal, results):
        raise RuntimeError("限流: 429")

    out = run([handoff("甲")], {"甲": "甲的结论"}, synthesize=synth)
    assert "甲的结论" in out.answer
    assert "汇总那一步失败了" in out.answer
    assert out.report()["lead_error"].startswith("RuntimeError")


def test_重复内容能被认出() -> None:
    out = run([handoff("甲"), handoff("乙")], {"甲": "三条一样的结论", "乙": "三条一样的结论"})
    assert out.duplicates() == [("甲", "乙")]


def test_汇总不调模型也能给出缺口() -> None:
    out = run([handoff("甲"), handoff("乙")], {"甲": "甲的结论", "乙": ""})
    assert "目标：" in out.answer and "## 甲" in out.answer
    assert "未交回内容的角色：乙" in out.answer
    report = out.report()
    assert report["tokens"]["total"] == out.tokens >= report["tokens"]["sub"] > 0
    assert report["status"] == {"甲": "ok", "乙": "empty"}
    assert report["gaps"] == ["乙"] and report["degraded"] == []


def test_并发上限不会因为角色多就无限制开线程() -> None:
    hs = [handoff(f"角色{i}", objective=f"查清第 {i} 块线索") for i in range(5)]
    answers = {f"角色{i}": f"结论{i}" for i in range(5)}
    out = orchestrate("目标", hs, config=Config(api_key="x"), registry_factory=REGISTRY,
                      system="s", max_workers=2, chat_fn=chat_for(answers))
    assert len(out.results) == 5
    assert sorted(r.answer for r in out.results) == sorted(answers.values())


def test_官方档位与编排器默认值对得上() -> None:
    """三条档位是官方给的经验值，编排器的默认上限不能比它松。"""
    agents, calls = ladder_for("complex")
    assert agents >= 6 and calls >= 15
    assert [n for n, _, _ in orch.EFFORT_LADDER] == ["simple", "compare", "complex"]
