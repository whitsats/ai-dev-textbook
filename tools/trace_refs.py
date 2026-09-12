#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改稿前的引用清单：给一个术语 / 数字 / 结论，列出全书哪些章节用到了它。

为什么不能直接用 grep
--------------------
**正文是硬换行的。** 一段话在磁盘上是好几行，浏览器里却渲染成连续的一段：

    一次不小心的原地修改，就会变成**偶发的、难以复现的 bug**（第 1.12 节的数据库会话、
    第 6.2 节的模型请求参数都会再遇到它）。

`grep "第 1.12 节的数据库会话"` 命中，`grep "会话、第 6.2 节"` 却命不中——**读者看得见，搜索看不见**。
改稿最怕的正是这种漏网：改了 1.12 的措辞，却不知道 1.2 里那句已经接不上了。
所以本工具先把被硬换行切断的段落接回一行再搜，并把命中的字符映射回**原始行号**，
报出来的行号可以直接跳过去改。

还有两件事 grep 也做不了：

- **数字的排版变体**。`26,091` / `26091` / `２６０９１` / `45%` / `45％` 是同一个数；
  同时 `45` 又不该命中 `1,450` 或 `3.45` 里的一段（千分位在这类报表里遍地都是）。
- **登记文件也要一起查**。改一个结论或一个数字，正文之外通常还要动
  `PLAN.md`（目录与计划字数）、`COVERAGE.md`（报表）、`LEDGER.md`（素材落点）、
  `GLOSSARY.md`（术语首现章）、`REFERENCES.md`（出处）。这些地方漏改不会报错，
  只会让文档互相矛盾——所以默认一起扫，并单独成节列出。

三种查询
--------
1. **术语**：字面匹配，忽略英文大小写（`上下文工程`、`R-P-I-V-D`、`JWT`）。
2. **数字**：字面匹配 + 变体归一 + 边界守卫（`26,091` 会连 `26091` 一起找；
   `45` 不会命中 `1,450`）。
3. **结论**：同一句话在不同章里几乎必然被改写，字面匹配必然漏。加 `--fuzzy`
   改比**词元重合度**（中文二元组 + 英文词 + 数字，按 IDF 调权，
   再取「加权覆盖」与「Dice」两种归一化的平均——它们各自偏一头，理由见 `fuzzy_score`），
   把「说得不一样但讲的是同一件事」的段落按分数排出来。这类结果**必须人工确认**，
   所以单独成节、附分数、默认只出前 10 条。分数高≠同一件事，看内容判断。

怎么读输出
----------
    ▸ [02] 2.2 Claude Code 实战 · 3 处
        L214–215  §2.2.4 R-P-I-V-D 六阶段 · 上下文必读    [正文] …把 26,091 理解为…

- `[本处]` = 用 `--from 2.2` 指定的、你正在改的那一章；其余章就是**改完要回头看的清单**。
- 类型标签（正文 / 条目 / 表格 / 代码 / 引用 / 标题）用来判断这条命中要不要跟着改：
  代码块里的常量改了，正文里的数字也得改；《本章小结》里只是复述，通常要一起顺。
- 行号是原始文件的行号，可直接用编辑器跳转。

两道守卫（沿用 8.5 的规矩：会响，且不乱响）
------------------------------------------
- **漏行守卫**：把每个文件切成单元时，若某个**非空行**没进入任何单元，就报警。
  解析规则（哪一行算续行）一旦改坏，命中的行号就会静默漂移——这正是
  `audit_coverage.py` 那类「报表自洽但少了一整章」的同族错误。
- **漏网守卫**：章节文件一律纳入索引。文件名不合 `<章号>-<标题>.md` 规范、
  或放在规范路径之外的文件会被**强制扫描**并提示，绝不静默跳过
  （`audit_coverage.py` 曾在含空格的 `2.2-Claude Code 实战.md` 上栽过）。

已知边界
--------
- 模糊匹配是**字面相似度**，不是语义：换用同义词（「幻觉」vs「编造」）不会命中。
  要查同义概念，用该词的其它写法各查一次。
- 代码块**按行索引、不跨行接续**（代码不像散文那样硬换行）；跨行的字符串字面量搜不到。
- 目录（`- [x]`）与表格按原样搜索；表格里的 `|` 会参与匹配。

用法
----
    python tools/trace_refs.py "上下文工程"                 # 术语
    python tools/trace_refs.py "26,091" --from 1.12         # 数字：26,091 与 26091 都命中
    python tools/trace_refs.py "安全漏洞不是靠写的时候小心" --fuzzy   # 结论被改写的地方
    python tools/trace_refs.py "RAG" --scope book --quiet   # 只列章，便于做回改清单
    python tools/trace_refs.py "上下文工程" --md             # markdown，可贴进台账/PR
    python tools/trace_refs.py --self-test                  # 用合成反例验证它会响、也不乱响

退出码：0 = 有命中，2 = 无命中（便于放进脚本里判断），1 = 自检失败。
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "book"

# 章节文件名规范：<章号>-<标题>.md。**故意写得宽松**（标题里可以有空格），
# 交给 parse_chapter 判定；不规范的由漏网守卫报出来。
CHAP_RE = re.compile(r"^(\d+\.\d+)-(.*)\.md$")

