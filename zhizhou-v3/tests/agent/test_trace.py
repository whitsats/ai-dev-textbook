# tests/agent/test_trace.py —— 不需要密钥：span 契约、指标口径、评测集与回归门
"""这一份测的是 3.9 的契约。六组：

1. **span 契约**：名字、父子、`gen_ai.*` 属性名；`error.type` 只在小集合里取值；
2. **内容默认不记**：默认只留指纹与长度，`capture_content=True` 才写正文（与 3.8 同一条边界）；
3. **一次逻辑操作一棵 span**：重试算在同一棵里，`attempts` 是属性而不是新 span；
4. **指标口径**：成功率、失败分布是有限档、分位不被长尾藏住、成本只在有单价时出现；
5. **有界**：记录不会只涨不落（进程活久了不能变成内存泄漏）；
6. **评测集与回归门**：题目质量可机检（正反两类都有），门在退步时真的响。
"""
import json
import os
import time
from pathlib import Path

from app.agent import trace as tr
from app.agent.loop import Budget, bind_tools, run_agent
from app.agent.policy import ModelPolicy
from app.agent.tools import zhizhou
from app.llm.client import ChatReply, Config, LlmError, LlmTransportError, RawChat, ToolCall, chat

EVAL = Path(__file__).resolve().parent / "eval_cases.jsonl"


def _run_with_chat_fn(chat_fn, *, tool_calls: bool = True, task: str = "读一下 42 号文章"):
    """跑一次带追踪的运行：真工具、真循环、真追踪器，只有模型是假的。"""
    cfg = Config(api_key="test")
    store: dict = {}
    reg = zhizhou.build(user_id=7, store=store)
    tracer = tr.Tracer()
    run = tracer.start_trace(task, run_id="t1")
    policy = ModelPolicy(config=cfg, system="你是知舟的助手。",
                         tool_specs=reg.specs_openai() if tool_calls else [],
                         chat_fn=chat_fn,
                         on_call=lambda info: tracer.record_model_call(run, agent_name="知舟", **info))
    tools = bind_tools(reg, run_id="t1", allow_write=True,
                       on_tool=lambda info: tracer.record_tool_call(run, **info))
    result = run_agent(task, policy, tools, Budget(max_steps=4, max_tokens=500))
    record = tracer.finish(run, reason=result.reason, steps=result.steps, calls=result.calls,
                           tokens=result.tokens, in_tokens=policy.in_tokens,
                           out_tokens=policy.out_tokens, answer_chars=len(result.answer or ""))
    return record, store, reg, tracer


