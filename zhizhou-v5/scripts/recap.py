#!/usr/bin/env python
"""5.9 的文档对账：**让手写的第二份清单自己对账。**

    python scripts/recap.py --check        # 文档 ↔ 树 的五条对账
    python scripts/recap.py --offline      # 同 --check（提交门的入口名），打印收尾标记
    python scripts/recap.py --self-test    # 28 条夹具（含「删一个模块名就红」「改一行就红」
                                           #              「夹具少写一条就红」）

五条对账，各自对应一种**不会报错**的漂移：

① **文档点名的模块必须存在**——点错了，读者照着找、找不到（读文档的人不会来问你）；
② **树里的每个模块都必须被点名**——新模块没进文档，图就从「现状」退化成一个
   不标日期的快照，而快照会被人当成现状引用；
③ **每条 ADR 引用的读数必须在实跑证据里找得到、且相等**——读数写成 `键=值`
   （放在反引号里的那一对），证据是 `experiments/eval_run.py --write-baseline`
   的产物 `experiments/eval_baseline.json`。这一条把「当时手上的那个数」
   从回忆变成**可复核的引用**：回忆会被后来的读数悄悄推翻，引用不会；
④ **文件旁边标了 `N 行` 就必须真的有 N 行**——行数与模块名同属**手写的第二份清单**：
   改一行不会让任何人报错，只会让那句话慢慢变成假的（它比模块名更难发现，
   因为「25 行」看起来永远像个真数）。这一条**只认写在反引号里的路径**：
   标注是一种约定，约定要看得见形状；
⑤ **「N 条夹具」与「N 条用例」必须与实得相等**——这两类数字只在**改脚本／测试**时
   才该变，而改脚本的人往往不觉得「文档里那个数」跟自己有关（本章接上它的头一天，
   就在架构文档里抓到一处「8 条夹具」而脚本当时已是 10 条）。两份**自描述条数**
   各有一个实得，而且**两个实得都是「跑出来的」**：夹具数在进程内数（`fixture_cases()`），
   用例数**导入那个测试模块、数它真的有几个 `test_` 函数能跑**——与树内自检
   （`tools/check_runnable.py` 那一趟逐个调起来的东西）**同一把尺子**。
   数文件里的 `def test_` 只当退路：类里写的用例、从别处引进来的用例会被那把尺子漏掉，
   而导入失败时又只有它能说话。**两个数不一样时会另报一行**——差异本身是信息，
   不该被一个数盖过去。

另加三条结构判定：ADR 必须有六个字段（编号与标题 ＋ 状态／背景／决定／
被否掉的选项／失效线）、编号不能重复，以及两条反向守——**一个模块都没解析到**、
**一条 ADR 都没解析到**，都直接报错（同 `check_runnable` 里那条「一个块都没解析到」：
解析一退化，输出就变成「全部通过」）。

**已知边界**：核到模块这一级，核不到函数名——图上写 `ingest.discover()` 而树里
改成了别的名字，这一关不会响（那是人看的那一半）。这条边界写在这里，
而不是等人某天发现它「原来没查过」。
"""
from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ARCH = DOCS / "architecture.md"
DECISIONS = DOCS / "decisions"
EVIDENCE = ROOT / "experiments" / "eval_baseline.json"
MARKER = "离线自检通过"

#: 文档里出现的可执行路径。范围与 `tools/check_runnable.py` 的 `PATH_RE` 一致：
#: 两处各写一份是**故意的**——共用同一个正则的话，正则本身写错时两边一起错而无人发现
#: （`check_runnable` 自检里那条「两种写法互相对照」是同一条纪律）。
PATH_RE = re.compile(r"\b((?:app|scripts|tests|experiments|migrations)/[\w/]+\.py)\b")
#: 读数引用：反引号里的 `键=值`。值只收数字，避免把 `k=v` 这类伪引用收进来。
CITE_RE = re.compile(r"`([A-Za-z_][\w.]*)=(-?\d+(?:\.\d+)?)`")
ADR_H1_RE = re.compile(r"^#\s*ADR-(\d{4})\s+(\S.*)$", re.M)
#: 一条 ADR 必须有的字段。「编号与标题」由 H1 承担，所以这里列五个。
FIELDS = ("状态", "背景", "决定", "被否掉的选项", "失效线")
FIELD_RES = tuple(
    (name, re.compile(r"^-\s*\*\*" + name + r"[^*]*\*\*", re.M)) for name in FIELDS
)


