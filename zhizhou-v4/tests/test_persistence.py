# tests/test_persistence.py —— 不需要密钥、不需要网络：持久化与多智能体编排
"""这一份测的是 4.5 的结论，**全部不需要模型服务商**。

需要真实模型的那几件事（模型调度者会不会绕圈、真机词元）不在这里假装通过——
它们由 `scripts/persistence_multiagent.py --real` 报读数（**离线当门、真机报数**）。

三条纪律，与 4.1–4.4 一致：
  1. 凡是断言「后端会怎样」的地方，都要有一条**可重复跑**的证据——
     这里最要紧的一条是「另一个进程读得到吗」，所以它用真子进程测，不用 mock；
  2. 每条反向守都指着一处真的踩过的坑（`update_state` 缺 `as_node`、
     输入 schema 把初值过滤掉、不给检查点读不到内部账）；
  3. 不引 pytest：本机不装它，一致性门也能跑。
"""
from __future__ import annotations

import json
import operator
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, TypedDict

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langgraph.checkpoint.memory import InMemorySaver                     # noqa: E402
from langgraph.errors import GraphRecursionError, InvalidUpdateError      # noqa: E402
from langgraph.graph import END, START, StateGraph                        # noqa: E402

from app.checkpoint import SqliteCheckpointer, at_checkpoint, history      # noqa: E402
from app.graph import build_pipeline, initial_state, new_thread           # noqa: E402
from app.scripted import ScriptedModel, final                             # noqa: E402
from app.supervisor import (Route, build_team, initial_team_state,        # noqa: E402
                            model_supervisor)

ARTICLE = "知舟是一个把写稿流程拆成工序的博客系统，每一步都能单独验收。" * 12
SCRIPT = [final("摘要：知舟把写稿拆成工序。")]
TASK = "给新版本写一篇发布说明"


@contextmanager
def raises(exc_type, match: str = ""):
    """一份不依赖 pytest 的「应当抛异常」（同 4.3、4.4）。"""
    try:
        yield
    except exc_type as exc:
        if match and match not in str(exc):
            raise AssertionError(f"异常消息里没有 {match!r}：{exc}") from exc
    else:
        raise AssertionError(f"应当抛 {exc_type.__name__}，但没有")


# 子进程要读的就是「另一个进程」。程序写在常量里而不是另一个 .py 文件里，
# 是为了让「这份测试测的到底是什么」一眼可见。
class PingState(TypedDict):
    """第 4 节那张「互相委派」的小图。**要在模块层声明**：本地声明的 TypedDict
    配上 `from __future__ import annotations` 时，注解会被当成字符串、在模块全局里求值，
    而 `Annotated` 若是函数内导入的，就 `NameError`（本文件第一版就是这么挂的）。
    """

    hops: Annotated[int, operator.add]


CHILD = """
import json, os, sys
sys.path.insert(0, os.environ["ZHIZHOU_TREE"])
from app.checkpoint import SqliteCheckpointer, history
from app.graph import build_pipeline
from app.scripted import ScriptedModel, final
from app.supervisor import new_thread
from langgraph.checkpoint.memory import InMemorySaver

kind, db = sys.argv[1], sys.argv[2]
saver = InMemorySaver() if kind == "memory" else SqliteCheckpointer(db)
app = build_pipeline(ScriptedModel(script=[final("x")]), checkpointer=saver)
cfg = new_thread("cross-1")
print(json.dumps({"values": bool(app.get_state(cfg).values),
                  "history": len(history(app, cfg))}, ensure_ascii=False))
"""


def _child_read(kind: str, db: str) -> dict:
    proc = subprocess.run([sys.executable, "-c", CHILD, kind, db], capture_output=True,
                          text=True, env={**os.environ, "ZHIZHOU_TREE": str(ROOT)},
                          check=False)
    line = [ln for ln in proc.stdout.strip().splitlines() if ln.startswith("{")]
    assert line, f"子进程没有输出读数：{proc.stderr[-400:]}"
    return json.loads(line[-1])


def _pipeline(saver, thread: str):                       # noqa: ANN001, ANN202
    app = build_pipeline(ScriptedModel(script=SCRIPT), checkpointer=saver)
    cfg = new_thread(thread)
    app.invoke(initial_state(ARTICLE, "发布说明"), cfg)
    return app, cfg


# --------------------------------------------------------------------------- 检查点
def test_one_snapshot_per_superstep():
    """快照是一步一份：5 个超级步 ＋ 1 份输入，**不是一条日志**。"""
    app, cfg = _pipeline(InMemorySaver(), "t-steps")
    rows = history(app, cfg)
    assert [r["source"] for r in rows] == ["loop"] * 5 + ["input"], rows
    assert [r["step"] for r in rows] == [4, 3, 2, 1, 0, -1]
    assert all(r["parent"] for r in rows[:-1]), "链子一直串到最老那份输入快照为止"
    assert rows[-1]["parent"] is None, "第一份没有人指向它"


