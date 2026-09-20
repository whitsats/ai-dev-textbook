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
    [接线]  第 3 篇每章必须有「知舟接线」小节，且四问小标题逐字齐全（依据 PROJECT.md）
    [术语]  GLOSSARY.md 的维护记录与术语表逐章对账（有词条的章必须有一行、每行必须三格）

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
PROJECT = ROOT / "PROJECT.md"
STYLE = ROOT / "STYLE.md"

# 所有章节都必须有的小节；「前置知识」仅第 1 篇及以后要求
REQUIRED_ALWAYS = ["本章导读", "## 学习目标", "## 本章小结", "## 延伸阅读"]
REQUIRED_NON_INTRO = ["## 前置知识", "## 常见坑", "## 面试视角", "## 练习"]

# 第 3 篇专属：每章要有「知舟接线」小节，且四个固定小标题逐字齐全。
# 起因：STYLE 第五节把「智能问答 ＋ Agent 工具调用」归给第 3、4 篇，
# 而 3.1–3.4 定稿时正文里「知舟」出现 0 次——学生读完 10 万字手里没有交付物。
# 契约（文件、端点、验收标准）见 PROJECT.md；其第六节进度表同时是**回填台账**：
# 标了「待回填」的章只报警告，没标的章缺一节就是错误。
WIRING_PART = "03"
# 小节标题形式：`## <章号>.<n> 知舟接线`（与正文其他 H2 一样带章内编号，
# 这样台账里写落点 3.4.9 能解析到真实小节）。只写 `## 知舟接线` 会被判缺失。
WIRING_HEAD = re.compile(r"^##\s*\d+\.\d+\.\d+\s*知舟接线", re.M)
_W_HEAD = "## 3.4.9 知舟接线\n"
WIRING_SUBS = ["### 加了什么", "### 接口契约", "### 怎么验", "### 不能破坏什么"]

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
# 围栏标记：` ```python `，也允许**语言后面再缀一段标注**——体例里的输出块就是这种：
# ` ```text $ python scripts/x.py --offline `（`STYLE` 三·6，`check_runnable` 的第八道靠它重跑）。
# 2026-09-17 之前这里只允许语言本身，于是带上标注的那一行**不被当成开围栏**，
# 反而被当成一条代码行：5.3–5.9 与 4.5 共 28 个标注块，每块凭空多算 15 有效字（合计 +420），
# 而 `lint` 与 `audit --check` 只会在章节字数上悄悄漂——**改一处体例，量它的那把尺子要一起改**。
_FENCE = re.compile(r"^[\s>]*```[A-Za-z0-9_+.-]*(?:\s+\$\s+\S.*)?\s*$")


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


def plan_lookup_issue(cid: str, plan: dict[str, int]) -> str:
    """章号在 PLAN 的章节表里解析不到时要报的那句话。**返回非空就必须报错。**

    为什么把它抽成一个函数：这个判定必须能被自检覆盖。原先是写在 `check_chapter`
    里的一句 `if planned:`——它读起来完全合理，但「`planned` 是 `None`」那条分支
    什么都不做，而 `None` 恰好是「PLAN 里那一行不见了」的信号。
    """
    if cid not in plan:
        return (f"PLAN.md 的章节表里没有 {cid} 这一行（计划字数解析不到）——"
                f"本章因此拿不到篇幅判定，且汇总数字会少掉一章")
    return ""


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
    # **解析不到计划值必须报错，不能静默跳过。**
    # 起因是一次真事故：PLAN 的 4.3 那一行被一次替换误删了（旧字符串恰好是新行的**前缀**），
    # 于是这一章的「篇幅」检查整段消失——输出里只有一行没有「/ 计划 N」的数字，
    # 与「这一章不参与篇幅校验」长得一模一样。同一族的漏账在本文件里已经出现过三次
    # （测试清单写死、路径范围漏 `scripts/`、离线入口只写第一个），第四次修在这里。
    missing = plan_lookup_issue(cid, plan_ch)
    if missing:
        rep.err(where, missing)
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


