#!/usr/bin/env python
"""4.4 的可运行脚本：图的机制读数，六组。

    python scripts/state_graph.py --offline     # 不需要密钥：小图 ＋ 剧本模型，当作提交门
    python scripts/state_graph.py --real        # 真机：同一张流水线换成真实服务商

**离线当门、真机报数**（从 3.9 起的做法）。前五组是**小图**——它们量的是机制，
不是业务：状态怎么合并、上限数什么、并行什么时候会炸、流吐几帧、
输入输出 schema 过滤掉什么。第六组才是有业务的知舟流水线。

两个反复出现的坑（都在本章正文里）：
  · 机制读数的图**不挂 checkpointer**，业务那张挂——因为第五组要量「不挂会怎样」；
  · 所有随机性都来自剧本模型，所以每一行读数都可以重复跑出来。
"""
from __future__ import annotations

import argparse
import operator
import sys
from pathlib import Path
from typing import Annotated, TypedDict

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langgraph.checkpoint.memory import InMemorySaver          # noqa: E402
from langgraph.graph import END, START, StateGraph             # noqa: E402
from langgraph.types import Command                            # noqa: E402

from app.graph import (DRAFT_TARGET_CHARS, MAX_ROUNDS, build_pipeline,  # noqa: E402
                       initial_state, new_thread)
from app.scripted import ScriptedModel, final                  # noqa: E402

LINE = "=" * 74
ARTICLE = "知舟是一个把写稿流程拆成工序的博客系统，每一步都能单独验收。" * 12


# ---------------------------------------------------------------------------
# ① 状态：三种合并，一个一个量
# ---------------------------------------------------------------------------
class MergeState(TypedDict):
    overwritten: str                       # 无 reducer → 覆盖
    accumulated: Annotated[list[str], operator.add]   # 有 reducer → 累加
    # `undeclared` 故意**不**声明在这里：4.4.2 要量它回来之后还在不在


def one(s):        # noqa: ANN001
    return {"overwritten": "A", "accumulated": ["A"], "undeclared": "A"}


def two(s):        # noqa: ANN001
    return {"overwritten": "B", "accumulated": ["B"], "undeclared": "B"}


def part1_merge() -> None:
    print(f"{LINE}\n① 状态：一份 schema，每个键各写各的合并规则\n{LINE}")
    g = StateGraph(MergeState)
    g.add_node("one", one)
    g.add_node("two", two)
    g.add_edge(START, "one")
    g.add_edge("one", "two")
    g.add_edge("two", END)
    out = g.compile().invoke({"overwritten": "-", "accumulated": ["start"]})
    print(f"  覆盖键 overwritten     ：'-' → 'A' → {out['overwritten']!r}")
    print(f"  累加键 accumulated     ：['start'] → {out['accumulated']}")
    print(f"  未声明键 undeclared    ：节点返回了两次，回来之后**没有这个键**"
          f"（{'undeclared' in out}）——不报错、不警告，与「值恰好为空」长得一样")

    # 累加键不给初值：框架用类型提示推一个空值，而不是抛错
    g2 = StateGraph(MergeState)
    g2.add_node("one", one)
    g2.add_edge(START, "one")
    g2.add_edge("one", END)
    out2 = g2.compile().invoke({})
    print(f"  累加键不给初值         ：{out2}——从类型提示推出来的空表，不是契约")


