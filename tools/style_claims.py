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
WIRED: tuple[str, ...] = ("lint_book", "index_book", "totals", "check_runnable", "appendix")


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
