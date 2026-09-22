#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通读修订的候选生成器（跨篇的一致性、口径与重复）。

    python tools/revisit.py --check       # 三张普查表 ＋ 与 REVISIT.md 里记的那一份逐处比
    python tools/revisit.py --shapes      # 只看体例形状普查
    python tools/revisit.py --dupes       # 只看跨篇重复段（候选，需人判）
    python tools/revisit.py --facts       # 只看「同一短语 ＋ 数字」的候选
    python tools/revisit.py --self-test   # 夹具（全合成输入）

为什么需要它
------------
单章审阅看的是「这一章对不对」，逐篇收尾看的是「这一篇落点/引用/术语齐不齐」——
两件都不是**横向**看的：同一个元素在 69 章里被写成了几种样子、同一句话在几处被说过，
只有把全书摆在一起才看得见。已有三道门各自守住了它们能守的那部分：
`lint_book` 守术语与引用、`totals` 守汇总数字、`index_book` 守「书改了索引没重生」。
它们**都只认关键字，不认形状**——`REQUIRED_ALWAYS` 里有「本章导读」，于是
「导读写成引用块」与「导读写成 H2 小节」都算通过。这一份工具补的正是这一层。

三条检测（各自的边界都写在函数上）
----------------------------------
1. `shapes()`  **体例形状普查**：十段式里那些「标题固定」的元素，实际被写成了几种形状
   （导读＝引用块／H2；常见坑＝列表／表格；练习＝三级标签／编号；延伸阅读＝分组／平铺），
   外加「常见坑」的条数分布——它是**普查**，不是判定：形状本身没有对错，
   但**同一种元素有两种形状**这件事必须有据可查，且由人来定哪一种作数。
2. `dupes()`   **跨篇重复段**：把硬换行的段落接回一行，跨章找 ≥26 个汉字的最长公共片段
   （汉字占比 ≥70%，排除 URL 段与「本章取用/落点/延伸阅读」这类台账句）。
   它给的是**候选**：相邻章重复同一条纪律句（「不改前四棵树」）是本书有意为之的体例，
   而同一句结论在两篇里各写一遍、且两处的数不一样，才是要动的东西。
3. `facts()`   **同一短语 ＋ 数字**：同一个「短语 ＋ 单位」在全书里出现过两个以上的值
   （「三棵树」与「四棵树」）。多数是同一条相对指称在不同篇里的正当取值
   （「本篇之前的树」随篇号变），少数才是漂移——所以它同样只出候选。