ZERO_WIDTH = "\u200b\u200c\u200d\u2060\ufeff"
FULLWIDTH_DIGITS = {chr(0xFF10 + i): chr(0x30 + i) for i in range(10)}
# 中文语境字符（含全角标点）：用于空格折叠与「要不要补一个空格」的判断
CJK_ISH_RE = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff01-\uff65\u2018\u2019"
                        r"\u201c\u201d\u2026\u2014\u2015\u3400-\u4dbf]")
# 结构行：出现即另起一个搜索单元（表格行、标题、列表项、围栏、引用……）
BREAK_RE = re.compile(r"^(#{1,6}\s|[-*+]\s|\d{1,3}[.、)]\s|\||>|```|~~~|"
                      r"<[-!/a-zA-Z]|={3,}|-{3,}|\*{3,})")
NUMERIC_Q_RE = re.compile(r"^[\d.,%+\-]+$")

STOPWORDS = {
    "the", "a", "an", "of", "and", "or", "to", "in", "on", "at", "is", "are",
    "be", "was", "were", "it", "its", "this", "that", "these", "those", "for",
    "with", "as", "by", "not", "no", "but", "if", "then", "than", "you", "your",
    "we", "our", "they", "their", "can", "will", "would", "should", "must",
}

BOLD, RESET = "\033[1m", "\033[0m"


# --------------------------------------------------------------------------
# 归一化：让「同一个东西的不同排版」变成同一个字符串
# --------------------------------------------------------------------------
def _fw(ch: str) -> str:
    return FULLWIDTH_DIGITS.get(ch, ch)


def _is_digit_at(s: str, i: int) -> bool:
    return 0 <= i < len(s) and _fw(s[i]).isdigit()


def _cjkish(ch: str) -> bool:
    return bool(ch) and CJK_ISH_RE.match(ch) is not None


def _next_visible(s: str, i: int) -> str:
    """越过零宽字符与空白，取下一个可见字符（判断要不要折叠空格用）。"""
    while i < len(s):
        c = s[i]
        if c in ZERO_WIDTH or c in " \t\u3000\u00a0":
            i += 1
            continue
        return _fw(c)
    return ""


def normalize(s: str) -> tuple[str, list[int]]:
    """归一化文本，返回（归一化串, 归一化串每个字符 → 原文下标）。

    规则与理由：
      * 删零宽字符——素材从 PDF 抽取而来，正文里偶有 U+200B，肉眼完全看不见；
      * 全角数字 / ％ → 半角——同一份数据在正文与表格里常常一半全角一半半角；
      * 数字之间的千分位逗号删掉——`26,091` 与 `26091` 必须互相命中；
      * 中文之间的空格删掉——**硬换行的接缝与手打空格必须等价**，
        否则「从原文复制一句话来搜」会因接缝处多一个空格而漏；
      * 连续空白折叠成一个；英文转小写（默认忽略大小写）。
    """
    out: list[str] = []
    idx: list[int] = []
    for j, ch in enumerate(s):
        if ch in ZERO_WIDTH:
            continue
        if ch in FULLWIDTH_DIGITS:
            ch = FULLWIDTH_DIGITS[ch]
        elif ch == "％":
            ch = "%"
        if ch in ",，" and _is_digit_at(s, j - 1) and _is_digit_at(s, j + 1):
            continue
        if ch in " \t\u3000\u00a0":
            prev = out[-1] if out else ""
            nxt = _next_visible(s, j + 1)
            if prev == " ":
                continue
            if _cjkish(prev) and _cjkish(nxt):
                continue
            ch = " "
        if ch.isascii() and ch.isalpha():
            ch = ch.lower()
        out.append(ch)
        idx.append(j)
    return "".join(out), idx


# --------------------------------------------------------------------------
# 切单元：把被硬换行切断的段落接回一行，并记住每个字符来自哪一行
# --------------------------------------------------------------------------
@dataclass
class Unit:
    """一个可搜索的单元（通常是一段话 / 一个列表项 / 一行代码 / 一行表格）。"""
    path: str
    line0: int                      # 单元起始行
    line1: int                      # 单元结束行
    kind: str                       # 正文 / 条目 / 表格 / 代码 / 引用 / 标题
    sec: str = ""                   # 最近的 ## 标题（定位用）
    sub: str = ""                   # 最近的 ### 及更细标题
    text: str = ""                  # 合并后的原文（去掉了续行前缀）
    lines: list[int] = field(default_factory=list)   # text 每字符 → 原始行号
    norm: str = ""                  # text 的归一化串
    norm_orig: list[int] = field(default_factory=list)  # norm 每字符 → text 下标

    def line_of(self, orig_index: int) -> int:
        if not self.lines:
            return self.line0
        i = min(max(orig_index, 0), len(self.lines) - 1)
        return self.lines[i]

    def label(self) -> str:
        loc = f"L{self.line0}" if self.line0 == self.line1 else f"L{self.line0}–{self.line1}"
        sec = f"§{self.sec}" if self.sec else ""
        sub = f" · {self.sub}" if self.sub else ""
        return f"{loc}  {sec}{sub}".rstrip()


def _kind_of(s: str) -> str:
    if s.startswith("#"):
        return "标题"
    if s.startswith("|"):
        return "表格"
    if s.startswith(">"):
        return "引用"
    if s.startswith(("```", "~~~")):
        return "代码"
    if re.match(r"([-*+]|\d{1,3}[.、)])\s", s):
        return "条目"
    return "正文"


