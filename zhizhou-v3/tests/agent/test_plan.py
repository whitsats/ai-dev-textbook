# tests/agent/test_plan.py —— 不需要模型、不需要数据库
from app.agent.plan import Step, draft_plan, layers, validate, apply_diff
from app.agent.plan import plan_from_reply


def test_五类坏计划各报一条():
    issues = validate(draft_plan({"goal": "g", "max_steps": 4, "steps": [
        {"id": "s1", "action": "a", "accept": "x"},
        {"id": "s1", "action": "a", "accept": "y"},
        {"id": "s2", "action": "b", "accept": "z", "deps": ["s9"]},
        {"id": "s3", "action": "c", "accept": "", "deps": ["s4"]},
        {"id": "s4", "action": "d", "accept": "w", "deps": ["s3"]}]}))
    assert len(issues) == 5
    assert any("重复" in i for i in issues)
    assert any("悬空依赖" in i for i in issues)
    assert any("没有验收标准" in i for i in issues)
    assert any("成环" in i for i in issues)
    assert any("超过上限" in i for i in issues)


def test_悬空依赖不会让校验器崩():
    """回归：校验器必须能报告坏计划，而不是自己被坏计划弄崩。"""
    assert validate(draft_plan({"goal": "g", "steps": [
        {"id": "s1", "action": "a", "accept": "x", "deps": ["nope"]}]}))


def test_关键路径按依赖层数算():
    plan = draft_plan({"goal": "g", "steps": [
        {"id": "s1", "action": "a", "accept": "x"},
        {"id": "s2", "action": "b", "accept": "y", "deps": ["s1"]},
        {"id": "s3", "action": "c", "accept": "z", "deps": ["s1"]},
        {"id": "s4", "action": "d", "accept": "w", "deps": ["s2", "s3"]}]})
    assert validate(plan) == []
    assert layers(plan) == [["s1"], ["s2", "s3"], ["s4"]]


def test_重规划只替换目标步骤():
    plan = draft_plan({"goal": "g", "steps": [
        {"id": "s1", "action": "a", "accept": "x"},
        {"id": "s2", "action": "b", "accept": "y", "deps": ["s1"]}]})
    plan.steps[0].status = "done"
    new = apply_diff(plan, [("replace", "s2", Step("s2", "b2", "y", ["s1"]))])
    assert [s.id for s in new.steps if s.status == "done"] == ["s1"]
    assert new.steps[1].action == "b2"
    assert validate(new) == []


def test_模型多给的字段不让解析崩():
    """真模型常常多写字段（为什么、备注）。多给的部分降级，而不是抛异常。"""
    p = plan_from_reply({"goal": "g", "max_steps": "6", "steps": [
        {"id": "s1", "action": "a", "accept": "x", "why": "因为", "note": "备注", "deps": None}]})
    assert p.max_steps == 6 and p.steps[0].deps == [] and validate(p) == []