与 `REVISIT.md` 的关系
----------------------
`REVISIT.md` 里那三张表**照抄 `--check` 的输出**，而 `--check` 会把盘上的普查与文档里
记的那一份逐处比——抄错了、或者书改了而记录没跟，都会报出来（与 `index_book.py`
「书改了而索引没重生就红」同一个形状）。人写的判定与建议不进比对：那是判断，不是实测。
"""
from __future__ import annotations

import argparse
import difflib
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOK = ROOT / "book"
REVISIT = ROOT / "REVISIT.md"

#: 段落切分时先排除的东西：台账句、出处段与题源路径——它们逐章重复是**应该**的。
_EXCLUDE_PARA = re.compile(r"sources/|本章取用|计划落点|延伸阅读|原始资料|参考资料|https?://")

#: 十段式里「标题固定」的元素（`STYLE.md` 第二节）。
#: 每一项写的是：元素名 → 期望形状的判据。**形状的取舍由人定**，这里只做普查。
SHAPE_KEYS = ("导读", "常见坑", "练习", "延伸阅读")


def chapter_id(path: pathlib.Path) -> str | None:
    m = re.match(r"(\d+\.\d+)", path.name)
    return m.group(1) if m else None


def chapter_lines() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for f in sorted(BOOK.rglob("*.md")):
        cid = chapter_id(f)
        if cid:
            out[cid] = f.read_text(encoding="utf-8").splitlines()
    return out


def sections(lines: list[str]) -> dict[str, list[str]]:
    """`## X` 名 → 它下面（到下一个 `##` 为止）的行。"""
    out: dict[str, list[str]] = {}
    cur: str | None = None
    for ln in lines:
        if ln.startswith("## "):
            cur = ln[3:].strip()
            out.setdefault(cur, [])
            continue
        if cur is not None:
            out[cur].append(ln)
    return out


# ---------------------------------------------------------------- ① 体例形状

def shape_of(lines: list[str]) -> dict[str, str]:
    """一章的四个形状 ＋ 常见坑条数。返回的键是 SHAPE_KEYS ＋ `坑条数`。"""
    secs = sections(lines)
    out: dict[str, str] = {}

    # 导读：引用块（`> **本章导读**：`）还是 H2 小节（`## 本章导读`）。
    # 两种都在书里真实存在，且**门只认「本章导读」这四个字**。
    if "本章导读" in secs:
        out["导读"] = "H2"
    elif any(ln.lstrip().startswith("> **本章导读**") for ln in lines):
        out["导读"] = "引用块"
    else:
        out["导读"] = "缺"

    # 常见坑：列表（`- ` / `1. `）还是三列表格（`| 现象 |`）。
    pit = secs.get("常见坑", [])
    body = "\n".join(pit)
    out["常见坑"] = "表格" if re.search(r"^\|.*现象", body, re.M) else "列表"
    # 条数：列表数「- 」「1. 」开头的行；表格数数据行（去掉表头与分隔行）。
    if out["常见坑"] == "表格":
        rows = [l for l in pit if l.strip().startswith("|")]
        out["坑条数"] = str(max(0, len(rows) - 2))
    else:
        out["坑条数"] = str(sum(1 for l in pit
                                if re.match(r"^\s*(?:[-*] |\d+\. )", l)))

    # 练习：三级标签（每条自己带 `- **基础**：`）还是编号列表。
    # 口径与 `lint_book.chapter_shape_issues` **同一把尺子**：认的是「每一条自己带标签」，
    # 而不是「这节里出现过 `**基础**`」——两者差在 1.9／1.10 那种「分组小标题 ＋ 连续编号」上，
    # 普查当时把它算作三级标签（笼口径），而形状检查把它报成了错（严口径）。
    ex = secs.get("练习", [])
    tagged = [l for l in ex if re.match(r"^- \*\*(基础|进阶|挑战)\*\*", l)]
    loose = [l for l in ex if re.match(r"^(?:- |\d+\. )", l) and l not in tagged]
    if tagged and not loose:
        out["练习"] = "三级标签"
    elif loose:
        out["练习"] = "编号／无标签"
    elif "\n".join(ex).strip():
        out["练习"] = "其它"
    else:
        out["练习"] = "缺"

    # 延伸阅读：有分组小标题（`**官方文档**`）还是平铺一串链接。
    rd = "\n".join(secs.get("延伸阅读", []))
    if re.search(r"\*\*官方文档\*\*", rd):
        out["延伸阅读"] = "分组"
    elif rd.strip():
        out["延伸阅读"] = "平铺"
    else:
        out["延伸阅读"] = "缺"
    return out


def shapes_table(chapters: dict[str, list[str]] | None = None
                 ) -> tuple[list[str], dict[str, dict[str, str]]]:
    """形状普查：每张表一行（`元素 ｜ 形状 N ｜ 形状 M`），另回逐章明细。"""
    chapters = chapters if chapters is not None else chapter_lines()
    detail = {cid: shape_of(lines) for cid, lines in chapters.items()}
    lines: list[str] = []
    for key in SHAPE_KEYS:
        counts: dict[str, list[str]] = defaultdict(list)
        for cid, sh in detail.items():
            counts[sh[key]].append(cid)
        cells = " ｜ ".join(f"{k} {len(v)}" for k, v in
                            sorted(counts.items(), key=lambda kv: -len(kv[1])))
        lines.append(f"{key} ｜ {cells}")
    # 常见坑条数：第二节 2026-09-22 前写的是「3–6 条」，而全书实际是 7–29 条——
    # 那一条已改成「至少 3 条、不设上限」（改文档不改章），这里仍按三个区间摆出分布，
    # 让「越工程越多」这件事看得见。
    buckets: dict[str, list[str]] = defaultdict(list)
    for cid, sh in detail.items():
        n = int(sh["坑条数"])
        buckets["3–6 条" if 3 <= n <= 6 else "7–14 条" if n <= 14 else "15 条以上"].append(cid)
    lines.append("坑条数（第二节：至少 3 条、不设上限）｜ " + " ｜ ".join(
        f"{k} {len(v)}" for k, v in sorted(buckets.items())))
    return lines, detail


# ---------------------------------------------------------------- ② 重复段

def paragraphs(lines: list[str]) -> list[str]:
    """把硬换行的段落接回一行；去围栏、表格、标题、引用块与台账句。"""
    out: list[str] = []
    buf: list[str] = []
    fence = False

    def flush() -> None:
        if buf:
            joined = " ".join(buf)
            if not _EXCLUDE_PARA.search(joined):
                out.append(joined)
            buf.clear()

    for ln in lines:
        s = ln.strip()
        if s.startswith("```"):
            flush()
            fence = not fence
            continue
        if fence or not s or s.startswith(("|", "#", ">", "---", "<!--")):
            flush()
            continue
        buf.append(s)
    flush()
    return out


def _norm(s: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s)


def _han(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def dupes(chapters: dict[str, list[str]] | None = None, *,
          least: int = 26, ratio: float = 0.7) -> list[tuple[str, tuple[str, ...]]]:
    """跨章重复段（候选）。`least` 是最短公共汉字数，`ratio` 是片段里汉字的占比下限。

    口径：只比**散文段落**（围栏、表格、标题、引用块与台账句都不进），
    先按 24 字窗口（归一化后）建倒排，再对同窗的段落两两取最长公共块。
    """
    chapters = chapters if chapters is not None else chapter_lines()
    idx: dict[str, list[tuple[str, int]]] = defaultdict(list)
    paras = {cid: paragraphs(lines) for cid, lines in chapters.items()}
    for cid, ps in paras.items():
        for i, p in enumerate(ps):
            n = _norm(p)
            for j in range(0, max(0, len(n) - 24 + 1)):
                idx[n[j:j + 24]].append((cid, i))
    found: dict[str, tuple[int, tuple[str, ...]]] = {}
    for occ in idx.values():
        if len({c for c, _ in occ}) < 2 or len(occ) > 10:
            continue
        for a in range(len(occ)):
            for b in range(a + 1, len(occ)):
                (c1, i1), (c2, i2) = occ[a], occ[b]
                if c1 == c2:
                    continue
                p1, p2 = _norm(paras[c1][i1]), _norm(paras[c2][i2])
                for bl in difflib.SequenceMatcher(None, p1, p2, autojunk=False
                                                  ).get_matching_blocks():
                    if bl.size < least:
                        continue
                    seg = p1[bl.a:bl.a + bl.size]
                    if _han(seg) < bl.size * ratio:
                        continue
                    ids = tuple(sorted((c1, c2)))
                    if seg not in found or found[seg][0] < bl.size:
                        found[seg] = (bl.size, ids)
    return [(seg, ids) for seg, (_n, ids) in
            sorted(found.items(), key=lambda kv: -kv[1][0])]


# ---------------------------------------------------------------- ③ 同短语异值

#: 「数量短语」的单位。只收「可数的东西」——「个/条/棵/章/道/门」这些，
#: 不把「%」「字」收进来（那些是度量，同名的两个值多数不是同一件事）。
_UNIT = "棵|个|章|条|行|处|种|层|类|节|份|组|道|片|句|轮|档|题|门|套|支"
#: 键取**单位 ＋ 紧跟在它后面的 1–2 个汉字**（「三棵树」→「棵树」、「17 条坑」→「条坑」），
#: 不取数字前面的那些字。理由是实测出来的：数字前面常是动词与语法词
#: （「这一章有」三棵树 vs「已经有」四棵树），拿它们当键会把同一件事拆成两个键，
#: 而**被数的那个东西**就在单位后面——它才是「同一件事」的身份。
#: 名词取单位后面**最多两个**汉字，再把尾上的语法字削掉（「棵树里」「棵树了」→「棵树」）——
#: 削的理由：不削时「三棵树」与「四棵树里」会分成两键，而它们要的是同一件事。
#: 名词用**前瞻**而不是真吃掉它：真吃掉时「一章有三棵树」里的「三棵树」会被前一个
#: 假数字（「这一章」的「一」）连带吞掉——这是自检夹具里堵住的第二个坑。
_FACT = re.compile(rf"(\d[\d,]*(?:\.\d+)?)\s*({_UNIT})(?=([\u4e00-\u9fff]{{0,2}}))")
_FACT_HAN = re.compile(rf"([一二三四五六七八九十两]+)({_UNIT})(?=([\u4e00-\u9fff]{{0,2}}))")
#: 名词尾上的语法字：削掉它们之后剩下的才是「被数的那个东西」。
_TAIL_STOP = "了的里都也与和可是在不一两三四五六七八九十中上中下前后之或就才又还而却把被则即且及"


def _noun(raw: str) -> str:
    while len(raw) > 1 and raw[-1] in _TAIL_STOP:
        raw = raw[:-1]
    return raw


def facts(chapters: dict[str, list[str]] | None = None, *,
          most: int = 8, least_chapters: int = 2
          ) -> list[tuple[str, dict[str, list[str]]]]:
    """同一个「东西」（单位 ＋ 紧跟的名词）在全书里出现过 ≥2 个值的那些（候选，需人判）。"""
    chapters = chapters if chapters is not None else chapter_lines()
    groups: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for cid, lines in chapters.items():
        for p in paragraphs(lines):
            for mo in _FACT.finditer(p):
                key = mo.group(2) + (_noun(mo.group(3)) if mo.group(3) else "")
                groups[key][mo.group(1).rstrip(",.")].append(cid)
            for mo in _FACT_HAN.finditer(p):
                key = mo.group(2) + (_noun(mo.group(3)) if mo.group(3) else "")
                groups[key][mo.group(1)].append(cid)
    out = []
    for key, vals in groups.items():
        val_chs = {v: sorted(set(cs)) for v, cs in vals.items()}
        if not 2 <= len(val_chs) <= most:
            continue
        if len({c for cs in val_chs.values() for c in cs}) < least_chapters:
            continue
        out.append((key, val_chs))
    return sorted(out, key=lambda kv: (-len(kv[1]), kv[0]))


# ---------------------------------------------------------------- 核验与自检

def recorded_lines() -> list[str] | None:
    """`REVISIT.md` 里那个 ``` 块（--check 就是拿它逐行比）。"""
    if not REVISIT.exists():
        return None
    text = REVISIT.read_text(encoding="utf-8")
    m = re.search(r"```text\n(.*?)```", text, re.S)
    return [l.rstrip() for l in m.group(1).splitlines() if l.strip()] if m else None


def check() -> int:
    live, _detail = shapes_table()
    print("通读普查（体例形状 ＋ 常见坑条数）")
    for l in live:
        print("  " + l)
    old = recorded_lines()
    if old is None:
        print("  · REVISIT.md 里没有记录块——把上面这几行照抄进去")
        return 1
    if old != live:
        print("  ✖ REVISIT.md 里记的那一份与盘上不一致：")
        for a, b in zip(old, live):
            if a != b:
                print(f"      文档：{a}\n      盘上：{b}")
        return 1
    print("  ✔ 与 REVISIT.md 里记的那一份逐行相符")
    return 0


def self_test() -> int:
    """夹具全是合成输入（与书稿现状无关，不会有「书走到哪一步它就没有了」）。"""
    cases: list[tuple[str, dict[str, list[str]], str, object]] = [
        ("导读写成引用块：认出来",
         {"1.1": ["# 1.1 标题", "", "> **本章导读**：一句话。", "",
                  "## 学习目标", "- [ ] 目标", "## 常见坑",
                  "- 现象 → 原因 → 修法", "## 练习", "- **基础**：做题",
                  "## 延伸阅读", "**官方文档**（必填）", "- X — https://x"]},
         "导读", "引用块"),
        ("导读写成 H2：认出来（门只认那四个字，所以它此前一直静默）",
         {"1.1": ["# 1.1 标题", "## 本章导读", "一段散文。", "## 常见坑",
                  "- 一条", "## 练习", "1. 做题", "## 延伸阅读", "- X"]},
         "导读", "H2"),
        ("常见坑写成表格：认出来，并数出数据行（表头与分隔行不算）",
         {"1.1": ["## 常见坑", "", "| 现象 | 真实原因 | 修法 |", "| --- | --- | --- |",
                  "| a | b | c |", "| d | e | f |"]},
         "常见坑", "表格"),
        ("常见坑表格的条数：两条数据行 → 「2」（不是 4）",
         {"1.1": ["## 常见坑", "", "| 现象 | 真实原因 | 修法 |", "| --- | --- | --- |",
                  "| a | b | c |", "| d | e | f |"]},
         "坑条数", "2"),
        ("练习写成编号列表：认出来",
         {"1.1": ["## 练习", "1. 做题", "2. 再做一道"]}, "练习", "编号／无标签"),
        ("练习三级标签：认出来",
         {"1.1": ["## 练习", "- **基础**：做题"]}, "练习", "三级标签"),
        ("「分组小标题 ＋ 连续编号」不算三级标签（严口径，1.9／1.10 就是这样）",
         {"1.1": ["## 练习", "**基础**", "", "1. 做题", "2. 再做一道"]},
         "练习", "编号／无标签"),
        ("既不是条目也不是编号（写成一行的 `**基础**：`）：算「其它」",
         {"1.1": ["## 练习", "**基础**：做题"]}, "练习", "其它"),
        ("延伸阅读平铺：认出来",
         {"1.1": ["## 延伸阅读", "- X — https://x"]}, "延伸阅读", "平铺"),
        ("延伸阅读分组：认出来",
         {"1.1": ["## 延伸阅读", "**官方文档**（本章结论的权威依据）", "- X — https://x"]},
         "延伸阅读", "分组"),
    ]
    ok = 0
    for name, chapters, key, want in cases:
        got = shape_of(chapters["1.1"])[key]
        if got == want:
            ok += 1
        else:
            print(f"  ✖ [形状] {name}：期望 {want}，实得 {got}")

    # 重复段：跨章同一句话要命中；同一章内重复不算（「不要自己跟自己比」）
    dup_case = {
        "1.1": ["这一章的结论是：读数要么能复算要么别写进正文，而抄下来的数没人会对它响。"],
        "1.2": ["这一章的结论是：读数要么能复算要么别写进正文，而抄下来的数没人会对它响。"],
        "1.3": ["完全不同的另一句话，讲的是另一件事，长度也够但内容无关。"],
    }
    hit = [seg for seg, ids in dupes(dup_case)]
    if hit:
        ok += 1
    else:
        print("  ✖ [重复] 跨章同一句话没有命中")
    same = {"1.1": ["同一章里重复同一句话，而它不该被当成跨章重复，因为只在一章里出现。"],
            "1.2": ["别的内容。"]}
    if not dupes(same):
        ok += 1
    else:
        print("  ✖ [重复] 同一章内重复不该命中")
    excl = {"1.1": ["`sources/01/素材.md`：本章取用 12,345 汉字，落点见台账。"],
            "1.2": ["`sources/01/素材.md`：本章取用 12,345 汉字，落点见台账。"]}
    if not dupes(excl):
        ok += 1
    else:
        print("  ✖ [重复] 台账句（sources/ 与「本章取用」）不该进比对")

    # 同短语异值：同一个「东西」的两个值要报出来——**键不看数字前面的动词**
    # （「这一章有」与「已经有」是同一个「棵树」，这曾经是这一条差点漏掉的地方）
    f1 = {"1.1": ["这一章有三棵树里的东西可以对照，先看第一棵。"],
          "1.2": ["到这一篇已经有四棵树了，逐棵看一眼。"]}
    got1 = facts(f1)
    if any(k.startswith("棵树") for k, _ in got1):
        ok += 1
    else:
        print(f"  ✖ [同短语异值] 三棵树 / 四棵树 没有报出来：{got1}")
    # 同一个数只说一次、或只在一章里出现：不报（否则满屏都是噪声）
    f2 = {"1.1": ["一共有三棵树。"], "1.3": ["其它内容。"]}
    if not facts(f2):
        ok += 1
    else:
        print(f"  ✖ [同短语异值] 只见过一个值的不该报：{facts(f2)}")

    total = len(cases) + 5
    print(f"自检：{ok}/{total} 通过")
    return 0 if ok == total else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="通读修订的候选生成器")
    ap.add_argument("--check", action="store_true",
                    help="普查并与 REVISIT.md 里记的那一份比对")
    ap.add_argument("--shapes", action="store_true", help="只看体例形状普查")
    ap.add_argument("--dupes", action="store_true", help="只看跨篇重复段（候选）")
    ap.add_argument("--facts", action="store_true", help="只看同短语异值（候选）")
    ap.add_argument("--self-test", action="store_true", help="夹具")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.shapes or (not (args.dupes or args.facts) and not args.check):
        table, _ = shapes_table()
        for l in table:
            print(l)
        return 0
    if args.dupes:
        for seg, ids in dupes():
            print(f"{','.join(ids):13s} {seg[:80]}")
        return 0
    if args.facts:
        for key, vals in facts():
            cells = " ｜ ".join(f"{v}（{','.join(cs[:6])}）" for v, cs in
                                sorted(vals.items()))
            print(f"{key:12s} {cells[:160]}")
        return 0
    return check()


if __name__ == "__main__":
    sys.exit(main())
