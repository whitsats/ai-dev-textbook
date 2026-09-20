#!/usr/bin/env python
"""全书汇总数字的**单一来源**：生成、对账、自检。

    python tools/totals.py --check      # 汇总数字是否都等于算出来的（提交门用）
    python tools/totals.py --sync       # 按算出来的值把它们写回去（写文档的那一步）
    python tools/totals.py --self-test  # 夹具：每一类站点「改一行就红」＋ sync 幂等
    python tools/totals.py --sites      # 打印站点清单与匹配数（看「检查覆盖到哪」）

为什么要有这个工具
------------------
这本书的汇总数字（已完稿章数、各篇实测字数、台账四符号计数、看板的「已完成」、
COVERAGE 全表）此前是**手抄**的：每交一章，要记得去改 LEDGER 篇级进度、PLAN 看板与
文首、README 进度句、COVERAGE——**四处以上，且它们互相之间没有先后关系**。
「同一件事写了两个副本」的代价在这里很具体：一次「一章一笔」的提交只带走了正文，
汇总就停在上一章，于是**那一笔自己跑不过门**——而它看上去完全正常（正文没错、
章级数字也没错，只有篇级/全书级的汇总没跟上）。

所以这里把关系倒过来：**汇总不由人写，由算出来的值写**。算它只要三样，
且三样都已经是单一实现：

  ① 篇章规划（篇号 / 章号 / 标题 / 计划汉字 / 素材规格）→ `audit_coverage.py` 的 `PLAN`；
  ② 正文实测有效字数 → `lint_book.py`（字数口径的唯一实现）；
  ③ 台账四个符号的逐篇计数 → `lint_book.ledger_symbol_counts()`。

派生的东西（每篇已完成章数、每篇实测字数、合计、素材比值、看板状态、批次小计、
需原创补写的章数）都在本文件里算一次，然后写进**每一个出现它的地方**。

站点是什么
----------
站点 = （文件，区间，正则，若干「组名 → 新值」）。`--check` 拿正则捕获的那一格与算出来的
值比；`--sync` **只替换那一格**——术语、叙述、注释、括号里的章号范围一个字都不动，
台账那列几千字的「反向核对」也一个字都不动。

两条必须写明的边界（都写成了夹具）：
  · **零比值的写法自由**：素材比值为 0 的格子里写 `—`、`0.00` 还是 `题库驱动` 都算数
    （三种本书都在用），加粗与否也不算漂；但**非零就必须是算出来的那个数**，
    而该有数字的篇写成 `—` 会报错——「两边都没写」的盲区靠这条堵。
  · **正则认不出的写法不会报错**：换了句式、拆成两句，站点就静默落空。所以每一类站点
    都自检「至少匹配到一次」，该有行的篇必须都有行（`parts_all` / `require_parts`），
    篇级小计句还必须覆盖所有已完稿的篇。这是 `STYLE` 8.5 那条「不出声的检查与没有检查
    在阅读上一样」在本工具里的落点。

它与 `audit_coverage.py --check` 的分工
--------------------------------------
`audit_coverage.py` 是**独立的第二双眼**：它也在比同一批数字（自己那套正则），
外加规划值、章表、逐节表、PROJECT 字数、STYLE 实测引用这些不在本工具射程里的东西。
两边都绿才说明「写对了」；两边读法不一致时会红——那正是要人看一眼的时候。
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_coverage as ac          # noqa: E402  规划值与素材口径的唯一实现
import lint_book as lb               # noqa: E402  字数口径与台账计数的唯一实现

PLAN_MD = "PLAN.md"
README_MD = "README.md"
LEDGER_MD = "LEDGER.md"
COVERAGE_MD = "COVERAGE.md"
DOCS = (PLAN_MD, README_MD, LEDGER_MD, COVERAGE_MD)

# 区间：定位到某张表/某一段，免得同名行（各表格里都是「| 数字 | … |」）串台。
LEDGER_PARTS = ("## 八、篇级进度", None)      # 到下一个一级标题
PLAN_BOARD = ("## 八、进度看板", "前置工作进度")
PLAN_COVER = ("**发现一：", "> 散文比值")
PLAN_BATCH = ("| 批次 | 范围 | 章数 | 字数 |", "每章执行节奏")
README_STRUCT = ("## 全书结构", None)


# ----------------------------------------------------------------- 事实（算一次）

class Facts:
    """全书汇总数字的唯一来源：三样输入，其余全在这里派生。"""

    def __init__(self) -> None:
        self.rows = ac.build_rows()                    # 逐章：计划 / 素材 / 比值
        self.agg = ac.part_aggregates()                # 逐篇：n / plan / prose / bank / ratio
        self.words = ac._chapter_effective_words()     # 逐章实测有效字数（走 lint_book）
        self.parts = sorted(self.agg)
        self.n = {p: int(self.agg[p]["n"]) for p in self.parts}
        self.plan = {p: int(self.agg[p]["plan"]) for p in self.parts}
        self.ratio = {p: self.agg[p]["ratio"] for p in self.parts}
        self.prose = {p: int(self.agg[p]["prose"]) for p in self.parts}
        self.bank = {p: int(self.agg[p]["bank"]) for p in self.parts}

        # 已完成 = 正文文件存在（口径同 lint_book：文件在就是写了，不采信叙述）
        self.done = {p: 0 for p in self.parts}
        self.part_words = {p: 0 for p in self.parts}
        for cid, w in self.words.items():
            head = cid.split(".")[0]
            if head.isdigit() and int(head) in self.done:
                self.done[int(head)] += 1
                self.part_words[int(head)] += w
        self.done_total = sum(self.done.values())
        self.chapters_total = sum(self.n.values())
        self.plan_total = sum(self.plan.values())
        self.words_total = sum(self.part_words.values())
        self.done_parts = [p for p in self.parts if self.done[p]]

        plan_text = _read(ROOT / PLAN_MD)
        ledger_text = _read(ROOT / LEDGER_MD)
        self.sym = lb.ledger_symbol_counts(ledger_text)   # 「第 N 篇」→ [✅ 🔀 ⏭ ⬜]
        self.batch = batch_of_part(plan_text)

        # 需原创补写的章（口径同 audit_coverage：判定偏薄及以下，或题库驱动且零散文）
        rows_all = [r for r in self.rows if r["plan"]]
        weak = [r for r in rows_all if ac.needs_original(r)]
        self.weak = len(weak)
        self.weak_total = len(rows_all)
        self.weak_zero = sum(1 for r in weak if r["prose"] == 0)

    def syms(self, p: int) -> list[int]:
        return self.sym.get(f"第 {p} 篇", [0, 0, 0, 0])

    def state_of(self, p: int) -> str:
        """看板「状态」那一格：由已完成章数与批次表算出来，不再手写。"""
        d, n = self.done[p], self.n[p]
        mark = "✅ 已完成" if (d and d == n) else ("🟡 进行中" if d else "⬜ 未开始")
        b = self.batch.get(p)
        return f"{mark}（{b}）" if b else mark

    def state_overall(self) -> str:
        """合计格：正在写的那一篇属于哪个批次；都写完了就是「全部完成」。"""
        for p in self.parts:
            if 0 < self.done[p] < self.n[p]:
                return f"🟡 {self.batch.get(p, '进行中')}进行中"
        if self.done_total == 0:
            return "⬜ 未开始"
        if self.done_total == self.chapters_total:
            return "✅ 全部完成"
        left = [p for p in self.parts if not self.done[p]]
        return f"⬜ {self.batch.get(left[0], '待开工')}待开工"


def _read(path: Path) -> str:
    """整篇读入，**不做换行翻译**：PLAN.md 与 LEDGER.md 在盘上是 CRLF，
    若按默认的 universal newlines 读再写，会把它们整篇改成 LF——一个大 diff，
    而且把「改数字」与「改换行」混成一件事，评审时分不清。
    """
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def batch_of_part(plan_text: str) -> dict[int, str]:
    """从 PLAN 的批次表读出「篇 → 批次」映射（批次表那几张数字另有站点在守）。"""
    out: dict[int, str] = {}
    for m in re.finditer(r"(?m)^\| \*\*(批次[一二三四五六七八九十]+)\*\* \| (?P<range>[^|\n]*) \|",
                         plan_text):
        for p in re.findall(r"第\s*(\d+)\s*篇", m.group("range")):
            out[int(p)] = m.group(1)
    return out


# ----------------------------------------------------------------- 站点（写在哪）

@dataclass
class Site:
    path: str
    label: str
    pattern: re.Pattern
    values: dict[str, Callable[[Facts, re.Match], str]]
    within: tuple[str, str | None] | None = None
    zero_ok: tuple[str, ...] = ("—", "题库驱动", "全部原创")
    require_parts: Callable[[Facts], Iterable[str]] | None = None
    # 所有**已完稿**的篇都必须有行（还没开工的篇根本不上表，所以不要求）
    parts_all: bool = False
    # 能不能拿去当篡改夹具的靶子：章号范围是「范围文」而不是一个数，
    # 它自有另一条形状的夹具（比区间），不参与「把数字 +1」那一轮。
    bumpable: bool = True


@dataclass
class Hit:
    site: Site
    match: object        # 区间内匹配 + 绝对下标（见 _Shifted）


class _Shifted:
    """区间内的匹配 → 绝对坐标视图（只实现本文件用到的那几个接口）。"""

    def __init__(self, m: re.Match, base: int) -> None:
        self._m, self._base = m, base

    def group(self, name):                       # type: ignore[no-untyped-def]
        return self._m.group(name)

    def groupdict(self):                         # type: ignore[no-untyped-def]
        return self._m.groupdict()

    def start(self, name=None):                  # type: ignore[no-untyped-def]
        return self._m.start(name) + self._base

    def end(self, name=None):                    # type: ignore[no-untyped-def]
        return self._m.end(name) + self._base


def _sec(text: str, within: tuple[str, str | None] | None) -> tuple[int, int]:
    """定位区间；标记缺失时返回 (-1, -1)（站点随后会报「一处都没匹配到」）。"""
    if within is None:
        return (0, len(text))
    start, end = within
    i = text.find(start)
    if i < 0:
        return (-1, -1)
    if end is None:
        m = re.compile(r"(?m)^## ").search(text, i + len(start))
        return (i, m.start() if m else len(text))
    j = text.find(end, i + len(start))
    return (i, j if j >= 0 else len(text))


def sites() -> list[Site]:
    S: list[Site] = []

    # ---- ① 台账「篇级进度」：章数 / ✅ / 🔀 / ⏭ / ⬜ ------------------------------
    # 章数一格统一写成「已完成 / 总章数」（原先四章写总数、四章写分数，两种都在）。
    # ✅ 那一格里的括号（「173（7.1–7.5）」）是**另一条站点**在守：它把「这些落点来自哪几章」
    # 写成了文，新章一交就该跟着动，所以由已存在的章号算出来。
    S.append(Site(
        LEDGER_MD, "LEDGER 篇级进度",
        re.compile(r"(?m)^\| 第 (?P<p>\d+) 篇 \| (?P<n>[^|]*?) \| (?P<ok>\d+)(?P<tail>[^|]*?) \| "
                   r"(?P<merge>[^|]*?) \| (?P<skip>[^|]*?) \| (?P<todo>[^|]*?) \|"),
        {
            "n": lambda f, m: f"{f.done[int(m.group('p'))]} / {f.n[int(m.group('p'))]}",
            "ok": lambda f, m: str(f.syms(int(m.group("p")))[0]),
            "merge": lambda f, m: str(f.syms(int(m.group("p")))[1]),
            "skip": lambda f, m: str(f.syms(int(m.group("p")))[2]),
            "todo": lambda f, m: str(f.syms(int(m.group("p")))[3]),
        },
        within=LEDGER_PARTS, parts_all=True))
    S.append(Site(
        LEDGER_MD, "LEDGER 篇级进度 ✅ 的章号范围",
        re.compile(r"(?m)^\| 第 (?P<p>\d+) 篇 \| [^|]* \| \d+（(?P<rng>[^）]*)）"),
        {"rng": lambda f, m: chapter_span(f, int(m.group("p")))},
        within=LEDGER_PARTS, bumpable=False))

    # ---- ② PLAN 文首 ---------------------------------------------------------
    S.append(Site(
        PLAN_MD, "PLAN 文首「全书进度」",
        re.compile(r"全书进度 \*\*(?P<done>\d+) / (?P<n>[\d,]+) 章\*\*，实测 (?P<w>[\d,]+) 字"),
        {"done": lambda f, m: str(f.done_total),
         "n": lambda f, m: f"{f.chapters_total:,}",
         "w": lambda f, m: f"{f.words_total:,}"}))
    S.append(Site(
        PLAN_MD, "PLAN 文首「全书为 N 篇 N 章 / 约 N 字」",
        re.compile(r"全书为 \*\*(?P<parts>\d+) 篇 (?P<n>[\d,]+) 章 / 约 (?P<w>[\d,]+) 字\*\*"),
        {"parts": lambda f, m: str(len(f.parts)),    # 第 9 篇是预留，不算进规划篇数
         "n": lambda f, m: f"{f.chapters_total:,}",
         "w": lambda f, m: f"{f.plan_total:,}"}))
    S.append(Site(
        PLAN_MD, "PLAN 篇级小计句（全篇多处）",
        re.compile(r"第\s*(?P<lo>\d+)(?:\s*[–\-—~]\s*(?P<hi>\d+))?\s*篇正文\*\*已完成\*\*"
                   r"（(?P<c>\d+)\s*章，实测\s*(?P<w>[\d,]+)\s*字(?=[），])"),
        {"c": lambda f, m: str(sum(f.done[p] for p in _bracket(m))),
         "w": lambda f, m: f"{sum(f.part_words[p] for p in _bracket(m)):,}"}))
    S.append(Site(
        PLAN_MD, "PLAN「计划总字数」那一格",
        re.compile(r"计划总字数 \| \*\*约 (?P<w>[\d,]+) 字\*\*"),
        {"w": lambda f, m: f"{f.plan_total:,}"}))
    S.append(Site(
        PLAN_MD, "PLAN「现行计划总量为 N 字」",
        re.compile(r"现行计划总量为\s*\*{0,2}(?P<w>[\d,]+)\*{0,2}\s*字"),
        {"w": lambda f, m: f"{f.plan_total:,}"}))
    S.append(Site(
        PLAN_MD, "PLAN「需原创补写的章」",
        re.compile(r"需原创补写的章 \| \*\*(?P<weak>\d+)\s*/\s*(?P<total>\d+)\s*章\*\*"
                   r"[^|\n]*?其中\s*(?P<zero>\d+)\s*章散文素材为零"),
        {"weak": lambda f, m: str(f.weak),
         "total": lambda f, m: str(f.weak_total),
         "zero": lambda f, m: str(f.weak_zero)}))

    # ---- ③ PLAN 篇级覆盖度表（素材与计划值：改规划值时它得跟着动） --------------
    S.append(Site(
        PLAN_MD, "PLAN 篇级覆盖度表",
        re.compile(r"(?m)^\| (?P<p>\d+) [^|\n]* \| (?P<n>[\d,]+) \| (?P<plan>[\d,]+) \| "
                   r"(?P<prose>[\d,]+) \| (?P<bank>[\d,]+) \| (?P<ratio>[^|]*?) \|"),
        {"n": lambda f, m: str(f.n[int(m.group("p"))]),
         "plan": lambda f, m: f"{f.plan[int(m.group('p'))]:,}",
         "prose": lambda f, m: f"{f.prose[int(m.group('p'))]:,}",
         "bank": lambda f, m: f"{f.bank[int(m.group('p'))]:,}",
         "ratio": lambda f, m: f"{f.ratio[int(m.group('p'))]:.2f}"},
        within=PLAN_COVER, parts_all=True))
    S.append(Site(
        PLAN_MD, "PLAN 篇级覆盖度表合计",
        re.compile(r"(?m)^\| \*\*合计\*\* \| \*\*(?P<n>[\d,]+)\*\* \| \*\*(?P<plan>[\d,]+)\*\*"),
        {"n": lambda f, m: f"{f.chapters_total:,}",
         "plan": lambda f, m: f"{f.plan_total:,}"},
        within=PLAN_COVER))
    S.append(Site(
        PLAN_MD, "PLAN 分篇标题（章数 / 字数）",
        re.compile(r"(?m)^### 第 (?P<p>\d+) 篇[^（\n]*（(?P<c>[\d,]+) 章 / (?P<w>[\d,]+) 字"),
        {"c": lambda f, m: f"{f.n[int(m.group('p'))]:,}",
         "w": lambda f, m: f"{f.plan[int(m.group('p'))]:,}"},
        parts_all=True))
    S.append(Site(
        PLAN_MD, "PLAN 分篇标题里的「素材 X.XX」",
        re.compile(r"(?m)^### 第 (?P<p>\d+) 篇[^（\n]*（[\d,]+ 章 / [\d,]+ 字，素材 (?P<ratio>\d+\.\d+)"),
        {"ratio": lambda f, m: f"{f.ratio[int(m.group('p'))]:.2f}"},
        # 有素材的篇必须写着那个数——写成「全部原创」会静默（同族的盲区）
        require_parts=lambda f: [str(p) for p in f.parts if f.ratio[p] > 0]))

    # ---- ④ PLAN 批次表 -------------------------------------------------------
    S.append(Site(
        PLAN_MD, "PLAN 批次表",
        re.compile(r"(?m)^\| \*\*(?P<name>批次[一二三四五六七八九十]+)\*\* \| (?P<range>[^|\n]*) "
                   r"\| (?P<c>[\d,]+) \| (?P<w>[\d,]+) \|"),
        {"c": lambda f, m: f"{sum(f.n[int(p)] for p in _batch_parts(m)):,}",
         "w": lambda f, m: f"{sum(f.plan[int(p)] for p in _batch_parts(m)):,}"},
        within=PLAN_BATCH))
    S.append(Site(
        PLAN_MD, "PLAN 批次表合计",
        re.compile(r"(?m)^\| \*\*合计\*\* \| \| \*\*(?P<c>[\d,]+)\*\* \| \*\*(?P<w>[\d,]+)\*\* \|"),
        {"c": lambda f, m: f"{f.chapters_total:,}",
         "w": lambda f, m: f"{f.plan_total:,}"},
        within=PLAN_BATCH))

    # ---- ⑤ PLAN 进度看板 -----------------------------------------------------
    S.append(Site(
        PLAN_MD, "PLAN 看板",
        re.compile(r"(?m)^\| (?P<p>\d+) [^|\n]* \| (?P<n>[\d,]+) \| (?P<plan>[\d,]+) \| "
                   r"(?P<ratio>[^|]*?) \| (?P<done>[\d,]+) \| (?P<state>[^|]*?) \|\s*$"),
        {"n": lambda f, m: str(f.n[int(m.group("p"))]),
         "plan": lambda f, m: f"{f.plan[int(m.group('p'))]:,}",
         "ratio": lambda f, m: f"{f.ratio[int(m.group('p'))]:.2f}",
         "done": lambda f, m: str(f.done[int(m.group("p"))]),
         "state": lambda f, m: f.state_of(int(m.group("p")))},
        within=PLAN_BOARD, parts_all=True))
    S.append(Site(
        PLAN_MD, "PLAN 看板合计",
        re.compile(r"(?m)^\| \*\*合计\*\* \| \*\*(?P<n>[\d,]+)\*\* \| \*\*(?P<plan>[\d,]+)\*\* \| "
                   r"\| \*\*(?P<done>[\d,]+)\*\* \| (?P<state>[^|]*?) \|\s*$"),
        {"n": lambda f, m: f"{f.chapters_total:,}",
         "plan": lambda f, m: f"{f.plan_total:,}",
         "done": lambda f, m: str(f.done_total),
         "state": lambda f, m: f.state_overall()},
        within=PLAN_BOARD))

    # ---- ⑥ README ------------------------------------------------------------
    S.append(Site(
        README_MD, "README 进度句",
        re.compile(r"（共\s*(?P<c>\d+)\s*章，实测\s*(?P<w>[\d,]+)\s*字）"),
        {"c": lambda f, m: str(f.done_total),
         "w": lambda f, m: f"{f.words_total:,}"}))
    S.append(Site(
        README_MD, "README「约 N 字」的规划总量",
        re.compile(r"约\s*(?P<w>[\d,]+)\s*字"),
        {"w": lambda f, m: f"{f.plan_total:,}"}))
    S.append(Site(
        README_MD, "README 全书结构的章数",
        re.compile(r"(?m)^\| (?P<p>\d+) \| (?P<name>[^|\n]*) \| [^|]* \| (?P<n>[\d,()]+) \|"),
        {"n": lambda f, m: str(f.n[int(m.group("p"))])},
        within=README_STRUCT, require_parts=lambda f: [str(p) for p in f.parts]))
    S.append(Site(
        README_MD, "README 全书结构的素材充裕度",
        re.compile(r"(?m)^\| (?P<p>\d+) \| [^|\n]* \| [^|]* \| [\d,()]+ \| (?P<ratio>\d+\.\d+)"),
        {"ratio": lambda f, m: f"{f.ratio[int(m.group('p'))]:.2f}"},
        within=README_STRUCT,
        require_parts=lambda f: [str(p) for p in f.parts if f.ratio[p] > 0]))

    return S


def chapter_span(f: Facts, p: int) -> str:
    """某一篇已完稿的章号范围：「1.1–1.15」；不连号时逐个列（不假装中间那些写完了）。"""
    ids = sorted((cid for cid in f.words if cid.split(".")[0].isdigit()
                  and int(cid.split(".")[0]) == p),
                 key=lambda c: tuple(int(x) for x in c.split(".")))
    if not ids:
        return ""
    seq = [tuple(int(x) for x in c.split(".")) for c in ids]
    if all(seq[i + 1][1] == seq[i][1] + 1 for i in range(len(seq) - 1)):
        return f"{ids[0]}–{ids[-1]}" if len(ids) > 1 else ids[0]
    return "、".join(ids)


def _bracket(m) -> list[int]:                     # type: ignore[no-untyped-def]
    lo = int(m.group("lo"))
    return list(range(lo, int(m.group("hi") or lo) + 1))


def _batch_parts(m) -> list[int]:                 # type: ignore[no-untyped-def]
    return [int(p) for p in re.findall(r"第\s*(\d+)\s*篇", m.group("range"))]


# ----------------------------------------------------------------- 匹配与比对

def _norm(s: str) -> str:
    """比对前归一：去掉首尾空白、去掉 markdown 加粗、去掉千分位。"""
    return s.strip().strip("*").strip().replace(",", "")


def _same(got: str, want: str, zero_ok: tuple[str, ...]) -> bool:
    if _norm(got) == _norm(want):
        return True
    return want == "0.00" and _norm(got) in {_norm(x) for x in zero_ok}


def find_hits(facts: Facts, texts: dict[str, str]) -> tuple[dict[str, list[Hit]], list[str]]:
    """匹配所有站点。返回（文件 → 命中, 结构性问题）。

    结构性问题 = 「这一处该有，却读不出来」：文件不在、正则一处没匹配到、
    某篇缺行、篇级小计句漏了已完稿的篇。它们与数字漂移分开，因为**修法不同**：
    漂移可以一键写回，缺行缺句得先把行/句建出来（工具不猜叙述）。
    """
    hits: dict[str, list[Hit]] = {name: [] for name in texts}
    problems: list[str] = []
    brackets: list[list[int]] = []
    for s in sites():
        text = texts.get(s.path)
        if text is None:
            problems.append(f"找不到 {s.path}，无法核对「{s.label}」")
            continue
        a, b = _sec(text, s.within)
        found = list(s.pattern.finditer(text[a:b])) if a >= 0 else []
        known = [m for m in found
                 if "p" not in m.groupdict() or int(m.group("p")) in facts.parts]
        for m in known:
            hits[s.path].append(Hit(s, _Shifted(m, a) if a else m))
        if s.label == "PLAN 篇级小计句（全篇多处）":
            brackets = [_bracket(m) for m in known]
        if not known:
            problems.append(f"{s.path}：「{s.label}」一处都没匹配到"
                            "（句式变了、或字段被改名了——这处检查已经不在看任何东西）")
            continue
        if s.parts_all:
            got = {int(m.group("p")) for m in known if "p" in m.groupdict()}
            miss = [p for p in facts.done_parts if p not in got]
            if miss:
                problems.append(f"{s.path}：「{s.label}」缺这些篇的行——"
                                + "、".join(f"第 {p} 篇" for p in miss))
        if s.require_parts:
            want = {str(x) for x in s.require_parts(facts)}
            got = {m.group("p") for m in known if "p" in m.groupdict()}
            miss = sorted(want - got, key=int)
            if miss:
                problems.append(f"{s.path}：「{s.label}」漏了这些篇——" + "、".join(miss))
    # 篇级小计句必须覆盖**每一个已完稿的篇**（漏一篇 = 文首的进度句在骗人）
    covered = {p for br in brackets for p in br}
    miss = [p for p in facts.done_parts if p not in covered]
    if brackets and miss:
        problems.append("PLAN 文首：篇级小计句漏了已完稿的篇——"
                        + "、".join(f"第 {p} 篇" for p in miss))
    return hits, problems


def drift_of(facts: Facts, texts: dict[str, str]) -> tuple[list[str], list[tuple]]:
    """逐格比对：返回（人读的漂移说明, 可执行的改动列表）。"""
    hits, _ = find_hits(facts, texts)
    drifts: list[str] = []
    edits: list[tuple[str, int, int, str]] = []
    for path, hs in hits.items():
        for h in hs:
            for name, fn in h.site.values.items():
                got = h.match.group(name)
                want = fn(facts, h.match)
                if _same(got, want, h.site.zero_ok):
                    continue
                drifts.append(f"{path}：「{h.site.label}」的 {name} 写 {got} ≠ 应为 {want}")
                edits.append((path, h.match.start(name), h.match.end(name), want))
    cover = texts.get(COVERAGE_MD)
    if cover is not None and cover != ac.report_text():
        drifts.append(f"{COVERAGE_MD}：与生成物不一致（它是自动生成的，跑 --sync 重写整份）")
    return drifts, edits


def apply_edits(texts: dict[str, str], edits: list[tuple]) -> dict[str, str]:
    """按改动列表重建文本（同文件内从后往前替换，避免下标漂移）。"""
    out = dict(texts)
    per_file: dict[str, list[tuple]] = {}
    for e in edits:
        per_file.setdefault(e[0], []).append(e)
    for path, es in per_file.items():
        text = out[path]
        for _p, a, b, want in sorted(es, key=lambda x: -x[1]):
            text = text[:a] + want + text[b:]
        out[path] = text
    if COVERAGE_MD in out and out[COVERAGE_MD] != ac.report_text():
        out[COVERAGE_MD] = ac.report_text()      # 整份重生成（不是逐格改）
    return out


def check_texts(facts: Facts, texts: dict[str, str]) -> tuple[list[str], list[str]]:
    _hits, structural = find_hits(facts, texts)
    drifts, _ = drift_of(facts, texts)
    return structural, drifts


# ----------------------------------------------------------------- 写回

def sync_texts(facts: Facts, texts: dict[str, str], *, write: bool) -> int:
    structural, drifts = check_texts(facts, texts)
    if structural:
        print("站点结构不全——先把行/句补出来，再让 --sync 填数（它不猜叙述）：")
        for s in structural:
            print(f"  ✖ {s}")
        return 1
    if not drifts:
        print("汇总数字已与实测一致：无需改动（--sync 是幂等的）")
        return 0
    _d, edits = drift_of(facts, texts)
    counts: dict[str, int] = {}
    for e in edits:
        counts[e[0]] = counts.get(e[0], 0) + 1
    new = apply_edits(texts, edits)
    if new.get(COVERAGE_MD) != texts.get(COVERAGE_MD):
        counts[COVERAGE_MD] = 0      # COVERAGE 是整份重生成，不按「几处」计
    for path, n in sorted(counts.items()):
        print(f"  · {path} " + ("（整份重写）" if path == COVERAGE_MD else f"（{n} 处）"))
    if write:
        for path in counts:
            with open(ROOT / path, "w", encoding="utf-8", newline="") as fh:
                fh.write(new[path])
        print("已写入。")
    again = check_texts(facts, new)
    if again[0] or again[1]:
        print("✖ --sync 之后仍有不一致（工具自身的问题，先别提交）：")
        for line in again[0] + again[1]:
            print(f"  ✖ {line}")
        return 1
    return 0


# ----------------------------------------------------------------- 自检

def self_test() -> int:
    """夹具：**每一类站点**都改一格、看它红不红，再确认能一键修回。"""
    facts = Facts()
    texts = load_texts()
    ok = total = 0

    def case(name: str, good: bool) -> None:
        nonlocal ok, total
        total += 1
        ok += good
        print(("  ✔ " if good else "  ✖ ") + name)

    # ① 未改动的原文必须沉默（工具自己不能虚报）
    st, dr = check_texts(facts, texts)
    case("未改动的原文应保持沉默", not st and not dr)

    # ② 每一类站点都得匹配到东西（正则写窄了 = 检查变成摆设）
    hits, _st = find_hits(facts, texts)
    per: dict[str, int] = {}
    for hs in hits.values():
        for h in hs:
            per[h.site.label] = per.get(h.site.label, 0) + 1
    empty = [s.label for s in sites() if not per.get(s.label)]
    case(f"每一类站点都匹配到了（{len(per)} 类，最少 {min(per.values())} 次）", not empty)
    for label in empty:
        print(f"      · 一处没匹配到：{label}")

    # ③ 每一类**带数字**的站点都抓得住漂移：改一格 → 必须报出，且能一键修回
    bumpable = [s for s in sites() if s.bumpable]
    checked = 0
    for s in bumpable:
        text = texts[s.path]
        a, b = _sec(text, s.within)
        m = s.pattern.search(text[a:b]) if a >= 0 else None
        if not m or ("p" in m.groupdict() and int(m.group("p")) not in facts.parts):
            continue
        picked = None
        for name in s.values:
            want = s.values[name](facts, m)
            if want == "0.00":
                picked = (name, "9.99")
            elif re.fullmatch(r"\d+\.\d+", want):
                picked = (name, f"{float(want) + 0.01:.2f}")   # 比值：挪一分也必须是错
            elif re.fullmatch(r"[\d,]+", want):
                picked = (name, f"{int(want.replace(',', '')) + 1:,}")
            if picked:
                break
        if not picked:
            continue
        name, bump = picked
        mutated = dict(texts)
        mutated[s.path] = text[:a + m.start(name)] + bump + text[a + m.end(name):]
        _st, dr = check_texts(facts, mutated)
        hit_label = [x for x in dr if (f"「{s.label}」" in x or s.label == COVERAGE_MD)]
        fixed = apply_edits(mutated, drift_of(facts, mutated)[1])
        _st2, dr2 = check_texts(facts, fixed)
        good = len(hit_label) == 1 and not dr2
        case(f"「{s.label}」的 {name} 改错一位会被当场报出，且能一键修回", good)
        checked += 1
    case(f"每一类带数字的站点都有篡改夹具（{checked} 条）", checked == len(bumpable))

    # ③b COVERAGE 是整份生成物：改一个字必须报出，而 --sync 必须**整份**改回来
    #     （这一条是补上的，因为 8.2 改计划值时抓到了本工具自身的一个真 bug：
    #      apply_edits 里那行「要不要重生成 COVERAGE」的比较曾经写成「和盘上原文比」——
    #      两者永远相等，于是 COVERAGE 这一路永远不重生成，而输出里只写着「已写入」）
    mut = dict(texts)
    mut[COVERAGE_MD] = texts[COVERAGE_MD].replace("素材覆盖度审计报告", "素材覆盖报告", 1)
    _st, dr = check_texts(facts, mut)
    back = apply_edits(mut, drift_of(facts, mut)[1])
    case("COVERAGE.md 被手改一个字会被报出，且 --sync 整份改回",
         any("生成物" in x for x in dr) and back[COVERAGE_MD] == ac.report_text())

    # ④ sync 幂等：算两遍与算一遍一样
    once = apply_edits(texts, drift_of(facts, texts)[1])
    twice = apply_edits(once, drift_of(facts, once)[1])
    case("--sync 幂等（再跑一次不再改动）", once == twice)

    # ⑤ 零比值的写法自由；非零不许被占位符盖住
    hit = next((h for h in hits[PLAN_MD]
                if h.site.label == "PLAN 篇级覆盖度表"
                and facts.ratio[int(h.match.group("p"))] > 0), None)
    if hit:
        t = texts[PLAN_MD]
        mut = dict(texts)
        mut[PLAN_MD] = (t[:hit.match.start("ratio")] + "—" + t[hit.match.end("ratio"):])
        _st, dr = check_texts(facts, mut)
        case("非零的素材比值写成「—」会被报出（占位符盖不住真数）",
             any("篇级覆盖度表" in x for x in dr))
    else:
        case("非零的素材比值写成「—」会被报出（占位符盖不住真数）", False)

    # ⑥ 缺一行必须报「结构性缺失」，而不是静静地少对一行
    board = next(h for h in hits[PLAN_MD] if h.site.label == "PLAN 看板")
    t = texts[PLAN_MD]
    mut = dict(texts)
    mut[PLAN_MD] = re.sub(r"(?m)^\| " + board.match.group("p") + r" [^\n]*\n", "", t, count=1)
    st, _dr = check_texts(facts, mut)
    case("看板里删掉一整行会报「缺这些篇的行」", any("缺这些篇的行" in x for x in st))

    print(f"自检：{ok}/{total} 通过")
    return 0 if ok == total else 1


# ----------------------------------------------------------------- 入口

def load_texts() -> dict[str, str]:
    return {name: _read(ROOT / name) for name in DOCS}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="汇总数字是否都等于算出来的")
    ap.add_argument("--sync", action="store_true", help="把算出来的值写回文档（交章前跑的就是它）")
    ap.add_argument("--self-test", action="store_true", help="只跑夹具")
    ap.add_argument("--sites", action="store_true", help="打印站点清单与匹配数")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    facts = Facts()
    texts = load_texts()

    if args.sites:
        hits, structural = find_hits(facts, texts)
        per: dict[str, int] = {}
        for hs in hits.values():
            for h in hs:
                per[h.site.label] = per.get(h.site.label, 0) + 1
        print(f"站点 {len(sites())} 类；逐篇表格的匹配数应等于规划篇数（{len(facts.parts)}）")
        print(f"COVERAGE.md 由 --sync 整份重写（逐字节比对）")
        for s in sites():
            n = per.get(s.label, 0)
            print(f"  · {s.path:<11} {s.label:<34} 匹配 {n:>2} 次"
                  f"{'   ← 一处都没有！' if not n else ''}")
        return 1 if structural else 0

    if args.sync:
        return sync_texts(facts, texts, write=True)

    structural, drifts = check_texts(facts, texts)
    for line in structural + drifts:
        print(f"  ✖ {line}")
    if structural or drifts:
        print(f"\n汇总数字与实测不一致（结构 {len(structural)} 处 ｜ 漂移 {len(drifts)} 处）。")
        print("修法：python tools/totals.py --sync —— 它按单一来源写回，不手抄。")
        return 1
    n_hits = sum(len(v) for v in find_hits(facts, texts)[0].values())
    print(f"汇总数字对账通过：{facts.done_total} / {facts.chapters_total} 章、"
          f"{facts.words_total:,} 字，台账四符号、看板状态、批次小计与 COVERAGE 全部等于算出来的值"
          f"（{len(sites())} 类站点、{n_hits} 处）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