def pointed_paths(text: str) -> set[str]:
    """一份文档点名的路径集合。"""
    return set(PATH_RE.findall(text))


def app_modules(root: Path = ROOT) -> list[str]:
    """树里的 `app/` 模块。**从盘上长出来**，不写清单（写清单必漏，本书栽过四次）。"""
    return sorted(p.relative_to(root).as_posix()
                  for p in (root / "app").rglob("*.py") if p.name != "__init__.py")


def module_issues(docs: dict[str, str], *, exists: Callable[[str], bool],
                  modules: list[str]) -> list[str]:
    """①②两条对账（＋「一份文档都没解析到」的反向守）。

    参数是 `exists` 与 `modules` 而不是一棵真目录：这一关的夹具要能凭空造出
    「文档点了不存在的模块」这种状态，而真目录里造不出来（`STYLE` 8.8 第 5 条）。
    """
    named_by: dict[str, str] = {}
    for name in sorted(docs):
        for rel in pointed_paths(docs[name]):
            named_by.setdefault(rel, name)
    bad: list[str] = []
    for rel, who in sorted(named_by.items()):
        if not exists(rel):
            bad.append(f"{who} 点名了 {rel}，而树里没有这个文件")
    for rel in modules:
        if rel not in named_by:
            bad.append(f"{rel} 在树里，但没有一份文档点名它——图画的是旧快照")
    if not named_by:
        bad.append("一份文档里都没解析到模块路径——检查器自己坏了，先修它")
    return bad


#: 行数标注：同一行里 `` `路径` `` **之后**、最近的一个 `N 行`。数字可带千位逗号。
#: 为什么按行配对而不是按全文配对：全文配对会把「上一段的路径 ＋ 下一段的数字」
#: 配成一对，而那种错配会报出一个**看起来很像真的**行数（假红比不报更坏：
#: 假红会让人把整条检查关掉）。
COUNT_RE = re.compile(r"(\d[\d,]*)\s*行")
#: 行数这一侧认的文件：树里的可执行文件，加上 `docs/` 下的文档。
#: 这一份正则与 `PATH_RE` 各写各的是**故意的**（同 `check_runnable` 里那条
#: 「两种写法互相对照」）：共用的话，正则写错时两边一起错而无人发现。
COUNTED_RE = re.compile(
    r"`((?:(?:app|scripts|tests|experiments|migrations)/[\w/]+\.py|docs/[\w/.-]+\.md))`")


def counted_lines(text: str) -> list[tuple[str, int]]:
    """一份文档里所有「文件 ＋ N 行」的标注，按出现顺序。

    只在**同一行内**配对，且路径必须在数字左边：这两种限制都是为了让「什么样的写法
    算标注」变成一句能写进文档的规则（写不成规则，就没法要求人遵守）。
    """
    out: list[tuple[str, int]] = []
    for line in text.splitlines():
        for m in COUNT_RE.finditer(line):
            named = COUNTED_RE.findall(line[:m.start()])
            if named:
                out.append((named[-1], int(m.group(1).replace(",", ""))))
    return out


def real_lines(root: Path, rel: str) -> int | None:
    """盘上一份文件的行数。读不出来返回 `None`——**「读不出来」与「0 行」分得开**。"""
    try:
        return len((root / rel).read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeDecodeError):
        return None