# ---------------------------------------------------------------------------
# ② 上限：`recursion_limit` 数的是 super-step
# ---------------------------------------------------------------------------
def part2_limits() -> None:
    print(f"{LINE}\n② 上限：它数的是 super-step，不是「节点数」也不是「模型调用数」\n{LINE}")

    class S(TypedDict):
        x: Annotated[int, operator.add]

    def inc(s):        # noqa: ANN001
        return {"x": 1}

    g = StateGraph(S)
    for i in range(3):
        g.add_node(f"n{i}", inc)
    g.add_edge(START, "n0")
    g.add_edge("n0", "n1")
    g.add_edge("n1", "n2")
    g.add_edge("n2", END)
    app = g.compile()
    print("  线性 3 节点图，逐档试出最小值：")
    for limit in (2, 3, 4):
        try:
            app.invoke({"x": 0}, {"recursion_limit": limit})
            print(f"    recursion_limit={limit} → 通过（x={3}）")
        except Exception as e:                        # noqa: BLE001
            print(f"    recursion_limit={limit} → {type(e).__name__}")

    class L(TypedDict):
        n: Annotated[int, operator.add]
        stop: int

    def work(s):       # noqa: ANN001
        return {"n": 1}

    def decide(s):     # noqa: ANN001
        return "again" if s["n"] < s["stop"] else "done"

    gl = StateGraph(L)
    gl.add_node("work", work)
    gl.add_edge(START, "work")
    gl.add_conditional_edges("work", decide, {"again": "work", "done": END})
    apl = gl.compile()
    for limit in (3, 4):
        try:
            r = apl.invoke({"n": 0, "stop": 3}, {"recursion_limit": limit})
            print(f"  循环图 3 轮（同一个节点跑 3 次）：limit={limit} → 通过（n={r['n']}）")
        except Exception as e:                        # noqa: BLE001
            print(f"  循环图 3 轮：limit={limit} → {type(e).__name__}")
    print("  折算：**图上的每一个节点一次算一个 super-step，再留一步收尾**"
          "（3 节点 → 4；3 轮循环 → 4）。\n"
          "  4.3 在 `create_agent` 上量到的「一次模型往返占 2 步」由此有了下落："
          "那里的图是\n  `model` 与 `tools` 两个节点来回，所以一次往返确实吃 2 步。")


# ---------------------------------------------------------------------------
# ③ 边：三种边各错一次
# ---------------------------------------------------------------------------
def part3_edges() -> None:
    print(f"{LINE}\n③ 边：普通边、条件边、路由映射表——三种边各错一次\n{LINE}")

    class S(TypedDict):
        x: Annotated[int, operator.add]

    def a(s):          # noqa: ANN001
        return {"x": 1}

    def b(s):          # noqa: ANN001
        return {"x": 10}

    # 错法一：路由函数返回一个**映射表里没有的名字**（键是它的返回值，不是节点名）
    g = StateGraph(S)
    g.add_node("a", a)
    g.add_node("b", b)
    g.add_edge(START, "a")
    g.add_conditional_edges("a", lambda s: "two", {"one": "b"})
    g.add_edge("b", END)
    try:
        print(f"  路由返回映射表里没有的名字 → {g.compile().invoke({'x': 0})}")
    except KeyError as e:
        print(f"  路由返回映射表里没有的名字 → KeyError {e}（compile 不报、无警告，"
              f"而且是运行到那一步才报）")

    # 错法二：映射表里的**目标名写错了**——这个 compile 就报
    g2 = StateGraph(S)
    g2.add_node("a", a)
    g2.add_edge(START, "a")
    g2.add_conditional_edges("a", lambda s: "ok", {"ok": "typo_node"})
    try:
        g2.compile()
        print("  映射表目标名写错 → compile 通过（那就不该通过）")
    except ValueError as e:
        print(f"  映射表目标名写错 → {type(e).__name__}：{e}")

    # 错法三：悬空节点——官方说 compile 会做「没有孤立节点」这类结构检查
    g3 = StateGraph(S)
    g3.add_node("a", a)
    g3.add_node("orphan", b)
    g3.add_edge(START, "a")
    g3.add_edge("a", END)
    app3 = g3.compile()
    print(f"  悬空节点 → compile 通过、运行不报错（x={app3.invoke({'x': 0})['x']}，"
          f"孤立那个一次都没跑）；"
          f"\n    但它**在图里**：{sorted(app3.get_graph().nodes)}")
    print("    「图上有它」不等于「它会跑」——这与 3.10 的接线状态表是同一条教训。")