def _needs_gap(left: str, right: str) -> bool:
    """接缝处要不要补一个空格：只有两侧都是 ASCII 字母数字时才补。

    中文接缝一律不补——`上下文工程` 被硬换行拆开之后仍要能被整词搜到。
    """
    return (left.isascii() and right.isascii()
            and left.isalnum() and right.isalnum())


def iter_units(text: str, path: str = "") -> tuple[list[Unit], list[int]]:
    """切分一个文件，返回（单元列表, 未进入任何单元的非空行号）。

    第二个返回值是**漏行守卫**：非空行必须全部落在某个单元里。解析规则一旦改坏，
    命中的行号就会静默漂移，而报表看上去仍然正常——所以要能自证。
    """
    lines = text.splitlines()
    units: list[Unit] = []
    rows: list[tuple[int, str]] = []      # 当前单元：(行号, 行内容)
    cur_kind = "正文"
    cur_sec, cur_sub = "", ""
    sec, sub = "", ""
    in_fence = False
    fence = "```"

    def flush() -> None:
        nonlocal rows
        if not rows:
            return
        parts: list[str] = []
        lmap: list[int] = []
        for k, (ln, content) in enumerate(rows):
            c = content
            if k > 0:                     # 续行：去掉引用符号（否则接缝处会横插一个 >）
                c = re.sub(r"^>\s?", "", c).strip()
            if not c:
                continue
            if parts and _needs_gap(parts[-1], c[0]):
                parts.append(" ")
                lmap.append(ln)
            parts.extend(c)
            lmap.extend([ln] * len(c))
        body = "".join(parts)
        # 即使 body 为空也照样登记（例如一行只有引用符 `>`）：否则那几行会从索引里消失，
        # 而它们是非空行，就会触发漏行守卫 —— 一道会因为无关原因报警的守卫等于没有守卫。
        u = Unit(path=path, line0=rows[0][0], line1=rows[-1][0], kind=cur_kind,
                 sec=cur_sec, sub=cur_sub, text=body, lines=lmap)
        u.norm, u.norm_orig = normalize(body)
        units.append(u)
        rows = []

    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        if in_fence:
            if s.startswith(fence):
                in_fence = False
                flush()
                rows = [(i, s)]
                cur_kind, cur_sec, cur_sub = "代码", sec, sub
                flush()
            elif s:
                flush()
                rows = [(i, s)]
                cur_kind, cur_sec, cur_sub = "代码", sec, sub
                flush()
            continue
        if not s:
            flush()
            continue
        if s.startswith("```") or s.startswith("~~~"):
            flush()
            in_fence = True
            fence = s[:3]
            rows = [(i, s)]
            cur_kind, cur_sec, cur_sub = "代码", sec, sub
            flush()
            continue
        if s.startswith("#"):
            flush()
            level = len(s) - len(s.lstrip("#"))
            title = s.lstrip("#").strip()
            if level <= 2:
                sec, sub = title, ""
            else:
                sub = title
            rows = [(i, s)]
            cur_kind, cur_sec, cur_sub = "标题", sec, sub
            flush()
            continue
        if BREAK_RE.match(s):
            flush()
            rows = [(i, s)]
            cur_kind, cur_sec, cur_sub = _kind_of(s), sec, sub
            if cur_kind == "表格":        # 表格行彼此独立，不互相接续
                flush()
            continue
        # 普通散文行：能接上一段就续接（这正是硬换行的接缝）
        if rows and cur_kind in ("正文", "条目", "引用"):
            rows.append((i, s))
        else:
            flush()
            rows = [(i, s)]
            cur_kind, cur_sec, cur_sub = "正文", sec, sub
    flush()

    covered = {ln for u in units for ln in set(u.lines)}
    lost = [i for i, raw in enumerate(lines, 1) if raw.strip() and i not in covered]
    return units, lost


# --------------------------------------------------------------------------
# 检索
# --------------------------------------------------------------------------
@dataclass
class Doc:
    rel: str                        # 相对仓库根的路径
    kind: str                       # 正文 / 登记
    cid: str | None
    title: str
    part: int
    order: float
    units: list[Unit] = field(default_factory=list)


@dataclass
class Hit:
    doc: Doc
    unit: Unit
    start: int                      # text 下标
    end: int
    score: float | None = None      # 模糊匹配的综合分
    detail: str = ""                # 模糊匹配的分项（加权覆盖 / Dice），供人判断

    @property
    def line_from(self) -> int:
        return self.unit.line_of(self.start)

    @property
    def line_to(self) -> int:
        e = max(self.end - 1, self.start)
        return self.unit.line_of(e)


def parse_chapter(name: str) -> tuple[str, str] | None:
    m = CHAP_RE.match(name)
    return (m.group(1), m.group(2)) if m else None


def _sort_key(cid: str) -> tuple[int, int]:
    a, b = cid.split(".")[:2]
    return int(a), int(b)