def line_count_issues(docs: dict[str, str], *, exists: Callable[[str], bool],
                      count_lines: Callable[[str], int | None]) -> list[str]:
    """④ 行数标注与盘上相等（＋ 两条反向守）。

    参数是 `exists` 与 `count_lines` 而不是一棵真目录，理由同 `module_issues`：
    夹具要能凭空造出「标了 259 行、盘上 260 行」这种状态，而真目录里造不出来——
    造不出来就没法验「它真的会响」。「改一行就红」那条夹具就是这么写的。
    """
    bad: list[str] = []
    seen: dict[str, tuple[int, str]] = {}
    total = 0
    for name in sorted(docs):
        for rel, n in counted_lines(docs[name]):
            total += 1
            if not exists(rel):
                bad.append(f"{name} 给 {rel} 标了 {n} 行，而树里没有这个文件")
                continue
            real = count_lines(rel)
            if real is None:
                bad.append(f"{name} 标的 {rel} 读不出行数——先确认它是不是文本文件")
            elif real != n:
                bad.append(f"{name} 说 {rel} 有 {n} 行，盘上是 {real} 行——把新数抄进去；"
                           f"别删这个标注：删了就等于把这一栏退回没人核的状态")
            if rel in seen and seen[rel][0] != n:
                bad.append(f"{rel} 被标了两个不同的行数：{seen[rel][1]} 说 {seen[rel][0]} 行，"
                           f"{name} 说 {n} 行——一处文件只留一个数")
            seen.setdefault(rel, (n, name))
    if not total:
        # 反向守：解析一退化，输出会变成「全部通过」（同 ①② 那两条）。
        bad.append("两份文档里都没解析到「N 行」标注——检查器自己坏了，先修它")
    return bad


#: 自描述条数：「N 条夹具」说的是本脚本自己的夹具数，写在哪儿都算（它只有一个主语）。
#: **约定与本文件其余几处一样要求「看得见形状」**：阿拉伯数字就是断言，
#: 而「引用一个旧数字」要写成汉字（八条夹具）——因为一条检查自己也会被引用，
#: 没有这一条的话，写历史的人只能选择「把数字改得好看」或「把检查关掉」。
FIXTURE_KEY = "<夹具>"
FIXTURE_CLAIM_RE = re.compile(r"(\d+)\s*条夹具")
#: 「N 条用例」必须挨着一个 `tests/*.py` 路径才算是关于那个文件的断言——
#: 正文里「5 条用例」这种泛指（比如 3.2 那批回归集）到处都是，收进来全是假红。
CASE_CLAIM_RE = re.compile(r"(\d+)\s*条用例")
TEST_FILE_RE = re.compile(r"`(tests/[\w/]+\.py)`")


def case_counts(text: str) -> list[tuple[str, int]]:
    """一份文档里的两类自描述条数：`(FIXTURE_KEY, N)` 与 `(测试文件, N)`。"""
    out: list[tuple[str, int]] = []
    for line in text.splitlines():
        out += [(FIXTURE_KEY, int(n)) for n in FIXTURE_CLAIM_RE.findall(line)]
        for m in CASE_CLAIM_RE.finditer(line):
            named = TEST_FILE_RE.findall(line[:m.start()])     # 路径必须在数字左边
            if named:
                out.append((named[-1], int(m.group(1))))
    return out


def ran_cases(root: Path, rel: str) -> int | None:
    """一个测试文件里**跑得起来几条用例**：导入那个模块，数 `dir()` 里 `test_` 开头的名字。

    与 `tools/check_runnable.py` 的树内自检**同一把尺子**（它也是 import 之后数
    `dir(mod)` 里的 `test_`），所以书这一侧写「这个文件有 N 条用例」时，
    两侧数的是同一件事。不调它们（过不过由树内自检说话，这里只要条数）。

    导不进来（文件不在、包不对、模块级代码出错）返回 `None`——**「没法核」与
    「零条」必须分得开**：不然一条数不出来的断言会缩在「全部通过」里。

    清 `sys.modules` 里 `tests.*` 的那几行：同一进程里先后核两次的话，
    上一趟的旧模块会顶替新文件（这一件事只在被导入使用时才成立——本脚本平时
    是自己的进程，且测试用子进程调它；所以清干净不会伤人）。
    """
    if not (rel.startswith("tests/") and rel.endswith(".py")):
        return None
    mod_name = rel[:-3].replace("/", ".")
    # 上一趟导入的旧模块会顶替新文件（同一进程里反复核不同的树时必须清）。
    for name in [m for m in sys.modules if m == "tests" or m.startswith("tests.")]:
        del sys.modules[name]
    here = str(root)
    sys.path.insert(0, here)
    try:
        mod = importlib.import_module(mod_name)
    except Exception:                                    # noqa: BLE001
        return None
    finally:
        if sys.path and sys.path[0] == here:
            sys.path.remove(here)
    return sum(1 for n in dir(mod) if n.startswith("test_"))


