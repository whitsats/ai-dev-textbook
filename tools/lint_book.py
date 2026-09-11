#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正文一致性校验（lint_book.py）

长篇教材最容易出的问题不是写错，而是「悄悄漂移」：体例缺小节、术语换了写法、
交叉引用指向不存在的章、链接没登记、素材溯源失效、同一段内容在多章重复。
本脚本把这些都变成可执行的检查，写完一章就跑一次。

用法
----
    python tools/lint_book.py                 # 校验全部章节
    python tools/lint_book.py --only 1.1      # 只校验指定章
    python tools/lint_book.py --quiet         # 只打印问题

检查项
------
    [体例]  十段式小节是否齐全（第 0 篇豁免「前置知识」）
    [命名]  文件名章号与正文 H1 章号是否一致
    [术语]  GLOSSARY.md 中「避免的写法」是否出现在正文
    [引用]  「见第 X.Y 节」与「X.Y–X.Z」范围是否指向 PLAN.md 中存在的章
    [链接]  正文所有 URL 必须能追溯到 REFERENCES.md（防臆造链接）
    [出处]  「延伸阅读」中官方文档链接是否 ≥ 2 条
    [溯源]  sources/... 路径是否真实存在
    [篇幅]  有效字数（汉字 + 代码行折算）与 PLAN.md 计划字数的偏差（容忍 ±40%）
    [重复]  跨章重复的长句（防止内容被复制粘贴到多处）
    [标点]  中文后紧跟半角标点的抽查
    [台账]  LEDGER.md 中待写（⬜）与有意省略（⏭）的数量提示

退出码：存在「错误」时为 1，只有「警告」时为 0。
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOK = ROOT / "book"
PLAN = ROOT / "PLAN.md"
REFS = ROOT / "REFERENCES.md"
GLOSSARY = ROOT / "GLOSSARY.md"
LEDGER = ROOT / "LEDGER.md"

# 所有章节都必须有的小节；「前置知识」仅第 1 篇及以后要求
REQUIRED_ALWAYS = ["本章导读", "## 学习目标", "## 本章小结", "## 延伸阅读"]
REQUIRED_NON_INTRO = ["## 前置知识", "## 常见坑", "## 面试视角", "## 练习"]

BANNED_WORDS = ["众所周知", "显而易见", "不难发现", "笔者", "同学们", "我们大家", "见上文", "据说"]

MIN_OFFICIAL_LINKS = 2
WORD_TOLERANCE = 0.40
# 一行有效代码（有内容、不含空行与围栏）约等于 15 个汉字的信息量。
# 技术章节的代码本身就是内容，只数汉字会把「代码密集 + 讲得清楚」的章误判为偷工减料；
# 也不能简单放宽容差，那会把真问题一起放过。折算成同一口径再比，才既不冤枉也不放水。
CODE_LINE_EQUIV = 15
DUP_MIN_HAN = 30  # 跨章重复检测的最小句长（汉字数）


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"[错误] {where}：{msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"[警告] {where}：{msg}")