def make_doc(path: Path, kind: str, warnings: list[str]) -> Doc:
    rel = path.relative_to(ROOT).as_posix()
    parsed = parse_chapter(path.name)
    if parsed:
        cid, title = parsed
        part, sub = _sort_key(cid)
        order = part * 1000 + sub
    else:
        cid, title = None, path.stem
        part, order = 0, -1.0
        if kind == "正文":
            warnings.append(f"「{rel}」不符合 <章号>-<标题>.md 规范——已强制纳入扫描，请改名")
    text = path.read_text(encoding="utf-8", errors="replace")
    units, lost = iter_units(text, rel)
    if lost:
        warnings.append(f"「{rel}」有 {len(lost)} 个非空行未进入索引（首行 {lost[0]}）——"
                        f"切分规则有漏洞，命中行号可能失准")
    return Doc(rel=rel, kind=kind, cid=cid, title=title, part=part, order=order, units=units)


def build_docs(scope: str) -> tuple[list[Doc], list[str]]:
    docs: list[Doc] = []
    warnings: list[str] = []
    if scope in ("book", "all"):
        seen: set[Path] = set()
        for f in sorted(BOOK.glob("*/*.md")):
            if f.name.lower() == "readme.md":
                continue
            seen.add(f)
            docs.append(make_doc(f, "正文", warnings))
        # 漏网守卫：**比解析器更宽的写法**（否则它只能永远沉默）
        for f in sorted(BOOK.rglob("*.md")):
            if f in seen or f.name.lower() == "readme.md":
                continue
            warnings.append(f"「{f.relative_to(ROOT).as_posix()}」不在 book/<篇>/<章>.md 路径下——"
                            f"已强制纳入扫描")
            docs.append(make_doc(f, "正文", warnings))
    if scope in ("meta", "all"):
        for f in sorted(ROOT.glob("*.md")):
            docs.append(make_doc(f, "登记", warnings))
    docs.sort(key=lambda d: (d.kind != "正文", d.order, d.rel))
    return docs, warnings


def is_numeric_query(qnorm: str) -> bool:
    return bool(NUMERIC_Q_RE.match(qnorm)) and any(c.isdigit() for c in qnorm)


def _owns_number(hay: str, a: int, b: int) -> bool:
    """数字命中的边界守卫：`45` 不该命中 `1450`，也不该命中 `3.45` 里的一段。"""
    def digit(i: int) -> bool:
        return 0 <= i < len(hay) and hay[i].isdigit()

    if digit(a - 1) or digit(b):
        return False
    if a >= 1 and hay[a - 1] == "." and digit(a - 2):
        return False
    if b + 1 < len(hay) and hay[b] == "." and digit(b + 1):
        return False
    return True


def find_hits(unit: Unit, qnorm: str, numeric: bool) -> list[tuple[int, int]]:
    """在单元里找字面命中，返回 [(原文起, 原文止)]（**原始下标**，便于取片段）。"""
    out: list[tuple[int, int]] = []
    if not qnorm:
        return out
    hay = unit.norm
    i = hay.find(qnorm)
    while i >= 0:
        j = i + len(qnorm)
        if not numeric or _owns_number(hay, i, j):
            out.append((unit.norm_orig[i], unit.norm_orig[j - 1] + 1))
        i = hay.find(qnorm, i + 1)
    return out


def token_counter(s: str) -> Counter:
    """把一句话拆成词元并计数。

    - 中文二元组：让「换个说法」仍能对上大半；单字信息量太低，不计；
    - 英文词：忽略大小写与停用词；
    - 数字：一段数字算一个词元（结论里的数字是硬约束，「通过率 55%」改了就是改了结论）。
    """
    c: Counter = Counter()
    for run in re.findall(r"[\u4e00-\u9fff]{2,}", s):
        for k in range(len(run) - 1):
            c[run[k:k + 2]] += 1
    for word in re.findall(r"[A-Za-z][A-Za-z0-9_.\-]{1,}", s):
        lw = word.lower()
        if lw not in STOPWORDS:
            c[lw] += 1
    for num in re.findall(r"\d[\d.]*", s):
        c[num.strip(".")] += 1
    return c


def stem(unit_text: str) -> str:
    return normalize(unit_text)[0]


def idf_weights(tokens: Counter, docs: list[Doc]) -> dict[str, float]:
    """按「该词元在全书有多稀罕」给权重，归一化到 (0, 1]。

    中文二元组里 `的时`、`是一` 这类在几千个单元里到处都是，`漏洞`、`脱钩` 才是信号。
    不加权的话，通用二元组会把分数拉平：实测同一句结论的同义改写只拿到 **0.32**，
    与完全无关的段子（0.24）几乎分不开——阈值再怎么调都调不出来。
    """
    units = [u for d in docs for u in d.units]
    n = max(len(units), 1)
    ceiling = math.log(n + 1)
    return {t: (math.log((n + 1) / (sum(1 for u in units if t in u.norm) + 1)) / ceiling
                if ceiling else 1.0)
            for t in tokens}


def token_total(norm: str) -> int:
    """一个单元的**词元总量**（与 token_counter 同口径，但不算到具体词上）。"""
    total = sum(max(0, len(r) - 1) for r in re.findall(r"[\u4e00-\u9fff]{2,}", norm))
    total += sum(1 for w in re.findall(r"[A-Za-z][A-Za-z0-9_.\-]{1,}", norm)
                 if w.lower() not in STOPWORDS)
    total += len(re.findall(r"\d[\d.]*", norm))
    return total


