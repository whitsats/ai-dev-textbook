"""知舟的计划层：表示、五类静态校验、分层与 diff 式重规划。

计划是**纯数据**：所以它能在动第一个工具之前被检查、被展示、被改。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Step:
    id: str
    action: str
    accept: str = ""
    deps: list[str] = field(default_factory=list)
    status: str = "todo"


@dataclass
class Plan:
    goal: str
    steps: list[Step]
    max_steps: int = 12

    @property
    def by_id(self) -> dict[str, Step]:
        return {s.id: s for s in self.steps}


def deps_of(plan: Plan, sid: str) -> list[str]:
    """取某步的**已有**依赖。

    这里必须容忍「引用了不存在的步骤」：校验器的职责正是把这种计划拦下来，
    它自己不能因为输入非法而崩——直接写 `plan.by_id[sid].deps`，
    碰到悬空依赖就抛 KeyError，那等于最该跑通的那条路径跑不通。
    """
    s = plan.by_id.get(sid)
    return [d for d in s.deps if d in plan.by_id] if s else []


def validate(plan: Plan) -> list[str]:
    """动第一个工具之前能查出来的五类问题。全是纯函数，不需要模型。"""
    issues: list[str] = []
    ids = [s.id for s in plan.steps]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        issues.append(f"步骤 id 重复：{dup}")
    for s in plan.steps:
        if not s.accept:
            issues.append(f"{s.id}：没有验收标准，完成后无法判断是否成功")
        for d in s.deps:
            if d not in ids:
                issues.append(f"{s.id}：依赖 {d} 不存在（悬空依赖）")
    color: dict[str, int] = {}          # 三色 DFS 找环
    cycle: list[str] = []

    def dfs(u: str, stack: list[str]) -> None:
        color[u] = 1
        for v in deps_of(plan, u):
            if v not in color:
                dfs(v, stack + [v])
            elif color[v] == 1 and not cycle:
                cycle.append(" → ".join(stack + [v]))
        color[u] = 2

    for s in plan.steps:
        if s.id not in color:
            dfs(s.id, [s.id])
    if cycle:
        issues.append(f"依赖成环：{cycle[0]}")
    if len(plan.steps) > plan.max_steps:
        issues.append(f"步骤数 {len(plan.steps)} 超过上限 {plan.max_steps}")
    return issues


def layers(plan: Plan) -> list[list[str]]:
    """拓扑分层：同层可并行，层数就是关键路径长度。只对校验通过的计划调用。"""
    depth: dict[str, int] = {}
    by_id = plan.by_id

    def d(i: str) -> int:
        if i not in depth:
            deps = [x for x in by_id[i].deps if x in by_id]
            depth[i] = 0 if not deps else 1 + max(d(x) for x in deps)
        return depth[i]

    for s in plan.steps:
        d(s.id)
    out: dict[int, list[str]] = {}
    for s in plan.steps:
        out.setdefault(depth[s.id], []).append(s.id)
    return [out[k] for k in sorted(out)]


def apply_diff(plan: Plan, ops: list[tuple[str, str, Step | None]]) -> Plan:
    """只允许替换 / 插入 / 删除三种操作，已完成步骤的 id 一律保留。"""
    steps = list(plan.steps)
    for op, sid, new in ops:
        if op == "replace":
            steps = [new if s.id == sid else s for s in steps]
        elif op == "insert":
            assert new is not None
            steps.insert(next(i for i, s in enumerate(steps) if s.id == sid) + 1, new)
        elif op == "delete":
            steps = [s for s in steps if s.id != sid]
    return Plan(goal=plan.goal, steps=steps, max_steps=plan.max_steps)


def draft_plan(model_reply: dict) -> Plan:
    """受约束解码把模型输出变成 dict，形状由 schema 保证。"""
    return Plan(goal=model_reply["goal"],
                max_steps=model_reply.get("max_steps", 12),
                steps=[Step(**s) for s in model_reply["steps"]])


def plan_from_reply(reply: dict) -> Plan:
    """真模型回来的 dict：多出的字段（模型爱加 note/why）降级成备注，不当作错误。"""
    steps = []
    for raw in reply.get("steps", []):
        steps.append(Step(id=str(raw.get("id", "")), action=str(raw.get("action", "")),
                          accept=str(raw.get("accept", "")),
                          deps=[str(d) for d in raw.get("deps", []) or []]))
    return Plan(goal=str(reply.get("goal", "")), steps=steps,
                max_steps=int(reply.get("max_steps", 12) or 12))


def describe(plan: Plan) -> str:
    """给人看的一行式计划：分层 + 状态，用于演示与日志。"""
    lay = layers(plan) if not validate(plan) else []
    done = [s.id for s in plan.steps if s.status == "done"]
    body = " ｜ ".join(f"L{i}: {','.join(v)}" for i, v in enumerate(lay)) or "（未通过校验）"
    return f"目标：{plan.goal}\n  关键路径 {len(lay)} 层 ｜ {body}\n  已完成：{done or '（无）'}"


BAD = {"goal": "给文章 42 生成摘要与标签并写草稿", "max_steps": 4, "steps": [
    {"id": "s1", "action": "load_article", "accept": "拿到 title 与 content"},
    {"id": "s1", "action": "load_article", "accept": "拿到作者昵称"},
    {"id": "s2", "action": "summarize", "accept": "摘要 80–120 字", "deps": ["s9"]},
    {"id": "s3", "action": "tag", "accept": "", "deps": ["s4"]},
    {"id": "s4", "action": "write_draft", "accept": "草稿落库且 drafted=0", "deps": ["s3"]},
]}

GOOD = {"goal": "给文章 42 生成摘要与标签并写草稿", "steps": [
    {"id": "s1", "action": "load_article", "accept": "拿到 title 与 content"},
    {"id": "s2", "action": "summarize", "accept": "摘要 80–120 字", "deps": ["s1"]},
    {"id": "s3", "action": "tag", "accept": "标签 1–3 个且属既有栏目", "deps": ["s1"]},
    {"id": "s4", "action": "write_draft", "accept": "草稿落库且 drafted=0", "deps": ["s2", "s3"]},
]}

if __name__ == "__main__":
    print("=== 第一次生成（形状合法，计划不一定活着）===")
    plan = draft_plan(BAD)
    for i in validate(plan):
        print("  ✗", i)

    print("\n=== 重新生成后 ===")
    plan = draft_plan(GOOD)
    print("  校验通过" if not validate(plan) else "  仍有问题")
    lay = layers(plan)
    print(f"  关键路径 {len(lay)} 层 ｜ " + " ｜ ".join(f"L{i}: {','.join(v)}" for i, v in enumerate(lay)))

    print("\n=== 执行到 s2 失败，重规划只改该改的 ===")
    plan.steps[0].status = "done"
    plan.steps[1].status = "failed"
    new = apply_diff(plan, [("replace", "s2", Step(
        "s2", "summarize_chunked", "分段摘要后合并，80–120 字", ["s1"]))])
    print("  diff：replace s2 → summarize_chunked（依赖不变，仍是 s1）")
    print(f"  已完成步骤未重跑：{[s.id for s in new.steps if s.status == 'done']}")
    print(f"  重跑范围：{[s.id for s in new.steps if s.status != 'done']}")
    print(f"  重规划后校验：{'通过' if not validate(new) else validate(new)}")