def static_cases(root: Path, rel: str) -> int | None:
    """数文件里的 `def test_`（退路那把尺子）。读不出来返回 `None`。"""
    try:
        text = (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return sum(1 for ln in text.splitlines() if ln.startswith("def test_"))


def real_cases(root: Path, rel: str, *, ran: Callable[[str], int | None] | None = None) -> int | None:
    """一个测试文件里有多少条用例：**先问跑起来几条，再退回数 `def test_`**。

    两把尺子都要：`ran` 抳得到类里的用例、或从别处引进来的用例（数文件那把漏掉），
    而导入失败时又只有数文件那把还能说话。两边都拿不到才是「没法核」。
    """
    if ran is not None:
        got = ran(rel)
        if got is not None:
            return got
    return static_cases(root, rel)


def self_description_issues(docs: dict[str, str], *, fixtures: int,
                            count_cases: Callable[[str], int | None],
                            count_cases_static: Callable[[str], int | None] | None = None
                            ) -> list[str]:
    """⑤ 自描述条数（＋「一处都没解析到」的反向守）。

    `fixtures` 由调用方从 `fixture_cases()` 数出来（而不是从 `--self-test` 的输出里
    回读）：两件事都要，但**不同层次**——回读那一种是 `tests/test_recap.py` 在做
    （它跑一次子进程读 stdout），两种写法互相对照（STYLE 8.8 第 5 条）。

    `count_cases_static`：数文件那把尺子的值。给了它之后，两把尺子量出的数不一样时
    也会报一行——**差异本身是信息**（那个文件里的用例不是顶层 `def test_`），
    而正文那一侧（`check_runnable` 第七道）也是这么办的。
    """
    bad: list[str] = []
    total = 0
    for name in sorted(docs):
        for rel, n in case_counts(docs[name]):
            total += 1
            real = fixtures if rel == FIXTURE_KEY else count_cases(rel)
            if rel != FIXTURE_KEY and count_cases_static is not None and real is not None:
                other = count_cases_static(rel)
                if other is not None and other != real:
                    bad.append(f"{name} {rel}：跑起来 {real} 条用例、数文件 {other} 条"
                               f"——两把尺子量出的不一样，先弄清这个文件的用例是怎么数的")
            if real is None:
                bad.append(f"{name} 写 {rel} 有 {n} 条用例，而这个文件读不出来")
            elif real != n:
                bad.append(f"{name} 写「{n} 条夹具」，实得 {real} 条——脚本改了就把数一起改；"
                           f"若这一处是在**引用一个旧数字**，把它写成汉字（八条夹具）"
                           if rel == FIXTURE_KEY else
                           f"{name} 写 {rel} 有 {n} 条用例，实得 {real} 条"
                           f"——测试改了就把数一起改")
    if not total:
        bad.append("两份文档里都没解析到「N 条夹具」或「N 条用例」——检查器自己坏了，先修它")
    return bad


def lookup(evidence: dict, key: str):
    """在证据文件里取一个读数。先查 `flat`（打平的点号键），再按点号逐级走。

    两级都要有：`flat` 里的键本身就是 `span.hybrid` 这种带点的整体，
    而 `cases`／`k` 这类只存在于 `raw` 里。取不到返回 `None`
    —— **「没找到」与「值为 0」必须分得开**（`sweep.windows_with_zero=0` 就是后者）。
    """
    flat = evidence.get("flat") or {}
    if key in flat:
        return flat[key]
    node = evidence.get("raw") or {}
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, (int, float)) and not isinstance(node, bool) else None


def adr_issues(name: str, text: str, evidence: dict) -> list[str]:
    """一条 ADR 的三处判定：编号标题、六个字段、读数引用。"""
    bad: list[str] = []
    if not ADR_H1_RE.search(text):
        bad.append(f"{name}：H1 里没有 `# ADR-0000 标题` 形式的编号与标题")
    for field, rx in FIELD_RES:
        if not rx.search(text):
            bad.append(f"{name}：缺「{field}」字段（六个字段一个都不能省）")
    cites = CITE_RE.findall(text)
    if not cites:
        bad.append(f"{name}：一个 `键=值` 读数引用都没有——那条「当时手上的数」是回忆，不是读数")
    for key, val in cites:
        got = lookup(evidence, key)
        if got is None:
            bad.append(f"{name}：读数引用 `{key}` 在 {EVIDENCE.name} 里找不到")
        elif abs(float(got) - float(val)) > 1e-9:
            bad.append(f"{name}：`{key}={val}` 与实跑读数 {got} 不等")
    return bad


