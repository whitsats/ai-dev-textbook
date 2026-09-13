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
    [出处]  「延伸阅读」中官方文档链接是否 ≥ 2 条（代码块内的 URL 不算出处）
    [溯源]  sources/... 路径是否真实存在
    [篇幅]  有效字数（汉字 + 代码行折算）与 PLAN.md 计划字数的偏差（容忍 ±40%）
    [重复]  跨章重复的长句（防止内容被复制粘贴到多处）
    [标点]  中文后紧跟半角标点的抽查（代码区不适用）
    [术语]  避免的写法（代码块、反引号与素材溯源区为逐字引用区，不参与）
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

# 禁用词的合法复合词：一刀切会把正确用法也拦下来——「判据说」里的「据说」
# 是「判据 + 说」而不是「据说」传闻。与术语表的 _term_hits 同一套处理。
BANNED_ALLOW = {"据说": ["判据说"]}

# 指代「写作原料」的词：读者手里没有素材，正文里出现它们就是在跟一份
# 他看不到的文档对话（STYLE.md 六.6）。
# 豁免两区：章末「素材溯源」（它的职责就是做素材与正文的对照），
# 以及 0.3 使用说明章（它本身就在讲全书的资料分工）。
RAW_WORDS = ["素材", "讲义", "资料包"]
RAW_EXEMPT_CH = {"0.3"}
RAW_TAIL_MARK = "**素材溯源**"

# 「我核过」的过程叙述（STYLE.md 六.7）：读者不需要知道写作过程，他需要的是结论。
# 注意不要连「未实跑」一起禁——那是**对读者有行动意义**的标注，必须留着。
PROCESS_WORDS = ["实跑核对", "实跑确认", "实跑验证", "实跑纠正", "实跑发现", "已实跑"]

MIN_OFFICIAL_LINKS = 2
WORD_TOLERANCE = 0.40
# 一行有效代码（有内容、不含空行与围栏）约等于 15 个汉字的信息量。
# 技术章节的代码本身就是内容，只数汉字会把「代码密集 + 讲得清楚」的章误判为偷工减料；
# 也不能简单放宽容差，那会把真问题一起放过。折算成同一口径再比，才既不冤枉也不放水。
CODE_LINE_EQUIV = 15
DUP_MIN_HAN = 30  # 跨章重复检测的最小句长（汉字数）

# ---------------- 交叉引用与台账落点（篇收尾的反向核对用） ----------------
#
# 为什么要单独一套判定：`1.6.0`、`3.5.3`、`3.11`、`2.10` 这些**版本号**与章号长得一样
# （Starlette 1.6.0、redis 3.5.3、PyJWT 2.10、Python 3.11）。只按「像章号」判定，
# 会把每一个版本号都当成悬空引用。实测过：裸扫描得 8 条命中，**全是版本号**。
# 所以只有出现引用语境（第…节 / 见 / 详见 / 括号包裹）才算引用——宁可少报，不可乱报。
REF_SOFT_PREFIX = "第见详参接与和同如按到在从（(，,、"
REF_HARD_PREFIX = ("第", "见", "详见", "参见", "参照")
# 台账落点里这些**文字落点**是合法的（它们指向章末固定小节或全书层面的说明）
LANDING_WORDS = ("延伸阅读", "练习", "常见坑", "本章小结", "面试视角", "学习目标",
                 "前言", "全书", "见 PLAN", "——", "同上")
SEC_REF = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2}\.\d{1,3})(?![\d.])")
CHAP_REF = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2})(?![\d.])")
LEDGER_SYMBOLS = ("✅", "🔀", "⏭", "⬜")


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


# 围栏行：可带语言标记，也可有前导空白或在引用块里（`> `）。
# 三种形态都在本书里真实出现过：` ```python `、`> ``` `（1.14）、`   ``` `（2.5 的列表内）。
_FENCE = re.compile(r"^[\s>]*```[A-Za-z0-9_+.-]*\s*$")


