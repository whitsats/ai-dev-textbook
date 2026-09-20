"""job 图与并发：`needs` 决定**关键路径**，`matrix` 决定**格数**，`concurrency` 决定**取消谁**。

这一块把「流水线有多快」拆成三个互不相干的旋钮，而它们的共同点是
**调错了都不会报错**——只会让你的门少了一层，或者让账单多几倍。

1. **`needs`**：它写的是「谁等谁」。不写就是「谁都不等谁」——那么所有 job **同时起**，
   墙钟最短，而**门是假的**：`e2e` 会跑在 `unit` 之前，跑出来的那个绿与这一版代码无关。
   这一块因此同时报两个数：**墙钟**与**顺序违背数**（有多少对「逻辑上必须先后」的关系
   没有被 `needs` 表达出来）。最快的图往往不是最好的图，而「快」这一栏永远比「对」显眼。
2. **并行槽位**：加槽位只在**关键路径还没被占满**时省时间。一条链（每步都要等上一步）
   无论给多少槽位都是那么久；而一个正确的图从 2 个槽加到 4 个槽，**一分钟都不省**。
3. **`matrix`**：它把**格数**变成 job 数，于是变成账单。官方口径里格与格之间**互不相干**，
   所以「6 格」意味着 6 倍的分钟数；`exclude` 掉两格就省三分之一，
   而 `fail-fast`（默认开）在某一格红掉时**取消**其余格——被取消的格报的是 `cancelled`，
   **既不是失败，也不是通过**（第 5 组那张表里它是唯一「跑了却没结论」的一格）。
4. **`concurrency`**：`cancel-in-progress: true` 会取消同一个 group **正在跑的那一个**。
   连推三次时它省下的是两次全量；而它也有一个不会报错的反面：`group:` 的键写宽了
   （例如只写 `ci` 而不带 `github.ref`），于是**在 main 上的一次运行会把 PR 的运行取消掉**。

官方给「必需检查」的合格结论只有三种（`successful` / `skipped` / `neutral`），
所以这一块报出来的第三种结论 `cancelled` 要单独记：它不在这三种里。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    name: str
    minutes: int
    needs: tuple[str, ...] = ()


#: 五个 job 的真实耗时（脚本化的分钟数）。
FLAT: tuple[Job, ...] = (
    Job("lint", 2),
    Job("unit", 6),
    Job("integration", 9),
    Job("e2e", 12),
    Job("deploy", 3),
)

#: 一条链：每一个都等上一个。**没有并行**，所以槽位加多少都不省。
CHAIN: tuple[Job, ...] = (
    Job("lint", 2),
    Job("unit", 6, needs=("lint",)),
    Job("integration", 9, needs=("unit",)),
    Job("e2e", 12, needs=("integration",)),
    Job("deploy", 3, needs=("e2e",)),
)

#: 正确的图：lint 与 unit 并行，**集成与 e2e 都等 unit**，部署等它们两个。
GRAPH: tuple[Job, ...] = (
    Job("lint", 2),
    Job("unit", 6),
    Job("integration", 9, needs=("unit",)),
    Job("e2e", 12, needs=("unit",)),
    Job("deploy", 3, needs=("integration", "e2e")),
)

#: 「逻辑上必须先后」的五对关系（这一列是人写下来的语义，不是算出来的）。
MUST_PRECEDE: tuple[tuple[str, str], ...] = (
    ("lint", "unit"),
    ("unit", "integration"),
    ("unit", "e2e"),
    ("integration", "deploy"),
    ("e2e", "deploy"),
)


def reaches(jobs: tuple[Job, ...], a: str, b: str) -> bool:
    """`a` 是不是 `b` 的（直接或间接）前置。"""
    index = {j.name: j for j in jobs}
    seen: set[str] = set()
    stack = [b]
    while stack:
        name = stack.pop()
        for dep in index[name].needs:
            if dep == a:
                return True
            if dep not in seen:
                seen.add(dep)
                stack.append(dep)
    return False


def violations(jobs: tuple[Job, ...]) -> tuple[tuple[str, str], ...]:
    """没有被 `needs` 表达出来的先后关系——**这些就是「门少了一层」的份数**。"""
    return tuple((a, b) for a, b in MUST_PRECEDE if not reaches(jobs, a, b))


def critical_path(jobs: tuple[Job, ...]) -> tuple[tuple[str, ...], int]:
    """最长的那条链（按 `needs` 算；并列时取名字序，保证可复现）。"""
    index = {j.name: j for j in jobs}

    def path(name: str) -> tuple[tuple[str, ...], int]:
        best: tuple[tuple[str, ...], int] = ((), 0)
        for dep in sorted(index[name].needs):
            p, m = path(dep)
            if m > best[1] or (m == best[1] and p < best[0]):
                best = (p, m)
        return best[0] + (name,), best[1] + index[name].minutes

    best: tuple[tuple[str, ...], int] = ((), 0)
    for job in sorted(jobs, key=lambda j: j.name):
        p, m = path(job.name)
        if m > best[1] or (m == best[1] and p < best[0]):
            best = (p, m)
    return best


def makespan(jobs: tuple[Job, ...], slots: int) -> int:
    """墙钟：把 job 按 `needs` 的顺序塞进 `slots` 条跑道（每条跑道一次跑一个 job）。

    调度规则是「谁的前置都做完了就起谁」，不预占——这足够复现这一块的每一条结论
    （加槽位只在关键路径没被占满时省时间），而它比真实 runner 的调度更好复算。
    """
    done: dict[str, int] = {}
    running: list[tuple[int, str]] = []          # (结束时刻, 名字)
    remaining = list(jobs)
    now = 0
    while remaining or running:
        free = slots - len(running)
        if free > 0:
            for job in sorted(remaining, key=lambda j: (-j.minutes, j.name)):
                if all(dep in done for dep in job.needs):
                    running.append((now + job.minutes, job.name))
                    remaining.remove(job)
                    free -= 1
                    if free == 0:
                        break
        if not running:                           # 前置成环之类：不该发生
            break
        end = min(e for e, _ in running)
        finished = [n for e, n in running if e == end]
        for name in finished:
            done[name] = end
        running = [(e, n) for e, n in running if e != end]
        now = end
    return max(done.values()) if done else 0


def graph_table() -> list[dict]:
    """三种图 × 三种并行槽位：墙钟、关键路径、顺序违背数。"""
    rows: list[dict] = []
    for label, jobs in (("扁平（谁都不 needs 谁）", FLAT),
                        ("一条链（每步都等上一步）", CHAIN),
                        ("正确的图（lint 与 unit 并行）", GRAPH)):
        path, minutes = critical_path(jobs)
        rows.append({
            "graph": label,
            "path": " → ".join(path),
            "critical": minutes,
            "slots1": makespan(jobs, 1),
            "slots2": makespan(jobs, 2),
            "slots4": makespan(jobs, 4),
            "violations": len(violations(jobs)),
        })
    return rows


# ------------------------------------------------------- matrix

#: 6 格的矩阵：三个 Python 版本 × 两个目录。格与格互不相干，所以 6 格 = 6 个 job。
MATRIX_PY = ("3.11", "3.12", "3.13")
MATRIX_DIR = ("backend", "frontend")
PER_CELL_MINUTES = 4

#: 官方口径里的 `exclude`：把「前端 × 两个旧版本」三格去掉，剩下 4 格。
EXCLUDE: tuple[dict[str, str], ...] = (
    {"dir": "frontend", "python": "3.11"},
    {"dir": "frontend", "python": "3.12"},
)


def matrix_cells() -> tuple[tuple[str, str], ...]:
    """`exclude` 之后真正会跑的格。"""
    return tuple((py, d) for py in MATRIX_PY for d in MATRIX_DIR
                 if not any(x["python"] == py and x["dir"] == d for x in EXCLUDE))


def matrix_table(slots: int = 2) -> list[dict]:
    """三档矩阵：全格 / 去掉两格 / 去掉两格且某一格红掉（`fail-fast` 默认开）。"""
    full = [(py, d) for py in MATRIX_PY for d in MATRIX_DIR]
    kept = matrix_cells()
    rows: list[dict] = []
    for label, cells in (("六格全跑", full),
                         ("exclude 掉两格", kept)):
        rows.append({
            "shape": label,
            "cells": len(cells),
            "billable": len(cells) * PER_CELL_MINUTES,
            "wall": -(-len(cells) * PER_CELL_MINUTES // slots),
        })
    # fail-fast：第一格在**第 1 分钟**就红掉，兄弟格当场被取消——所以它不是「省了几分钟」，
    # 是「兄弟格还没跑完就被叫停」；代价是那三格从此**没有结论**（官方口径里 `cancelled`
    # 既不是失败，也不是通过）。
    rows.append({
        "shape": "其中第一格红掉（fail-fast）",
        "cells": len(kept),
        "billable": 1 + 1,                       # 红的那格跑了 1 分钟 + 一个兄弟也跑了 1 分钟
        "wall": 1,
        "cancelled": len(kept) - 1,
        "verdicts": ("failure",) + ("cancelled",) * (len(kept) - 1),
    })
    return rows


# ------------------------------------------------------- concurrency

#: 官方语法：`concurrency.group` 相同即互斥；`cancel-in-progress: true` 取消正在跑的那一个。
def concurrency_table(run_minutes: int = 21, gap: int = 3) -> list[dict]:
    """连推三次（每 3 分钟一次）时的账单：取消 / 排队 / 键写宽了三种写法。"""
    rows: list[dict] = []
    # ① 取消：第 1 次跑到第 3 分钟被第 2 次取消，第 2 次跑到第 3 分钟被第 3 次取消
    rows.append({
        "shape": "cancel-in-progress: true（group 带 ref）",
        "billable": gap + gap + run_minutes,
        "runs": 3,
        "killed": 2,
        "last_word": "最后一次",
        "note": "前两次各跑到被取消那一刻，只有最后一次给结论",
    })
    # ② 排队：三个 run 都要跑完，而前两个测的是已经不在的代码
    rows.append({
        "shape": "不写 cancel-in-progress（同一个 group 排队）",
        "billable": run_minutes * 3,
        "runs": 3,
        "killed": 0,
        "last_word": "最后一次（前两次的结论已经过期）",
        "note": "一次推送的延迟变成了后面所有推送的等待",
    })
    # ③ group 键写宽了：不带 ref，于是跨分支互相取消
    rows.append({
        "shape": "group 写宽了（只写 ci，不带 ref）",
        "billable": gap + gap + run_minutes,
        "runs": 3,
        "killed": 2,
        "last_word": "最后一次",
        "note": "**在 main 上的一次运行会把 PR 的运行取消掉**——两次不相干的推送互相踩",
    })
    return rows