def read_docs() -> tuple[dict[str, str], list[str]]:
    """要核对的文档：架构文档 ＋ 决策目录下的每一份。**缺谁都要报，不静默少核。**"""
    bad: list[str] = []
    docs: dict[str, str] = {}
    if ARCH.exists():
        docs["docs/architecture.md"] = ARCH.read_text(encoding="utf-8")
    else:
        bad.append("缺少 docs/architecture.md——架构图是这一章的交付物，不能缺")
    if DECISIONS.exists():
        for p in sorted(DECISIONS.glob("*.md")):
            docs[f"docs/decisions/{p.name}"] = p.read_text(encoding="utf-8")
    else:
        bad.append("缺少 docs/decisions/——决策记录是这一章的交付物，不能缺")
    return docs, bad


def run_check() -> int:
    docs, bad = read_docs()
    if not EVIDENCE.exists():
        print(f"  ✖ 缺少 {EVIDENCE.relative_to(ROOT).as_posix()}——"
              f"先跑 `python experiments/eval_run.py --offline --write-baseline`")
        return 1
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    # ①② 模块双向点名
    modules = app_modules()
    mod_bad = module_issues(docs, exists=lambda rel: (ROOT / rel).exists(), modules=modules)
    named = set()
    for text in docs.values():
        named |= pointed_paths(text)
    print(f"  模块：文档点名 {len(named)} 个路径（其中 app 模块 "
          f"{len([r for r in named if r.startswith('app/')])} 个）｜ 树里 {len(modules)} 个")
    bad += mod_bad

    # ③ ADR：字段、编号、读数引用
    adr_docs = {k: v for k, v in docs.items() if k.startswith("docs/decisions/")}
    if not adr_docs:
        bad.append("docs/decisions/ 下一份 ADR 都没解析到——检查器自己坏了，先修它")
    ids = [m.group(1) for m in (ADR_H1_RE.search(t) for t in adr_docs.values()) if m]
    for i in sorted({x for x in ids if ids.count(x) > 1}):
        bad.append(f"ADR 编号 {i} 出现了 {ids.count(i)} 次")
    cites = 0
    for name in sorted(adr_docs):
        text = adr_docs[name]
        cites += len(CITE_RE.findall(text))
        bad += adr_issues(name, text, evidence)
    print(f"  ADR：{len(adr_docs)} 条（编号 {min(ids, default='—')}–{max(ids, default='—')}）"
          f"｜ 读数引用 {cites} 条，逐条与 {EVIDENCE.name} 比")

    # ④ 行数标注
    counted = [(name, rel, n) for name in sorted(docs)
               for rel, n in counted_lines(docs[name])]
    bad += line_count_issues(docs, exists=lambda rel: (ROOT / rel).exists(),
                            count_lines=lambda rel: real_lines(ROOT, rel))
    print(f"  行数：{len(counted)} 处「N 行」标注（{len({r for _, r, _ in counted})} 份文件），"
          f"逐处与盘上的行数比")

    # ⑤ 自描述条数：夹具数与测试文件的用例数
    claims = [(name, rel, n) for name in sorted(docs) for rel, n in case_counts(docs[name])]
    n_fix = len(fixture_cases())
    ran = lambda rel: ran_cases(ROOT, rel)                                  # noqa: E731
    static = lambda rel: static_cases(ROOT, rel)                            # noqa: E731
    bad += self_description_issues(docs, fixtures=n_fix,
                                   count_cases=lambda rel: real_cases(ROOT, rel, ran=ran),
                                   count_cases_static=static)
    print(f"  自描述：{len(claims)} 处条数标注（其中夹具 {n_fix} 条是本脚本实有），"
          f"逐处与实得比")

    if bad:
        for m in bad:
            print(f"  ✖ {m}")
        print(f"\n文档对账不通过：{len(bad)} 处")
        return 1
    print(f"文档对账：五条全过 ｜ {MARKER}")
    return 0


# ---------------------------------------------------------------------------
# 夹具：每一处判定都要有一个「该响」与一个「该沉默」的分支（STYLE 8.5）
_ADR_OK = """# ADR-0001 示例决定

- **状态**：已决定
- **背景（当时手上的那个数）**：片级 `span.hybrid=0.8333`，题数 `cases=24`
- **决定**：照旧
- **被否掉的选项及否掉的理由**：换掉它——代价大于收益
- **失效线（什么条件下该推翻它）**：语料规模翻十倍时重评
"""