# ---------------------------------------------------------------------------
# ④ 并行：什么时候必须给 reducer
# ---------------------------------------------------------------------------
def part4_parallel() -> None:
    print(f"{LINE}\n④ 并行：同一个 super-step 里两个节点写同一个键\n{LINE}")

    class S(TypedDict):
        plain: str
        joined: Annotated[list[str], operator.add]

    def a(s):          # noqa: ANN001
        return {"plain": "a", "joined": ["a"]}

    def b(s):          # noqa: ANN001
        return {"plain": "b", "joined": ["b"]}

    def build(node_a, node_b):      # noqa: ANN001
        g = StateGraph(S)
        g.add_node("a", node_a)
        g.add_node("b", node_b)
        g.add_edge(START, "a")
        g.add_edge(START, "b")
        g.add_edge("a", END)
        g.add_edge("b", END)
        return g.compile()

    try:
        out = build(a, b).invoke({"plain": "-", "joined": []})
        print(f"  两节点 fan-out 写同一个**无 reducer** 键：{out}")
    except Exception as e:                            # noqa: BLE001
        print(f"  两节点 fan-out 写同一个**无 reducer** 键 → {type(e).__name__}")
        print(f"    {str(e).splitlines()[0]}")
        print("    并行不是「优化选项」：只要两条边从同一个节点出发，"
              "**写同一个键就是错的**。")

    def b_only_joined(s):    # noqa: ANN001
        return {"joined": ["b"]}

    out2 = build(a, b_only_joined).invoke({"plain": "-", "joined": []})
    print(f"  只写累加键（第二个节点不碰 plain）：{out2}——"
          f"顺序按节点名的字典序，不按边的书写顺序")


# ---------------------------------------------------------------------------
# ⑤ 帧数：三种 stream 模式
# ---------------------------------------------------------------------------
def part5_frames() -> None:
    print(f"{LINE}\n⑤ 流：同一次运行，三种模式吐几帧（3 节点线性图）\n{LINE}")

    class S(TypedDict):
        x: Annotated[int, operator.add]

    def inc(s):        # noqa: ANN001
        return {"x": 1}

    g = StateGraph(S)
    for i in range(3):
        g.add_node(f"n{i}", inc)
    g.add_edge(START, "n0")
    g.add_edge("n0", "n1")
    g.add_edge("n1", "n2")
    g.add_edge("n2", END)
    app = g.compile()
    for mode in ("values", "updates", "debug"):
        frames = list(app.stream({"x": 0}, stream_mode=mode))
        print(f"  stream_mode={mode:<8} → {len(frames):>2} 帧")
    print("  规则：`values` 每个 super-step 一帧**全量快照**（含起始那一帧），"
          "`updates` 只吐**这一步改了什么**，\n"
          "  `debug` 每个节点两帧（任务 ＋ 结果）。读数在 `updates` 上最干净，"
          "但它不含未变的键。")


# ---------------------------------------------------------------------------
# ⑥ 多 schema：过滤谁、给谁看
# ---------------------------------------------------------------------------
class OutState(TypedDict):
    shown: str


class InState(TypedDict):
    seed: str


class InnerState(TypedDict):
    seed: str
    shown: str
    private_note: str


def part6_schemas() -> None:
    print(f"{LINE}\n⑥ 输入/输出 schema 与私有键：`invoke` 过滤的是什么\n{LINE}")

    def step(s):       # noqa: ANN001
        return {"shown": s["seed"] + "!", "private_note": "内部账，不该对外"}

    g = StateGraph(InnerState, input_schema=InState, output_schema=OutState)
    g.add_node("step", step)
    g.add_edge(START, "step")
    g.add_edge("step", END)
    app = g.compile()

    out = app.invoke({"seed": "正文", "shown": "坏的初值", "private_note": "坏的初值"})
    print(f"  invoke 回来             ：{out}")
    print("    两个发现：**不在输入 schema 里的初值进不来**（`shown` 直接进节点前就被丢了）；"
          "**不在输出 schema 里的键\n    出不去**（`private_note` 在内部有值、在返回值里没有键）。")
    frames = list(app.stream({"seed": "正文"}, stream_mode="values"))
    print(f"  stream_mode='values' 的第一帧：{frames[0]}")
    print(f"  stream_mode='values' 的最后一帧键：{sorted(frames[-1])}")
    print("    官方文档的原话：私有通道**不对 `invoke` 隐身、对流不隐身**。"
          "要真的只吐一部分，\n    得显式给 `output_keys`。")