def fuzzy_score(qcount: Counter, weights: dict[str, float],
                unit: Unit) -> tuple[float, float, float]:
    """返回（综合分, 加权覆盖, Dice）。两个归一化各自偏一头，取平均。

    两种量法在实测里朝**相反方向**出偏，所以都不能单独用：

    | 量法 | 含义 | 失败方向 |
    | --- | --- | --- |
    | 加权覆盖 = 命中权重 / 查询权重 | 「这句话有多少出现在本段」 | 查询写长一点（多几处修饰）分数就跌（0.33 → 0.21），而改稿时句子只会越改越长 |
    | Dice = 2×共同 / (查询 + 本段) | 同时看两侧长度 | 本段很长时分数被拉低（真正的目标段 0.61 → 0.22） |

    取平均后，实测：同义改写 0.22–0.61，无关段 ≤ 0.13。**两个数都会打印出来**，
    因为最终要人来判断；只给一个综合分反而看不出它是哪一种偏差。
    """
    if not qcount:
        return 0.0, 0.0, 0.0
    counts = {t: unit.norm.count(t) for t in qcount}
    shared = sum(min(k, counts[t]) for t, k in qcount.items())
    q_w = sum(weights[t] * k for t, k in qcount.items())
    shared_w = sum(weights[t] * min(k, counts[t]) for t, k in qcount.items())
    coverage = shared_w / q_w if q_w else 0.0
    denom = sum(qcount.values()) + token_total(unit.norm)
    dice = 2.0 * shared / denom if denom else 0.0
    return 0.5 * (coverage + dice), coverage, dice


# --------------------------------------------------------------------------
# 报告
# --------------------------------------------------------------------------
def snippet(hit: Hit, ctx: int, hl: bool) -> str:
    t = hit.unit.text
    a = max(0, hit.start - ctx)
    b = min(len(t), hit.end + ctx)
    pre = "…" if a > 0 else ""
    post = "…" if b < len(t) else ""
    mid = t[hit.start:hit.end]
    if hl:
        mid = f"{BOLD}{mid}{RESET}"
    body = re.sub(r"\s+", " ", t[a:hit.start] + mid + t[hit.end:b])
    return f"{pre}{body.strip()}{post}"


def load_glossary_terms() -> dict[str, tuple[str, str]]:
    """解析 GLOSSARY.md 的登记术语 →（首选写法, 首次出现章）。用于首现章核对。"""
    f = ROOT / "GLOSSARY.md"
    if not f.exists():
        return {}
    text = f.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"LINT:TERMS:BEGIN(.*?)LINT:TERMS:END", text, re.S)
    if not m:
        return {}
    table: dict[str, tuple[str, str]] = {}
    for line in m.group(1).splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4 or cells[0] in ("首选写法", ""):
            continue
        preferred, english, first = cells[0], cells[1], cells[3]
        for alias in [preferred] + re.split(r"[/,，、]", english):
            alias = alias.strip()
            if alias and alias != "—":
                table[normalize(alias)[0]] = (preferred, first)
    return table


def group_by_doc(hits: list[Hit], from_chapter: str | None) -> list[tuple[Doc, list[Hit]]]:
    by_doc: dict[str, list[Hit]] = {}
    order: list[str] = []
    for h in hits:
        if h.doc.rel not in by_doc:
            by_doc[h.doc.rel] = []
            order.append(h.doc.rel)
        by_doc[h.doc.rel].append(h)
    if from_chapter:
        order.sort(key=lambda r: 0 if _doc_cid(by_doc[r][0].doc) == from_chapter else 1)
    return [(by_doc[r][0].doc, by_doc[r]) for r in order]


def _doc_cid(doc: Doc) -> str | None:
    return doc.cid


def doc_heading(doc: Doc, from_chapter: str | None) -> str:
    if doc.kind == "登记":
        return f"{doc.rel}"
    mark = "  【本处】" if from_chapter and doc.cid == from_chapter else ""
    part = f"[{doc.part:02d}] " if doc.part else ""
    cid = f"{doc.cid} " if doc.cid else ""
    return f"{part}{cid}{doc.title}{mark}"