def han_len(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def load_plan_chapters() -> dict[str, int]:
    """从 PLAN.md 解析 {章号: 计划字数}。"""
    plan: dict[str, int] = {}
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        m = re.fullmatch(r"(\d+\.\d+)", cells[0])
        if not m:
            continue
        words = None
        for cell in cells[1:6]:
            if re.fullmatch(r"[\d,]{3,}", cell):
                words = int(cell.replace(",", ""))
                break
        if words:
            plan[m.group(1)] = words
    return plan


def load_plan_parts() -> set[int]:
    """从 PLAN.md 解析已启用的篇号。"""
    text = PLAN.read_text(encoding="utf-8")
    parts = {int(n) for n in re.findall(r"###\s*第\s*(\d+)\s*篇", text)}
    parts |= {int(n) for n in re.findall(r"第\s*(\d+)\s*篇", text)}
    return parts


def load_glossary() -> list[tuple[str, str]]:
    """返回 [(首选写法, 避免的写法), ...]。

    只解析 GLOSSARY.md 中 LINT:TERMS:BEGIN/END 标记之间的表格，
    避免把说明性表格（如维护记录的表头「原因」）当成术语。
    """
    rows: list[tuple[str, str]] = []
    if not GLOSSARY.exists():
        return rows
    text = GLOSSARY.read_text(encoding="utf-8")
    m = re.search(r"LINT:TERMS:BEGIN(.*?)LINT:TERMS:END", text, re.S)
    if not m:
        return rows
    for line in m.group(1).splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        preferred, avoid = cells[0], cells[2]
        if preferred in ("首选写法", ""):
            continue
        for bad in re.split(r"[、,，]", avoid):
            bad = bad.strip()
            # 避免列表里若写的是首选写法的子串（如「观测性」之于「可观测性」），不作为独立禁词
            if bad and bad != "—" and bad not in preferred:
                rows.append((preferred, bad))
    return rows


def load_refs_urls() -> set[str]:
    text = REFS.read_text(encoding="utf-8")
    urls = re.findall(r"https?://[^\s|)\]\uff0c\u3002]+", text)
    return {u.rstrip("/") for u in urls}


def chapter_files(only: str | None) -> list[pathlib.Path]:
    files = sorted(BOOK.glob("*/*.md"))
    files = [f for f in files if f.name.lower() != "readme.md"]
    if only:
        files = [f for f in files if f.name.startswith(f"{only}-")]
    return files


def check_chapter(path: pathlib.Path, ctx: dict) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    rep: Report = ctx["report"]
    where = path.name
    m = re.match(r"(\d+\.\d+)-(.*)\.md$", path.name)
    if not m:
        rep.err(where, "文件名不符合「<章号>-<标题>.md」规范")
        return "", text
    cid = m.group(1)
    part = int(cid.split(".")[0])

    # [命名] H1 与文件名一致
    h1 = re.search(r"^#\s+(.+)$", text, re.M)
    if not h1:
        rep.err(where, "缺少一级标题")
    elif not h1.group(1).startswith(cid):
        rep.err(where, f"H1「{h1.group(1)[:20]}」与文件名章号 {cid} 不一致")

    # [体例] 固定小节
    missing = [s for s in REQUIRED_ALWAYS if s not in text]
    if part != 0:
        missing += [s for s in REQUIRED_NON_INTRO if s not in text]
    if missing:
        rep.err(where, f"缺少小节：{'、'.join(missing)}")

    # [术语] 避免的写法（排除作为首选写法子串出现的情况）
    for preferred, bad in ctx["glossary"]:
        hits = text.count(bad)
        if bad in preferred:
            hits -= text.count(preferred)
        if hits > 0:
            rep.err(where, f"术语违规：应写「{preferred}」，正文出现「{bad}」{hits} 次")

    # [禁用词]
    for w in BANNED_WORDS:
        if w in text:
            rep.err(where, f"出现规范禁用词「{w}」")

    # [引用] 交叉引用必须存在于 PLAN
    plan_ch = ctx["plan_chapters"]
    for ref in re.findall(r"第\s*(\d+\.\d+(?:\.\d+)?)\s*节", text):
        chap = ".".join(ref.split(".")[:2])
        if chap not in plan_ch:
            rep.err(where, f"交叉引用「第 {ref} 节」指向不存在的章 {chap}")
    for a, b in re.findall(r"(\d+\.\d+)\s*[\u2013\u2014-]\s*(\d+\.\d+)", text):
        for x in (a, b):
            if x not in plan_ch:
                rep.err(where, f"范围引用中的 {x} 在 PLAN.md 中不存在")
    for a, b in re.findall(r"第\s*(\d+)\s*[\u2013\u2014-]\s*(\d+)\s*篇", text):
        for x in (a, b):
            if int(x) not in ctx["plan_parts"]:
                rep.err(where, f"篇引用「第 {x} 篇」在 PLAN.md 中未启用")

    # [链接] 必须登记在 REFERENCES.md
    urls = re.findall(r"https?://[^\s|)\]\uff0c\u3002]+", text)
    refs = ctx["refs"]
    for u in urls:
        # 本地地址（开发服务器）不是“出处”，无需登记
        if re.search(r"(127\.0\.0\.1|localhost|0\.0\.0\.0)", u):
            continue
        if u.rstrip("/") not in refs:
            rep.err(where, f"链接未登记于 REFERENCES.md：{u}")

    # [出处] 延伸阅读内官方文档数量
    if "## 延伸阅读" in text:
        tail = text.split("## 延伸阅读", 1)[1]
        official = len(re.findall(r"https?://", tail))
        if official < MIN_OFFICIAL_LINKS:
            rep.err(where, f"「延伸阅读」官方文档链接仅 {official} 条，少于 {MIN_OFFICIAL_LINKS} 条")

    # [溯源] sources/ 路径存在性
    for src in re.findall(r"`(sources/[^`]+)`", text):
        if not (ROOT / src).exists():
            rep.err(where, f"素材溯源路径不存在：{src}")

    # [篇幅] 与 PLAN 计划偏差：统一换算成「有效字数」再比（口径见 CODE_LINE_EQUIV）。
    planned = plan_ch.get(cid)
    actual = han_len(text)
    code_lines = [ln for ln in re.findall(r"```.*?```", text, re.S)
                  for ln in ln.splitlines() if ln.strip()]
    effective = actual + CODE_LINE_EQUIV * len(code_lines)
    if planned:
        ratio = effective / planned
        if abs(1 - ratio) > WORD_TOLERANCE:
            rep.warn(where, f"有效字数 {effective}（汉字 {actual} + 代码 {len(code_lines)} 行），"
                            f"计划 {planned}（偏差 {ratio - 1:+.0%}，容差 ±{WORD_TOLERANCE:.0%}）")

    # [标点] 中文后紧跟半角标点（代码块与行内代码不适用该规范，先剔除）
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    prose = re.sub(r"`[^`]*`", "", prose)
    odd = re.findall(r"[\u4e00-\u9fff][,;:?!](?![0-9])", prose)
    if odd:
        rep.warn(where, f"中文后使用了半角标点 {len(odd)} 处，例如「{odd[0]}」")

    return cid, text


def check_duplicates(chapters: dict[str, str], rep: Report) -> None:
    """跨章重复的长句检测。"""
    sentences: dict[str, list[str]] = defaultdict(list)
    for cid, text in chapters.items():
        for raw in re.split(r"[\n\u3002\uff01\uff1f]", text):
            s = re.sub(r"[`*\[\]()>#\s]", "", raw)
            if han_len(s) >= DUP_MIN_HAN:
                sentences[s].append(cid)
    for s, cids in sentences.items():
        uniq = sorted(set(cids))
        if len(uniq) > 1:
            rep.warn("跨章重复", f"{'/'.join(uniq)} 出现相同长句（{han_len(s)} 字）：{s[:40]}…")


def check_blank_lines(rep: Report) -> None:
    """标题前必须有空行。

    这条是为脚本改动服务的：用脚本批量回填台账/表格时，很容易把新标题直接粘在
    上一行末尾（TEXT 拼接丢掉尾随空行），Markdown 渲染会当成普通文字而不成标题。
    肉眼很难发现，机械校验一抓就有。
    """
    heading = re.compile(r"^#{1,6}\s")
    targets = [LEDGER, PLAN, REFS, GLOSSARY]
    targets += list(BOOK.rglob("*.md"))
    for f in targets:
        if not f.exists():
            continue
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        in_fence = False
        for i, ln in enumerate(lines):
            if ln.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            # 代码块里的 # 是注释（如 # 输出），不是标题，不参与检查
            if in_fence or not heading.match(ln):
                continue
            if i > 0 and lines[i - 1].strip():
                rep.err(f.name, f"第 {i + 1} 行标题「{ln[:24]}」前缺少空行")


def check_ledger(rep: Report) -> None:
    if not LEDGER.exists():
        rep.warn("台账", "未找到 LEDGER.md")
        return
    # 只统计「知识点行」。
    # 注意不能简单地「首格以反引号开头就当成图例行」——很多知识点本身就以代码写法开头
    # （如 `*args` / `**kwargs`、「`global` 的使用」），那样会被误删、导致台账少算
    # 而“看上去存量变少了”。图例行只有一种：首格恰好是一个状态符号。
    legend = re.compile(r"^`(?:✅|🔀|⏭|⬜)`$")
    part = None
    per_part: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])  # ✅ 🔀 ⏭ ⬜
    for ln in LEDGER.read_text(encoding="utf-8").splitlines():
        if ln.startswith("## ") and "篇级进度" in ln:
            part = None  # 汇总表自身不参与统计，否则会把合计数字重复计入最后一篇
        m = re.match(r"##\s*[一-鿿]*、第\s*(\d+)\s*篇", ln)
        if m:
            part = f"第 {m.group(1)} 篇"
        if part is None or not ln.startswith("|") or "---" in ln:
            continue
        if legend.match(ln.strip("|").strip().split("|")[0].strip()):
            continue
        if ln.strip("|").strip().split("|")[0].strip() == "篇":
            continue
        for i, sym in enumerate(("✅", "🔀", "⏭", "⬜")):
            per_part[part][i] += ln.count(sym)
    done, merge, skip, todo = (sum(v[i] for v in per_part.values()) for i in range(4))
    print(f"台账 LEDGER.md：已落点 {done} 条 ｜ 合并 {merge} 条 ｜ 有意省略 {skip} 条 ｜ 待写 {todo} 条")
    for p, (d, mg, sk, td) in per_part.items():
        print(f"  {p}：✅{d} ｜🔀{mg} ｜⏭{sk} ｜⬜{td}")
    if todo:
        rep.warn("台账", f"仍有 {todo} 条知识点处于「待写」，篇收尾前必须清零或改标 ⏭")
    # 防止「台账覆盖不到的篇」：只要求**已经写出正文的篇**建表，
    # 空目录（预留但尚未开写）不报。否则报警器一旦吵，就没人看了。
    for pl in sorted({int(d.name[:2]) for d in BOOK.iterdir()
                      if d.is_dir() and d.name[:2].isdigit()
                      and any(d.glob("*.md"))}):
        key = f"第 {pl} 篇"
        if key not in per_part:
            rep.warn("台账", f"已有正文的{key}在 LEDGER.md 中没有对应的小节台账")