def wiring_issues(text: str, in_backlog: bool) -> tuple[list[str], list[str]]:
    """返回 (错误, 警告)。抽成纯函数是为了能用夹具钉住三个分支。"""
    missing: list[str] = []
    if not WIRING_HEAD.search(text):
        missing.append("小节标题（应为 `## <章号>.N 知舟接线`）")
    missing += [s.removeprefix("### ") for s in WIRING_SUBS if s not in text]
    if not missing:
        return [], []
    msg = "缺「知舟接线」小节：" + "、".join(missing)
    return ([], [msg]) if in_backlog else ([msg], [])


def wiring_backlog() -> set[str]:
    """PROJECT.md 第六节进度表里标了「待回填」的章号（回填完就从表里消失）。"""
    if not PROJECT.exists():
        return set()
    out: set[str] = set()
    for ln in PROJECT.read_text(encoding="utf-8").splitlines():
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) < 4 or not re.fullmatch(r"\d+\.\d+", cells[0]):
            continue
        # 扫整行而不是某一列：这个记号有时写在「代码实跑」列，有时写在「备注」列，
        # 只读一列会把「已登记的回填待办」当成「没登记」，于是误报成错误（本轮踩过一次）。
        if any("待回填" in c for c in cells):
            out.add(cells[0])
    return out


def check_project_wiring(rep: Report) -> None:
    if not PROJECT.exists():
        rep.err("接线", "缺少 PROJECT.md：它是第 3 篇各章写作与验收的依据，不能缺")
        return
    backlog = wiring_backlog()
    for f in sorted(BOOK.glob(f"{WIRING_PART}-*/*.md")):
        if not re.match(r"\d+\.\d+-", f.name):
            continue
        cid = f.name.split("-", 1)[0]
        errs, warns = wiring_issues(f.read_text(encoding="utf-8"), cid in backlog)
        for m in errs:
            rep.err("接线", f"{cid}：{m}（第 3 篇必须按 PROJECT.md 的四问写）")
        for m in warns:
            rep.warn("接线", f"{cid}：{m}（PROJECT.md 记为待回填，写好即从台账划掉）")


# ---------------- 「第 N 个实测」的引用闭环 ----------------
# 起因是一次真事故：5.3 的台账写着「两条写进 STYLE 8.7 第十七个实测的修因」，
# 而 STYLE 8.7 里根本没有第十七个（当时最后一条是第十六个）。5.1／5.2 那一轮
# 也出现过同一条指向空处的引用，那次是人工核出来的。
# 这类引用最阴的地方在于**它不产生任何数字**：篇幅对账、台账计数、可运行树三关
# 都不会响——与 2.3 那次「整块没记账」同族，都是「没有任何数字与它对不上」。
_ORD = "〇一二三四五六七八九十百"
_ORD_RE = re.compile(rf"第([{_ORD}]+)个")
_MEASURE_WINDOW = 45
# 窗口只解决「多远算同一句话」，管不了「这个序数算不算在说实测」。8.1 的实测里
# 有一句「备查的第二个数按第 7 篇五章合计比值 0.912 折出 ≈ 9,700，而实测 10,434」
# ——「第二个」离「实测」只有十几个字，窗口法把它当成了一条引用，而 STYLE 8.7 里
# 并没有第二条实测。所以序数与「实测」之间**只允许出现连接词与另一个序数**：
# 「第十五个与第十六个实测」的前一个要收，「第二个数…实测」的那个不能收。
# 括号里夹的限定语（「第十七个「成对引用」实测」）算连写，散文夹的字（「第二个数…实测」）不算。
_CHAIN_RE = re.compile(
    rf"(?:[与和、，／/及]|第[{_ORD}]+个|[「『（(【][^」』）)】]*[」』）)】])*\s*")


def measurement_refs(text: str) -> set[str]:
    """文本里引用了哪些「第 X 个实测」。

    只在「实测」二字前面取一小段窗口：正文里正常的「本章实测 13,326 有效字」
    不会被误收（它前面那一段里没有「第 X 个」）。窗口取 45 字是为了容下
    「见第十五个与第十六个实测」这种成对引用——两个序数都要收。
    而窗口里每一个序数还要过一遍**邻接判据**（见 `_CHAIN_RE`）：
    序数与「实测」之间只许有连接词或另一个序数，中间夹了解释性文字的
    （「第二个数」）不算引用。
    """
    out: set[str] = set()
    for m in re.finditer("实测", text):
        start = max(0, m.start() - _MEASURE_WINDOW)
        for om in _ORD_RE.finditer(text[start:m.start()]):
            if _CHAIN_RE.fullmatch(text[start + om.end():m.start()]):
                out.add(om.group(1))
    return out