def print_console(query: str, mode_txt: str, docs: list[Doc], exact: list[Hit],
                  fuzzy: list[Hit], from_chapter: str | None, ctx: int,
                  max_per_chapter: int, quiet: bool, glossary: dict[str, tuple[str, str]],
                  qnorm: str, warnings: list[str], hl: bool,
                  fuzzy_best: float | None = None) -> None:
    body_docs = [d for d in docs if d.kind == "正文"]
    meta_docs = [d for d in docs if d.kind == "登记"]
    lost_files = sum(1 for w in warnings if "未进入索引" in w)

    if quiet:
        for doc, hits in group_by_doc(exact, from_chapter):
            print(f"{doc.cid or doc.rel}\t{doc.title}\t{len(hits)}")
        return

    print(f"查询「{query}」｜{mode_txt}")
    print(f"索引：正文 {len(body_docs)} 章 ｜ 登记文件 {len(meta_docs)} 个 ｜ "
          f"有漏行守卫的文件 {lost_files} 个 ｜ "
          f"命中 {len(exact)} 处（{len({h.doc.rel for h in exact})} 个文件）")
    for w in warnings:
        print(f"  ⚠️  {w}")
    print()

    body_hits = [h for h in exact if h.doc.kind == "正文"]
    meta_hits = [h for h in exact if h.doc.kind == "登记"]

    print("一、正文命中" + (f"：{len({h.doc.rel for h in body_hits})} 章 / {len(body_hits)} 处"
                          if body_hits else "：无"))
    if not body_hits:
        print("    （未在任何章节正文里出现）")
    for doc, hits in group_by_doc(body_hits, from_chapter):
        print(f"  ▸ {doc_heading(doc, from_chapter)} · {len(hits)} 处")
        for h in hits[:max_per_chapter]:
            print(f"      {h.unit.label():<44} [{h.unit.kind}] {snippet(h, ctx, hl)}")
        if len(hits) > max_per_chapter:
            print(f"      … 另有 {len(hits) - max_per_chapter} 处（--max-per-chapter 调整）")

    if meta_hits:
        print(f"\n二、登记文件命中：{len({h.doc.rel for h in meta_hits})} 个 / {len(meta_hits)} 处"
              f"（改正文后要一起同步的地方）")
        for doc, hits in group_by_doc(meta_hits, None):
            print(f"  ▸ {doc.rel} · {len(hits)} 处")
            for h in hits[:max_per_chapter]:
                print(f"      {h.unit.label():<30} [{h.unit.kind}] {snippet(h, ctx, hl)}")
            if len(hits) > max_per_chapter:
                print(f"      … 另有 {len(hits) - max_per_chapter} 处")

    if qnorm in glossary:
        preferred, first = glossary[qnorm]
        chapter_first = next((h for h in body_hits if h.doc.cid == first), None)
        tick = "✓ 命中" if chapter_first else "✗ 没有命中"
        print(f"\n术语表核对：「{preferred}」登记的首现章是 {first} —— 正文 {tick}"
              + ("" if chapter_first else "（登记与正文不一致，或该章还没写）"))

    if fuzzy:
        print(f"\n三、近似命中（结论被改写的地方，{len(fuzzy)} 处，需人工确认）")
        for h in fuzzy:
            body = re.sub(r"\s+", " ", h.unit.text)
            print(f"  分数 {h.score:.2f}（{h.detail}）  {doc_heading(h.doc, from_chapter)} · "
                  f"{h.unit.label()}"
                  f"\n      [{h.unit.kind}] {body[:120]}{'…' if len(body) > 120 else ''}")
        print("  （分数只是排序参考：高不等于同一件事，低不等于无关——看内容判断）")
    elif fuzzy_best is not None:
        # 沉默也要说清楚：否则读者分不清「没有近似命中」与「功能没生效」
        print(f"\n三、近似命中：无（全书最高 {fuzzy_best:.2f}，低于阈值；"
              f"可调低 --threshold 再看）")

    # 改稿视角的收尾：明确列出「除了本处，还要回头看谁」
    others = [d for d in {h.doc.rel: h.doc for h in body_hits}.values()
              if not from_chapter or d.cid != from_chapter]
    other_meta = {h.doc.rel for h in meta_hits}
    if exact or fuzzy:
        print("\n需回看："
              + (f"正文 {len(others)} 章（" +
                 "、".join(f"{d.cid or d.rel}" for d in sorted(others, key=lambda d: d.order)) + "）"
                 if others else "正文 0 章")
              + (f" ｜ 登记 {len(other_meta)} 个（" + "、".join(sorted(other_meta)) + "）"
                 if other_meta else ""))


def print_markdown(query: str, mode_txt: str, docs: list[Doc], exact: list[Hit],
                   fuzzy: list[Hit], from_chapter: str | None,
                   glossary: dict[str, tuple[str, str]], qnorm: str) -> None:
    body_hits = [h for h in exact if h.doc.kind == "正文"]
    meta_hits = [h for h in exact if h.doc.kind == "登记"]
    print(f"## 引用清单：`{query}`\n")
    print(f"- 查询模式：{mode_txt}")
    print(f"- 索引范围：正文 {len([d for d in docs if d.kind == '正文'])} 章 / "
          f"登记文件 {len([d for d in docs if d.kind == '登记'])} 个")
    print(f"- 命中：正文 {len(body_hits)} 处、登记 {len(meta_hits)} 处\n")

    print("### 需回看的章（改稿清单）\n")
    for doc, hits in group_by_doc(body_hits, from_chapter):
        mark = "（本处）" if from_chapter and doc.cid == from_chapter else ""
        print(f"- [ ] `{doc.cid or doc.rel}` {doc.title}{mark} —— {len(hits)} 处")
    if not body_hits:
        print("- （无正文命中）")

    print("\n### 逐处位置\n")
    print("| 章 | 节 | 类型 | 行 | 片段 |")
    print("| --- | --- | --- | --- | --- |")
    for h in exact:
        sec = h.unit.sec or "—"
        if h.unit.sub:
            sec += f" · {h.unit.sub}"
        # 命中里若本来就带 markdown 强调符号，先去掉再加 `**`，否则会打印出 `****` 这种残迹
        snip = re.sub(r"\*+", "", h.unit.text[h.start:h.end])
        pre = re.sub(r"\*+", "", h.unit.text[max(0, h.start - 20):h.start])
        post = re.sub(r"\*+", "", h.unit.text[h.end:h.end + 20])
        cell = re.sub(r"\s+", " ", f"…{pre}**{snip}**{post}…").replace("|", "\\|")
        loc = f"{h.line_from}" if h.line_from == h.line_to else f"{h.line_from}–{h.line_to}"
        print(f"| {h.doc.cid or h.doc.rel} | {sec} | {h.unit.kind} | {loc} | {cell} |")

    if qnorm in glossary:
        preferred, first = glossary[qnorm]
        hit_first = any(h.doc.cid == first for h in body_hits)
        print(f"\n> 术语表：「{preferred}」登记首现章 {first} —— "
              + ("正文命中 ✓" if hit_first else "**正文未见 ✗**"))

    if fuzzy:
        print("\n### 近似命中（分数只是排序参考，需人工确认）\n")
        for h in fuzzy:
            snip = re.sub(r"\s+", " ", h.unit.text)
            print(f"- {h.score:.2f} · `{h.doc.cid or h.doc.rel}` {h.unit.label()} "
                  f"[{h.unit.kind}] —— {snip[:90]}…")