def main() -> int:
    ap = argparse.ArgumentParser(description="正文一致性校验")
    ap.add_argument("--only", help="只校验指定章，例如 1.1")
    ap.add_argument("--quiet", action="store_true", help="只打印问题")
    args = ap.parse_args()

    files = chapter_files(args.only)
    if not files:
        print("没有找到待校验的章节文件。")
        return 0

    rep = Report()
    ctx = {
        "report": rep,
        "plan_chapters": load_plan_chapters(),
        "plan_parts": load_plan_parts(),
        "glossary": load_glossary(),
        "refs": load_refs_urls(),
    }

    chapters: dict[str, str] = {}
    for f in files:
        cid, text = check_chapter(f, ctx)
        if cid:
            chapters[cid] = text
        if not args.quiet:
            n = len(re.findall(r"[\u4e00-\u9fff]", text))
            # 同时报出代码行占比：PLAN.md 的「✅ N 字」一律取这里的汉字数，
            # 代码占比用来解释“为什么汉字比计划少并不等于偷工减料”。
            code = [ln for ln in re.findall(r"```.*?```", text, re.S)
                    for ln in ln.splitlines() if ln.strip()]
            effective = n + CODE_LINE_EQUIV * len(code)
            planned = ctx["plan_chapters"].get(cid)
            tail = f" / 计划 {planned}（达成 {effective / planned:.0%}）" if planned else ""
            print(f"  {f.name}  有效字数 {effective}（汉字 {n} + 代码 {len(code)} 行）{tail}")

    check_duplicates(chapters, rep)
    check_blank_lines(rep)

    print()
    print(f"校验章节 {len(files)} 章 ｜ 引用库 {len(ctx['refs'])} 条链接 ｜ 术语 {len(ctx['glossary'])} 条禁止写法")
    check_ledger(rep)

    if rep.errors:
        print()
        for e in rep.errors:
            print(e)
    if rep.warnings:
        print()
        for w in rep.warnings:
            print(w)

    print()
    print(f"汇总：错误 {len(rep.errors)} ｜ 警告 {len(rep.warnings)}")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