def code_lines_of(text: str) -> list[str]:
    """围栏内的有效代码行：剔空行，也剔两行围栏标记自身。

    口径必须与 CODE_LINE_EQUIV 的注释一致：「有内容、不含空行与围栏」。
    这里曾经把整块 `splitlines` 全数计入，于是开围栏（` ```python `）与闭围栏
    各占去 15 个汉字的位置——**全书 671 个围栏，虚增 20,130 有效字**，
    而它同时是 `PLAN.md` 每章「✅ 字数」、「达成%」与汇总分的输入。
    2026-09-13 修正；旧口径下的历史快照（各章「事后校准」里的叙述数字）不再改动，
    由 `PLAN.md` 「字数口径」节的一句变更说明交代。

    注意闭围栏不总是裸 ` ``` `：1.14 有一个代码块整块在引用块里（行首 `> `），
    2.5 有一个在列表项里（行首缩进）。所以判定围栏要允许前导空白与 `> `。
    """
    out: list[str] = []
    for block in re.findall(r"```.*?```", text, re.S):
        lines = block.splitlines()
        if lines and _FENCE.match(lines[0]):
            lines = lines[1:]
        if lines and _FENCE.match(lines[-1]):
            lines = lines[:-1]
        out += [ln for ln in lines if ln.strip()]
    return out


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
    #
    # 代码块与反引号里是**逐字引用**（素材文件名、标识符、报错原文），不能改写：
    # 素材文件名里就带着「数据验证」这类写法，改成「数据校验」等于把可追溯性改坏。
    # 因此这两区不判错。但反引号里的出现会降级提示一次：它既可能是逐字引用，
    # 也可能是顺手写错，这个区别只有人能判断，不应静默放过。
    # 含路径分隔符或扩展名的反引号片段视为逐字引用（如 `sources/…/xx.md`），不提示。
    # 注意：不要用「截掉素材溯源小节」的办法来避开文件名——那会把该小节之后
    # 的一切正文一起豁免掉（负向验证时正是这个缺陷让一处真违规降成了警告）。
    term_text = re.sub(r"```.*?```", "", text, flags=re.S)
    quoted_text = re.sub(r"`[^`]*`", "", term_text)

    def _term_hits(hay: str, preferred: str, bad: str) -> int:
        n = hay.count(bad)
        if bad in preferred:
            n -= hay.count(preferred)
        return n

    for preferred, bad in ctx["glossary"]:
        hits = _term_hits(quoted_text, preferred, bad)
        if hits > 0:
            rep.err(where, f"术语违规：应写「{preferred}」，正文出现「{bad}」{hits} 次")
            continue
        ambiguous = sum(
            1 for span in re.findall(r"`([^`]*)`", term_text)
            if bad in span and not re.search(r"[/\\._]", span)
        )
        if bad in preferred:
            ambiguous -= term_text.count(preferred)
        if ambiguous > 0:
            rep.warn(where, f"「{bad}」在反引号里出现 {ambiguous} 次"
                            f"（逐字引用则正常，若是笔误请改为「{preferred}」）")

    # [禁用词]
    for w in BANNED_WORDS:
        n = text.count(w) - sum(text.count(ok) for ok in BANNED_ALLOW.get(w, ()))
        if n > 0:
            rep.err(where, f"出现规范禁用词「{w}」（{n} 次）")

    # [视角] 正文不得指代写作原料（STYLE.md 六.6）
    # 代词出现在标题里比出现在段落里更刺眼——读者翻目录就会撞上
    # 「素材的顺序说明是反的」这种只对作者有意义的标题，所以逐行点名行号。
    # 行号必须在原始文本上数（剔代码块会打乱行号），因此用状态机而不是正则。
    if cid not in RAW_EXEMPT_CH:
        cut = text.find(RAW_TAIL_MARK)
        body = text[:cut] if cut != -1 else text
        in_fence = False
        for lineno, line in enumerate(body.splitlines(), start=1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            hit = next((w for w in RAW_WORDS if w in line), None)
            if hit:
                rep.err(where, f"第 {lineno} 行正文出现「{hit}」：读者看不到素材，"
                                f"请直接给结论（对照写进章末「素材溯源」）")
            hit = next((w for w in PROCESS_WORDS if w in line), None)
            if hit:
                rep.err(where, f"第 {lineno} 行出现过程叙述「{hit}」："
                                f"写结论（「实测得到 X」），不要写核对过程")

    # [引用] 交叉引用必须存在于 PLAN
    plan_ch = ctx["plan_chapters"]
    for ref in re.findall(r"第\s*(\d+\.\d+(?:\.\d+)?)\s*节", text):
        chap = ".".join(ref.split(".")[:2])
        if chap not in plan_ch:
            rep.err(where, f"交叉引用「第 {ref} 节」指向不存在的章 {chap}")
    # 只校验「章范围」。
    # 不能把正文里的小节范围（如延伸阅读写法「1.6.9–1.6.10」）当章范围：
    # 那会误报，而且 1.5 的「1.5.1–1.5.7」因为第 5 篇恰好有 5.1–5.7 而「碰巧通过」——
    # 假绿灯比报错更危险。判定依据：后面紧跟「节/章」，或前面是「第」。
    for m in re.finditer(r"(\d+\.\d+)\s*[\u2013\u2014-]\s*(\d+\.\d+)", text):
        after = text[m.end():m.end() + 2]
        before = text[max(0, m.start() - 2):m.start()]
        if not ("节" in after or "章" in after or "第" in before):
            continue
        for x in (m.group(1), m.group(2)):
            if x not in plan_ch:
                rep.err(where, f"范围引用中的 {x} 在 PLAN.md 中不存在")
    for a, b in re.findall(r"第\s*(\d+)\s*[\u2013\u2014-]\s*(\d+)\s*篇", text):
        for x in (a, b):
            if int(x) not in ctx["plan_parts"]:
                rep.err(where, f"篇引用「第 {x} 篇」在 PLAN.md 中未启用")

    # [链接] 必须登记在 REFERENCES.md
    # 代码块与行内代码里的 URL 是「数据」（如 license_info 里的地址、示例域名），
    # 不是「出处」——把它们也拉进来登记，会逼着清单收录一堆与权威性无关的链接。
    # 因此与标点检查一致，先剔除代码，再抽 URL。
    prose_for_links = re.sub(r"```.*?```", "", text, flags=re.S)
    prose_for_links = re.sub(r"`[^`]*`", "", prose_for_links)
    urls = re.findall(r"https?://[^\s|)\]\uff0c\u3002]+", prose_for_links)
    refs = ctx["refs"]
    for u in urls:
        # 本地地址（开发服务器）不是“出处”，无需登记；
        # example.com / .invalid 是 RFC 2606 保留的示例域名，代码里当占位符用，也不是出处。
        if re.search(r"(127\.0\.0\.1|localhost|0\.0\.0\.0)", u):
            continue
        if re.search(r"\bexample\.(com|org|net)|\bexample\.invalid\b", u):
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
    code_lines = code_lines_of(text)
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
            if in_fence:
                continue
            if heading.match(ln):
                if i > 0 and lines[i - 1].strip():
                    rep.err(f.name, f"第 {i + 1} 行标题「{ln[:24]}」前缺少空行")
                continue
            # 标题被粘在上一行末尾（用脚本回填台账时最容易出）：
            # `| … | ✅ |### 1.11 依赖注入与中间件`。行首不是 #，所以上面那条规则
            # 完全看不到它——渲染后标题变成表格里的一串文字，而且把它当“小节”的
            # 台账会静默归属到上一章（本轮就是这么发现的）。用 `### 1.11` 这种
            # 「# 号 + 章号」的形状判定，不会误伤 `C# 语言` 这类正文。
            if re.search(r"#{2,6}\s*\d+\.\d+", ln):
                rep.err(f.name, f"第 {i + 1} 行里粘着一个标题（前缺少空行）：「{ln[-32:]}")


def build_book_index() -> tuple[set[str], dict[str, set[str]]]:
    """扫描 book/ 已有正文，返回（有正文的章号，{章号: {小节号}}）。

    交叉引用可能指向**别的章**（「详见 1.12」写在第 1.15 章里），所以索引必须扫全书，
    不能只看本次校验的章。
    """
    body: set[str] = set()
    secs: dict[str, set[str]] = defaultdict(set)
    for f in BOOK.rglob("*.md"):
        m = re.match(r"(\d+\.\d+)-(.*)\.md$", f.name)
        if not m:
            continue
        cid = m.group(1)
        body.add(cid)
        text = f.read_text(encoding="utf-8", errors="replace")
        secs[cid] |= set(re.findall(r"^##\s+(\d+\.\d+\.\d+)", text, re.M))
    return body, secs


def _is_section_ref(prose: str, m: re.Match, strict: bool) -> bool:
    """判断一个 x.y.z / x.y 记号是不是**交叉引用**，而不是版本号。

    strict=True 用于两段式记号（`1.14`）：它和常见版本号（`3.11`、`2.10`）无法仅凭
    上下文区分，只认「第 … 节」「见 …」「（…）」三种明确写法。
    三段式（`1.14.9`）的误报率实测为 0，因此允许中文语境前缀（「与 1.12.3」「接 1.13.5」）。
    """
    pre = prose[:m.start()]
    suf = prose[m.end():]
    if suf.startswith(("节", "章")):
        return True
    if pre.rstrip()[-1:] == "第" or pre.rstrip()[-2:] in ("详见", "参见", "参照"):
        return True
    if pre.rstrip()[-1:] == "见":
        return True
    if not strict:
        # 只对三段式（`（1.12.3）`）认这个写法：两段式的括号里几乎都是版本号
        # （「PyJWT 的类型校验（2.10）」），而版本号与「章号」在字面上无法区分。
        wrapped = pre.rstrip()[-1:] in "（(" and suf.startswith(("）", ")"))
        if wrapped:
            # `Python（3.11.9）`：括号前是产品名 → 版本号，不是引用
            before = pre.rstrip()[:-1]
            if re.search(r"[A-Za-z0-9][\w.\- ]*$", before):
                return False
            return True
    if strict:
        return False
    tail = pre.rstrip()[-1:]
    if tail in REF_SOFT_PREFIX:
        # `本书统一按 3.11+ 执行`：前缀是「按」且后面跟 +/- → 版本号
        if suf[:1] in ("+", "-") and re.search(r"\d$", pre.rstrip()[:-1]):
            return False
        return True
    return False


def check_cross_refs(chapters: dict[str, str], rep: Report) -> None:
    """章内交叉引用必须真实存在。

    已有的引用校验只查到「章」这一级（且只认「第 x.y 节」写法）。改编号、拆章节之后
    最容易悄悄坏掉的正是**小节级**引用——「详见 1.14.6」在 1.14 只剩 5 节时就悬空了，
    而正文渲染出来看不出任何异常。这里把两种粒度的引用都落到真实标题上。
    """
    plan_ch = load_plan_chapters()
    body, secs = build_book_index()
    for cid, text in chapters.items():
        prose = re.sub(r"```.*?```", "", text, flags=re.S)
        for m in SEC_REF.finditer(prose):
            ref = m.group(1)
            chap = ".".join(ref.split(".")[:2])
            if chap not in plan_ch or not _is_section_ref(prose, m, strict=False):
                continue
            # `1.6.0`、`3.11.0` 这类第三段为 0 的记号是版本号：本书小节从 1 开始编号。
            if ref.endswith(".0"):
                continue
            # 只在目标章**已有正文**时才能判定小节是否存在：
            # 预告尚未开写的章（）“详见 6.3.2”）不是错误，只是此刻无法校验。
            if chap in body and ref not in secs.get(chap, set()):
                rep.err(cid, f"交叉引用「{ref}」悬空：{chap} 中没有这一小节")
        for m in CHAP_REF.finditer(prose):
            ref = m.group(1)
            if not _is_section_ref(prose, m, strict=True):
                continue
            if ref not in plan_ch:
                rep.err(cid, f"交叉引用「{ref}」悬空：PLAN.md 中没有这一章")
            # 指向「还没写的章」不报警：这是**正常的前置铺垫**
            # （1.4 讲重试装饰器时预告 6.3，1.2 讲推导式时预告 6.2），
            # 全书写完之前这类引用本来就该存在。报警器一旦吵，就没人看了。


def check_ledger_landings(rep: Report) -> None:
    """台账反向核对：每条 `✅` 的落点必须能在正文里指到真实位置。

    台账最容易出现的一种假绿灯是：知识点标了 `✅`，落点也填了，但**那一节并不存在**
    （章节拆分/改编号后落点没跟着改）。这类行只有把落点逐个解析出来才对得上，
    靠人翻 600 多条是不可能的。
    """
    if not LEDGER.exists():
        return
    plan_ch = load_plan_chapters()
    body, secs = build_book_index()
    current = None
    # 先把「粘在行尾的标题」拆出来，否则它们后面的行会被静默算到上一章头上，
    # 报错信息里的章号就是错的。这种形状本身由 check_blank_lines 报错。
    ledger_text = re.sub(r"^(\|.*?\S)###\s+(?=\d+\.\d+)", r"\1\n\n### ",
                         LEDGER.read_text(encoding="utf-8"), flags=re.M)
    for ln in ledger_text.splitlines():
        if ln.startswith("### "):
            m = re.match(r"###\s+(\d+\.\d+)", ln)
            current = m.group(1) if m else None
            continue
        if ln.startswith("## "):
            current = None
            continue
        if current is None or not ln.startswith("|") or "---" in ln:
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) < 3:
            continue
        landing, status = cells[-2], cells[-1]
        if landing in ("落点", "正文落点", "计划落点"):
            continue
        sym = next((s for s in LEDGER_SYMBOLS if s in status), None)
        if sym is None:
            continue
        where = f"台账 {current}"
        sec_refs = SEC_REF.findall(landing)
        chap_refs = CHAP_REF.findall(landing)
        for ref in sec_refs:
            chap = ".".join(ref.split(".")[:2])
            # 同上：目标章还没开写时不判小节存在性（否则预置的「归位行」会被误报）
            if chap in body and ref not in secs.get(chap, set()):
                rep.err(where, f"落点「{ref}」不存在"
                               f"（{cells[0][:18]}…）")
        for ref in chap_refs:
            if ref not in plan_ch:
                rep.err(where, f"落点「{ref}」不在 PLAN.md 中（{cells[0][:18]}…）")
        if sym == "✅":
            refs = sec_refs + chap_refs
            if not refs and not any(w in landing for w in LANDING_WORDS):
                rep.err(where, f"标了 ✅ 但落点无法定位：「{landing[:24]}」（{cells[0][:18]}…）")
            elif refs:
                # 只在落点指向的章**真实存在**时才问「有没有正文」：
                # 章号不存在已经报过了，再报一条“没正文”只是重复。
                chaps = [".".join(x.split(".")[:2]) for x in refs]
                known = [c for c in chaps if c in plan_ch]
                if known and not any(c in body for c in known):
                    rep.err(where, f"标了 ✅ 但落点的章都还没有正文（{cells[0][:18]}…）")