# ---------------------------------------------------------------------------
# ⑦ 知舟流水线：循环、两个出口、中断
# ---------------------------------------------------------------------------
def part7_pipeline(model, *, real: bool) -> None:      # noqa: ANN001
    print(f"{LINE}\n⑦ 知舟流水线：起草 → 自评 →（不够就再来一轮）→ 发布要人点头\n{LINE}")
    app = build_pipeline(model, checkpointer=InMemorySaver())

    # 出口一：质量够了
    cfg = new_thread("offline-pass")
    first = app.invoke(initial_state(ARTICLE, "知舟简介"), cfg)
    print(f"  长正文（{len(ARTICLE)} 字）")
    print(f"    第一次 invoke 的返回值键：{sorted(first)}")
    print("    注意 `approved` **不在**里面：输出 schema 只过滤、不补默认值——"
          "没写过的键就是没有键，\n    取它会 `KeyError`，不是 `False`。")
    print(f"    中断负载：{first['__interrupt__'][0].value}")
    inner = app.get_state(cfg).values
    print(f"    内部账：rounds={inner['rounds']}｜revisions={len(inner['revisions'])}"
          f"｜frames(log)={len(inner['log'])}｜summary={inner['summary'][:18]!r}")
    print("    log 逐条：" + " → ".join(inner["log"]))
    resumed = app.invoke(Command(resume=True), cfg)
    print(f"    恢复后：approved={resumed['approved']}｜log 尾条={app.get_state(cfg).values['log'][-1]}")

    # 出口二：预算用尽（正文短到两轮都不够）
    cfg2 = new_thread("offline-budget")
    app.invoke(initial_state("太短。", "预算出口"), cfg2)
    inner2 = app.get_state(cfg2).values
    print(f"  短正文（4 字）")
    print(f"    log 逐条：" + " → ".join(inner2["log"]))
    print(f"    rounds={inner2['rounds']}（= max_rounds）→ 走的是**预算出口**，"
          f"不是质量出口")

    # 不挂 checkpointer 会怎样
    bare = build_pipeline(model)
    paused = bare.invoke(initial_state(ARTICLE, "无检查点"))
    print(f"  把 checkpointer 去掉：{type(paused).__name__}，"
          f"中断照样发生（{'__interrupt__' in paused}）")
    try:
        bare.invoke(Command(resume=True))
        print("    但 `Command(resume=True)` 也能跑完——**这是一次全新的运行**，不是恢复："
              "它没有上次那一步可以接。")
    except Exception as e:                            # noqa: BLE001
        print(f"    恢复 → {type(e).__name__}: {str(e).splitlines()[0][:70]}")
    if real:
        inner3 = bare.invoke(initial_state(ARTICLE, "无检查点")).get("draft", "")
        print(f"    证伪它的办法：数 prompt 里的用量——不带检查点那次是**重新算了一遍**"
              f"（草稿 {len(inner3)} 字）")


def real_readings() -> None:
    from app.llm import build_model

    print(f"{LINE}\n真机：同一张图，换成真实服务商\n{LINE}")
    model = build_model()
    app = build_pipeline(model, checkpointer=InMemorySaver())
    cfg = new_thread("real-1")
    first = app.invoke(initial_state(ARTICLE, "知舟简介"), cfg)
    inner = app.get_state(cfg).values
    print(f"  第一次 invoke：键 {sorted(first)}｜中断 {bool(first.get('__interrupt__'))}")
    print(f"  内部账：rounds={inner['rounds']}｜summary {len(inner['summary'])} 字｜"
          f"草稿 {len(inner['draft'])} 字")
    print("  log：" + " → ".join(inner["log"]))
    resumed = app.invoke(Command(resume=False), cfg)
    print(f"  拒发后：approved={resumed['approved']}｜log 尾条="
          f"{app.get_state(cfg).values['log'][-1]}")
    print("  说明：**同一张图在离线与真机上走的是同一条路径**，"
          "差别只在摘要那一句是谁写的。")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="小图 ＋ 剧本模型，不需要密钥")
    ap.add_argument("--real", action="store_true", help="调真实服务商，报读数")
    args = ap.parse_args()
    if not args.offline and not args.real:
        args.offline = True

    print(f"zhizhou-v4 / 4.4 LangGraph｜{'剧本模型' if args.offline else '真实服务商'}"
          f"｜起草目标 {DRAFT_TARGET_CHARS} 字、上限 {MAX_ROUNDS} 轮")
    part1_merge()
    part2_limits()
    part3_edges()
    part4_parallel()
    part5_frames()
    part6_schemas()
    model = ScriptedModel(script=[final("摘要：知舟把写稿拆成工序，每一步都能单独验收。")])
    part7_pipeline(model, real=False)
    if args.real:
        real_readings()
    print("\n✔ 离线自检通过" if args.offline else "\n✔ 真机读数完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