def measurement_defs(style_text: str) -> set[str]:
    """STYLE 8.7 里真正写了的那几条实测（定义行形态：`- **第十五个实测（…`）。"""
    return set(re.findall(rf"(?m)^\s*-\s*\*\*第([{_ORD}]+)个实测", style_text))


def measurement_issues(style_text: str, others: dict[str, str]) -> list[str]:
    defs = measurement_defs(style_text)
    out: list[str] = []
    for name, text in [("STYLE.md", style_text), *others.items()]:
        for ord_ in sorted(measurement_refs(text) - defs):
            out.append(f"{name} 引用了「第{ord_}个实测」，但 STYLE 8.7 里没有这一条")
    return out


def check_measurement_refs(rep: Report) -> None:
    if not STYLE.exists():
        rep.err("篇幅实测", "缺少 STYLE.md：篇幅估算的依据全在那里，不能缺")
        return
    others = {p.name: p.read_text(encoding="utf-8")
              for p in (LEDGER, PLAN, PROJECT, ROOT / "GAPS.md") if p.exists()}
    for m in measurement_issues(STYLE.read_text(encoding="utf-8"), others):
        rep.err("篇幅实测", f"{m}（要么补上那一条，要么把引用改到真实存在的那一条）")


# ---------------- 术语表 ↔ 维护日志的对账（GLOSSARY.md） ----------------
# 为什么需要这一关：「三、维护记录」是**手写的第二份清单**（STYLE 8.8 第 7 条），
# 而它此前没有任何机器核过。2026-09-17 核了一遍，三类问题各有一例：
#   · 有词条、没有行：日志 32 行覆盖不到 1.12 / 2.1 / 2.6 / 3.1 / 5.6 五章；
#   · 少一个换行、一行被粘进上一行：3.6（原因格被吞成空）与 5.2（整行丢失）都中过；
#   · 5.8 那一处是当轮自己造的，同一种形态。
# 而当时 `--self-test` 20/20、397 条禁词全过、错误 0 警告 0——因为所有检查都不解析
# 这张表。所以这里补的正是「它到底逐到了几条」那一问（同 8.8 第 5 条的反向守）。
#
# 判定规则收紧过一次，为的是**不漏报**（漏报与乱报都真犯过）：
#   · 不按「整行里出现章号」判——那样 2.1 / 3.1 / 5.6 会被别行的顺带提法掩盖
#     （5.6 只在 5.1 那行的「一跑就打到 5.6 与 6.x 的正文」里露过面），
#     而 0.2 又靠一条顺带提法侥幸通过；
#   · 章号只认**原因格开头那一句**——那是本表既有的声明位置（32 行里 29 行以
#     「N.N 写…前定口径」开头），顺带提法一律不算；小节号（`3.1.10`）按它所属的章算；
#   · 篇级声明只认写明了「完稿」的篇（第 0 篇那 20 个词就登在「建立本表」那一行，
#     它的原因格写的是「第 0 篇完稿」）；「第 1 篇开写前统一口径」不认——
#     认了会把 1.12 的缺口一并盖住。
GLOSS_SECTION = "维护记录"
GLOSS_LOG_COLS = ("日期", "变更", "原因")
_GLOSS_SEC_RE = re.compile(r"^##\s*[^\n]*" + GLOSS_SECTION + r"\s*$")
# 「第 P 篇完稿 / 已定稿」才算篇级声明（`第 1 篇开写前统一口径` 不算）
_GLOSS_PART_DONE = re.compile(r"第\s*(\d+)\s*篇(?:完稿|已定稿)")
# 小节号 → 章号：`3.1.10` 记的是 **3.1**（台账落点回查用的是同一套近似）
_SECTION_TO_CHAP = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2})\.\d{1,3}(?![\d.])")