def split_cells(row: str) -> list[str]:
    """按单元格切分表格行，**跳过反引号里的竖线与转义竖线**。

    台账里 `Mapped[int \\| None]`、`int | str` 这类写法很常见：
    直接 `row.split("|")` 会把一格切成两格，状态格就跑到前面去了。
    """
    cells, cur, in_code = [], "", False
    for ch in row.strip().strip("|"):
        if ch == "`":
            in_code = not in_code
            cur += ch
        elif ch == "|" and not in_code and not cur.endswith("\\"):
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
    cells.append(cur.strip())
    return cells


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
        # 状态只看**最后一格的开头**，不数整行里出现的符号。
        # 原因：说明文字里提到状态符号是常事（例如「既没落点也没标 ⏭」），
        # 而按整行计数会把它当成一条「有意省略」——本表自己就踩过一次。
        cells = split_cells(ln)
        m2 = re.match(r"([✅🔀⏭⬜])", cells[-1]) if cells else None
        if m2:
            per_part[part][("✅", "🔀", "⏭", "⬜").index(m2.group(1))] += 1
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

    # 「篇级进度」表是**手写**的汇总，最容易漂——本轮就填错过一次：手写 287，
    # 脚本实数是 286。所以这里按**表头定位列**逐个对账（加列、调列序都不会错位），
    # 缺列则跳过（表结构还没加就当作不知道，不报错）。
    in_progress = False
    cols: dict[str, int] = {}
    for ln in LEDGER.read_text(encoding="utf-8").splitlines():
        if ln.startswith("## ") and "篇级进度" in ln:
            in_progress = True
            continue
        if in_progress and ln.startswith("## "):
            break
        if not in_progress or not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if "已落点" in "".join(cells):
            for i, c in enumerate(cells):
                for sym in ("✅", "🔀", "⏭", "⬜"):
                    if c.startswith(f"`{sym}`"):
                        cols[sym] = i
            continue
        if not cols:
            continue
        m = re.match(r"^第\s*(\d+)\s*篇$", cells[0].strip("`*"))
        if not m:
            continue
        key = f"第 {int(m.group(1))} 篇"
        if key not in per_part:
            continue
        for sym, idx in cols.items():
            if idx >= len(cells):
                continue
            got = re.match(r"^(\d+)", cells[idx])
            if not got:
                continue
            want = per_part[key][("✅", "🔀", "⏭", "⬜").index(sym)]
            if int(got.group(1)) != want:
                rep.err("台账", f"LEDGER 篇级进度 {key}：{sym} 写 {got.group(1)} ≠ 实测 {want}")


