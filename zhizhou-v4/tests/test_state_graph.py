# tests/test_state_graph.py —— 不需要密钥、不需要网络：图的合并规则、上限、并行与中断
"""这一份测的是 4.4 的结论，**全部不需要模型服务商**。

需要真实模型的那几件事（摘要写得对不对、真机词元）不在这里假装通过——
它们由 `scripts/state_graph.py --real` 报读数（**离线当门、真机报数**）。

三条纪律，和 4.1–4.3 一样：
  1. 凡是断言「框架会怎样」的地方，都要有一条**可重复跑**的证据——这一章抓到三条：
     未声明的键被静默丢弃、输入 schema 会连初值一起过滤、输出 schema 不补默认值；
  2. 每一条反向守都指着一处**真的踩过**的坑（`max_rounds` 曾被输入 schema 丢掉）；
  3. 不引 pytest：本机不装它，一致性门也能跑（同 4.3 的 `raises`）。
"""
from __future__ import annotations

import operator
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, TypedDict

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.graph import (DRAFT_TARGET_CHARS, MAX_ROUNDS, build_pipeline, initial_state,
                       new_thread)
from app.scripted import ScriptedModel, final

ARTICLE = "知舟是一个把写稿流程拆成工序的博客系统，每一步都能单独验收。" * 12
SCRIPT = [final("摘要：知舟把写稿拆成工序。")]


@contextmanager
def raises(exc_type, match: str = ""):
    """一份不依赖 pytest 的「应当抛异常」（同 4.3：测试文件不能引 pytest）。"""
    try:
        yield
    except exc_type as exc:
        if match and match not in str(exc):
            raise AssertionError(f"异常消息里没有 {match!r}：{exc}") from exc
    else:
        raise AssertionError(f"应当抛 {exc_type.__name__}，但没有")


# ---------------------------------------------------------------------------
# 状态：三种合并规则
# ---------------------------------------------------------------------------
class MergeState(TypedDict):
    overwritten: str
    accumulated: Annotated[list[str], operator.add]


def _merge_graph(*, undeclared: bool):
    def one(s):                                    # noqa: ANN001
        out = {"overwritten": "A", "accumulated": ["A"]}
        return {**out, "undeclared": "A"} if undeclared else out

    def two(s):                                    # noqa: ANN001
        out = {"overwritten": "B", "accumulated": ["B"]}
        return {**out, "undeclared": "B"} if undeclared else out

    g = StateGraph(MergeState)
    g.add_node("one", one)
    g.add_node("two", two)
    g.add_edge(START, "one")
    g.add_edge("one", "two")
    g.add_edge("two", END)
    return g.compile()


def test_default_reducer_overwrites():
    out = _merge_graph(undeclared=False).invoke({"overwritten": "-", "accumulated": ["start"]})
    assert out["overwritten"] == "B", out
    assert out["accumulated"] == ["start", "A", "B"], out


def test_undeclared_key_is_silently_dropped():
    """反向守：节点返回的键不在 schema 里 → 不报错，但**回来之后没有这个键**。"""
    out = _merge_graph(undeclared=True).invoke({"overwritten": "-", "accumulated": []})
    assert "undeclared" not in out, out


def test_accumulator_without_initial_value():
    """累加键不给初值不会抛错：框架从类型提示推一个空表（这是推断，不是契约）。"""
    class S(TypedDict):
        xs: Annotated[list[str], operator.add]

    def add(s):                                    # noqa: ANN001
        return {"xs": ["a"]}

    g = StateGraph(S)
    g.add_node("add", add)
    g.add_edge(START, "add")
    g.add_edge("add", END)
    assert g.compile().invoke({})["xs"] == ["a"]


# ---------------------------------------------------------------------------
# 上限：数的是 super-step
# ---------------------------------------------------------------------------
def _linear(n: int):
    class S(TypedDict):
        x: Annotated[int, operator.add]

    def inc(s):                                    # noqa: ANN001
        return {"x": 1}

    g = StateGraph(S)
    for i in range(n):
        g.add_node(f"n{i}", inc)
    for i in range(n - 1):
        g.add_edge(f"n{i}", f"n{i + 1}")
    g.add_edge(START, "n0")
    g.add_edge(f"n{n - 1}", END)
    return g.compile()


def test_recursion_limit_counts_super_steps():
    """3 个节点要 limit=4：**每个节点一步，再留一步收尾**。"""
    app = _linear(3)
    with raises(Exception, "Recursion limit"):
        app.invoke({"x": 0}, {"recursion_limit": 3})
    assert app.invoke({"x": 0}, {"recursion_limit": 4})["x"] == 3


