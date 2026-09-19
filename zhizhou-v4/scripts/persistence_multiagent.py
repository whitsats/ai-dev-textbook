#!/usr/bin/env python
"""4.5 的可运行脚本：持久化与多智能体编排，五组读数。

    python scripts/persistence_multiagent.py --offline    # 不需要密钥：离线当门
    python scripts/persistence_multiagent.py --real       # 真机：模型调度者 ＋ 模型角色

五组读数的分工：

  ① 快照长什么样、一步一份          —— 检查点不是日志，是**状态在某一刻的整份**
  ② 换一个进程还读得到吗             —— 内存后端不行，SQLite 后端行（**子进程实测**）
  ③ 回到旧的那一步再走一遍           —— 时间旅行与分支：同一个 step 出现两份快照
  ④ 交接没上限会怎样                 —— `GraphRecursionError`；有上限才自己收口
  ⑤ 三人团队一遍                     —— 上场顺序、交接次数、两条出口的不同痕迹

前四组都是**机制读数**（小图 ＋ 剧本模型），第五组才是知舟的团队。
「离线当门、真机报数」是 3.9 起的做法：离线那几条必须每次都一样，
真机那几条只报数、不进提交门（同一路径跑两遍的差可能大于两条路径之差，4.3 量过）。
"""
from __future__ import annotations

import argparse
import operator
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated, TypedDict

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langgraph.checkpoint.memory import InMemorySaver              # noqa: E402
from langgraph.errors import GraphRecursionError, InvalidUpdateError  # noqa: E402
from langgraph.graph import END, START, StateGraph                  # noqa: E402
from langgraph.types import Command                                 # noqa: E402

from app.checkpoint import SqliteCheckpointer, at_checkpoint, history  # noqa: E402
from app.graph import build_pipeline, initial_state                 # noqa: E402
from app.scripted import ScriptedModel, final                       # noqa: E402
from app.supervisor import (build_team, build_team_with_goto,       # noqa: E402
                            initial_team_state, new_thread)

LINE = "=" * 74
ARTICLE = "知舟是一个把写稿流程拆成工序的博客系统，每一步都能单独验收。" * 12
TASK = "给新版本写一篇发布说明"


# ---------------------------------------------------------------------------
# ① 快照：一步一份，读回来是一张表
# ---------------------------------------------------------------------------
def part1_snapshots(db: Path) -> None:
    print(f"{LINE}\n① 检查点：一步一份，而不是一条日志\n{LINE}")
    model = ScriptedModel(script=[final("摘要一句")])
    app = build_pipeline(model, checkpointer=SqliteCheckpointer(str(db)))
    cfg = new_thread("snap-1")
    out = app.invoke(initial_state(ARTICLE, "发布说明"), cfg)
    rows = history(app, cfg)
    print(f"一次 invoke 的返回值键：{sorted(out.keys())}")
    print(f"{'步骤':<6}{'来源':<8}{'下一步':<22}{'账目条数'}")
    for row in rows:
        print(f"{row['step']:<6}{row['source']:<8}{str(row['next']):<22}{row['log_len']}")
    loop_steps = [r for r in rows if r["source"] == "loop"]
    print(f"快照 {len(rows)} 份 = 超级步 {len(loop_steps)} 步 ＋ 1 份输入（step=-1）")
    print("返回值里**看不到** `log` 与 `rounds`：它们是内部账，但快照里全都在")
    app.checkpointer.close()
    return app


# ---------------------------------------------------------------------------
# ② 跨进程：内存后端不行，SQLite 后端行
# ---------------------------------------------------------------------------
CHILD = """
import json, sys
sys.path.insert(0, __import__("os").environ["ZHIZHOU_TREE"])
from app.checkpoint import SqliteCheckpointer, history
from app.graph import build_pipeline, initial_state
from app.scripted import ScriptedModel, final
from langgraph.checkpoint.memory import InMemorySaver
from app.supervisor import new_thread

kind, db = sys.argv[1], sys.argv[2]
saver = InMemorySaver() if kind == "memory" else SqliteCheckpointer(db)
app = build_pipeline(ScriptedModel(script=[final("x")]), checkpointer=saver)
cfg = new_thread("cross-1")
state = app.get_state(cfg).values
print(json.dumps({"values": bool(state), "history": len(history(app, cfg))},
                 ensure_ascii=False))
"""


