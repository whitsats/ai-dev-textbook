"""触发与过滤：**一次提交会不会进流水线，由过滤器决定——而过滤器写窄一格，就是一类改动从此没有门。**

8.1 那一章问的是「打出来的东西有多重」；从这一块起，问题换成**「有没有人去打它」**。
流水线的第一道关口不是测试，是**触发器**：`on:` 决定这个工作流响应哪些事件，
`paths:` / `paths-ignore:` 决定**哪些改动根本不进流水线**。后者的性质值得单说一句：
它**不是「跳过一次检查」，而是「这一类改动从此没有再被检查过」**——而这一点不会出现在任何输出里。

四种写法各自的脾气：

1. **不写过滤器**：所有改动都进流水线。代价是账单（文档改一次也跑一轮全量），
   好处是**没有盲区**——它的问题是「跑得太多」，而多跑是不报错的；
2. **白名单**（`paths:`）：默认拒绝。它漏掉的是**名单之外的现在**——
   包括「改工作流自己」那一条（改门的人被关在门外），以及任何后来新增的目录；
3. **黑名单**（`paths-ignore:`）：默认放行。它漏掉的是**没人想到要挡的未来**——
   今天不痛，因为新目录默认是被检查的；痛在「某天有人往一个被忽略的目录里放了一个配置文件」；
4. **`[skip ci]`**：写在提交信息里，**五个固定的字符串之一**，让 push 与 pull_request
   两个事件都不起流水线。它是最锋利也最容易被当成「省时间」的一招：
   官方口径明确说，因提交信息被跳过的检查会**停在 Pending**——
   而要求这些检查通过的 PR **会被挡住合并**（见 `gate` 那一块）。

还有一件与过滤无关、但同样只在账单上显形的事：**同仓分支的一次提交会起两个 run**
（`push` 一个、`pull_request` 一个），因为两个事件都成立。fork 来的 PR 只有一个
（那个 push 发生在 fork 里，用的是 fork 自己的配置）。

这一块因此不量「CI 有多快」（那要看机器与并发），只量**哪些改动进了流水线、
哪些没进、以及没进的那一条本该不该进**——后者是这一块唯一需要人断言的地方，
所以它被单列成 `SHOULD_RUN`。
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass


@dataclass(frozen=True)
class Change:
    """一次提交。`paths` 是它碰到的所有路径（本项目里一次提交常常只碰一处）。"""

    label: str
    paths: tuple[str, ...]
    fork: bool = False
    message: str = ""

    @property
    def skips(self) -> bool:
        """提交信息里有没有那五个跳过标记之一（官方给的是这五个字符串）。"""
        upper = self.message.upper()
        return any(mark in upper for mark in SKIP_MARKS)


#: 官方口径：加进提交信息（push 那条，或 PR 的 HEAD 提交）里就跳过流水线的五个字符串。
#: 另有 `skip-checks:true` 预告行（要求写在信息末尾、前面空两行），本树不建模它——
#: 它与这五个是同一个开关的两种写法，多建一个字段只会让夹具多一倍。
SKIP_MARKS: tuple[str, ...] = ("[SKIP CI]", "[CI SKIP]", "[NO CI]", "[SKIP ACTIONS]",
                               "[ACTIONS SKIP]")


@dataclass(frozen=True)
class Workflow:
    """一个工作流的触发面。`paths` 与 `paths_ignore` **互斥**（官方语法里也是二选一）。"""

    name: str
    events: tuple[str, ...] = ("push", "pull_request")
    paths: tuple[str, ...] = ()
    paths_ignore: tuple[str, ...] = ()
    branches_ignore: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.paths and self.paths_ignore:
            raise ValueError("paths 与 paths-ignore 不能同时写（官方语法只认其中一个）")


def matches(patterns: tuple[str, ...], path: str) -> bool:
    """某个路径是否被这一组模式命中（`**` 与 `*` 按 glob 的常规读法）。"""
    return any(fnmatch.fnmatchcase(path, pat) for pat in patterns)


def passes(wf: Workflow, change: Change) -> tuple[bool, str]:
    """这一组改动符不符合这个工作流的路径条件；不符合时给出是哪一条把它挡掉的。"""
    if wf.paths_ignore:
        for path in change.paths:
            if matches(wf.paths_ignore, path):
                return False, f"paths-ignore 命中 {path}"
        return True, "黑名单未命中"
    if wf.paths:
        for path in change.paths:
            if matches(wf.paths, path):
                return True, f"白名单命中 {path}"
        return False, "白名单未命中"
    return True, "没有过滤器"


def runs_for(change: Change, wf: Workflow) -> tuple[int, str]:
    """一次提交在这个工作流下会起几个 run，以及为什么。

    三个都来自官方口径：同一仓库分支的 `push` 与 `pull_request` **都**成立（两个 run）；
    fork 的 PR 只有一个（push 在 fork 里）；提交信息带跳过标记时**两个事件都不起**——
    但那时**检查会停在 Pending**，这件事记在 `gate` 那一块的账上。
    """
    if change.skips:
        return 0, "[skip ci]：两个事件都不起（检查停在 Pending）"
    ok, why = passes(wf, change)
    if not ok:
        return 0, f"被过滤器挡住（{why}）——检查停在 Pending"
    events = [e for e in wf.events if e in ("push", "pull_request")]
    if change.fork:
        return (1, "fork 的 PR：只有 pull_request（push 发生在 fork 里）") if events else (0, "无")
    return len(events), f"{' ＋ '.join(events)} 各一个 run"


# ------------------------------------------------------- 两个断言表

#: 十次提交。`should_run` 是**人断言的**那一列（这一块唯一不是算出来的东西）：
#: 「这一处改动会影响交付出去的东西吗」——除了改文档，其余九处都会。
@dataclass(frozen=True)
class Case:
    change: Change
    should_run: bool
    note: str = ""


CASES: tuple[Case, ...] = (
    Case(Change("fix: 修一个空指针", ("app/main.py",)), True),
    Case(Change("docs: 补一段说明", ("README.md",)), False, "只有它不该跑"),
    Case(Change("deps: 升 fastapi", ("requirements.txt",)), True),
    Case(Change("feat: 前端加一个组件", ("web/src/App.tsx",)), True),
    Case(Change("chore: 调一下 Dockerfile", ("Dockerfile",)), True),
    Case(Change("test: 补一条用例", ("tests/test_api.py",)), True),
    Case(Change("fix: 改检索层", ("app/rag.py",)), True),
    Case(Change("chore: 顺手改一下门自己", (".github/workflows/ci.yml",)), True,
         "改的是那个会决定「谁跑」的文件"),
    Case(Change("chore: 加一个发布脚本", ("scripts/release.sh",)), True),
    Case(Change("chore: 更新镜像构建参数", (".github/actions/build/action.yml",)), True),
    Case(Change("chore: 新增一个部署目录", ("ops/deploy.sh",)), True,
         "白名单是枚举——而枚举永远漏一个"),
)

#: 四种过滤器写法（同一套事件）。第 2／4 行是白名单的两档宽窄，第 3 行是黑名单。
FILTERS: tuple[Workflow, ...] = (
    Workflow("不写过滤器"),
    Workflow("白名单·窄（只 app/ 与依赖）", paths=("app/**", "requirements*.txt")),
    Workflow("黑名单·宽（只挡文档）", paths_ignore=("docs/**", "**.md")),
    Workflow("白名单·宽（把该管的都列上）",
             paths=("app/**", "web/**", "tests/**", "scripts/**", "Dockerfile",
                    "requirements*.txt", "pyproject.toml", ".github/**")),
)


def filter_table() -> list[dict]:
    """四种写法 × 十次提交：进几次流水线、漏掉几条本该跑的、最贵的那条漏在谁身上。"""
    rows: list[dict] = []
    for wf in FILTERS:
        ran, missed, worst = 0, [], ""
        for case in CASES:
            n, _ = runs_for(case.change, wf)
            if n:
                ran += 1
            elif case.should_run:
                missed.append(case.change.label)
        # 「最贵的那条」＝ 漏掉里影响面最大的一条：这里按固定优先级点名
        for label in ("chore: 顺手改一下门自己", "chore: 更新镜像构建参数",
                      "chore: 新增一个部署目录", "chore: 调一下 Dockerfile",
                      "feat: 前端加一个组件"):
            if label in missed:
                worst = label
                break
        rows.append({
            "filter": wf.name,
            "ran": ran,
            "missed": len(missed),
            "missed_labels": tuple(missed),
            "worst": worst,
        })
    return rows


def skip_table() -> list[dict]:
    """一次提交起几个 run：同仓 / fork / 带跳过标记，三种情形。"""
    same = Change("fix: 改检索层", ("app/rag.py",), fork=False)
    fork = Change("fix: 改检索层", ("app/rag.py",), fork=True)
    skip = Change("fix: 改检索层（[skip ci]）", ("app/rag.py",),
                  message="fix: 改检索层\n\n[skip ci] 本地已经跑过了")
    wf = Workflow("CI")
    rows: list[dict] = []
    for label, change in (("同仓分支", same), ("fork 的 PR", fork),
                          ("提交信息带 [skip ci]", skip)):
        n, why = runs_for(change, wf)
        rows.append({"case": label, "runs": n, "why": why,
                     "check": "Pending" if n == 0 else "会有结论"})
    return rows


#: 十次提交里「本该进流水线」的条数（人断言的那一列之和）。
SHOULD_RUN = sum(1 for c in CASES if c.should_run)