def glossary_term_chapters(text: str) -> dict[str, list[str]]:
    """GLOSSARY 术语表里 {首次出现的章号: 该章的词条名}（按表中顺序）。

    括号注解先剥掉：`0.1（展开于 5.4）` 记的是 **0.1**（5.4 有它自己那批行）。
    与 `load_glossary()` 同一口径：只读 LINT:TERMS 标记之间的表。
    """
    out: dict[str, list[str]] = {}
    m = re.search(r"LINT:TERMS:BEGIN(.*?)LINT:TERMS:END", text, re.S)
    if not m:
        return out
    for line in m.group(1).splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4 or cells[0] == "首选写法":
            continue
        for cid in CHAP_REF.findall(re.sub(r"（[^）]*）", "", cells[3])):
            out.setdefault(cid, []).append(cells[0])
    return out


def glossary_log_rows(text: str) -> list[tuple[int, list[str]]]:
    """「三、维护记录」表的数据行：[(行号, 单元格), ...]（表头与分隔行不算）。

    必须圈定在这张小节内：第二节「固定指代」也是表，但只有两格——不圈范围的话，
    它会被同一个判定当成两种东西各报一次。
    """
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("##") and _GLOSS_SEC_RE.match(ln.strip()):
            start = i + 1
            break
    if start is None:
        return []
    rows: list[tuple[int, list[str]]] = []
    for i in range(start, len(lines)):
        ln = lines[i]
        if ln.startswith("## "):
            break
        if not ln.startswith("|"):
            continue
        cells = split_cells(ln)
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append((i + 1, cells))
    return [r for r in rows if [c.strip("*") for c in r[1]] != list(GLOSS_LOG_COLS)]


def glossary_log_issues(text: str, written: set[str]) -> list[str]:
    """术语表与维护日志的对账问题。抽成纯函数是为了能用夹具钉住每个分支。

    三类问题各自对应一次真实事故：
      ① 有词条的章没有一行在给它登记（1.12 / 2.1 / 2.6 / 3.1 / 5.6 五处）；
      ② 行被粘坏——格数不为 3，或有一格被吞成空（3.6 / 5.2 / 5.8 三次）；
      ③ 两个反向守：日志一行都没解析到、术语表一个章号都没解析到。没有它们，
         解析一旦退化，输出会是「全部通过」——与 `check_runnable` 里
         「一个代码块都没解析到」是同一类静默失败（STYLE 8.8 第 5 条）。

    `written` 是**已有正文**的章号：只对它们提要求。第 6 篇的 6.1 / 6.3 已按
    「先登记再写」提前登记、正文还没落地，这一步不要求日志行；正文一写出来，
    要求自动生效（同 `check_ledger` 只对已有正文的篇要求台账）。
    """
    issues: list[str] = []
    rows = glossary_log_rows(text)
    term_chaps = glossary_term_chapters(text)
    if not term_chaps:
        issues.append("术语表里一个章号都没解析到——LINT:TERMS 标记、表头或「首次出现」列"
                      "是不是被改坏了？（解析退化时，这一关会静默变成「全部通过」）")
    if not rows:
        issues.append("「三、维护记录」里一行数据都没解析到——小节标题、表头或分隔行"
                      "（`| --- | --- | --- |`）是不是被改坏了？")
        return issues
    for lineno, cells in rows:
        if len(cells) != len(GLOSS_LOG_COLS):
            issues.append(
                f"维护记录第 {lineno} 行有 {len(cells)} 格，应为 {len(GLOSS_LOG_COLS)} 格"
                f"（{'/'.join(GLOSS_LOG_COLS)}）——多半是上一行结尾少了一个换行、"
                f"这一行被粘了进去（3.6、5.2、5.8 三次都是这个形态）")
            continue
        for name, cell in zip(GLOSS_LOG_COLS, cells):
            if not cell:
                issues.append(f"维护记录第 {lineno} 行的「{name}」格是空的——粘行时"
                              f"多半把这一格吞掉了（3.6 那次就是「原因」格被吞成空）")
    covered: set[str] = set()
    for _lineno, cells in rows:
        if len(cells) != len(GLOSS_LOG_COLS):
            continue  # 格数都不对，它声明了什么不可信（上面已经报过）
        head = re.split(r"。", cells[2])[0]          # 只读「原因」格的开头一句
        covered |= set(CHAP_REF.findall(_SECTION_TO_CHAP.sub(r"\1", head)))
        for part in _GLOSS_PART_DONE.findall(" ".join(cells)):
            covered |= {c for c in term_chaps if c.split(".")[0] == str(int(part))}
    for cid in sorted(term_chaps, key=lambda c: tuple(int(x) for x in c.split("."))):
        if cid not in written or cid in covered:
            continue
        names = term_chaps[cid]
        issues.append(f"术语表里有 {cid} 的 {len(names)} 个词条（如「{names[0]}」），"
                      f"但「三、维护记录」里没有一行在给它登记（原因格开头没有 {cid}）——"
                      f"补一行，别指望别处的顺带提法算数")
    return issues