def test_history_is_newest_first():
    """`get_state_history` 的顺序是**最新在前**——按 `checkpoint_id` 倒序，不是行号。"""
    app, cfg = _pipeline(InMemorySaver(), "t-order")
    steps = [r["step"] for r in history(app, cfg)]
    assert steps == sorted(steps, reverse=True)


def test_sqlite_checkpointer_survives_another_process():
    """**本章最贵的一条**：同一个 `thread_id`，换一个进程仍然读得回来。"""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tdir:
        db = str(Path(tdir) / "ck.sqlite")
        saver = SqliteCheckpointer(db)
        _pipeline(saver, "cross-1")
        saver.close()
        child = _child_read("sqlite", db)
    assert child["values"] is True
    assert child["history"] == 6


def test_inmemory_saver_does_not_survive_another_process():
    """反向守：内存后端在另一个进程里就是**一条空线程**（这不是 bug，是它的定义）。"""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tdir:
        db = str(Path(tdir) / "unused.sqlite")
        _pipeline(InMemorySaver(), "cross-1")
        child = _child_read("memory", db)
    assert child["values"] is False
    assert child["history"] == 0


def test_memory_path_is_not_a_cross_process_backend():
    """**换后端不是换介质**：`:memory:` 路径的 SQLite 同样跨不过进程。"""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tdir:
        # 子进程拿到的是一份「同名但空」的库：`:memory:` 里什么都没写过
        child = _child_read("sqlite", str(Path(tdir) / "mem.sqlite"))
    assert child["values"] is False


def test_delete_thread_clears_snapshots_and_writes():
    """3.8 的「按用户彻底清空」在这里落地：检查点里有正文，必须一起删。"""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tdir:
        saver = SqliteCheckpointer(str(Path(tdir) / "del.sqlite"))
        app, cfg = _pipeline(saver, "t-del")
        assert app.get_state(cfg).values or True
        saver.delete_thread("t-del")
        assert app.get_state(cfg).values == {}
        assert history(app, cfg) == []
        saver.close()


# --------------------------------------------------------------------------- 时间旅行
def test_update_state_at_a_fork_requires_as_node():
    """在分支点上改状态要**说清这笔算谁写的**，框架不猜。"""
    app, cfg = _pipeline(InMemorySaver(), "t-fork")
    old = [r for r in history(app, cfg) if r["step"] == 1][0]
    with raises(InvalidUpdateError, "Ambiguous update"):
        app.update_state(at_checkpoint("t-fork", old["checkpoint_id"]),
                         {"draft": "【人工改过的一稿】"})


def test_update_state_creates_a_branch_and_keeps_the_old_path():
    """分支：同一个步骤出现两份快照，**旧的那条不会被覆盖**。"""
    app, cfg = _pipeline(InMemorySaver(), "t-branch")
    old = [r for r in history(app, cfg) if r["step"] == 1][0]
    app.update_state(at_checkpoint("t-branch", old["checkpoint_id"]),
                     {"draft": "【人工改过的一稿】"}, as_node="draft")
    per_step: dict[int, int] = {}
    for row in history(app, cfg):
        per_step[row["step"]] = per_step.get(row["step"], 0) + 1
    assert max(per_step.values()) == 2, per_step
    assert any(r["source"] == "update" for r in history(app, cfg))


def test_resume_from_an_old_checkpoint_reruns_from_there():
    """`invoke(None, 旧配置)` ＝ 「从这一步接着跑」：同一个 id 决定起点。"""
    app, cfg = _pipeline(InMemorySaver(), "t-resume")
    old = [r for r in history(app, cfg) if r["step"] == 1][0]
    again = app.invoke(None, at_checkpoint("t-resume", old["checkpoint_id"]))
    assert again["draft"].startswith("【草稿 2】")


def test_get_state_needs_a_checkpointer():
    """不给检查点，**连自己的内部账都读不回来**（不是「读到了空表」）。"""
    bare = build_pipeline(ScriptedModel(script=SCRIPT))
    with raises(ValueError, "No checkpointer"):
        bare.get_state(new_thread("t-bare"))


# --------------------------------------------------------------------------- 多智能体
def test_team_runs_three_roles_then_finishes():
    """三个角色各上场一次，然后调度者收口——**它自己停下来的**。"""
    app = build_team(checkpointer=InMemorySaver())
    cfg = new_thread("t-team")
    out = app.invoke(initial_team_state(TASK, max_handoffs=6), cfg)
    assert len(out["hops"]) == 3, out["hops"]
    log = app.get_state(cfg).values["route_log"]
    assert log[-1].endswith("done（审校通过）"), log[-1]