def test_loop_three_rounds_needs_four():
    """同一个节点跑 3 次也是 3 步：循环不额外计费。"""
    class L(TypedDict):
        n: Annotated[int, operator.add]
        stop: int

    def work(s):                                   # noqa: ANN001
        return {"n": 1}

    def decide(s):                                 # noqa: ANN001
        return "again" if s["n"] < s["stop"] else "done"

    g = StateGraph(L)
    g.add_node("work", work)
    g.add_edge(START, "work")
    g.add_conditional_edges("work", decide, {"again": "work", "done": END})
    app = g.compile()
    with raises(Exception, "Recursion limit"):
        app.invoke({"n": 0, "stop": 3}, {"recursion_limit": 3})
    assert app.invoke({"n": 0, "stop": 3}, {"recursion_limit": 4})["n"] == 3


# ---------------------------------------------------------------------------
# 边：三种错法
# ---------------------------------------------------------------------------
def test_route_value_missing_from_map_is_runtime_keyerror():
    """反向守：路由返回的名字不在映射表里——compile 不报，跑到那一步才抛 `KeyError`。"""
    class S(TypedDict):
        x: Annotated[int, operator.add]

    g = StateGraph(S)
    g.add_node("a", lambda s: {"x": 1})
    g.add_node("b", lambda s: {"x": 10})
    g.add_edge(START, "a")
    g.add_conditional_edges("a", lambda s: "two", {"one": "b"})
    g.add_edge("b", END)
    app = g.compile()                                   # 这里不报错，正是坑的一半
    with raises(KeyError, "two"):
        app.invoke({"x": 0})


def test_typo_in_map_target_fails_at_compile():
    """映射表里的目标名写错是 compile 期就能拦下的——三种错法里只有这一种。"""
    class S(TypedDict):
        x: Annotated[int, operator.add]

    g = StateGraph(S)
    g.add_node("a", lambda s: {"x": 1})
    g.add_edge(START, "a")
    g.add_conditional_edges("a", lambda s: "ok", {"ok": "typo_node"})
    with raises(ValueError, "unknown target"):
        g.compile()


def test_orphan_node_is_silent():
    """反向守：孤立节点 compile 不报、运行也不报，它只是**一次都不跑**。

    官方对 `compile` 的描述里提到「孤立节点」那类结构检查；1.2.2 上实测没有拦。
    「图上写了它」与「它会跑」是两件事（3.10 的接线状态表是同一条教训）。
    """
    class S(TypedDict):
        x: Annotated[int, operator.add]

    def a(s):                                          # noqa: ANN001
        return {"x": 1}

    def orphan(s):                                     # noqa: ANN001
        return {"x": 100}

    g = StateGraph(S)
    g.add_node("a", a)
    g.add_node("orphan", orphan)
    g.add_edge(START, "a")
    g.add_edge("a", END)
    app = g.compile()
    assert app.invoke({"x": 0})["x"] == 1
    assert "orphan" in app.get_graph().nodes


# ---------------------------------------------------------------------------
# 并行：写同一个键就炸
# ---------------------------------------------------------------------------
def _fanout(a_writes: dict, b_writes: dict):
    class S(TypedDict):
        plain: str
        joined: Annotated[list[str], operator.add]

    g = StateGraph(S)
    g.add_node("a", lambda s: a_writes)
    g.add_node("b", lambda s: b_writes)
    g.add_edge(START, "a")
    g.add_edge(START, "b")
    g.add_edge("a", END)
    g.add_edge("b", END)
    return g.compile()


def test_parallel_same_key_needs_reducer():
    """反向守：两条边从同一节点出发，写同一个无 reducer 的键 → `InvalidUpdateError`。"""
    with raises(Exception, "Can receive only one value per step"):
        _fanout({"plain": "a"}, {"plain": "b"}).invoke({"plain": "-", "joined": []})


def test_parallel_reducer_merges_in_node_order():
    out = _fanout({"joined": ["a"]}, {"joined": ["b"]}).invoke({"plain": "-", "joined": []})
    assert out["joined"] == ["a", "b"], out
    assert out["plain"] == "-", out          # 没人写它 → 保持初值


# ---------------------------------------------------------------------------
# 流：帧数
# ---------------------------------------------------------------------------
def test_stream_frame_counts():
    app = _linear(3)
    assert len(list(app.stream({"x": 0}, stream_mode="values"))) == 4
    assert len(list(app.stream({"x": 0}, stream_mode="updates"))) == 3
    assert len(list(app.stream({"x": 0}, stream_mode="debug"))) == 6


# ---------------------------------------------------------------------------
# 多 schema：过滤的是谁
# ---------------------------------------------------------------------------
class _In(TypedDict):
    seed: str


class _Out(TypedDict):
    shown: str


class _Inner(TypedDict):
    seed: str
    shown: str
    private_note: str


def _schema_graph():
    def step(s):                                   # noqa: ANN001
        return {"shown": s["seed"] + "!", "private_note": "内部账"}

    g = StateGraph(_Inner, input_schema=_In, output_schema=_Out)
    g.add_node("step", step)
    g.add_edge(START, "step")
    g.add_edge("step", END)
    return g.compile()


def test_input_schema_filters_initial_values():
    """反向守：不在输入 schema 里的初值**进不来**（`max_rounds` 就是这么丢的）。"""
    out = _schema_graph().invoke({"seed": "正文", "shown": "坏的初值", "private_note": "坏的初值"})
    assert out == {"shown": "正文!"}, out