def check_glossary_log(rep: Report) -> None:
    if not GLOSSARY.exists():
        rep.err("术语日志", "缺少 GLOSSARY.md：它是全书术语的唯一事实来源，不能缺")
        return
    text = GLOSSARY.read_text(encoding="utf-8")
    written = {f.name.split("-", 1)[0] for f in chapter_files(None)}
    term_chaps = glossary_term_chapters(text)
    rows = glossary_log_rows(text)
    print(f"术语日志 GLOSSARY.md：维护记录 {len(rows)} 行 ｜ 词条覆盖 {len(term_chaps)} 章"
          f"（其中已有正文 {len(set(term_chaps) & written)} 章）")
    for m in glossary_log_issues(text, written):
        rep.err("术语日志", m)


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
    ("带命令标注的输出块（`text $ python …`）：标注行不算代码行",
     "```text $ python scripts/x.py --offline\n一读数\n二读数\n```", 2),
    ("语言后面的非 `$` 标注不当围栏（宁可不认，也不要多算一行）",
     "```text 这一段是模型输出\n一\n```", 2),
]

# [计划行] 夹具：**PLAN 里那一行不见了** vs 在册。
# 这一条在真事故之后补：4.3 的 PLAN 行被一次替换误删（旧字符串恰好是新行的前缀），
# 而当时的输出是「没有报错、也没有数字」——与「这一章不参与篇幅校验」无法区分。
# 反向守的意义与 `check_runnable` 里那条「一个块都没解析到就报错」相同：
# **所有「逐条校验」的工具，都要有一个用例问「它到底逐到了几条」。**
_PLAN_CASES = [
    ("章号不在 PLAN（那一行被误删）", "4.3", {"4.1": 7000, "4.2": 7000}, True),
    ("章号在册", "4.3", {"4.3": 7000}, False),
]


# [接线] 检查的三个分支：齐了要沉默、缺了要报错、在回填台账里只警告。
# 前两条是「不响」与「乱响」各一侧，第三条防的是「把待办改成永久豁免」。
# 夹具用真换行拼接（写成字面 `\n` 时四个子串仍然都在，测试会照旧全绿——
# 对形状不敏感的夹具等于没有夹具，所以这里必须拼接成真正的多行文本）。
_WIRING_CASES = [
    ("标题带编号且四问齐全应沉默", _W_HEAD + "\n".join(WIRING_SUBS), False, (0, 0)),
    ("标题不带编号：也算缺", "## 知舟接线\n" + "\n".join(WIRING_SUBS), False, (1, 0)),
    ("缺一节且不在台账：报错", _W_HEAD + "### 加了什么\n### 接口契约", False, (1, 0)),
    ("缺一节但在回填台账：只警告", _W_HEAD + "### 加了什么\n### 接口契约", True, (0, 1)),
    ("完全没有小节且不在台账：报错", "## 3.9 别的章", False, (1, 0)),
]