def _child_read(kind: str, db: Path) -> dict:
    """在**另一个进程**里读同一条线程。这是本组唯一诚实的测法。"""
    env = {"ZHIZHOU_TREE": str(ROOT)}
    import os
    proc = subprocess.run([sys.executable, "-c", CHILD, kind, str(db)],
                          capture_output=True, text=True, env={**os.environ, **env},
                          check=False)
    line = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
    if not line:
        return {"error": proc.stderr.strip().splitlines()[-1] if proc.stderr else "?"}
    import json
    return json.loads(line[-1])


def part2_cross_process(tmp: Path) -> None:
    print(f"{LINE}\n② 跨进程：换一个进程，还读得到吗\n{LINE}")
    for kind in ("memory", "sqlite"):
        db = tmp / f"cross_{kind}.sqlite"
        saver = InMemorySaver() if kind == "memory" else SqliteCheckpointer(str(db))
        app = build_pipeline(ScriptedModel(script=[final("摘要一句")]), checkpointer=saver)
        app.invoke(initial_state(ARTICLE, "发布说明"), new_thread("cross-1"))
        same = app.get_state(new_thread("cross-1")).values
        child = _child_read(kind, db)
        label = "InMemorySaver" if kind == "memory" else "SqliteCheckpointer"
        print(f"{label:<20} 同进程：{'有' if same else '无':<4}"
              f" 另一个进程：{'有' if child.get('values') else '无'}"
              f"（快照 {child.get('history', '-')} 份）")
        # 关掉连接：Windows 上没关就删不掉临时目录（本脚本第一版就是这么挂的）
        if kind == "sqlite":
            saver.close()
    print("结论：**换后端不是换介质**。InMemorySaver 活在进程的内存里，")
    print("      所以「同一台机器、同一个 thread_id」在新进程里就是一条空线程。")
    print("另外：SqliteCheckpointer(':memory:') 同样跨不过进程——路径才是契约。")


# ---------------------------------------------------------------------------
# ③ 时间旅行与分支：回到旧的那一步
# ---------------------------------------------------------------------------
def part3_time_travel(db: Path) -> None:
    print(f"{LINE}\n③ 时间旅行：回到旧快照，再往前走\n{LINE}")
    app = build_pipeline(ScriptedModel(script=[final("摘要一句")]),
                         checkpointer=SqliteCheckpointer(str(db)))
    cfg = new_thread("fork-1")
    app.invoke(initial_state(ARTICLE, "发布说明"), cfg)
    rows = history(app, cfg)
    target = [r for r in rows if r["step"] == 1][0]
    print(f"第 1 步的快照：{target['checkpoint_id'][:8]}… next={target['next']}")
    # 三个键一次给全（少 `checkpoint_ns` 时内存后端会 KeyError，而本模块的 SQLite
    # 后端拿 `.get` 兜住了——两个后端对「配置缺键」的容忍度不一样）。
    old_cfg = at_checkpoint("fork-1", target["checkpoint_id"])
    try:
        app.update_state(old_cfg, {"draft": "【人工改过的一稿】"})
    except InvalidUpdateError as exc:
        # 分支点上有可能「上一个超级步是好几个节点一起写的」，于是这一笔人工修改
        # **算在谁头上**就有歧义。框架不猜，直接要求 `as_node`——
        # 报错文案（`Ambiguous update, specify as_node`）比它的名字友好得多。
        print(f"不给归属 → {type(exc).__name__}: {exc}")
        app.update_state(old_cfg, {"draft": "【人工改过的一稿】"}, as_node="draft")
        print("补上 `as_node='draft'` 之后：这一笔记在 `draft` 头上")
    after = history(app, cfg)
    per_step: dict[int, int] = {}
    for row in after:
        per_step[row["step"]] = per_step.get(row["step"], 0) + 1
    print("分支后各步骤的快照份数：", dict(sorted(per_step.items())))
    forked = sorted(step for step, n in per_step.items() if n > 1)
    print(f"步骤 {forked} 各有 2 份快照——**同一个步骤两条路**，旧的那条不会被覆盖")
    again = app.invoke(None, old_cfg)
    print(f"从第 1 步再走一遍：草稿＝{again['draft'][:24]}…（长度 {len(again['draft'])}）")
    print("`update_state` 造的是 `source='update'` 的新快照；")
    print("**被分支的旧路不会被删**，所以「改坏了退回去」是真的退得回去。")
    print("而 `invoke(None, 旧配置)` 就是「从这一步接着跑」——")
    print("      同一台机器、同一张图、不同的起点，靠的全是配置里的那个 id。")
    app.checkpointer.close()


