#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""书侧手写数字的对账（style_claims.py）

**为什么单开一个模块**：`STYLE.md` 与 `README.md` 里散着一批「实跑值的复述」——
「`index_book.py` 的 `--self-test` 14 条夹具」这种句子。这些数的**作者是工具**、
**抄写员是文档**，而抄写发生在两个**不归任何工具管**的文件里：
写错了不会让任何数字变难看，`lint_book` 也不看它们（它只扫 LEDGER 与 `book/`）。
于是「夹具条数」这一类数没有对账方——本书已经吃过同一族错（`totals.py`
那一行写着 25 条，而实跑是 26 条，中间隔着一次加夹具）。

模块只做一件事：**让每支工具在 `--check` 里核一次「文档里写的是不是它的真实条数」**。
所以它没有自己的入口，谁也不该单独跑它——那样「谁没调」就没人知道；
调用点在各工具的 `main()` 里（`lint_book` / `totals` / `index_book` 三支，
也就是文档目前真的引用了条数的那三支）。

**只认一种句式**：`<tool>.py` 与「N 条夹具」出现在**同一小句**里。
两处都是刻意的：
① 「同一小句」是因为「没写工具名的那句多半在讲某一批子集」（`STYLE` 8.4 里
   「16 条夹具里会红 8 条」讲的是引用复核那一批，不是 `lint_book` 的总数），
   要求工具名入句，才不会有假阳性；
② 只认阿拉伯数字，沿用 5.9 那一轮定下的**「阿拉伯数字是断言，引用旧数字写成汉字」**
   ——所以「自检从四十八条长到 64 条」里，四十八条是引文而不是断言。

**它同时钉住一个反向盲区**：文档里若**一次都没**提到某支工具的条数，
本模块保持沉默（没写就不管）。这个边界是有意的，而且写在这里，
免得下一次有人把「没报错」读成「覆盖到了」。
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: 会复述实跑值的两份文档。`LEDGER.md` 不在此列——它已经被三道门按格扫着，
#: 而且它的每一格都是**建章当天的历史值**（51／52／53…），不是当前值。
DOC_FILES = ("STYLE.md", "README.md")

#: 小句的分隔符：只切句末与分号（逗号与顿号不切——一句话里的两个数属于同一句）。
_SEP_RE = re.compile("[。；;！？]")

#: 句式：`**26 条夹具**`。`[\s*_]{0,4}` 是给加粗留的（与 `lint_book` 那三句同一处理）。
_CLAIM = re.compile(r"([\d,]+)[\s*_]{0,4}条夹具")


#: 已接线的工具：它们在自检末尾调 `report()`（名单跟作实跑值一起变）。
#: 文档里引用了「N 条夹具」而名字不在这里的工具，由 `unwired_tools()` 报出来。
WIRED: tuple[str, ...] = ("lint_book", "index_book", "totals", "check_runnable", "appendix",
                         "learning_path", "crosscheck")


def clauses(line: str) -> list[str]:
    """把一行切成小句（供「同一小句里必须有工具名」这条判据用）。"""
    return [c for c in _SEP_RE.split(line) if c]