# [实测编号] 夹具：**引用了不存在的那一条** vs 在册。带三个「应沉默」的分支
# 与一个「必须拦」的分支，另加一条「正文里的实测不带序数」的沉默用例——
# 报警器一旦会对无关文本响，就会被绕过（同 check_refs 里「超时」那一档的教训）。
_MEASURE_CASES = [
    ("引用了不存在的编号：要拦",
     "- **第六个实测（`3.1`）：…**\n", "见第十七个实测。", 1),
    ("定义与引用都在册：沉默",
     "- **第六个实测（`3.1`）：…**\n", "见第六个实测。", 0),
    ("成对引用：两个都在册：沉默",
     "- **第十五个实测（`5.1`）：…**\n- **第十六个实测（`5.2`）：…**\n",
     "见第十五个与第十六个实测。", 0),
    ("成对引用：后一个不在册：只报那一个",
     "- **第十五个实测（`5.1`）：…**\n", "见第十五个与第十六个实测。", 1),
    ("正文里的实测不带序数：沉默",
     "- **第六个实测（`3.1`）：…**\n", "本章实测 13,326 有效字。", 0),
    # 8.1 的真实误报：序数之间夹了解释性文字，说的不是「第几个实测」。
    # 报警器一旦对这类文本响，八章之外就会有人开始「改正文来消警告」。
    ("「第二个数」不是一条实测引用：沉默",
     "- **第六个实测（`3.1`）：…**\n",
     "备查的第二个数按第 7 篇五章合计比值 0.912 折出 ≈ 9,700，而实测 10,434。", 0),
    ("夹了字的序数仍要报：拦",
     "- **第六个实测（`3.1`）：…**\n", "见第十七个「成对引用」实测。", 1),
]


# [术语日志] 夹具：**有词条的章没有登记行** vs 有；**行被粘成 4 格 / 格被吞成空** vs 3 格。
# 这一组里必须留着「顺带提法不算数」那条——5.6 当年就是靠 5.1 那行的顺带提法混过了人工核对，
# 报警器要是把「整行里出现过章号」当成登记，那道缺口会再躲一次；也不能少了「第 1 篇开写前
# 统一口径」那条（认了它，1.12 的缺口同样会被盖住）。
_GLOSS_DOC = ("<!-- LINT:TERMS:BEGIN -->\n"
              "| 首选写法 | 英文 | 避免的写法 | 首次出现 |\n"
              "| --- | --- | --- | --- |\n"
              "{terms}"
              "<!-- LINT:TERMS:END -->\n\n"
              "## 三、维护记录\n\n"
              "| 日期 | 变更 | 原因 |\n"
              "| --- | --- | --- |\n"
              "{log}")
_T_EVAL = "| 评测集 | Evaluation Set | 测试集 | 5.6 |\n"
_T_WATER = "| 水位线 | Water mark | 警戒水位、阈线 | 3.1 |\n"
_T_VECDB = "| 向量数据库 | Vector Database | 矢量数据库 | 1.12 |\n"
_T_LLM = "| 大语言模型 | Large Language Model, LLM | 大型语言模型 | 0.3 |\n"
_L_EVAL = "| 2026-09-16 | 补登 1 个术语（评测集） | 5.6 写评估前定口径 |\n"
_L_ASIDE = ("| 2026-09-16 | 补登 1 个术语（拒答） | 5.1 写 RAG 全景前定口径，**先登记再写**。"
            "「召回率」一跑就打到 5.6 与 6.x 的正文 |\n")
_L_OTHER = "| 2026-09-16 | 补登 1 个术语（拒答） | 5.1 写 RAG 全景前定口径，**先登记再写** |\n"
_L_PART0 = "| 2026-09-11 | 建立本表，登记 20 个术语 | 第 0 篇完稿，第 1 篇开写前统一口径 |\n"
_T_CORS = "| 跨域资源共享 | Cross-Origin Resource Sharing, CORS | 跨来源资源共享 | 1.8 |\n"
_L_CORS = ("| 2026-09-11 | 补登 5 个术语（CORS / 限流 / 洋葱模型 / 依赖覆盖 / 主机头） | "
           "1.11 写中间件前定口径；CORS 早在 1.8 出现却漏登，一并补上 |\n")