# ---------------------------------------------------------------------------
# ④ 交接限额：没有它，图不会自己停
# ---------------------------------------------------------------------------
class Ping(TypedDict):
    hops: Annotated[int, operator.add]
    log: Annotated[list[str], operator.add]


def _alternating():      # noqa: ANN202
    """造一对互相委派的节点，并**记下它们各跑了多少次**（靠闭包，不靠框架）。"""
    seen: list[str] = []

    def ping(state: Ping) -> dict:
        seen.append("ping")
        return {"hops": 1, "log": ["ping"]}

    def pong(state: Ping) -> dict:
        seen.append("pong")
        return {"hops": 1, "log": ["pong"]}

    return ping, pong, seen


def part4_handoff_limits() -> None:
    print(f"{LINE}\n④ 交接：没有上限的团队靠异常停下\n{LINE}")
    ping, pong, seen = _alternating()
    g = StateGraph(Ping)
    g.add_node("ping", ping)
    g.add_node("pong", pong)
    g.add_edge(START, "ping")
    g.add_edge("ping", "pong")
    g.add_edge("pong", "ping")          # 互相委派，谁也不说「我干完了」
    try:
        g.compile().invoke({"hops": 0, "log": []})
    except GraphRecursionError as exc:
        print(f"无上限 → {type(exc).__name__}：{str(exc).splitlines()[0][:64]}")
        print(f"         两个节点共跑了 {len(seen)} 次（默认上限是一个大得不像话的数）")
    ping2, pong2, seen2 = _alternating()
    g2 = StateGraph(Ping)
    g2.add_node("ping", ping2)
    g2.add_node("pong", pong2)
    g2.add_edge(START, "ping")
    g2.add_edge("ping", "pong")
    g2.add_edge("pong", "ping")
    try:
        g2.compile().invoke({"hops": 0, "log": []}, {"recursion_limit": 12})
    except GraphRecursionError:
        print(f"recursion_limit=12 → 同样撞，共跑了 {len(seen2)} 次："
              f"**上限管的是图，不管业务**")
    print("这一组要说明的只有一句：**「谁会停」必须写在流程里**，")
    print("      否则唯一能停住它的东西是一个异常（3.3 的五类终止条件同一条纪律）。")

    # 有上限的团队：自己收口，并且两条出口留下不同的痕迹。
    # 这里用内存后端就够（同一个进程里读自己的账），也顺带量一件事：
    # **不挂检查点，连自己的调度记录都读不回来**。
    bare = build_team()
    cfg = new_thread("limit-1")
    bare.invoke(initial_team_state(TASK, max_handoffs=2), cfg)
    try:
        bare.get_state(cfg)
    except ValueError as exc:
        print(f"不给检查点 → get_state 抛 {type(exc).__name__}: {exc}")
    team = build_team(checkpointer=InMemorySaver())
    app3 = team.invoke(initial_team_state(TASK, max_handoffs=2), cfg)
    last = team.get_state(cfg).values["route_log"][-1]
    print(f"有上限（2 次）→ **正常返回**：上场 {len(app3['hops'])} 次，末条决定：{last}")
    print("于是「被限额截断」在账上是一条记录（`限额用尽`），而不是一个异常。")

    # `Command(goto=...)`：跳转写在节点里，目标名写错不会报错
    broken = build_team_with_goto()
    print(f"`Command(goto)` 版装配了 {len(broken.get_graph().nodes) - 2} 个节点，"
          f"图上没有条件边：{not any(e.conditional for e in broken.get_graph().edges)}")