def _two_step_chat(*, in_tokens: int = 30, out_tokens: int = 10, attempts: int = 1):
    """第一次调工具、第二次给答案的假模型。"""
    calls = {"n": 0}

    def chat_fn(messages, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return ChatReply("", [ToolCall("c0", "read_article", '{"article_id": 42}')],
                             in_tokens + out_tokens, attempts, "假模型", in_tokens, out_tokens)
        return ChatReply("令牌那篇讲了三种做法。", [], in_tokens + out_tokens, attempts,
                         "假模型", in_tokens, out_tokens)
    return chat_fn


# ------------------------------------------------------------------ 1. span 契约

def test_span树的名字与属性按语义约定来() -> None:
    record, _, _, _ = _run_with_chat_fn(_two_step_chat())
    assert record.spans[0].name == "invoke_agent 知舟"
    assert record.spans[0].attributes["gen_ai.operation.name"] == "invoke_agent"
    chats = record.spans_of(tr.CHAT)
    tools = record.spans_of(tr.EXECUTE_TOOL)
    assert [s.name for s in chats] == ["chat 假模型", "chat 假模型"]
    assert [s.name for s in tools] == ["execute_tool read_article"]
    assert chats[0].attributes["gen_ai.request.model"] == "假模型"
    assert chats[0].attributes["gen_ai.usage.input_tokens"] == 30
    assert chats[0].attributes["gen_ai.usage.output_tokens"] == 10
    assert chats[0].attributes["gen_ai.response.finish_reasons"] == ["tool_calls"]
    assert tools[0].attributes["gen_ai.tool.name"] == "read_article"
    assert tools[0].status == "ok"
    # 子 span 都挂在根上（本项目的操作没有嵌套），导出形状里有 parent_span_id
    assert all(s.parent_id == record.spans[0].span_id for s in record.spans[1:])
    otel = chats[0].to_otel()
    assert otel["status"] == "OK" and otel["kind"] == "CLIENT" and "attributes" in otel


def test_error_type只在小集合里取值() -> None:
    """`error.type` 是高基数就失去意义：按它分组会分出一堆只出现一次的柱子。"""
    _, _, reg, _ = _run_with_chat_fn(_two_step_chat(), tool_calls=False)
    tracer = tr.Tracer()
    run = tracer.start_trace("测失败档")
    tools = bind_tools(reg, run_id="t2", allow_write=True,
                       on_tool=lambda info: tracer.record_tool_call(run, **info))
    tools["read_article"]('{"article_id": "四十二"}')          # 类型不对（参数不合 schema）
    tools["create_draft"]('{"article_id": 42}')               # 缺必填
    tools["publish_article"]('{"article_id": 42}')            # 未获人工确认
    kinds = {s.attributes.get("error.type") for s in run.spans if s.status == "error"}
    assert kinds <= {"参数不合 schema", "未获人工确认"}, kinds
    assert kinds, "三类失败都要各留一棵 span（不然失败分布会缺柱）"
    assert all(s.name.startswith("execute_tool ") for s in run.spans if s.status == "error")


def test_工具异常也被记成一棵失败的span() -> None:
    record, _, _, _ = _run_with_chat_fn(_two_step_chat(), tool_calls=True)
    # 越权 id：授权钩子抛 ToolError，注册表把它变成一条失败结果（不是异常）
    tracer = tr.Tracer()
    run = tracer.start_trace("越权")
    reg = zhizhou.build(user_id=7, store={})
    tools = bind_tools(reg, run_id="t3", on_tool=lambda info: tracer.record_tool_call(run, **info))
    tools["read_article"]('{"article_id": 99}')
    span = run.spans[-1]
    assert span.status == "error" and span.attributes["error.type"] == "目标不存在"
    assert record.spans[0].status == "ok"                       # 另一次运行不受影响


# ------------------------------------------------------------------ 2. 内容是 opt-in

def test_内容默认不记只留指纹与长度() -> None:
    record, _, _, _ = _run_with_chat_fn(_two_step_chat())
    text = json.dumps([s.attributes for s in record.spans], ensure_ascii=False)
    assert "令牌那篇讲了三种做法" not in text, "默认模式把答案正文写进了属性"
    assert "gen_ai.output.messages" not in text
    chat0 = record.spans_of(tr.CHAT)[0]
    assert chat0.attributes["zhizhou.content.digest"] == tr.digest("")
    tool0 = record.spans_of(tr.EXECUTE_TOOL)[0]
    assert tool0.attributes["zhizhou.result.chars"] > 0         # 长度有，正文没有


def test_打开内容捕获才写正文() -> None:
    cfg = Config(api_key="test")
    reg = zhizhou.build(user_id=7, store={})
    tracer = tr.Tracer(capture_content=True)
    run = tracer.start_trace("开内容捕获")
    policy = ModelPolicy(config=cfg, system="s", tool_specs=reg.specs_openai(),
                         chat_fn=_two_step_chat(),
                         on_call=lambda info: tracer.record_model_call(run, **info))
    tools = bind_tools(reg, run_id="cap", allow_write=True,
                       on_tool=lambda info: tracer.record_tool_call(run, **info))
    run_agent("开内容捕获", policy, tools, Budget(max_steps=3))
    assert run.spans[0].attributes["gen_ai.input.messages"] == "开内容捕获"
    assert any("gen_ai.tool.call.result" in s.attributes for s in run.spans)


# ------------------------------------------------------------------ 3. 重试合并

def test_重试算在同一棵span里而不是多一棵() -> None:
    """官方原文：span SHOULD cover the duration of the logical operation with all retries。"""
    seen = {"n": 0}

    def transport(messages, cfg, **kw):
        seen["n"] += 1
        if seen["n"] == 1:
            raise LlmTransportError("限流", "429")              # 可重试
        return RawChat("好", [], 20, "stop", in_tokens=15, out_tokens=5)

    cfg = Config(api_key="test", max_attempts=2)
    started = None
    reply = chat([{"role": "user", "content": "hi"}], config=cfg, transport=transport)
    tracer = tr.Tracer()
    run = tracer.start_trace("重试")
    span = tracer.record_model_call(run, model=cfg.model, duration_ms=12.5, tokens=reply.tokens,
                                    in_tokens=reply.in_tokens, out_tokens=reply.out_tokens,
                                    attempts=reply.attempts)
    assert reply.attempts == 2 and started is None
    assert len(run.spans_of(tr.CHAT)) == 1, "重试不该多出一棵 span"
    assert span.attributes["zhizhou.attempts"] == 2
    # 重试那次请求也真的发了：计入这一次逻辑调用的词元里（账单不会替你省略它）
    assert span.attributes["gen_ai.usage.input_tokens"] == 15


# ------------------------------------------------------------------ 4. 指标口径

def _record(tracer, *, reason, steps, calls, tokens, in_tokens, out_tokens, tools=(), ms=10.0):
    run = tracer.start_trace("t")
    for name in tools:
        tracer.record_tool_call(run, tool=name, duration_ms=1.0, ok=True)
    tracer.record_model_call(run, model="m", duration_ms=2.0, tokens=tokens,
                             in_tokens=in_tokens, out_tokens=out_tokens)
    return tracer.finish(run, reason=reason, steps=steps, calls=calls, tokens=tokens,
                         in_tokens=in_tokens, out_tokens=out_tokens, duration_ms=ms)


def test_四类指标一次算完() -> None:
    tracer = tr.Tracer()
    _record(tracer, reason="模型给出最终答案", steps=2, calls=2, tokens=100, in_tokens=80,
            out_tokens=20, tools=("read_article",), ms=10)
    _record(tracer, reason="预算耗尽 → 收口", steps=8, calls=8, tokens=900, in_tokens=800,
            out_tokens=100, tools=("read_article", "read_article"), ms=30)
    _record(tracer, reason="卡死：连续 3 次相同动作 → 收口", steps=3, calls=3, tokens=300,
            in_tokens=280, out_tokens=20, ms=20)
    got = tracer.metrics(price=tr.Price(1.0, 4.0, "元"))
    assert got["runs"] == 3 and got["success_rate"] == round(1 / 3, 4)
    assert got["failure_distribution"] == {"成功": 1, "预算收口": 1, "卡死": 1}
    assert set(got["failure_distribution"]) <= set(tr.KINDS)
    assert got["tokens"]["avg"] == round(1300 / 3, 1)
    assert got["tokens"]["input_share"] == round(1160 / 1300, 4)
    assert got["by_tool"]["read_article"]["calls"] == 3
    # 成本：输入与输出分开算（1 元/百万输入、4 元/百万输出）
    assert got["cost"]["per_task"] == round((1160 * 1.0 + 140 * 4.0) / 1e6 / 3, 6)
    assert got["latency_ms"]["p50"] == 20 and got["latency_ms"]["p95"] == 29.0


def test_没配单价就不报钱() -> None:
    """一个编出来的价会让整张表看起来都不可疑——但它是编的。"""
    tracer = tr.Tracer()
    _record(tracer, reason="模型给出最终答案", steps=1, calls=1, tokens=10, in_tokens=5, out_tokens=5)
    assert tracer.metrics()["cost"] is None


def test_分位不被长尾藏住() -> None:
    xs = [10.0, 10.0, 10.0, 10.0, 1000.0]
    mean = sum(xs) / len(xs)
    assert tr.percentile(xs, 0.5) == 10
    assert tr.percentile(xs, 0.95) > mean, "P95 必须比均值更能暴露长尾"
    assert tr.percentile([], 0.95) == 0.0 and tr.percentile([7.0], 0.95) == 7.0


def test_服务商没分开报时输入占比是空而不是零() -> None:
    tracer = tr.Tracer()
    _record(tracer, reason="模型给出最终答案", steps=1, calls=1, tokens=10, in_tokens=0, out_tokens=0)
    assert tracer.metrics()["tokens"]["input_share"] is None


def test_多代理时按角色分维度() -> None:
    tracer = tr.Tracer()
    run = tracer.start_trace("多代理")
    tracer.record_model_call(run, model="m", duration_ms=5.0, agent_name="检索者")
    tracer.record_model_call(run, model="m", duration_ms=7.0, agent_name="写作者")
    tracer.record_model_call(run, model="m", duration_ms=9.0, agent_name="写作者")
    tracer.finish(run, reason="模型给出最终答案", steps=3, calls=3, tokens=3)
    got = tracer.metrics()["by_role"]
    assert got["写作者"]["calls"] == 2 and got["检索者"]["avg_ms"] == 5.0


# ------------------------------------------------------------------ 5. 有界

def test_记录有上界不会只涨不落() -> None:
    tracer = tr.Tracer(max_runs=3)
    for _ in range(10):
        _record(tracer, reason="模型给出最终答案", steps=1, calls=1, tokens=1, in_tokens=1,
                out_tokens=0)
    assert len(tracer.runs) == 3 and tracer.metrics()["runs"] == 3


# ------------------------------------------------------------------ 6. 评测集与门

def _cases() -> list[dict]:
    return [json.loads(x) for x in EVAL.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_评测集两边都有题() -> None:
    """一边倒的题集养出一边倒的优化：只测「该搜的时候搜了」，最后就会变成什么都搜。"""
    cases = _cases()
    kinds = {g["type"] for c in cases for g in c["graders"]}
    assert {"tool_run", "tool_no_run", "outcome_draft_status"} <= kinds
    assert any(c["suite"] == "capability" for c in cases)
    assert any(c["suite"] == "regression" for c in cases)
    assert all(c["trials"] >= 2 for c in cases), "每条都要跑多次：单次成功不能当通过"
    # 判产出而不是判路径：没有任何判分器要求某个动作序列
    assert "tool_order" not in kinds


def test_评测集离线跑出来的读数() -> None:
    import experiments.eval_run as ev
    cases = ev.load_cases()
    report = ev.run_suite(cases, mode="offline")
    assert report["totals"]["trials"] == sum(c["trials"] for c in cases)
    ids = {c["id"] for c in report["cases"]}
    assert "stuck-third-trial" in ids
    stuck = next(c for c in report["cases"] if c["id"] == "stuck-third-trial")
    # 这条刻意做成了「三次里有一次卡住」：pass@k 与 pass^k 在这里分开
    assert stuck["any"] and not stuck["all"], stuck
    assert ev.regression_gate(report, report) == []


def test_回归门在退步时会响() -> None:
    """反例夹具：门必须**在真的退步时响**。不测这一条，它「沉默」与「坏了」长得一样。"""
    import experiments.eval_run as ev
    cases = ev.load_cases()
    base = ev.run_suite(cases, mode="offline")
    tight = json.loads(json.dumps(cases))
    tight[0]["graders"] = [{"name": "收紧", "type": "max_steps", "value": 1}]
    assert ev.regression_gate(ev.run_suite(tight, mode="offline"), base), "收紧标准后门没响"
    fewer = [c for c in cases if c["id"] != "summary-three-tools"]
    assert ev.regression_gate(ev.run_suite(fewer, mode="offline"), base), "删用例后门没响"
    real = dict(base, mode="real")
    assert ev.regression_gate(real, base), "拿真机读数去比离线基线时门没响"


def test_中断的试验必须记成不通过() -> None:
    """限流/断连打断一次试验时：它不能被算成“通过”。

    一个没跑完的试验会轻松通过所有「不该做 X」的判分器（因为什么都没发生）——
    照常打分的话，基础设施抖动会把成功率**抬上去**。
    """
    import experiments.eval_run as ev
    one = [next(c for c in ev.load_cases() if c["id"] == "draft-then-stop")]
    original = ev.trial_offline

    def boom(case, n):
        time.sleep(0.02)               # 真的等了 20ms，才有可量的时长
        raise RuntimeError("限流")

    ev.trial_offline = boom
    try:
        report = ev.run_suite(one, mode="offline")
    finally:
        ev.trial_offline = original
    row = report["cases"][0]
    assert row["passed"] == 0 and not row["any"] and not row["all"]
    assert "中断" in row["failed"][0]["reason"]
    # 中断也要带上**真实已耗**：默认 0 会让一批中断把延迟分位拖到 0.0ms，
    # 而「p50 0.0ms」看起来像「很快」，实际是「一半样本没有时长」。
    assert report["totals"]["metrics"]["latency_ms"]["p95"] >= 20.0
    # 中断必须自成**一档**：记成「模型失败」会让「该改提示」和「该加重试」看起来是同一件事。
    assert report["totals"]["metrics"]["failure_distribution"] == {"运行中断": row["trials"]}


def test_评测集与已提交的基线一致() -> None:
    import experiments.eval_run as ev
    assert ev.BASELINE.exists(), "没有基线文件：跑 --write-baseline 生成它"
    base = json.loads(ev.BASELINE.read_text(encoding="utf-8"))
    assert ev.regression_gate(ev.run_suite(ev.load_cases(), mode="offline"), base) == []


# ------------------------------------------------------------------ 7. 端点

def test_metrics端点不需要模型密钥() -> None:
    """看账不该要求密钥：没配模型的开发机上，「刚才那几次跑成什么样」也要答得出来。"""
    from app.api import agent as api
    saved = {k: os.environ.pop(k, None) for k in ("LLM_API_KEY",)}
    try:
        got = api.metrics(window=5, svc=api.get_memory_service())
        assert got.code == 0 and got.data["runs"] == 0
        raised = False
        try:
            Config.from_env()
        except LlmError:
            raised = True
        assert raised, "这一条的前提是环境里确实没有模型凭据"
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def test_payload里带着trace_id() -> None:
    """响应体里要能拿到这次运行的 trace_id：不然日志与指标对不上号。"""
    from app.services.agent_service import AgentService
    svc = AgentService(Config(api_key="测试"), user_id=7,
                       chat_fn=_two_step_chat(), sessions=None)
    r = svc.chat("读一下 42 号文章")
    payload = AgentService.to_payload(r)
    assert payload["trace_id"].startswith("trace-")
    assert payload["trace_id"] == r.record.trace_id                    # type: ignore[attr-defined]
    assert svc.metrics()["runs"] == 1