_GLOSS_LOG_CASES = [
    ("有词条也有登记行：沉默", _T_EVAL, _L_EVAL, {"5.6"}, 0),
    ("有词条却没有登记行：要拦", _T_EVAL, _L_OTHER, {"5.6"}, 1),
    ("只在别行的顺带提法里出现：仍要拦", _T_EVAL, _L_ASIDE, {"5.6"}, 1),
    ("章号在「原因」格开头那一句里：算登记（CORS 行的形态）", _T_CORS, _L_CORS, {"1.8"}, 0),
    ("小节号声明（3.1.10）算作 3.1 的行：沉默",
     _T_WATER, "| 2026-09-13 | 补登 1 个术语（水位线） | 3.1.10 的接线小节引入了这个词 |\n",
     {"3.1"}, 0),
    ("篇级行「第 0 篇完稿」覆盖该篇各章：沉默", _T_LLM, _L_PART0, {"0.3"}, 0),
    ("「第 1 篇开写前统一口径」不算登记：要拦", _T_VECDB, _L_PART0, {"1.12"}, 1),
    ("一行被粘成 4 格：要拦（前一行正常，只报这一行）",
     _T_EVAL, _L_EVAL + "| 2026-09-16 | 补登 1 个术语（评测集） | 5.6 写评估前定口径 | 2026-09-17 |\n",
     {"5.6"}, 1),
    ("一行只剩 2 格：要拦", _T_EVAL, _L_EVAL + "| 2026-09-16 | 补登 1 个术语（评测集） |\n",
     {"5.6"}, 1),
    ("「原因」格被吞成空：要拦", _T_EVAL,
     _L_EVAL + "| 2026-09-16 | 补登 1 个术语（评测集） |  |\n", {"5.6"}, 1),
    ("格数坏掉的行不拿它当登记：要拦（既报行也报缺登记）",
     _T_EVAL, "| 2026-09-16 | 补登 1 个术语（评测集） | 5.6 写评估前定口径 | 2026-09-17 |\n",
     {"5.6"}, 2),
    ("维护记录一行都没有：要拦（反向守）", _T_EVAL, "", {"5.6"}, 1),
    ("术语表一个章号都没有：要拦（反向守）", "| 评测集 | Evaluation Set | 测试集 | — |\n",
     _L_EVAL, {"5.6"}, 1),
    ("正文还没写出的章不要求登记行：沉默", _T_VECDB, _L_PART0, set(), 0),
]


def self_test() -> int:
    ok = 0
    for name, text, backlog, (we, ww) in _WIRING_CASES:
        errs, warns = wiring_issues(text, backlog)
        if (len(errs), len(warns)) == (we, ww):
            ok += 1
        else:
            print(f"  ✖ [接线] {name}：期望 错误{we}/警告{ww}，实得 错误{len(errs)}/警告{len(warns)}")
    for name, text, want in _CODE_LINE_CASES:
        got = len(code_lines_of(text))
        if got == want:
            ok += 1
        else:
            print(f"  ✖ {name}：期望 {want} 行，实得 {got} 行")
    for name, cid, plan, want_issue in _PLAN_CASES:
        got = bool(plan_lookup_issue(cid, plan))
        if got == want_issue:
            ok += 1
        else:
            print(f"  ✖ [计划行] {name}：期望{'报错' if want_issue else '不报错'}，"
                  f"实得{'报错' if got else '不报错'}")
    for name, style_text, refs_text, want in _MEASURE_CASES:
        got = len(measurement_issues(style_text, {"LEDGER.md": refs_text}))
        if got == want:
            ok += 1
        else:
            print(f"  ✖ [实测编号] {name}：期望 {want} 条问题，实得 {got} 条")
    for name, terms, log, written, want in _GLOSS_LOG_CASES:
        doc = _GLOSS_DOC.format(terms=terms, log=log)
        got = len(glossary_log_issues(doc, written))
        if got == want:
            ok += 1
        else:
            print(f"  ✖ [术语日志] {name}：期望 {want} 条问题，实得 {got} 条")
    total = (len(_WIRING_CASES) + len(_CODE_LINE_CASES) + len(_PLAN_CASES)
             + len(_MEASURE_CASES) + len(_GLOSS_LOG_CASES))
    print(f"自检：{ok}/{total} 通过")
    return 0 if ok == total else 1


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
    check_project_wiring(rep)
    check_measurement_refs(rep)

    print()
    print(f"校验章节 {len(files)} 章 ｜ 引用库 {len(ctx['refs'])} 条链接 ｜ 术语 {len(ctx['glossary'])} 条禁止写法")
    check_ledger(rep)
    check_glossary_log(rep)

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