def fixture_cases() -> list[tuple[str, bool]]:
    """夹具清单。**单独成函数**是为了让第五条对账能数它的条数——文档里写的
    「N 条夹具」必须与这里返回的条数相等；否则那个数只能靠人记得改，
    而「改脚本的人」与「改文档的人」往往不是同一个脑子里的同一件事。"""
    cases: list[tuple[str, bool]] = []          # (说明, 是否应当沉默)
    # ①② 模块双向点名
    exists_all = lambda _rel: True              # noqa: E731
    cases.append(("双向点名齐全：沉默",
                  not module_issues({"docs/architecture.md":
                                     "见 `app/ingest.py` 与 `scripts/recap.py`"},
                                    exists=exists_all,
                                    modules=["app/ingest.py"])))
    cases.append(("文档点名了树里没有的模块：要拦",
                  bool(module_issues({"docs/architecture.md": "见 `app/gone.py`"},
                                     exists=lambda rel: rel != "app/gone.py",
                                     modules=["app/gone.py"]))))
    cases.append(("树里有模块没被点名：要拦（删一个模块名就红）",
                  bool(module_issues({"docs/architecture.md": "见 `app/ingest.py`"},
                                     exists=exists_all,
                                     modules=["app/ingest.py", "app/corpus.py"]))))
    cases.append(("一份文档都没解析到模块：要拦（反向守）",
                  bool(module_issues({"docs/architecture.md": "只有散文"},
                                     exists=exists_all, modules=["app/ingest.py"]))))
    # ③ ADR
    ev = {"flat": {"span.hybrid": 0.8333}, "raw": {"cases": 24}}
    cases.append(("ADR 字段齐、读数对得上：沉默", not adr_issues("a.md", _ADR_OK, ev)))
    cases.append(("少了「失效线」字段：要拦",
                  bool(adr_issues("a.md", _ADR_OK.replace("- **失效线", "- **备注"), ev))))
    cases.append(("读数与证据不等（0.8334 ≠ 0.8333）：要拦",
                  bool(adr_issues("a.md", _ADR_OK.replace("=0.8333", "=0.8334"), ev))))
    cases.append(("引用的键在证据里不存在（拼错名）：要拦",
                  bool(adr_issues("a.md", _ADR_OK.replace("span.hybrid", "span.hybird"), ev))))
    cases.append(("一个读数引用都没有（背景是回忆）：要拦",
                  bool(adr_issues("a.md", _ADR_OK.replace("`span.hybrid=0.8333`", "0.8333")
                                  .replace("`cases=24`", "24"), ev))))
    cases.append(("`windows_with_zero=0` 不能被当成「取不到」",
                  lookup(ev, "span.hybrid") == 0.8333 and lookup(ev, "nope") is None))
    # ④ 行数标注
    files = {"scripts/recap.py": 260, "tests/test_recap.py": 128}
    exists_py = lambda rel: rel in files                    # noqa: E731
    count_py = lambda rel: files.get(rel)                   # noqa: E731
    cases.append(("行数标注与盘上相等：沉默",
                  not line_count_issues({"d.md": "| `scripts/recap.py` | 260 行 | 对账 |"},
                                        exists=exists_py, count_lines=count_py)))
    cases.append(("改一行就红（标 259、盘上 260）",
                  bool(line_count_issues({"d.md": "| `scripts/recap.py` | 259 行 | 对账 |"},
                                         exists=exists_py, count_lines=count_py))))
    cases.append(("一处标注都没解析到：要拦（反向守）",
                  bool(line_count_issues({"d.md": "这份文档一个行数都没写"},
                                         exists=exists_py, count_lines=count_py))))
    cases.append(("同一份文件标了两个不同的行数：要拦",
                  bool(line_count_issues(
                      {"d.md": "`scripts/recap.py` 260 行\n`scripts/recap.py` 259 行"},
                      exists=exists_py, count_lines=count_py))))
    cases.append(("标的文件在树里没有：要拦",
                  bool(line_count_issues({"d.md": "| `scripts/gone.py` | 12 行 | 对账 |"},
                                         exists=exists_py, count_lines=count_py))))
    cases.append(("路径与数字不在同一行：不算标注，沉默（错配假红比不报更坏）",
                  not line_count_issues(
                      {"d.md": "| `tests/test_recap.py` | 128 行 | 用例 |\n"
                               "`scripts/recap.py`\n这一轮改了 12 行"},
                      exists=exists_py, count_lines=count_py)))
    # ⑤ 自描述条数
    real_tests = {"tests/test_recap.py": 5}
    cases.append(("「N 条夹具」写对了：沉默",
                  not self_description_issues(
                      {"d.md": "python scripts/recap.py --self-test  # 3 条夹具"},
                      fixtures=3, count_cases=lambda rel: real_tests.get(rel))))
    cases.append(("**夹具少写一条就红**（写 2、实有 3）",
                  bool(self_description_issues(
                      {"d.md": "python scripts/recap.py --self-test  # 2 条夹具"},
                      fixtures=3, count_cases=lambda rel: real_tests.get(rel)))))
    cases.append(("「N 条用例」写对了：沉默（那个文件真有 5 条）",
                  not self_description_issues(
                      {"d.md": "| `tests/test_recap.py` | 154 行 | 5 条用例 |"},
                      fixtures=3, count_cases=lambda rel: real_tests.get(rel))))
    cases.append(("**用例少写一条就红**（写 4、实有 5）",
                  bool(self_description_issues(
                      {"d.md": "| `tests/test_recap.py` | 154 行 | 4 条用例 |"},
                      fixtures=3, count_cases=lambda rel: real_tests.get(rel)))))
    cases.append(("一处条数标注都没有：要拦（反向守）",
                  bool(self_description_issues({"d.md": "两份文档都只有散文"},
                                               fixtures=3,
                                               count_cases=lambda rel: real_tests.get(rel)))))
    cases.append(("「N 条用例」前面没有测试文件路径：不算标注（正文里到处是「5 条用例」）",
                  not case_counts("这一章一共 5 条用例，分四类，每类都给有代价的答法")))
    # 用例数：两把尺子（跑起来几个 / 数文件几个）
    cases.append(("用例数取跑出来的值（跑 5、数文件 4）",
                  real_cases(ROOT, "tests/test_recap.py", ran=lambda rel: 5) == 5))
    cases.append(("导入不进来：退回数文件（盘上真有这个文件）",
                  real_cases(ROOT, "tests/test_recap.py", ran=lambda rel: None)
                  == static_cases(ROOT, "tests/test_recap.py")))
    cases.append(("两把尺子量出的不一样（跑 5、数文件 4）：要报",
                  any("两把尺子" in m for m in self_description_issues(
                      {"d.md": "| `tests/test_recap.py` | 5 条用例 |"},
                      fixtures=3, count_cases=lambda rel: 5,
                      count_cases_static=lambda rel: 4))))
    cases.append(("两把尺子一致（都 5）：沉默",
                  not self_description_issues(
                      {"d.md": "| `tests/test_recap.py` | 5 条用例 |"},
                      fixtures=3, count_cases=lambda rel: 5,
                      count_cases_static=lambda rel: 5)))
    cases.append(("两把尺子都拿不到（文件不在）：要报「没法核」，不是叛它过",
                  bool(self_description_issues(
                      {"d.md": "| `tests/gone.py` | 5 条用例 |"},
                      fixtures=3, count_cases=lambda rel: None,
                      count_cases_static=lambda rel: None))))
    cases.append(("引用旧数字时写汉字（八条夹具）：不算断言——否则检查会咬着历史叙述",
                  not case_counts("接上这条的当天抓到一处写少的「八条夹具（实际已有 10 条）」")))
    return cases


def self_test() -> int:
    cases = fixture_cases()
    ok = bad = 0
    for name, passed in cases:
        if passed:
            ok += 1
        else:
            bad += 1
            print(f"  ✖ {name}")
    print(f"自检 {ok}/{len(cases)} 通过")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="5.9 的文档对账（离线的五条）")
    ap.add_argument("--check", action="store_true", help="文档 ↔ 树 的对账")
    ap.add_argument("--offline", action="store_true", help="同 --check（提交门的入口名）")
    ap.add_argument("--self-test", action="store_true", help="夹具")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.check or args.offline:
        return run_check()
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