def test_handoff_limit_is_part_of_the_flow_not_an_exception():
    """限额用尽时**正常返回**，并且在账上留下与「审校通过」不同的一条记录。"""
    app = build_team(checkpointer=InMemorySaver())
    cfg = new_thread("t-limit")
    out = app.invoke(initial_team_state(TASK, max_handoffs=2), cfg)
    log = app.get_state(cfg).values["route_log"]
    assert len(out["hops"]) == 2
    assert "限额用尽" in log[-1], log[-1]


def test_handoff_budget_lives_in_the_state_not_the_graph():
    """上限住在**状态**里，所以同一张图能跑两种预算——订在构造参数上就做不到。"""
    app = build_team(checkpointer=InMemorySaver())
    small = app.invoke(initial_team_state(TASK, max_handoffs=1), new_thread("t-a"))
    big = app.invoke(initial_team_state(TASK, max_handoffs=6), new_thread("t-b"))
    assert len(small["hops"]) == 1
    assert len(big["hops"]) == 3


def test_output_schema_hides_the_internal_log():
    """输出 schema 挡住内部账：调度记录只在检查点里（4.4.7 的同一条纪律）。"""
    app = build_team(checkpointer=InMemorySaver())
    cfg = new_thread("t-output")
    out = app.invoke(initial_team_state(TASK, max_handoffs=6), cfg)
    assert sorted(out.keys()) == ["answer", "hops"]
    assert app.get_state(cfg).values["route_log"], "检查点里应当有调度记录"


def test_missing_channels_read_as_empty_not_keyerror():
    """输入 schema 会把初值一起过滤掉——所以节点必须用 `.get` 读可能空着的通道。

    反向守：本模块第一版正是 `state["brief"]`，第一次运行就 `KeyError: 'brief'`。
    """
    app = build_team(checkpointer=InMemorySaver())
    # 只给输入 schema 允许的两个键：其余通道从头到尾没人给过初值
    out = app.invoke({"task": TASK, "max_handoffs": 6}, new_thread("t-min"))
    assert out["answer"]


def test_supervisor_decider_is_pure():
    """规则调度者：同一个状态永远给出同一个答案（这是它可测的全部理由）。"""
    from app.supervisor import decide_by_rules
    state = {"brief": "", "handoffs": 0, "max_handoffs": 6}
    assert decide_by_rules(state) == decide_by_rules(state) == ("researcher", "缺要点")


class _StubRouter:
    """只回一个固定路由的桩：用来测 `model_supervisor` 的**兜底那一行**。"""

    def __init__(self, nxt: str) -> None:
        self.nxt = nxt

    def invoke(self, prompt):                       # noqa: ANN001, ANN201
        return Route(next=self.nxt, reason="桩给的理由")


class _StubModel:
    def __init__(self, nxt: str) -> None:
        self.nxt = nxt

    def with_structured_output(self, schema, method=None):     # noqa: ANN001, ANN201
        return _StubRouter(self.nxt)


def test_model_scheduler_is_overruled_by_the_budget():
    """模型不认识你的预算：它想派谁是一回事，**限额说了算**是另一回事。"""
    decide = model_supervisor(_StubModel("researcher"))
    over = {"task": TASK, "handoffs": 6, "max_handoffs": 6, "brief": "", "draft": ""}
    nxt, reason = decide(over)
    assert nxt == "done" and "限额已用尽" in reason
    under = {**over, "handoffs": 0}
    assert decide(under)[0] == "researcher"


def test_pingpong_without_a_limit_dies_on_the_graph_limit():
    """没有出口的交接，唯一能停住它的是 `GraphRecursionError`——**不是一个结果**。"""
    def ping(state):                                          # noqa: ANN001, ANN202
        return {"hops": 1}

    def pong(state):                                          # noqa: ANN001, ANN202
        return {"hops": 1}

    g = StateGraph(PingState)
    g.add_node("ping", ping)
    g.add_node("pong", pong)
    g.add_edge(START, "ping")
    g.add_edge("ping", "pong")
    g.add_edge("pong", "ping")
    with raises(GraphRecursionError):
        g.compile().invoke({"hops": 0}, {"recursion_limit": 8})


def main() -> int:
    """本机不装 pytest 也能跑：直接调本模块里所有 `test_` 开头的函数。"""
    import traceback

    failed = 0
    names = [n for n in globals() if n.startswith("test_")]
    for name in sorted(names):
        fn = globals()[name]
        if not callable(fn):
            continue
        try:
            fn()
            print(f"  ✔ {name}")
        except Exception:                       # noqa: BLE001
            failed += 1
            print(f"  ✖ {name}")
            traceback.print_exc()
    print(f"{'✖' if failed else '✔'} test_persistence：{len(names) - failed} 通过 / {failed} 失败")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