# ---------------- 自检（--self-test） ----------------
# code_lines_of 是本书所有字数数字的单一输入，而它的判定要认三种围栏形态
# （裸行、引用块里的 `> ``` `、列表项里的缩进围栏）。这类口径一旦退化，
# **输出看上去仍然正常**，只是每章静默少减/多减两行——正是 2026-09-13 那次
# 虚增 20,130 字的形态。所以用夹具把三态钉住，并附一条应当保持沉默的反例。
_CODE_LINE_CASES = [
    ("普通围栏", "```python\nx = 1\ny = 2\n```", 2),
    ("无语言标记", "```\nls -la\n```", 1),
    ("引用块内的围栏（1.14 形态）", "> ```bash\n> echo hi\n> ```", 1),
    ("列表项内缩进的围栏（2.5 形态）", "- 步骤：\n   ```python\n   x = 1\n   ```", 1),
    ("块内空行不算", "```python\nx = 1\n\ny = 2\n```", 2),
    ("前后有正文时只数块内", "说明：\n```python\nx = 1\n```\n结束。", 1),
    ("空围栏：一行内容都没有", "```\n```", 0),
    ("行内代码不是围栏（应保持沉默）", "用 `` `code` `` 这样写", 0),
]


def self_test() -> int:
    ok = 0
    for name, text, want in _CODE_LINE_CASES:
        got = len(code_lines_of(text))
        if got == want:
            ok += 1
        else:
            print(f"  ✖ {name}：期望 {want} 行，实得 {got} 行")
    print(f"自检：{ok}/{len(_CODE_LINE_CASES)} 通过")
    return 0 if ok == len(_CODE_LINE_CASES) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="正文一致性校验")
    ap.add_argument("--only", help="只校验指定章，例如 1.1")
    ap.add_argument("--quiet", action="store_true", help="只打印问题")
    ap.add_argument("--self-test", action="store_true", help="只跑字数口径的自检")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

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
            # PLAN.md 的「✅ N 字」一律取这里的**有效字数**（不是汉字数）——
            # 这行注释曾写成「取汉字数」而与实现相反，是又一处「注释与代码各说各话」。
            # 代码行占比用来解释「为什么汉字比计划少并不等于偷工减料」。
            code = code_lines_of(text)
            effective = n + CODE_LINE_EQUIV * len(code)
            planned = ctx["plan_chapters"].get(cid)
            tail = f" / 计划 {planned}（达成 {effective / planned:.0%}）" if planned else ""
            print(f"  {f.name}  有效字数 {effective}（汉字 {n} + 代码 {len(code)} 行）{tail}")

    check_duplicates(chapters, rep)
    check_blank_lines(rep)
    check_cross_refs(chapters, rep)
    check_ledger_landings(rep)

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