def test_output_schema_does_not_default_missing_keys():
    """输出 schema 只过滤，不补默认值：**谁都没写过**的键不在返回值里，不是 `None`/`False`。

    第一版把 `flag` 放进输入里再断言它不在输出里——写错了：**输入给过的键不算「没写过」**。
    改成一个输入 schema 没有、节点也不碰的键，读数才对上流水线里 `approved` 的实情。
    """
    class Inner(TypedDict):
        note: str
        flag: bool

    class In(TypedDict):
        note: str

    class Out(TypedDict):
        note: str
        flag: bool

    def step(s):                                   # noqa: ANN001
        return {"note": "写了一点点"}

    g = StateGraph(Inner, input_schema=In, output_schema=Out)
    g.add_node("step", step)
    g.add_edge(START, "step")
    g.add_edge("step", END)
    out = g.compile().invoke({"note": ""})
    assert out["note"] == "写了一点点"
    assert "flag" not in out, out


def test_private_channel_leaks_in_values_stream():
    """官方文档明写、这条测试守住它：私有通道**对流不隐身**。"""
    frames = list(_schema_graph().stream({"seed": "正文"}, stream_mode="values"))
    assert "private_note" in frames[-1], frames[-1]


# ---------------------------------------------------------------------------
# 流水线：两个出口、子图、中断
# ---------------------------------------------------------------------------
def _pipeline(**kw):
    return build_pipeline(ScriptedModel(script=list(SCRIPT)),
                          checkpointer=InMemorySaver(), **kw)


def test_pipeline_runs_two_rounds_and_pauses():
    app = _pipeline()
    cfg = new_thread("t-pass")
    first = app.invoke(initial_state(ARTICLE, "知舟简介"), cfg)
    inner = app.get_state(cfg).values
    assert inner["rounds"] == 2, inner["log"]
    assert len(inner["revisions"]) == 2
    assert inner["log"][-1].startswith("review pass"), inner["log"]
    assert len(inner["draft"]) >= DRAFT_TARGET_CHARS
    assert "__interrupt__" in first
    assert "approved" not in first          # 还没写过的键不在输出里


def test_pipeline_resume_marks_approved():
    app = _pipeline()
    cfg = new_thread("t-approve")
    app.invoke(initial_state(ARTICLE, "知舟简介"), cfg)
    out = app.invoke(Command(resume=True), cfg)
    assert out["approved"] is True, out
    assert out["summary"], out               # 子图当节点的产物进了输出 schema


def test_pipeline_budget_exit():
    """短正文两轮都不够 → 走预算出口，而它**不会**把没通过的稿子标成通过。"""
    app = _pipeline()
    cfg = new_thread("t-budget")
    app.invoke(initial_state("太短。", "预算出口"), cfg)
    inner = app.get_state(cfg).values
    assert inner["rounds"] == MAX_ROUNDS
    assert all("review pass" not in line for line in inner["log"]), inner["log"]


def test_pipeline_without_checkpointer_cannot_resume():
    """反向守：不挂检查点时**中断照样发生**，但恢复会抛——两半都要测。"""
    app = build_pipeline(ScriptedModel(script=list(SCRIPT)))
    paused = app.invoke(initial_state(ARTICLE, "无检查点"))
    assert "__interrupt__" in paused
    with raises(RuntimeError, "without checkpointer"):
        app.invoke(Command(resume=True))


def test_subgraph_node_can_be_switched_off():
    """子图的价值在接口：关掉它，主图其余部分一字不改（`summary` 连键都没有）。

    注意这里断言的是**「没有这个键」**而不是「等于空串」——`initial_state()` 里那个 `"summary": ""`
    本来也进不来（它不在输入 schema 里）。两件事叠在一起，读数是同一个。
    """
    app = _pipeline(with_summary=False)
    cfg = new_thread("t-nosummary")
    app.invoke(initial_state(ARTICLE, "没有子图"), cfg)
    assert "summary" not in app.get_state(cfg).values


def test_completed_thread_does_not_replay_on_resume():
    """反向守：跑完之后再 `resume` 是空转——它返回旧状态，**不重放**。"""
    app = _pipeline()
    cfg = new_thread("t-idle")
    app.invoke(initial_state(ARTICLE, "知舟简介"), cfg)
    app.invoke(Command(resume=True), cfg)
    before = list(app.get_state(cfg).values["log"])
    app.invoke(Command(resume=True), cfg)
    assert app.get_state(cfg).values["log"] == before


def main() -> int:
    """本机不装 pytest 也能跑：直接调本模块里所有 `test_` 开头的函数。"""
    import traceback

    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ✔ {name}")
            except Exception:                       # noqa: BLE001
                failed += 1
                print(f"  ✖ {name}")
                traceback.print_exc()
    print(f"{'✖' if failed else '✔'} test_state_graph："
          f"{len([n for n in globals() if n.startswith('test_')]) - failed} 通过 / {failed} 失败")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