# ---------------------------------------------------------------------------
# ⑤ 三人团队：上场顺序、交接次数、两条出口
# ---------------------------------------------------------------------------
def part5_team(real: bool, model=None, db: Path | None = None) -> dict:    # noqa: ANN001
    print(f"{LINE}\n⑤ 团队一遍：{'真机（模型调度者）' if real else '离线（规则调度者）'}\n{LINE}")
    # **团队必须配检查点**，否则指挥记录读不回来：`route_log` 不在输出 schema 里，
    # 它只在内部通道，而「内部通道」就是快照存下的那一份（4.4.7 与本节的交界）。
    saver = SqliteCheckpointer(str(db)) if db else None
    app = build_team(model if real else None, real=real, checkpointer=saver)
    cfg = new_thread("team-1")
    out = app.invoke(initial_team_state(TASK, max_handoffs=6), cfg)
    inner = app.get_state(cfg).values
    print(f"输出 schema 的键：{sorted(out.keys())}")
    print("上场顺序（也在返回值里）：")
    for line in out["hops"]:
        print("  ", line)
    print("调度记录（**只在检查点里**）：")
    for line in inner["route_log"]:
        print("  ", line)
    last = inner["route_log"][-1]
    roles = [line.split("->")[1].split("（")[0].strip() for line in inner["route_log"]]
    counted: dict[str, int] = {}
    for role in roles:
        counted[role] = counted.get(role, 0) + 1
    print(f"调度了 {len(inner['route_log'])} 次：{counted}")
    print(f"交接次数：{len(out['hops'])} ｜ 最后一条：{last}")
    print(f"答案长度：{len(out['answer'])} 字")
    if saver:
        saver.close()
    return {**out, "route_log": inner["route_log"]}


def real_readings(db: Path) -> None:
    from app.config import Config
    from app.llm import build_model
    cfg = Config.from_env()
    print(f"服务商：{cfg.redacted()['base_url']}｜模型：{cfg.model}")
    model = build_model(cfg)
    part5_team(True, model, db)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="机制读数 ＋ 规则团队，不需要密钥")
    ap.add_argument("--real", action="store_true", help="模型调度者 ＋ 模型角色，报读数")
    ap.add_argument("--keep", action="store_true", help="保留临时目录（默认跑完就删）")
    args = ap.parse_args()
    if not args.offline and not args.real:
        ap.error("要 --offline 或 --real")

    # `ignore_cleanup_errors`：Windows 上被占用的 sqlite 文件删不掉，
    # 而那是本机文件系统的脾气，不该让一次读数变成一次报错。
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tdir:
        tmp = Path(tdir)
        if args.offline:
            part1_snapshots(tmp / "snap.sqlite")
            part2_cross_process(tmp)
            part3_time_travel(tmp / "fork.sqlite")
            part4_handoff_limits()
            part5_team(False, db=tmp / "team.sqlite")
        else:
            part1_snapshots(tmp / "snap.sqlite")
            real_readings(tmp / "team_real.sqlite")
        if args.keep:
            print(f"临时目录：{tmp}")
    print(f"{LINE}\n{'离线自检通过' if args.offline else '真机读数完成'}\n{LINE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
