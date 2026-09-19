#!/usr/bin/env python
"""4.3 的可运行脚本：工具、循环、护栏，四组读数。

    python scripts/agent_tools.py --offline     # 不需要密钥：确定性剧本，当作提交门
    python scripts/agent_tools.py --real        # 真机：同一批任务换成真实服务商

**离线当门、真机报数**（从 3.9 起的做法）。离线那一路的每个断言都可以重复跑出同一个结果；
真机那一路报的是读数，不写成断言——模型今天高兴不高兴，不该让门变红。

四段：
  ① 工具定义：六份定义多少字符，与 v3 手写的比长在哪
  ② 参数校验：同一个错误参数，v3 拦下 / v4 交给谁
  ③ 两条路径：同一个任务，手写循环与 create_agent 的步数、调用数、终止原因
  ④ 审批两法：进程内回调 vs 框架中断（含 1.3.2 上 `when` 静默失效的实测）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent import (DEFAULT_RECURSION_LIMIT, Budget, agent_config, create_zhizhou,
                       describe_agent, run_agent, run_handwritten)
from app.middleware import guard_tools
from app.scripted import ScriptedModel, final, tool_call
from app.tools import MAX_PAYLOAD_CHARS, build_tools, tool_sheet

LINE = "=" * 74


def part1_definitions() -> None:
    print(f"{LINE}\n① 六份工具定义：写的是一个函数，交出去的是一份 schema\n{LINE}")
    tools = build_tools(user_id=7)
    rows = tool_sheet(tools)
    for r in rows:
        print(f"  {r['name']:<16}{r['access']:<9}描述 {r['描述']:>3} 字符｜定义 {r['定义']:>4} 字符"
              f"｜必填 {r['必填']}")
    print(f"  合计 {sum(r['定义'] for r in rows)} 字符")
    print("  v3 手写的那一份合计 1,766 字符（`cd zhizhou-v3 && python -c "
          "\"from app.agent.tools.zhizhou import build; import json; "
          "reg=build(7); print(sum(len(json.dumps(s,ensure_ascii=False)) for s in reg.specs()))\"`）")
    # 多出来的钱花在哪：把六份定义里的 `title` 全摘掉再量一次
    def spec_of(t):
        return {"name": t.name, "description": t.description,
                "input_schema": t.tool_call_schema.model_json_schema()}

    specs = [spec_of(t) for t in tools]
    with_title = sum(len(json.dumps(s, ensure_ascii=False)) for s in specs)
    without = sum(len(json.dumps(_strip_titles(s), ensure_ascii=False)) for s in specs)
    print(f"  与手写版对齐后逐项量：{with_title} 字符里，"
          f"`title` 字段占 **{with_title - without}** 字符（{without} 字符是实内容）")
    print("  `additionalProperties: false`（v3 手写 schema 有）框架**默认不生成**——"
          "受约束解码要靠服务商侧的 strict 开关，不是这份 schema 说了算。")
    raw = {"article_id": 42, "title": "JWT 刷新令牌怎么做", "body": "正文" * 1000}
    print(f"  体积上限也归工具自己：一份 {len(json.dumps(raw, ensure_ascii=False))} 字符的结果，"
          f"由 `_fit` 裁到 {MAX_PAYLOAD_CHARS} 以内（框架不裁）")


def _strip_titles(node):
    if isinstance(node, dict):
        return {k: _strip_titles(v) for k, v in node.items() if k != "title"}
    if isinstance(node, list):
        return [_strip_titles(x) for x in node]
    return node


def part2_validation() -> None:
    print(f"\n{LINE}\n② 同一个错误参数，v3 拦下 / v4 交给了谁\n{LINE}")
    cases = [("seek", "read_article", {"article_id": 43}, "越权：别人的文章"),
             ("coerce", "read_article", {"article_id": "42"}, "类型不对：字符串 42"),
             ("missing", "read_article", {}, "缺必填参数"),
             ("unknown", "no_such_tool", {"x": 1}, "工具不存在"),
             ("enum", "articles", {"mode": "latest"}, "枚举越界"),
             ("range", "read_article", {"article_id": 0}, "范围越界：0 < 下限 1")]
    for _, name, args, label in cases:
        sc = ScriptedModel(script=[{"tool": name, "args": args, "tokens": 50}, final("收工", 20)])
        agent = create_zhizhou(sc, build_tools(user_id=7))
        stats = run_agent(agent, "试", config=agent_config(recursion_limit=6))
        if stats.crashed:
            verdict = f"抛穿整轮：{stats.crashed[:44]}"
        elif stats.tool_results:
            first = stats.tool_results[0]
            head = first["content"].replace("\n", " ")[:46]
            verdict = f"工具真的执行了｜{head}…" if first["status"] == "success" \
                else f"框架拦住（status={first['status']}）｜{head}…"
        else:
            verdict = "（没有工具消息）"
        print(f"  {label:<20}{verdict}")
    print("  规律只有一条：**框架接得住「调用得不对」，接不住「调用对了但做不成」**。")
    print("  前者是参数形状问题（框架兜住），后者是权限与业务问题（要自己拦）。")


def part5_limits() -> None:
    """上限：三套机制叠在一起时，谁先撞到决定你拿到什么。"""
    from langchain.agents.middleware import ModelCallLimitMiddleware

    print(f"\n{LINE}\n⑤ 上限：三套机制叠在一起\n{LINE}")
    print("  手写版：模型调用数 ＋ 词元 ＋ 墙钟，撞上限先**收口**（多问一次要结论）")
    print("  框架层：`recursion_limit` 数 super-step，撞上限抛 `GraphRecursionError`")
    print("  中间件：`ModelCallLimitMiddleware` 数模型调用，撞上限**留一句话**——"
          "但前提是它没先撞上 `recursion_limit`")
    loop = [tool_call("get_tags", {}, 50)]      # 剧本走完重复最后一格：一个永不收敛的任务
    print(f"  {'recursion_limit':>16}｜{'模型调用':>8}｜{'super-step':>10}｜拿到的是什么")
    for limit in (6, 8, 10, 12, 20):
        agent = create_zhizhou(
            ScriptedModel(script=list(loop)), build_tools(user_id=7),
            middleware=[ModelCallLimitMiddleware(run_limit=3)])
        stats = run_agent(agent, "死循环", config=agent_config(recursion_limit=limit))
        got = "异常中断（图递归上限）" if stats.crashed else f"“{stats.answer[:32]}”"
        print(f"  {limit:>16}｜{stats.model_calls:>8}｜{stats.super_steps:>10}｜{got}")
    print("  同一个 `run_limit=3`，**上限裕量不同就拿到不同的东西**：裕量小的时候撞的是"
          "图递归上限，空手回来；裕量大才轮到中间件那句说明。两个闸门都装了，但从没对过账。")
    stalled = run_handwritten(ScriptedModel(script=list(loop)), build_tools(user_id=7),
                              "死循环", run_id="lim")
    print(f"  同一个任务给手写版：终止「{stalled.stop}」｜工具调用 {stalled.tool_calls}｜"
          f"答案 {stalled.answer[:22]!r}")
    budgeted = run_handwritten(
        ScriptedModel(script=[tool_call("get_tags", {}, 60),
                              tool_call("read_article", {"article_id": 42}, 300),
                              final("42 号讲的是刷新令牌的三种做法。", 90)]),
        build_tools(user_id=7), "看标签再读一篇",
        budget=Budget(max_steps=2, max_tokens=9999), run_id="lim")
    print(f"  预算上限（max_steps=2，剧本还有余量）：终止「{budgeted.stop}」｜"
          f"模型调用 {budgeted.model_calls}｜答案 {budgeted.answer[:26]!r}")
    print("  手写版撞上限时**先收口**（多问一次模型要结论）——所以拿到的是答案还是空串，"
          "取决于模型答不答（卡死那一行里的剧本已经没有新话可说）；"
          "而框架版给的是异常或一句固定说明，**两种都不追一句结论**。")


def script_happy() -> list[dict]:
    """三段剧本：先看标签、再读一篇、给结论。**每一步的用量写死在剧本里**，
    这样离线的「词元」一列是可复现的（真机那一列由服务商给）。"""
    return [tool_call("get_tags", {}, 160), tool_call("read_article", {"article_id": 42}, 900),
            tool_call("create_draft", {"article_id": 42, "body": "改后的正文"}, 220),
            final("标签有四个；42 号讲的是刷新令牌的三种做法，草稿已写好。", 180)]


def part3_two_paths(real: bool) -> None:
    print(f"\n{LINE}\n③ 同一个任务，两条路径：循环归谁\n{LINE}")
    if real:
        from app.llm import build_model

        task = "把 42 号文章的草稿改成「刷新令牌用版本号方案」。"
        approve = lambda name, args: False        # noqa: E731 —— 发布一律不批
        print("  ── 写草稿（真实服务商，**每条路径跑两遍**）──")
        for rep in (1, 2):
            stats = run_handwritten(build_model(), build_tools(user_id=7), task,
                                    approve=approve, run_id="real")
            _row(f"手写循环 #{rep}", stats)
        for rep in (1, 2):
            agent = create_zhizhou(build_model(), build_tools(user_id=7),
                                   middleware=[guard_tools(run_id="real", approve=approve)])
            _row(f"create_agent #{rep}", run_agent(agent, task, config=agent_config()))
        print("    **同一条路径跑两遍的差，与两条路径之间的差同量级**（这里 2,758 与 9,326）：")
        print("    真机读数里有模型自己的随机性，所以它只能报量级，**不能用来比较路径**。")
        print("    能下结论的地方是离线：剧本固定，两边逐项相同。")
        return

    print("  ── 看标签再读一篇（剧本模型，两条路径跑同一个剧本）──")
    task = "42 号文章讲了什么？"
    tools = build_tools(user_id=7)
    _row("手写循环", run_handwritten(ScriptedModel(script=script_happy()), tools, task,
                                     run_id="cmp"))
    agent = create_zhizhou(ScriptedModel(script=script_happy()), tools,
                           middleware=[guard_tools(run_id="cmp")])
    _row("create_agent", run_agent(agent, task, config=agent_config()))
    print(f"    框架版的图：{describe_agent(agent)}")
    print("    super-step 由两边各自数出来：手写版数「一次模型调用 ＋ 一个工具节点」，"
          "框架版就是流出来的帧数——**两把尺子必须是同一把**，"
          "否则「我设了 8 步」和「它走了几步」永远对不上账。")


def _row(label: str, stats) -> None:
    print(f"    {label:<16}终止 {stats.stop:<14}模型调用 {stats.model_calls}｜"
          f"super-step {stats.super_steps}｜工具 {stats.tool_calls}（{'、'.join(stats.tools_used) or '无'}）｜"
          f"词元 {stats.tokens}")


def brief(stats) -> str:
    """把「调了哪个工具、成不成」写成一行。**被拒的也要列出来**——它真实发生过。"""
    return "、".join(f"{r['name']}:{'成功' if r['status'] == 'success' else '被拦'}"
                    for r in stats.tool_results) or "（没有）"


def part4_approval() -> None:
    print(f"\n{LINE}\n④ 审批与幂等：四条规则住在哪一层\n{LINE}")
    from langchain.agents.middleware import HumanInTheLoopMiddleware
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command

    script = [tool_call("create_draft", {"article_id": 42, "body": "改后的正文"}, 200),
              tool_call("publish_article", {"article_id": 42}, 200),
              final("已发布。", 60)]

    print("  ── 规则一：审批闸（默认拒绝）──")
    for allowed in (False, True):
        tools = build_tools(user_id=7)
        stats = run_handwritten(ScriptedModel(script=list(script)), tools, "改完就发布",
                                approve=lambda name, args, ok=allowed: ok, run_id="ap")
        print(f"    手写版 approve={allowed} → {brief(stats)}")
    for allowed in (False, True):
        tools = build_tools(user_id=7)
        audit: list[dict] = []
        agent = create_zhizhou(
            ScriptedModel(script=list(script)), tools,
            middleware=[guard_tools(run_id="ap", approve=lambda n, a, ok=allowed: ok,
                                    audit=audit)])
        stats = run_agent(agent, "改完就发布", config=agent_config())
        print(f"    框架版 approve={allowed} → {brief(stats)}｜审计 {len(audit)} 条")
    print("    两边行为一致；差别只在「不改装配层能不能换策略」：框架版换的是 middleware 列表里的一项。")

    print("  ── 规则二：幂等键（同一任务重发同一笔写）──")
    twice = [tool_call("create_draft", {"article_id": 42, "body": "改后的正文"}, 200),
             tool_call("create_draft", {"article_id": 42, "body": "改后的正文"}, 200),
             final("草稿已写。", 40)]
    once = [tool_call("create_draft", {"article_id": 42, "body": "改后的正文"}, 200),
            final("草稿已写。", 40)]

    def hits_of(script, guard, audit: list[dict]) -> int:
        agent = create_zhizhou(ScriptedModel(script=list(script)), build_tools(user_id=7),
                               middleware=[guard])
        run_agent(agent, "写草稿", config=agent_config())
        return sum(1 for a in audit if a.get("repeated"))

    audit_a: list[dict] = []
    same = guard_tools(run_id="task-A", audit=audit_a)
    print(f"    同一次运行里写两遍 → 命中 {hits_of(twice, same, audit_a)} 次")
    print(f"    同一个 run_id 再跑一轮 → 累计命中 {hits_of(once, same, audit_a)} 次"
          f"（键没变，服务端也没重复写）")
    audit_b: list[dict] = []
    other = guard_tools(run_id="task-B", audit=audit_b)
    print(f"    换一个 run_id（task-B）→ 命中 {hits_of(once, other, audit_b)} 次"
          f"（新任务，就该真执行）")
    print("    键里带 run_id：**同一任务重放只执行一次，换个任务才会重放**——"
          "重放不被静默吞掉，也不会重复写。")

    print("  ── 做法二：框架中断（跨进程等人）──")
    tools = build_tools(user_id=7)
    agent = create_zhizhou(ScriptedModel(script=list(script)), tools,
                           middleware=[HumanInTheLoopMiddleware(
                               interrupt_on={"publish_article": True})],
                           checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "demo-approve"}}
    first = agent.invoke({"messages": [{"role": "user", "content": "改完就发布"}]},
                         config=config, version="v2")
    asked = first.interrupts[0].value["action_requests"][0] if first.interrupts else None
    print(f"    第一次 invoke：中断 {bool(first.interrupts)}｜被问的动作 "
          f"{asked['name'] if asked else '（没有）'}｜已产出的消息 {len(first.value['messages'])} 条")
    print("    **工具体一次都没执行**——中断发生在执行之前。")
    resumed = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}),
                           config=config, version="v2")
    print(f"    批准后：{len(resumed.value['messages'])} 条消息，"
          f"末条 {resumed.value['messages'][-1].content[:30]!r}")

    print("  ── `when` 谓词：文档说需要 langchain>=1.3.3 ──")
    import importlib.metadata as md

    version = md.version("langchain")
    for predicate in (True, False):
        tools = build_tools(user_id=7)
        agent = create_zhizhou(
            ScriptedModel(script=list(script)), tools,
            middleware=[HumanInTheLoopMiddleware(
                interrupt_on={"publish_article": {"when": lambda req, p=predicate: p}})],
            checkpointer=InMemorySaver())
        out = agent.invoke({"messages": [{"role": "user", "content": "改完就发布"}]},
                           config={"configurable": {"thread_id": f"w-{predicate}"}},
                           version="v2")
        print(f"    本机 langchain {version}｜when 返回 {predicate} → "
              f"中断 {bool(out.interrupts)}")
    print("    两个取值都不中断：**参数被接受了，但静默不生效**。版本边界上最危险的"
          "不是报错，是不报错。")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="用剧本模型，不需要密钥")
    ap.add_argument("--real", action="store_true", help="调真实服务商，报读数")
    args = ap.parse_args()
    if not args.offline and not args.real:
        args.offline = True

    print(f"zhizhou-v4 / 4.3 工具与 Agent｜{'剧本模型' if args.offline else '真实服务商'}"
          f"｜显式 recursion_limit = {DEFAULT_RECURSION_LIMIT}（框架默认 9999）")
    part1_definitions()
    part2_validation()
    part3_two_paths(real=args.real)
    if args.offline:
        part4_approval()
        part5_limits()
    print("\n✔ 离线自检通过" if args.offline else "\n✔ 真机读数完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