def blocks(text: str) -> list[tuple[int, str]]:
    """把文档切成段落，返回 [(首行号, 段落文本)]。

    以段落为单位（不是行）：一句话会在中间换行（写文档时的手工折行），
    而行级扫描会把「工具名在这一行、那个数在下一行」的句子整个漏掉——
    这正是刚接上本模块时它自己的一声哨：`lint_book` 那两句的引用数只数到一处，
    而文档里写着两处。
    """
    out: list[tuple[int, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        start = i
        buf: list[str] = []
        while i < len(lines) and lines[i].strip():
            buf.append(lines[i])
            i += 1
        out.append((start + 1, "\n".join(buf)))
    return out


def fixture_claims(text: str, tool: str) -> list[tuple[int, int]]:
    """文档里把「N 条夹具」记在这份工具名下的那些小句，返回 [(行号, 断言值)]。

    `tool` 传脚本名（不带 `.py`）：判定要求 `<tool>.py` 与该数同在一小句里。
    """
    name = f"{tool}.py"
    out: list[tuple[int, int]] = []
    for start, block in blocks(text):
        if name not in block:
            continue
        for cl in _SEP_RE.split(block):
            if name not in cl:
                continue
            for mo in _CLAIM.finditer(cl):
                out.append((start + cl[:mo.start()].count("\n"),
                            int(mo.group(1).replace(",", ""))))
    return out


def fixture_claim_issues(text: str, tool: str, total: int,
                         where: str = "文档") -> tuple[list[str], int]:
    """返回（问题列表, 比过的断言个数）。`total` 是这份工具**本次**自检的条数。

    比过的个数要报出来：这类键只在「写了」时才有断言，而
    「覆盖从 3 处掉到 0 处」与「全对」在输出上必须能分开。
    """
    claims = fixture_claims(text, tool)
    issues = [
        f"{where} 第 {ln} 行：`{tool}.py` 的夹具条数写的是 {n} 条，实跑 {total} 条"
        f"——阿拉伯数字是断言：把数改对，或把引用旧值写成汉字（口径见 `STYLE` 8.11）"
        for ln, n in claims if n != total
    ]
    return issues, len(claims)


def doc_claims(tool: str, total: int) -> tuple[list[str], int]:
    """把两份文档一起过一遍（各工具 `main()` 里调这一支）。"""
    issues: list[str] = []
    checked = 0
    for name in DOC_FILES:
        path = ROOT / name
        if not path.exists():
            continue
        got, n = fixture_claim_issues(path.read_text(encoding="utf-8"), tool, total, name)
        issues += got
        checked += n
    return issues, checked


def report(tool: str, total: int) -> int:
    """各工具自检末尾调它：返回应当并入退出码的 0/1；比过几处也要报出来。"""
    issues, checked = doc_claims(tool, total)
    for msg in issues:
        print(f"  ✖ [书侧引用] {msg}")
    if checked:
        print(f"  · 书侧写了「{tool}.py … N 条夹具」{checked} 处，"
              + ("有问题 " + str(len(issues)) + " 条" if issues else "逐处相符"))
    return 1 if issues else 0


# ---------------------------------------------------------------- 库存声明
# 第三类手抄的数：**按盘上清点的那几句**（目录体积、文件数、PDF 数、唯一链接数）。
# 它们与「夹具条数」同族——作者是盘，抄写员是 `README`／`PLAN`——但以前**一处都没接**：
# 加一份素材、给 `REFERENCES.md` 添一条链接，那几个数一个字都不会变难看。
# 本轮就是靠这份清单发现 `README` 里 `sources/` 的体积停在 **6.1MB**（盘上 5.5MB）。
#
# 两条口径写在这里，免得下次又各说各话：
#   ① **体积**＝文件字节数之和 ÷ 2²⁰，保留一位小数（`du -sh` 按块对齐统计，两种数
#      不必相等——所以判据是 **±10% 的带**，而不是逐字相等）；
#   ② **计数**逐字比（个、份、条都算整数），且**必须带路径上下文**：
#      光看「999 个文件」不知道它指哪儿，拄下来只会是假阳性。
#   汉字写的数不是断言（沿用 5.9 那一轮的约定），所以正则只认阿拉伯数字。
_VOLUME_BAND = 0.10

#: 扫哪几份文档。`PLAN` 比夹具那一家族多进来一步：它的汇总表归 `audit_coverage`，
#: 但「raw/ 295MB」「sources/ 216 个文件」这几句它照样手抄。
INVENTORY_DOCS: tuple[str, ...] = ("STYLE.md", "README.md", "PLAN.md")

#: (键, 句式, 这个数是什么)。句式必须自带路径上下文。
_CLAIMS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("sources_files", re.compile(r"sources/[^\n]{0,80}?([\d,]+)\s*个文件"),
     "`sources/` 下的文件数"),
    ("sources_mb", re.compile(r"sources/[^\n]{0,80}?([\d.]+)\s*MB"),
     "`sources/` 的体积"),
    ("raw_big_pdf_mb", re.compile(r"含\s*([\d.]+)\s*MB\s*单文件"),
     "`raw/` 里最大的单文件体积"),
    ("raw_mb", re.compile(r"raw/[^\n]{0,80}?([\d.]+)\s*MB"),
     "`raw/` 的体积"),
    ("raw_pdfs", re.compile(r"([\d,]+)\s*个原始 PDF"),
     "`raw/pdf/` 下的原件数"),
    ("ref_links", re.compile(r"([\d,]+)\s*个唯一链接"),
     "`REFERENCES.md` 里的唯一链接数"),
)


def _tree_size(path: pathlib.Path) -> tuple[int, int]:
    """（文件数, 字节数之和）。目录不存在时返回 (0, 0)——由调用方自己判断要不要出声。"""
    if not path.exists():
        return 0, 0
    files = [p for p in path.rglob("*") if p.is_file()]
    return len(files), sum(p.stat().st_size for p in files)


def inventory_facts() -> dict[str, float]:
    """盘上现读的那几份库存。某一项读不到就不放进字典（那一句因此静默）。"""
    out: dict[str, float] = {}
    n, size = _tree_size(ROOT / "sources")
    if n:
        out["sources_files"] = float(n)
        out["sources_mb"] = size / 2**20
    n, size = _tree_size(ROOT / "raw")
    if n:
        out["raw_mb"] = size / 2**20
        biggest = max((p for p in (ROOT / "raw").rglob("*") if p.is_file()),
                      key=lambda p: p.stat().st_size, default=None)
        if biggest is not None:
            out["raw_big_pdf_mb"] = biggest.stat().st_size / 2**20
    pdfs = ROOT / "raw" / "pdf"
    if pdfs.exists():
        out["raw_pdfs"] = float(len([p for p in pdfs.glob("*") if p.is_file()]))
    refs = ROOT / "REFERENCES.md"
    if refs.exists():
        text = refs.read_text(encoding="utf-8")
        urls = {u.rstrip("/").rstrip(".,;:)") for u in re.findall(r"https?://[^\s|)\]，。]+", text)}
        out["ref_links"] = float(len(urls))
    return out


#: 一条边界写在这里：这是六句里**只取“路径后最近的那个数”**的句式，而不是
#: 「同一小句里最后一个」。原因是这一族的句子没有「从 A 变成 B」那种固定形状——
#: `raw/（295MB，含 125MB 单文件 PDF）` 里两个数都属于同一个路径，
#: 取“最后一个”会把「最大单文件」当成目录体积（假阳性）。
#: 所以想在正文里引用旧值，沿用 5.9 那一轮的约定：**写成汉字**。


def inventory_issues(text: str, where: str = "文档",
                     facts: dict[str, float] | None = None) -> tuple[list[str], int]:
    """文档里那几句库存声明与盘上现读的比。返回（问题列表, 比过的断言个数）。"""
    f = inventory_facts() if facts is None else facts
    issues: list[str] = []
    checked = 0
    for key, pattern, what in _CLAIMS:
        fact = f.get(key)
        if fact is None:
            continue
        for mo in pattern.finditer(text):
            value = mo.group(1).replace(",", "")
            try:
                claimed = float(value)
            except ValueError:                      # 夹具里喂了非数字——当作没写
                continue
            checked += 1
            if key.endswith("_mb"):
                if abs(claimed - fact) > _VOLUME_BAND * fact:
                    issues.append(f"{where}：{what}写的是 {claimed:g}MB，盘上是 {fact:.1f}MB"
                                  f"（体积按字节数之和、判据 ±{_VOLUME_BAND:.0%}，"
                                  f"因为 `du` 按块对齐统计）")
            elif int(claimed) != int(fact):
                issues.append(f"{where}：{what}写的是 {int(claimed)}，盘上是 {int(fact)}")
    return issues, checked


def inventory_doc_issues() -> tuple[list[str], int]:
    """把该扫的几份文档一起过一遍（由 `lint_book.py` 调）。"""
    issues: list[str] = []
    checked = 0
    for name in INVENTORY_DOCS:
        path = ROOT / name
        if not path.exists():
            continue
        got, n = inventory_issues(path.read_text(encoding="utf-8"), name)
        issues += got
        checked += n
    return issues, checked


def unwired_tools() -> list[str]:
    """文档里被引用了夹具条数、却没有接线的 `tools/*.py`（升序）。

    这一道回查的是**名单**：一句新写的「`xxx.py` 的 14 条夹具」若没有对应的
    `report()` 调用，它就静默地落在所有门的射程外——而输出看起来一切正常。
    （与 `audit_coverage` 的夹具名字清单同一条思路：不只是「少了几条」，
    而是「少的是哪一条」。树内脚本（`zhizhou-v*/scripts/*.py`）不在此列，
    它们由 `check_runnable` 的条数格与 `recap.py` 自己的第五条守着。）
    """
    found: set[str] = set()
    for name in DOC_FILES:
        path = ROOT / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for cand in sorted((ROOT / "tools").glob("*.py")):
            tool = cand.stem
            if tool == "style_claims":
                continue
            if fixture_claims(text, tool):
                found.add(tool)
    return sorted(found - set(WIRED))