# --------------------------------------------------------------------------
# 自检：合成反例（会响的那几条 + 应当沉默的那几条）
# --------------------------------------------------------------------------
FIXTURE = '''## 1.1 示例章

这是第一段，句子被硬换行切成两行，
第二行接着讲 26,091 这个数字。

- 第一条：概念叫「上下文工程」，
  它在本行继续说明。

```python
print("上下文工程")
```

> 引用里的 26091 也要能搜到。
>



### 小节

**加粗段落**里的 1,450 不能被它的后两位命中，也不该漏掉 １，４５０ 的全角写法。

| 表头 | 值 |
| --- | --- |
| 上下文工程 | 26,091 |
'''


def self_test() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    units, lost = iter_units(FIXTURE, "fixture.md")

    def hits(q: str) -> list[Hit]:
        qn = normalize(q)[0]
        out: list[Hit] = []
        for u in units:
            for a, b in find_hits(u, qn, is_numeric_query(qn)):
                out.append(Hit(Doc("x", "正文", "1.1", "x", 1, 1.1), u, a, b))
        return out

    # 1) 硬换行接缝：跨行的句子必须能整句搜到（这是本工具存在的理由）
    h = hits("被硬换行切成两行，第二行接着讲")
    check("跨行接缝的整句能被搜到", len(h) == 1 and h[0].line_from == 3,
          f"命中 {len(h)} 处")

    # 2) 硬换行接缝：接缝处不能凭空多出一个空格（否则从正文复制的句子会漏）
    check("接缝处不插空格（中文）", "切成两行，第二行" in units[1].text, units[1].text[:40])

    # 3) 数字变体：千分位 / 全角 / ％
    check("26,091 命中 26091", len(hits("26,091")) >= 2, f"{len(hits('26,091'))} 处")
    # 同一行里同时写了半角与全角两种写法，两边都该各自命中一次
    check("全角 １，４５０ 与 1,450 等价", len(hits("1,450")) == len(hits("１，４５０")) == 2,
          f"{len(hits('1,450'))} / {len(hits('１，４５０'))}")

    # 4) 数字边界守卫：应当沉默的三条
    # 注意夹具正文里不能再出现裸的 `45`，否则这条测的就不是“边界”而是“确实存在”——
    # 第一版夹具就栽在这里（原文写着「不能被 45 命中」，于是 45 真的命中了一次）。
    check("45 不命中 1,450", not hits("45"), f"{len(hits('45'))} 处")
    check("609 不命中 26,091", not hits("609"), f"{len(hits('609'))} 处")
    check("6091 不命中 26,091", not hits("6091"), f"{len(hits('6091'))} 处")

    # 5) 中文之间的空格折叠：手打空格与硬换行接缝等价
    check("空格折叠（上下文 工程）", len(hits("上下文 工程")) == len(hits("上下文工程")),
          f"{len(hits('上下文 工程'))} / {len(hits('上下文工程'))}")

    # 6) 分类与行号：代码块要单独成单元，且行号指到那一行
    kinds = {u.kind for u in units if "上下文工程" in u.text}
    check("代码块 / 列表项 / 表格各自成单元", kinds == {"条目", "代码", "表格"}, str(kinds))
    code_unit = next(u for u in units if u.kind == "代码" and "上下文" in u.text)
    check("代码块行号准确", code_unit.line0 == 10, f"L{code_unit.line0}")

    # 7) 引用续行的 > 前缀不参与匹配
    check("引用整句可搜（去掉 > 前缀）", len(hits("引用里的 26091 也要能搜到")) == 1,
          f"{len(hits('引用里的 26091 也要能搜到'))} 处")

    # 8) 漏行守卫：非空行必须全部进入索引
    # 夹具里特放了一行只有 `>` 的空引用行：它必须被登记（哪怕正文为空），
    # 否则守卫会因为「非空行没进索引」而抶下来——一道会因为无关原因报警的守卫将被绕过。
    check("漏行守卫为 0（含只有引用符的空行）", not lost, str(lost))

    # 9) 章节名解析：含空格的标题也要认（audit_coverage 在这里栽过）
    check("含空格的章名可解析",
          parse_chapter("2.2-Claude Code 实战.md") == ("2.2", "Claude Code 实战"),
          str(parse_chapter("2.2-Claude Code 实战.md")))
    check("不合规范的名字判为不认识", parse_chapter("readme.md") is None, "")

    # 10) 模糊匹配：该响的响、该沉默的沉默
    qt = token_counter(stem("概念叫上下文工程，本行继续说明"))
    fake = [Doc("x", "正文", "1.1", "x", 1, 1.1, units)]
    w = idf_weights(qt, fake)
    good = max(fuzzy_score(qt, w, u)[0] for u in units)
    check("近似匹配能认出改写后的同一句话", good >= 0.3, f"分数 {good:.2f}")
    qt = token_counter(stem("完全无关的一句话，讲的是另一件完全不同的事"))
    w = idf_weights(qt, fake)
    bad = max(fuzzy_score(qt, w, u)[0] for u in units)
    check("近似匹配不乱响（无关句分数低）", bad < 0.15, f"分数 {bad:.2f}")

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        extra = f"  {detail}" if detail and not ok else ""
        print(f"  [{mark}] {name}{extra}")
    print(f"\n自检：{len(checks) - len(failed)}/{len(checks)} 通过")
    return 1 if failed else 0


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="改稿前查引用：给一个术语 / 数字 / 结论，列出全书命中的位置")
    ap.add_argument("query", nargs="*", help="要追踪的术语 / 数字 / 结论（建议加引号）")
    ap.add_argument("--from", dest="from_chapter", metavar="章号",
                    help="你正在改的章，例如 2.2；该章的命中标为【本处】并置顶")
    ap.add_argument("--fuzzy", action="store_true",
                    help="结论查询：按词元重合度找「说得不一样但讲的是同一件事」的段落")
    ap.add_argument("--threshold", type=float, default=0.15,
                    help="模糊匹配的分数下限（默认 0.15；实测同义改写 0.19–0.61，无关段 ≤ 0.09。"
                         "它只是一条打印门限，不是判定结论)")
    ap.add_argument("--top", type=int, default=10, help="模糊匹配最多列几条（默认 10）")
    ap.add_argument("--scope", choices=("book", "meta", "all"), default="all",
                    help="book=只看正文；meta=只看登记文件；all=都看（默认）")
    ap.add_argument("--context", type=int, default=28, help="命中片段两侧的上下文字数（默认 28）")
    ap.add_argument("--max-per-chapter", type=int, default=8, help="每章最多列出几条（默认 8）")
    ap.add_argument("--md", action="store_true", help="输出 markdown，便于贴进台账 / PR")
    ap.add_argument("--quiet", action="store_true", help="只列「章号 / 标题 / 命中数」")
    ap.add_argument("--self-test", action="store_true", help="用合成反例自检")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    query = " ".join(args.query).strip()
    if not query:
        ap.error('请给出要追踪的术语 / 数字 / 结论，例如：python tools/trace_refs.py "上下文工程"')

    qnorm = normalize(query)[0].strip()
    if not qnorm:
        ap.error("查询内容为空（去掉零宽字符后没有可匹配的字符）")

    docs, warnings = build_docs(args.scope)
    names = {d.cid for d in docs if d.cid}
    if args.from_chapter and args.from_chapter not in names:
        print(f"⚠️  --from {args.from_chapter} 不在已索引的章节里（可能还没写）\n", file=sys.stderr)

    numeric = is_numeric_query(qnorm)
    exact: list[Hit] = []
    for d in docs:
        for u in d.units:
            for a, b in find_hits(u, qnorm, numeric):
                exact.append(Hit(d, u, a, b))

    covered_units = {(h.doc.rel, h.unit.line0, h.unit.kind) for h in exact}

    fuzzy: list[Hit] = []
    fuzzy_best = 0.0
    if args.fuzzy:
        qcount = token_counter(qnorm)
        weights = idf_weights(qcount, docs)
        cand: list[Hit] = []
        for d in docs:
            for u in d.units:
                if (d.rel, u.line0, u.kind) in covered_units:
                    continue
                score, cov, dice = fuzzy_score(qcount, weights, u)
                fuzzy_best = max(fuzzy_best, score)
                if score >= args.threshold:
                    # 模糊命中没有单一匹配区间：片段取整个单元的开头，不做高亮
                    cand.append(Hit(d, u, 0, 0, score,
                                    f"覆盖 {cov:.2f} · Dice {dice:.2f}"))
        cand.sort(key=lambda h: (-h.score, h.doc.order))
        fuzzy = cand[:args.top]
        if len(qcount) < 4:
            print("提示：模糊匹配需要更长的句子（当前词元太少），结论请整句粘进来\n",
                  file=sys.stderr)

    glossary = load_glossary_terms()
    mode = "字面（忽略英文大小写）"
    mode += " · 数字边界守卫" if numeric else ""
    if args.fuzzy:
        mode += f" + 近似（分数 ≥ {args.threshold}）"

    use_color = sys.stdout.isatty() and not args.md

    if args.md:
        print_markdown(query, mode, docs, exact, fuzzy, args.from_chapter, glossary, qnorm)
    else:
        print_console(query, mode, docs, exact, fuzzy, args.from_chapter, args.context,
                      args.max_per_chapter, args.quiet, glossary, qnorm, warnings, use_color,
                      fuzzy_best if args.fuzzy else None)
    return 0 if (exact or fuzzy) else 2


if __name__ == "__main__":
    sys.exit(main())
