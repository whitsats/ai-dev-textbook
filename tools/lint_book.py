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
    [引用]  「小节级引用 N 处／章级引用 M 处／悬空 K 处」这几句（台账与正文）
            写了就必须与实跑相等（没写则沉默；引用旧值写成汉字）

退出码：存在「错误」时为 1，只有「警告」时为 0。
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import style_claims as sc         # noqa: E402 —— 书侧「N 条夹具」那句的登记式对账

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


def load_glossary_rows() -> list[dict[str, str]]:
    """解析 GLOSSARY.md 的术语表区间，返回 [{'preferred','en','avoid','first'}]。

    只解析 LINT:TERMS:BEGIN/END 之间的表格，避免把说明性表格当成术语。
    抽出来是因为 **同一份表现在有两处要读它**：本文件的禁词扫描（只要首选与避免列）
    与 `index_book.py` 的全书索引（要四列）。两处各写一个正则就是「手写的第二份清单」，
    而且它们一旦读法不同，就会出现「lint 认得、索引不认得」这种谁也发现不了的盯空。
    """
    rows: list[dict[str, str]] = []
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
        if len(cells) < 3 or cells[0] in ("首选写法", ""):
            continue
        rows.append({"preferred": cells[0],
                     "en": cells[1],
                     "avoid": cells[2],
                     "first": cells[3] if len(cells) > 3 else ""})
    return rows


def load_glossary() -> list[tuple[str, str]]:
    """返回 [(首选写法, 避免的写法), ...]。

    只解析 GLOSSARY.md 中 LINT:TERMS:BEGIN/END 标记之间的表格，
    避免把说明性表格（如维护记录的表头「原因」）当成术语。
    """
    rows: list[tuple[str, str]] = []
    for row in load_glossary_rows():
        preferred = row["preferred"]
        for bad in re.split(r"[、,，]", row["avoid"]):
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


# ---------------------------------------------------------------- 体例形状
# 十段式里有两处「曾经各有两个写法」，2026-09-22 定形后由这里守（口径见 `STYLE` 第二节）：
#   导读：一律 `## 本章导读` 小节（原来 53 章写成 `> **本章导读**：…`）；
#   练习：一律三级标签，按 基础 → 进阶 → 挑战 排列，且至少含「基础」与「进阶」两级。
# 这一层原来没人守，所以两个写法都「合法」——`REQUIRED_ALWAYS` 里只有「本章导读」四个字，
# 引用块与 `##` 小节都通过。逐章明细（形状普查）在 `tools/revisit.py`：它记账，这里判对错。
_SHAPE_LEVELS = ("基础", "进阶", "挑战")
_LEVEL_RANK = {k: i for i, k in enumerate(_SHAPE_LEVELS)}


def chapter_shape_issues(text: str) -> list[str]:
    """一章的导读与练习形状。返回非空就必须报错。"""
    issues: list[str] = []
    # 导读
    if not re.search(r"^##\s*本章导读\s*$", text, re.M):
        if re.search(r"^>\s*\*\*本章导读\*\*", text, re.M):
            issues.append("「本章导读」写成了引用块——导读一律写成 `## 本章导读` 小节")
        else:
            issues.append("没有 `## 本章导读` 小节")
    # 练习：只认「有内容」的小节——第 0 篇与求职篇允许裁剪它（`STYLE` 第二节的例外）
    m = re.search(r"^##\s*练习\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if m:
        body = m.group(1)
        items = re.findall(r"^- \*\*(基础|进阶|挑战)\*\*", body, re.M)
        # 「没带标签的条目」包括两种旧写法：顶层的 `- ` 与顶层的编号 `N. `
        # （1.9／1.10 是「分组小标题 ＋ 连续编号」，编号不在条目上）。
        loose = [ln for ln in body.splitlines()
                 if re.match(r"^(?:- |\d+\. )", ln)
                 and not re.match(r"^- \*\*(?:基础|进阶|挑战)\*\*", ln)]
        if loose:
            issues.append(f"练习里有 {len(loose)} 条没带三级标签"
                          "（每条都要以 `- **基础**：`／`- **进阶**：`／`- **挑战**：` 开头）")
        if not items:
            issues.append("练习里没有一条三级标签")
        else:
            ranks = [_LEVEL_RANK[x] for x in items]
            if ranks != sorted(ranks):
                issues.append("练习的级别顺序不是 基础 → 进阶 → 挑战")
            for need in ("基础", "进阶"):
                if need not in items:
                    issues.append(f"练习里没有「{need}」这一级（每章至少要有「基础」与「进阶」）")
    return issues


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

    # [体例] 形状（导读与练习；口径与判据见 `STYLE` 第二节）
    for issue in chapter_shape_issues(text):
        rep.err(where, issue)

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


# 引用复核的三个数（小节级／章级／悬空）由 `cross_ref_scan` 一处数出来，
# 汇总行里实报。为什么要它进门：篇收尾的「三件事」里有一项叫「引用复核」，
# 而它们（第 5 篇的 41 处、第 6 篇的 38 处＋1 处、第 8 篇的 214 处）
# 都是**人跑一次、手写一个数**——
# 正是 `STYLE` 8.11「写的是数，不是句子」要防的东西，却漏在射程外。
# 计数与报错共用同一份循环，所以「报错用的口径」与「抄进台账的那个数」不会各说各话。
REF_TALLY_KEYS = ("小节级", "章级", "悬空")


def cross_ref_scan(prose: str, plan_ch: dict[str, int], body: set[str],
                   secs: dict[str, set[str]]) -> tuple[dict[str, int], list[str]]:
    """扫一章正文，返回（{小节级, 章级, 悬空}, 逐条问题）。

    `prose` 是**已剔掉围栏**的正文（围栏里是逐字引用与代码，不是引用语境）。
    计数只算「被判成真引用」的记号：版本号（`3.11`、`1.6.0`）与裸数字既不计、也不报。
    悬空的定义与报错逐字一致：小节级引用指向的目标章**已有正文**却没有那一小节；
    章级引用在 PLAN 里找不到那一行。指向「还没写的章」不算悬空（那是正常的前置铺垫）。

    抽成纯函数是为了让这条口径能被夹具钉住：三个数一旦退化，汇总行照样打印一份
    看不出异常的数字，而它会被人抄进台账（那一格没有第二道检查）。
    """
    counts = dict.fromkeys(REF_TALLY_KEYS, 0)
    problems: list[str] = []
    for m in SEC_REF.finditer(prose):
        ref = m.group(1)
        chap = ".".join(ref.split(".")[:2])
        if chap not in plan_ch or not _is_section_ref(prose, m, strict=False):
            continue
        # `1.6.0`、`3.11.0` 这类第三段为 0 的记号是版本号：本书小节从 1 开始编号。
        if ref.endswith(".0"):
            continue
        counts["小节级"] += 1
        # 只在目标章**已有正文**时才能判定小节是否存在：
        # 预告尚未开写的章（“详见 6.3.2”）不是错误，只是此刻无法校验。
        if chap in body and ref not in secs.get(chap, set()):
            counts["悬空"] += 1
            problems.append(f"交叉引用「{ref}」悬空：{chap} 中没有这一小节")
    for m in CHAP_REF.finditer(prose):
        ref = m.group(1)
        if not _is_section_ref(prose, m, strict=True):
            continue
        counts["章级"] += 1
        if ref not in plan_ch:
            counts["悬空"] += 1
            problems.append(f"交叉引用「{ref}」悬空：PLAN.md 中没有这一章")
        # 指向「还没写的章」不报警：这是**正常的前置铺垫**
        # （1.4 讲重试装饰器时预告 6.3，1.2 讲推导式时预告 6.2），
        # 全书写完之前这类引用本来就该存在。报警器一旦吵，就没人看了。
    return counts, problems


def cross_ref_totals(per_chapter: dict[str, dict[str, int]]) -> dict[int, dict[str, int]]:
    """把逐章计数按篇汇总，返回 {篇号: {小节级, 章级, 悬空}}。

    按篇分组而不是只报全书总分：篇收尾那一格要的是**这一篇**的三个数，
    而它此前是人在一次全量运行里自己挑出来手算的。
    """
    out: dict[int, dict[str, int]] = defaultdict(lambda: dict.fromkeys(REF_TALLY_KEYS, 0))
    for cid, c in per_chapter.items():
        part = int(cid.split(".")[0])
        for k in REF_TALLY_KEYS:
            out[part][k] += c.get(k, 0)
    return out


# ---- 台账与正文里那三个数：**写了就必须与实跑相等，没写则沉默** --------------
# 汇总行把三个数报出来了，可它们仍是「抄不抄、抄对没有」靠人的一类：
# 篇收尾那一格（以及统稿记录与复盘章那张表里的同一句话）写的是人手敲进去的数，
# **数错了不会有任何检查变红**——读数与实跑差一个数，输出上完全看不出来。
# 于是这一条把「抄」也接进对账路：只要写了「小节级引用 N 处」这种句子，
# 就与 `cross_ref_scan` 的实跑值逐处比；一个字都没写就保持沉默（第 7 篇那一格
# 只写了「0 悬空」，第 0／1／2／3／4 篇的统稿记录更是一个数都没有）。
#
# 出口约定沿用 5.9 那一轮定下的**「阿拉伯数字是断言，引用旧数字写成汉字」**：
# 正则只认阿拉伯数字，所以「四十一处」是引文而不是断言（它不会被判成写错）。
# 这条约定是必要的——因为**一个数只有带着它的口径才能被复核**：
# 第 8 篇统稿记录里那个 214 数的是「三节号形状的记号」，换个口径就是一个错数，
# 而它在句子里读起来与「小节级引用」完全一样。
_LEDGER_PART_ROW = re.compile(r"^\|\s*第\s*(\d+)\s*篇\s*\|")
_LEDGER_HEAD_PART = re.compile(r"第\s*(\d+)\s*篇")
_LEDGER_HEAD_CHAP = re.compile(r"^#{1,3}\s+(\d+)\.\d+")
#: 一句话里出现这些词时，那三个数按**全书**总数比（而不是按所在篇）。
_BOOK_SCOPE_WORDS = ("全书", "合计", "总计", "总共")
#: 书侧那两份文档：它们写的是**实跑值的复述**，而它们不归 `book/` 也不归台账。
_STYLE_DOCS = ("STYLE.md", "README.md")
#: 切小句的分隔符：只切句末与分号，**不切逗号／顿号**（一句里的三个数属于同一句）。
_CLAUSE_SEPS = ("。", "；", ";", "！", "？")
#: 三个断言各自的两种语序：`小节级引用 57 处` 与 `57 处小节级引用`。
#: `[\s*_]{0,4}` 是给加粗留的——台账里绝大多数数都写成 `**57 处**`。
_TALLY_CLAIM_RES: dict[str, tuple[re.Pattern[str], ...]] = {
    "小节级": (re.compile(r"小节级(?:引用)?[\s*_]{0,3}[^\d\n]{0,2}?(\d+)[\s*_]{0,4}处"),
               re.compile(r"(\d+)[\s*_]{0,4}处[\s*_]{0,2}小节级")),
    "章级": (re.compile(r"章级(?:引用)?[\s*_]{0,3}[^\d\n]{0,2}?(\d+)[\s*_]{0,4}处"),
             re.compile(r"(\d+)[\s*_]{0,4}处[\s*_]{0,2}章级")),
    "悬空": (re.compile(r"悬空[\s*_]{0,3}[^\d\n]{0,2}?(\d+)[\s*_]{0,4}处"),
             re.compile(r"(\d+)[\s*_]{0,4}处?[\s*_]{0,2}悬空")),
}


def ledger_ref_tally_issues(text: str,
                            per_part: dict[int, dict[str, int]],
                            book: dict[str, int],
                            scope_hint: int | None = None,
                            require_explicit_scope: bool = False) -> tuple[list[str], int]:
    """扫那三句话（台账全文或一章正文），返回（问题列表, 比过的断言个数）。

    归属按「行首 `| 第 N 篇 |` → 所在小节标题里的第 N 篇 → 所在章的篇号」三级找，
    一句话里带「全书／合计／总计」的按全书总数比。**三种都判不出来时报错**：
    一个找不到归属的数，与写错的数一样没法复核。`scope_hint` 是给**正文**用的：
    章文件的所属篇由文件名定，不再从标题里猜（章里「与第 6 篇的分工」这种标题
    会拿错篇号，而它恰好出现在好几章里）。

    抽成纯函数（喂合成台账 ＋ 合成总数）是为了让这条口径能被钉住：
    它断言的正是「**抄下来的数**与实跑相等」，而这类错在书里从不发声。
    """
    issues: list[str] = []
    checked = 0
    scope_head: int | None = scope_hint
    for lineno, ln in enumerate(text.splitlines(), 1):
        if ln.startswith("#"):
            if scope_hint is None:
                m = _LEDGER_HEAD_PART.search(ln)
                if m:
                    scope_head = int(m.group(1))
                else:
                    m2 = _LEDGER_HEAD_CHAP.match(ln)
                    scope_head = int(m2.group(1)) if m2 else None
            continue
        m_row = _LEDGER_PART_ROW.match(ln)
        scope = int(m_row.group(1)) if m_row else scope_head
        for key, patterns in _TALLY_CLAIM_RES.items():
            for rx in patterns:
                for mo in rx.finditer(ln):
                    claimed = int(mo.group(1))
                    # 「全书还是这一篇」看的是**这一句所属的那一小句**，不是固定宽度的窗口：
                    # 「全书合计：小节级 623 处、章级 329 处」里只有第一个数紧贴着「全书」，
                    # 而三个数是同一句的。按句号／分号／换行切小句，三个数就都共享了「全书」。
                    start = max((ln.rfind(sep, 0, mo.start()) for sep in _CLAUSE_SEPS),
                                default=-1) + 1
                    ends = [ln.find(sep, mo.end()) for sep in _CLAUSE_SEPS]
                    end = min((e for e in ends if e != -1), default=len(ln))
                    ctx = ln[start:end]
                    if any(w in ctx for w in _BOOK_SCOPE_WORDS):
                        actual = book.get(key)
                        where = "（全书）"
                    else:
                        # 归属第一优先是**本句里写明的「第 N 篇」**：书侧的复盘文档（`STYLE`）
                        # 没有台账那样的行首格，而它那句话里的篇号写在正文里
                        # （「第 6 篇这一次三件事的结果：…小节级引用 **38 处**」）。
                        # 本句没写才退回行首／小节标题；两处都判不出就报错。
                        m_part = _LEDGER_HEAD_PART.search(ctx)
                        scope_here = (int(m_part.group(1))
                                      if m_part and int(m_part.group(1)) in per_part else scope)
                        if require_explicit_scope and not (m_part and scope_here in per_part):
                            # 书侧那两份文档里，「本节标题的篇号」与这一句毫无关系
                            # （8.4 是规程节、不是第 8 篇的事）——所以那里**只认本句写明的篇号**，
                            # 否则会把「第 8 篇」当成默认主语而报出一批假错。
                            # 代价是「写了一句没带篇号的当前值」不会被比——这一条边界记在 8.4。
                            continue
                        if scope_here is None:
                            issues.append(
                                f"第 {lineno} 行那句引用复核数找不到归属的篇："
                                f"「{ln.strip()[:36]}…」——写清是哪一篇"
                                f"（本节标题、行首 `| 第 N 篇 |`，或在本句里写「第 N 篇」），"
                                f"或把引用旧值写成汉字（阿拉伯数字是断言）")
                            continue
                        actual = per_part.get(scope_here, {}).get(key)
                        where = f"第 {scope_here} 篇"
                    if actual is None:
                        continue          # 那一篇这次没进全量运行（`--only`）
                    checked += 1
                    if claimed != actual:
                        issues.append(
                            f"{where}（第 {lineno} 行）：引用复核的「{key}」写的是 {claimed} 处，"
                            f"实跑 {actual} 处——阿拉伯数字是断言：把数改对，"
                            f"或把引用旧值写成汉字（口径见 `STYLE` 8.4）")
    return issues, checked


def check_ref_tally(rep: Report, chapters: dict[str, str],
                    per_part: dict[int, dict[str, int]], book: dict[str, int]) -> int:
    """把台账与正文里那三个数与实跑逐处比。返回比过的断言个数（汇总行拿它当凭据）。

    正文也要扫：那三句话第一次出现就是在 5.9.9 那张表里（「本篇 41 处小节级引用逐条回查」），
    而它是**从台账到正文的同一句话**——只扫台账会把它留在射程外。

    **书侧的复盘文档（`STYLE`／`README`）也要扫**：那三个数的故事就写在 8.4，
    而它抄下来的是同一句话（「全书合计：小节级 623 处」「小节级引用 **38 处**」）。
    它们与台账的区别只有一处：书侧那句多半**在本句里写明是第几篇**（没有行首的表格里），
    所以归属优先看本句里的「第 N 篇」，再退回所在小节标题。
    """
    checked = 0
    if LEDGER.exists():
        issues, n = ledger_ref_tally_issues(
            LEDGER.read_text(encoding="utf-8"), per_part, book)
        checked += n
        for msg in issues:
            rep.err("台账引用复核", msg)
    for cid, text in chapters.items():
        prose = re.sub(r"```.*?```", "", text, flags=re.S)
        issues, n = ledger_ref_tally_issues(
            prose, per_part, book, scope_hint=int(cid.split(".")[0]))
        checked += n
        for msg in issues:
            rep.err(f"正文 {cid} 引用复核", msg)
    for name in _STYLE_DOCS:
        path = ROOT / name
        if not path.exists():
            continue
        issues, n = ledger_ref_tally_issues(
            path.read_text(encoding="utf-8"), per_part, book, require_explicit_scope=True)
        checked += n
        for msg in issues:
            rep.err(f"{name} 引用复核", msg)
    return checked


# ---------------------------------------------------------------------------
# 书侧手写数字：`STYLE.md`／`README.md` 里那些「实跑值的复述」
#
# 这一类数是**工具算出来、文档抄一遍**——抄错了不会让任何数字变难看，
# 而它恰好是 8.11「写的是数，不是句子」的主场。口径与台账那三句完全一致：
# **只认阿拉伯数字（它是断言），引用旧值写成汉字**；**没写则沉默**；
# 并报出「比过几处」——覆盖从 3 处掉到 0 处，必须与「全对」在输出上分得开。
# ---------------------------------------------------------------------------

#: 句式一：术语表那三个数。关键字后面**那一小句里最后一个数字**才是当前值
#: （「词条数因此从 369 变成 **365**」里只有 365 是断言，369 是历史）。
_GLOSS_NUMBER_CLAIMS: tuple[tuple[str, re.Pattern[str], re.Pattern[str]], ...] = (
    ("词条数", re.compile(r"词条(?:数|总数)"), re.compile(r"([\d,]+)")),
    ("维护日志行数", re.compile(r"(?:维护|术语)(?:日志|记录)"),
     re.compile(r"([\d,]+)[\s*_]{0,4}行")),
    ("词条覆盖章数", re.compile(r"词条覆盖"), re.compile(r"([\d,]+)[\s*_]{0,4}章")),
)


def _num(s: str) -> int:
    return int(s.replace(",", ""))


def cls_of(line: str) -> list[str]:
    """把一行切成小句（只切句末与分号，**逗号与顿号不切**——一句里的几个数属于同一句）。"""
    out = line
    for sep in _CLAUSE_SEPS:
        out = out.replace(sep, "\u0000")
    return [c for c in out.split("\u0000") if c]


def glossary_number_issues(text: str, sources: dict[str, int],
                           where: str) -> tuple[list[str], int]:
    """术语那三个数（词条数／维护日志行数／词条覆盖章数）逐处与实跑比。

    抽成纯函数：它断言的正是「术语表的**元数据**被抄对了没有」，
    而这类数在书里从不发声（写错 365 与写对 365 在阅读上一模一样）。
    """
    issues: list[str] = []
    checked = 0
    for lineno, ln in enumerate(text.splitlines(), 1):
        if ln.startswith("|") and ln.count("|") > 8:
            cl = ln                       # 表格行：整行当一小句（术语表自己的行不进这里）
            clauses = [cl]
        else:
            clauses = cls_of(ln)
        for cl in clauses:
            for key, kw_re, val_re in _GLOSS_NUMBER_CLAIMS:
                kw = kw_re.search(cl)
                if not kw:
                    continue
                after = cl[kw.end():]
                vals = list(val_re.finditer(after))
                if not vals:
                    continue          # 写了关键词而没有单位（「维护日志里（一行三格）」）——沉默
                claimed = _num(vals[-1].group(1))
                actual = sources.get(key)
                if actual is None:
                    continue
                checked += 1
                if claimed != actual:
                    issues.append(
                        f"{where} 第 {lineno} 行的「{key}」写的是 {claimed}，实跑 {actual}"
                        f"——阿拉伯数字是断言：把数改对，或把引用旧值写成汉字（口径见 `STYLE` 8.11）")
    return issues, checked


#: 句式二：`STYLE` 8.7 的实测条目。只认这一种句式（一行四个数）：
#: `分项之和 **X**；实测 **N**（汉字 A ＋ B 行围栏）＝ 对计划 Z 的 P%`。
#: 更早的条目写法各异（有的把实测写成「本章实测」、有的不带「分项之和」）——
#: 它们保持沉默，边界写在 8.7 里：**先把句式统一，才能逐处比**。
#: 条目头的正则：**同时**把「第 N 个」里的那个 N 收进来。
#: 它一度只收了章号，而报错时说「第 {位置序号} 个实测」——两个编号体系混着用，
#: 于是报出来的编号与条目头上的编号对不上（文件里的次序并不等于条目的序号）。
_STYLE_MEASURE_HEAD = re.compile(r"^- \*\*第([^（\n]*?)个实测（`(\d+\.\d+)`）", re.M)
#: 统一句式（用命名组，因为前后两段都可选——6.3／7.1 是「事前估没落笔」的两章）：
#: `分项之和 **X**；实测 **N**（汉字 A ＋ B 行围栏）＝ 对计划 Z 的 P%——（可选）对分项之和 ＝ 估高/低 D%`
_STYLE_MEASURE_LINE = re.compile(
    r"(?:分项之和\s*\*{0,2}(?P<sum>[\d,]+)\*{0,2}\s*[；;，,]\s*)?"
    r"实测\s*\*{0,2}(?P<measured>[\d,]+)\*{0,2}\s*"
    r"（汉字\s*(?P<han>[\d,]+)\s*＋\s*(?P<fences>[\d,]+)\s*行围栏）"
    r"\s*＝\s*对计划\s*(?P<plan>[\d,]+)\s*的\s*\*{0,2}(?P<pct>\d+)%"
    r"(?P<tail>[^\n]{0,40}?对分项之和\s*＝\s*\*{0,2}估(?P<dir>高|低)\s*"
    r"(?P<diff>\d+(?:\.\d+)?)%\*{0,2})?")
#: PLAN 章表那一行里的「事前估 N」（分项之和的唯一来源）。
_PLAN_EST = re.compile(r"事前估\s*\*{0,2}([\d,]+)")
_PLAN_ROW = re.compile(r"^\|\s*(\d+\.\d+)(?:（[^）]*）)?\s*\|")
#: 「计划值 10,000 → **14,000**」——计划值改过时，PLAN 自己把旧值留在那一行里。
_PLAN_SUPERSEDED = re.compile(r"计划值\s*([\d,]+)\s*→\s*\*{0,2}([\d,]+)")


def plan_estimates(text: str) -> tuple[dict[str, int], dict[str, set[int]]]:
    """PLAN 章表里逐章的（事前估分项之和, 用过的计划值集合）。

    第二个是给「对计划 N 的 P%」那种句子用的：**达成比的分母是那一刻的计划**，
    而计划值改过的章（目前两章）会把旧值留在 PLAN 的同一个行里
    （「计划值 10,000 → **14,000**」）——所以旧值也是合法分母，
    但必须**在 PLAN 里有据**（否则分母就是个凭空的数）。
    """
    est: dict[str, int] = {}
    plans: dict[str, set[int]] = {}
    for ln in text.splitlines():
        m = _PLAN_ROW.match(ln)
        if not m:
            continue
        cid = m.group(1)
        e = _PLAN_EST.search(ln)
        if e and cid not in est:
            est[cid] = _num(e.group(1))
        for old, new in _PLAN_SUPERSEDED.findall(ln):
            plans.setdefault(cid, set()).update({_num(old), _num(new)})
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) > 2 and re.fullmatch(r"[\d,]+", cells[2]):
            plans.setdefault(cid, set()).add(_num(cells[2]))
    return est, plans


#: 事后校准的注（8.7 里漂移的唯一记账处）与它里面的「A → B」。
_NOTE_MARK = "【事后校准"
#: 一条链的长相：「10,434 → 10,453 → 10,462」。**不能用「数 → 数」逐对匹配**——
#: 那样第二对会被第一对吃掉（10,453 已经作为目标被消费，不再是下一段的起点），
#: 而它正是链能连通的关键。所以先圈出整条「数（→ 数）+」的串，再逐对拆开。
_CHAIN_RUN = re.compile(r"[\d,]+(?:\s*→\s*\*{0,2}[\d,]+)+")


def drift_chains(text: str) -> dict[int, set[int]]:
    """收集事后校准注里记下的「从哪个数漂到哪个数」（只收注里的链，别处的叙述不算）。

    注的正文可能跨行，所以收的是「标记那一行 + 后面缩进更深的行」——
    把范围限在注里，是因为**只有注是记历史的地方**：正文里的数仍然是断言。
    """
    graph: dict[int, set[int]] = {}
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if _NOTE_MARK not in ln:
            continue
        indent = len(ln) - len(ln.lstrip())
        block = [ln]
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                break
            if len(nxt) - len(nxt.lstrip()) <= indent:
                break
            block.append(nxt)
        for run in _CHAIN_RUN.findall("\n".join(block)):
            nums = [_num(x) for x in re.findall(r"[\d,]+", run)]
            for old, new in zip(nums, nums[1:]):
                graph.setdefault(old, set()).add(new)
    return graph


def chain_reaches(graph: dict[int, set[int]], start: int, goal: int,
                  seen: set[int] | None = None) -> bool:
    """`start` 能不能沿着注里的链走到 `goal`。"""
    if start == goal:
        return True
    seen = set() if seen is None else seen
    for nxt in graph.get(start, ()):
        if nxt in seen:
            continue
        seen.add(nxt)
        if chain_reaches(graph, nxt, goal, seen):
            return True
    return False


def style_measure_issues(text: str, stats: dict[str, tuple[int, int, int]],
                         plan: dict[str, int], est: dict[str, int],
                         plan_history: dict[str, set[int]],
                         graph: dict[int, set[int]]) -> tuple[list[str], int]:
    """`STYLE` 8.7 的实测条目：一行里的几个数与盘上逐处比。

    `stats[cid] = (汉字, 围栏行数, 有效字数)`、`plan[cid]` 是当前计划、`est[cid]` 是事前估、
    `graph` 是事后校准注里的漂移链（「A → B」的有向图）。

    三类判据分开：
    ① **盘上算得出来的**（实测／汉字／围栏行数）逐处比——这一条接住「书改了、复盘没跟」。
       头条记的是**定稿值**（8.7 的体例），所以它允许落后于当前值，条件是
       **注里那条链从头条出发能走到当前值**；链断了与写错同等报出。
    ② **句子里自己就算得出来的**（有效字 ＝ 汉字 ＋ 15 × 围栏行、达成比 ＝ 实测 ÷ 认的分母）
       ——这一条接住「四个数里改了一个、另一个没跟」；
    ③ 分母得**有据**：`对计划 N` 里的 N 要么是当前计划、要么是 PLAN 里记过的旧值。
    ② 用**句子里写的**实测去算达成比（不用盘上的），这样一个漂了的位置只报一道错，
    不会连着报两道。
    """
    issues: list[str] = []
    checked = 0
    g = lambda mo, k: (None if mo.group(k) is None else _num(mo.group(k)))   # noqa: E731
    heads = [(m.start(), m.group(1), m.group(2)) for m in _STYLE_MEASURE_HEAD.finditer(text)]
    for i, (pos, ordinal, cid) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        block = text[pos:end]
        for mo in _STYLE_MEASURE_LINE.finditer(block):
            have = stats.get(cid)
            if have is None:
                continue
            han, fences, effective = have
            declared_sum = g(mo, "sum")
            declared = g(mo, "measured")
            declared_han = g(mo, "han")
            declared_fences = g(mo, "fences")
            declared_plan = g(mo, "plan")
            declared_pct = int(mo.group("pct"))
            where = f"8.7 的「第{ordinal}个实测（{cid}）」那一行"
            # 头条（实测／汉字／围栏行）记的是**定稿值**——这是 8.7 的体例，
            # 而定稿后正文又改过时，漂移记在同一条目里的事后校准注里。
            # 所以这三项走「两选一」：要么直接等于当前值，
            # 要么注里那条链**从头条出发、能走到当前值**（链断了就报）。
            drifted = declared != effective
            chained = (not drifted) or chain_reaches(graph, declared, effective)
            checks: list[tuple[str, int | None, int | None, str]] = [
                ("分项之和", declared_sum, est.get(cid), "事前估（PLAN 章表）"),
                # ② 句内算术：本书的篇幅口径就是「汉字 ＋ 15 × 围栏行」。
                ("句内的有效字", declared,
                 declared_han + CODE_LINE_EQUIV * declared_fences,
                 "同一句里的汉字 ＋ 15 × 围栏行"),
            ]
            if not chained:
                checked += 1
                reach = [str(x) for x in sorted(graph.get(declared, ()))] or ["—"]
                issues.append(
                    f"{where}的实测写的是 {declared}，而盘上是 {effective}"
                    f"（这一章的正文改过，而事后校准注里那条链从 {declared} 只走到 "
                    f"{'／'.join(reach)}）——把新的那一跳补进注里（口径见 `STYLE` 8.7），"
                    f"或把头条改成当前值")
            elif not drifted:
                # 头条本就等于当前值：汉字与围栏行也逐处比（三项同源，不同步就是抄错）。
                # 头条是定点值时不再拿当前汉字数去比它——同一次漂移不该报两遍。
                checks += [("汉字", declared_han, han, "汉字数（盘上现算）"),
                           ("围栏行数", declared_fences, fences, "围栏行数（盘上现算）")]
            allowed = set(plan_history.get(cid, set()))
            if cid in plan:
                allowed.add(plan[cid])
            if allowed and declared_plan not in allowed:
                checked += 1
                issues.append(
                    f"{where}的「对计划 {declared_plan}」不是一个有据的分母——"
                    f"PLAN 里这一章的计划值是 {'／'.join(str(x) for x in sorted(allowed))}"
                    f"（旧值也可以，但它得写在 PLAN 的「计划值 A → B」里）")
            else:
                checked += 1
                if declared_pct != round(declared / declared_plan * 100):
                    issues.append(
                        f"{where}的「达成比」写的是 {declared_pct}%，而同一句里的"
                        f"实测 {declared} ÷ 计划 {declared_plan} 是 "
                        f"{round(declared / declared_plan * 100)}%")
            for label, claimed, actual, source in checks:
                if actual is None or claimed is None:
                    continue
                checked += 1
                if claimed != actual:
                    issues.append(
                        f"{where}里「{label}」写的是 {claimed}，而{source}是 {actual}"
                        f"——阿拉伯数字是断言：把数改对，"
                        f"或把引用旧值写成汉字（口径见 `STYLE` 8.11）")
            # ③b 句尾那句「对分项之和 ＝ 估高/低 D%」也是句内算术（两个数都在同一行里）。
            if mo.group("diff") and declared_sum:
                checked += 1
                delta = (declared_sum - declared) / declared_sum * 100
                want_dir = "高" if delta >= 0 else "低"
                want_diff = round(abs(delta), 1)
                claimed_diff = float(mo.group("diff"))
                if mo.group("dir") != want_dir or abs(claimed_diff - want_diff) > 0.05:
                    issues.append(
                        f"{where}尾上写的是「估{mo.group('dir')} {mo.group('diff')}%」，"
                        f"而同一行里的 {declared_sum} 与 {declared} 算出来是"
                        f"估{want_dir} {want_diff}%")
    # ③c **覆盖不能悄悄变窄**：每个条目都要在射程内。
    #
    # 这一条是 2026-09-21 补的：句式统一之前，8.7 里有一半条目写的是
    # 「事前估 X…，实写 N（汉字 A ＋ 代码 B 行）＝ 达成 P%」——它们**一个数都没进射程**，
    # 而输出里那句话（「本次比过 N 处」）照样是绿的。凡「覆盖会变窄而输出不变」的地方，
    # 都要有一条会响的路（与 8.5 那条同形）。
    for pos, ordinal, cid in heads:
        end = next((p for p, _, _ in heads if p > pos), len(text))
        if not _STYLE_MEASURE_LINE.search(text[pos:end]):
            checked += 1
            issues.append(
                f"8.7 的「第{ordinal}个实测（{cid}）」那一行不在射程内——它没写成统一句式"
                f"（`分项之和 X；实测 N（汉字 A ＋ B 行围栏）＝ 对计划 Z 的 P%`），"
                f"于是这一条的数落在所有门的射程外；改成统一句式，或把它的实测写成汉字引文")
    return issues, checked


def check_style_numbers(rep: Report, stats: dict[str, tuple[int, int, int]],
                       plan: dict[str, int]) -> int:
    """书侧两份文档里那些「实跑值的复述」逐处比。返回比过的断言个数。"""
    sources = {
        "词条数": len(load_glossary_rows()),
        "维护日志行数": len(glossary_log_rows(GLOSSARY.read_text(encoding="utf-8"))),
        "词条覆盖章数": len(glossary_term_chapters(GLOSSARY.read_text(encoding="utf-8"))),
    }
    est, plan_history = (plan_estimates(PLAN.read_text(encoding="utf-8"))
                         if PLAN.exists() else ({}, {}))
    checked = 0
    for name in _STYLE_DOCS:
        path = ROOT / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        issues, n = glossary_number_issues(text, sources, name)
        checked += n
        for msg in issues:
            rep.err(f"书侧 {name} 术语数", msg)
        issues, n = style_measure_issues(text, stats, plan, est, plan_history,
                                          drift_chains(text))
        checked += n
        for msg in issues:
            rep.err(f"书侧 {name} 篇幅实测", msg)
    return checked


def check_style_claims_wired(rep: Report) -> int:
    """文档里引用了「N 条夹具」却没接线的工具——报出来。

    接线是每支工具在自己 `--self-test` 末尾调一次 `style_claims.report()`（零额外开销）。
    这一道回查**名单**：新给某支工具写一句「N 条夹具」而不接线时，
    那句话就静默地落在门之外（与 8.5 那条「覆盖变窄而输出不变」同形）。
    """
    loose = sc.unwired_tools()
    for tool in loose:
        rep.err("书侧夹具条数",
                f"`{tool}.py` 在文档里被引用了夹具条数，却没有在自检末尾接上"
                f"`style_claims.report()`——那颗数落在所有门的射程外")
    return len(loose)


def check_style_inventory(rep: Report) -> int:
    """`README`／`PLAN`／`STYLE` 里那几句「按盘上清点」的数：目录体积、文件数、唯一链接数。

    它们与「`N` 条夹具」同族（作者是盘、抄写员是文档），但以前**一处都没接**：
    加一份素材、给 `REFERENCES.md` 添一条链接，那几个数一个字都不会变难看。
    口径（体积按字节数之和、判据 ±10%；计数逐字比；只认带路径上下文的句子）
    写在 `style_claims` 里——那里是它唯一的实现。
    """
    issues, checked = sc.inventory_doc_issues()
    for msg in issues:
        rep.err("书侧库存声明", msg)
    return checked


def check_cross_refs(chapters: dict[str, str], rep: Report) -> dict[str, dict[str, int]]:
    """章内交叉引用必须真实存在；同时把三个数交给调用方去汇总实报。

    已有的引用校验只查到「章」这一级（且只认「第 x.y 节」写法）。改编号、拆章节之后
    最容易悄悄坏掉的正是**小节级**引用——「详见 1.14.6」在 1.14 只剩 5 节时就悬空了，
    而正文渲染出来看不出任何异常。这里把两种粒度的引用都落到真实标题上。
    """
    plan_ch = load_plan_chapters()
    body, secs = build_book_index()
    per_chapter: dict[str, dict[str, int]] = {}
    for cid, text in chapters.items():
        prose = re.sub(r"```.*?```", "", text, flags=re.S)
        counts, problems = cross_ref_scan(prose, plan_ch, body, secs)
        for msg in problems:
            rep.err(cid, msg)
        per_chapter[cid] = counts
    return per_chapter


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


def ledger_symbol_counts(ledger_text: str) -> dict[str, list[int]]:
    """按「## …第 N 篇…」小节数四个状态符号，返回 {「第 N 篇」: [✅, 🔀, ⏭, ⬜]}。

    抽成独立函数是为了**口径只有一份实现**：`tools/totals.py` 要把这四个数写进
    「篇级进度」那张表，而这里要把表里的数与它比——两边若各数一遍，漂的就是口径本身。

    只统计「知识点行」。注意不能简单地「首格以反引号开头就当成图例行」——很多知识点
    本身就以代码写法开头（如 `*args` / `**kwargs`、「`global` 的使用」），那样会被误删、
    导致台账少算而“看上去存量变少了”。图例行只有一种：首格恰好是一个状态符号。
    """
    legend = re.compile(r"^`(?:✅|🔀|⏭|⬜)`$")
    part = None
    per_part: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])  # ✅ 🔀 ⏭ ⬜
    for ln in ledger_text.splitlines():
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
    return per_part


def check_ledger(rep: Report) -> None:
    if not LEDGER.exists():
        rep.warn("台账", "未找到 LEDGER.md")
        return
    per_part = ledger_symbol_counts(LEDGER.read_text(encoding="utf-8"))
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
# 有一句「备查的第二个数按第 7 篇五章合计比值 0.912 折出 ≈ 9,700，而实测 10,453」
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
     "备查的第二个数按第 7 篇五章合计比值 0.912 折出 ≈ 9,700，而实测 10,453。", 0),
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


# [引用复核] 夹具：**引用复核的三个数**（小节级／章级／悬空）。
# 为什么这三条要进门：篇收尾那一格里的数（第 5 篇 41 处、第 6 篇 38 处＋1 处、第 8 篇 214 处）
# 从前是人跑一次、手写一个数，**而它不是文字错、是数错**——数错不会让任何检查变红，
# 只会让台账里的那句话与书稿差一个数。夹具直接喂 `cross_ref_scan` 需要的一切
# （正文、PLAN 章表、有正文的章、已有小节），因此**不依赖书稿走到哪一步**。
# 每个用例给的是（小节级, 章级, 悬空）三元组。
_REF_TALLY_CASES = [
    ("三段式带「第…节」：计 1 处小节级", "详见第 1.2.3 节。",
     {"1.2": 7000}, {"1.2"}, {"1.2": {"1.2.3"}}, (1, 0, 0)),
    ("小节级只计一次（不被当成章级再计一遍）", "见 1.2.3。",
     {"1.2": 7000}, {"1.2"}, {"1.2": {"1.2.3"}}, (1, 0, 0)),
    ("目标章已有正文、小节不在：计 1 处并报 1 悬空", "见 1.2.9。",
     {"1.2": 7000}, {"1.2"}, {"1.2": {"1.2.3"}}, (1, 0, 1)),
    ("目标章还没开写：不计悬空（预告不是错）", "见 6.3.2 节。",
     {"6.3": 7000}, set(), {}, (1, 0, 0)),
    ("第三段为 0（`见 1.6.0`）：版本号，不计", "见 1.6.0。",
     {"1.6": 7000}, {"1.6"}, {}, (0, 0, 0)),
    ("括号里的三段式但括号前是产品名（`Python（3.11.9）`）：不计",
     "同 Python（3.11.9）。", {"3.11": 7000}, {"3.11"}, {}, (0, 0, 0)),
    ("章级带「详见」：计 1 处章级", "详见 6.3。", {"6.3": 7000}, set(), {}, (0, 1, 0)),
    ("章级不在 PLAN：计 1 处并报 1 悬空", "详见 9.9。", {"6.3": 7000}, set(), {}, (0, 1, 1)),
    ("两段式没有引用语境（`本章 3.4 张表`）：不计", "本章 3.4 张表。",
     {"3.4": 7000}, {"3.4"}, {}, (0, 0, 0)),
    ("正文里一个记号都没有：三个数全 0（反向守）", "本节只讲思路，不指别处。",
     {"1.2": 7000}, {"1.2"}, {}, (0, 0, 0)),
]


# [引用复核] 夹具：**台账里那三句话**（写了就必须与实跑相等）。
# 为什么这一组要进门：前面十个夹具钉的是「数怎么数」，而这一组钉的是「数怎么抄」——
# 汇总行把三个数报出来了，抄进台账那一步仍是人手动作，**数错了不会让任何检查变红**。
# 台账与总数都是合成的（不读盘上任何文件），因此**不依赖书稿走到哪一步**。
# 每个用例给的是（合成台账, 合成的逐篇总数＋全书总数, 期望问题条数）。
# 两个篇：第 5 篇用于台账那一组，第 6／7 篇用于「标题里的篇号不能把归属带走」那条；
# 第 6 篇的数（38 ＋ 1）是实书里第 6 篇的真值——这样那条夹具在两个实现下**结果不同**
# （若按标题误判成第 6 篇，38 与 38 相等，它会静静放过）。
_T_PART_TOTALS = {5: {"小节级": 57, "章级": 4, "悬空": 0},
                  6: {"小节级": 38, "章级": 1, "悬空": 0},
                  7: {"小节级": 86, "章级": 3, "悬空": 0}}
_T_BOOK_TOTALS = {"小节级": 623, "章级": 329, "悬空": 0}
_LEDGER_TALLY_CASES = [
    ("写对了：沉默（反向守）",
     "| 第 5 篇 | 9 / 9 | 183 | …小节级引用 57 处 ＋ 章级引用 4 处，0 悬空 |\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 0),
    ("小节级写错了：要拦（41 ≠ 57）",
     "| 第 5 篇 | 9 / 9 | 183 | …小节级引用 41 处 ＋ 章级引用 4 处，0 悬空 |\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 1),
    ("加粗写对了：沉默（台账里的数几乎都带加粗）",
     "| 第 5 篇 | …小节级引用 **57 处** ＋ 章级引用 **4 处**，**0 悬空** |\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 0),
    ("另一种语序（「41 处小节级引用」）：同样要拦",
     "| 第 5 篇 | …抽 8 条落点全命中、41 处小节级引用复核 |\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 1),
    ("章级写错：要拦",
     "| 第 5 篇 | …小节级引用 57 处 ＋ 1 处章级，0 悬空 |\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 1),
    ("悬空写成 3 而实跑 0：要拦",
     "| 第 5 篇 | …小节级引用 57 处 ＋ 章级引用 4 处，3 悬空 |\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 1),
    ("一句话里一个字都没写：沉默（第 7 篇就是这种）",
     "| 第 5 篇 | …小节级引用与章级引用 0 悬空 |\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 0),
    ("引用旧值写成汉字（「四十一处」）：不是断言，沉默",
     "| 第 5 篇 | …旧记四十一处小节级引用，口径不同 |\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 0),
    ("同一句话写在章的统稿记录里：按所在篇判（41 ≠ 57）",
     "### 5.9 项目复盘\n\n| 项 | 结果 |\n| --- | --- |\n"
      "| 交叉引用复核 | 小节级 41 处 ＋ 章级 4 处，0 悬空 |\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 1),
    ("篇标题写在 ## 一级标题上：按那一篇判（57 对）",
     "## 七之一、第 5 篇 · RAG与生产级系统\n\n小节级引用 57 处、章级引用 4 处、悬空 0 处。\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 0),
    ("全书口径（带「全书」）：按总数比（623 对）",
     "## 八、篇级进度\n\n全书合计：小节级引用 623 处、章级引用 329 处、悬空 0 处。\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 0),
    ("全书口径数写错：要拦（600 ≠ 623）",
     "## 八、篇级进度\n\n全书合计：小节级引用 600 处。\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 1),
    ("找不到归属的篇：要拦（一个没法复核的数与写错的数同级）",
     "## 九、附录\n\n小节级引用 57 处。\n",
     _T_PART_TOTALS, _T_BOOK_TOTALS, 1),
]

# [引用复核] 正文那一侧：同一句话第一次出现就是在 5.9.9 那张表里，
# 所以所属篇由**文件名／题名**给定（`scope_hint`），不从标题里猜。
# 用例给的是（名称, 一章正文, 所属篇, 期望问题条数）。
_TALLY_HINT_CASES = [
    ("正文里的同一句话写错了：要拦（41 ≠ 57）",
     "# 5.9 项目复盘\n\n| 交叉引用复核 | 本篇 41 处小节级引用逐条回查；改编号后悬空 0 处 |\n", 5, 1),
    ("正文里的同一句话写对了：沉默",
     "# 5.9 项目复盘\n\n| 交叉引用复核 | 本篇 57 处小节级引用逐条回查；改编号后悬空 0 处 |\n", 5, 0),
    ("章里提到别的篇号的标题不能把归属带走（按 `scope_hint` 判第 7 篇：38 ≠ 86）",
     "# 7.2 可观测性\n\n## 与第 6 篇的分工\n\n小节级引用 38 处。\n", 7, 1),
]


# [书侧数字] 术语表那三个数（`STYLE`／`README` 里的复述）：全用合成输入，
# 不读盘上任何文件，所以书稿走到哪一步都不影响它们。
_T_TERM_NUMBERS = {"词条数": 365, "维护日志行数": 57, "词条覆盖章数": 59}
_GLOSS_NUMBER_CASES = [
    ("词条数写成当前值：沉默（反向守）", "本书的词条数 **365** 条。\n", 0),
    ("词条数写成旧值：要拦", "本书的词条数 **369** 条。\n", 1),
    ("「从旧到新」两种写法：只比最后一个（369 是历史、365 是断言）",
     "词条数因此从 369 变成 **365**。\n", 0),
    ("引用旧数字写成汉字：不是断言，沉默", "词条数因此从三百六十九条变成 **365** 条。\n", 0),
    ("维护日志行数与词条覆盖章数写对：沉默", "术语日志 **57** 行，词条覆盖 **59** 章。\n", 0),
    ("维护日志行数写错：要拦", "维护记录 **56** 行。\n", 1),
    ("词条覆盖章数写错：要拦", "词条覆盖 **58** 章。\n", 1),
    ("写了关键词而没有单位（「维护日志里（一行三格）」）：沉默",
     "账记在 `GLOSSARY` 的维护日志里（一行三格）。\n", 0),
]

# [书侧库存声明] `README`／`PLAN` 里那几句「按盘上清点」的数。事实是**喂进去的**，
# 所以夹具与盘上无关（否则「今天恰好相等」会让它们看不出退化）。
_T_INVENTORY = {"sources_files": 216, "sources_mb": 5.5, "raw_mb": 293.5,
                "raw_big_pdf_mb": 128.9, "raw_pdfs": 12, "ref_links": 483}
_INVENTORY_CASES = [
    ("计数与体积都写对：沉默", "├── sources/  ← 纯文本素材库（已纳入 git，216 个文件 / 5.5MB）\n", 2, 0),
    ("计数写错：要拦", "├── sources/  ← 纯文本素材库（已纳入 git，217 个文件 / 5.5MB）\n", 2, 1),
    ("体积写在 ±10% 带内：沉默（`du` 按块对齐，两种数不必逐字相等）",
     "├── raw/  ← 原始资料归档（295MB，未纳入 git）\n", 1, 0),
    ("体积差得远：要拦", "├── raw/  ← 原始资料归档（120MB，未纳入 git）\n", 1, 1),
    ("「含 N MB 单文件」按最大文件判（带内的差不报）",
     "`raw/` 当前经 `.gitignore` 排除（295MB，含 125MB 单文件 PDF）。\n", 2, 0),
    ("单文件体积差得远：要拦",
     "`raw/` 当前经 `.gitignore` 排除（295MB，含 60MB 单文件 PDF）。\n", 2, 1),
    ("原件数与唯一链接数各自逐字比",
     "│   ├── pdf/  ← 12 个原始 PDF\n`REFERENCES.md`（483 个唯一链接）\n", 2, 0),
    ("同一句里两个体积：只取路径后最近的那个（否则会把「最大单文件」当成目录体积）",
     "`raw/` 当前被排除（295MB，含 125MB 单文件 PDF）。\n", 2, 0),
    ("没有路径上下文的数字不碰（「共 999 个文件」不知道指哪儿）",
     "仓库里共 999 个文件。\n", 0, 0),
    ("汉字写的数不是断言（沿用 5.9 那轮的约定）", "sources/ 里共二百一十六个文件。\n", 0, 0),
]

# [书侧数字] 漂移链：事后校准注里记的「A → B」（正文里同样的箭头不算）。
_CHAIN_CASES = [
    ("注里的三段链被收进来，且起点走得到终点",
     "  - **【事后校准 2026-09-20】**：本章的实测从 **10,434 → 10,453 → 10,462**（汉字 9,103 → 9,112）。\n    还有一行续文。\n",
     10434, 10462, True),
    ("链断了一节：走不到",
     "  - **【事后校准 2026-09-20】**：实测从 **10,434 → 10,453** 就停了。\n",
     10434, 10480, False),
    ("不在注里的箭头不算链",
     "  正文里的叙述：实测从 **10,434 → 10,453**。\n",
     10434, 10453, False),
    ("三段链的第二跳也要收（它正是链能连通的那一环）",
     "  - **【事后校准 2026-09-20】**：实测 **10,434 → 10,453 → 10,462**。\n",
     10453, 10462, True),
]

# [书侧数字] 8.7 的实测条目：头条（定稿值）要么等于当前值，要么注里有链能走到当前值。
_T_MEASURE_STATS = {"9.9": (1000, 10, 1150)}
_T_MEASURE_PLAN = {"9.9": 1000}
_T_MEASURE_EST = {"9.9": 1200}
_T_MEASURE_HISTORY = {"9.9": {1000, 800}}      # 800 是 PLAN 里记过的旧值


def _m_entry(measured: str, han: str = "1000", fences: str = "10",
             total: str | None = "1200", plan_n: str = "1000", pct: str = "115",
             tail: str = "", note: str = "") -> str:
    head = f"分项之和 **{total}**；" if total else ""
    out = ("- **第 1 个实测（`9.9`）：一句话。**\n\n"
           f"  {head}实测 **{measured}**（汉字 {han} ＋ {fences} 行围栏）"
           f"＝ 对计划 {plan_n} 的 **{pct}%**{tail}\n")
    return out + note


_CHAIN_NOTE = ("  - **【事后校准 2026-09-20】**：本章的实测从 **1160 → 1150**。\n")
#: 定稿值那一组（1160 ＝ 1010 ＋ 15 × 10）——它本身就是一套自洽的数，
#: 与当前值（1150 ＝ 1000 ＋ 15 × 10）只差在「后来又改了一句」。
_STYLE_MEASURE_CASES = [
    ("头条就是当前值，而六个数全对：沉默（反向守）", _m_entry("1150"), 0),
    ("汉字写成别的值：要拦（它同时破了句内算术，所以报两道）",
     _m_entry("1150", han="999"), 2),
    ("围栏行数写错：要拦（它同时破了句内算术，所以报两道）",
     _m_entry("1150", fences="11"), 2),
    ("头条不等于当前值而注里没有链：要拦（书改了、复盘没跟）",
     _m_entry("1160", han="1010", pct="116"), 1),
    ("头条是定稿值而注里的链走到当前值：沉默",
     _m_entry("1160", han="1010", pct="116", note=_CHAIN_NOTE), 0),
    ("分项之和与 PLAN 的事前估不等：要拦", _m_entry("1150", total="1201"), 1),
    ("达成比算错：要拦", _m_entry("1150", pct="114"), 1),
    ("分母是个没据的数（既不是当前计划也不是 PLAN 记过的旧值）：要拦",
     _m_entry("1150", plan_n="900"), 1),
    ("分母是 PLAN 里改过的旧值（且比值得当）：合法（沉默）",
     _m_entry("1150", plan_n="800", pct="144"), 0),
    ("尾上那句「对分项之和 ＝ 估高/低估」写对：沉默",
     _m_entry("1150", tail="——对分项之和 ＝ **估高 4.2%**"), 0),
    ("尾上那句方向写反了：要拦",
     _m_entry("1150", tail="——对分项之和 ＝ **估低 4.2%**"), 1),
    ("尾上那句数字写错了：要拦",
     _m_entry("1150", tail="——对分项之和 ＝ **估高 9.9%**"), 1),
    ("没写分项之和（6.3／7.1 那种「事前估没落笔」）：其余照比（沉默）",
     _m_entry("1150", total=None), 0),
    ("没写分项之和、而其实该有（写的是当前值）：仍沉默（数字对）",
     _m_entry("1150", total=None, plan_n="800", pct="144"), 0),
    # ③c 覆盖不能悄悄变窄：条目写成了旧句式（那 22 条统一之前的写法）时要响，
    # 否则它的几个数落在射程之外，而输出里依旧是「逐处相符」。
    ("条目写成旧句式（不在射程内）：要拦——覆盖变窄与「全对」必须分得开",
     "- **第 1 个实测（`9.9`）：一句话。**\n\n"
     "  事前估 **1,000**，实写 **1,150**（汉字 1,000 ＋ 代码 10 行）＝ 达成 115%。\n", 1),
    ("条目写成旧句式、而那个数其实是对的：仍然要拦（对也没用——它没被比过）",
     "- **第 1 个实测（`9.9`）：一句话。**\n\n"
     "  事前估 **1,000**，实写 **1,150** 有效字（汉字 1,000 ＋ 代码 10 行）。\n", 1),
]

# [书侧引用复核] 文档里那句「只认本句写明的篇号」（不拿所在小节的标题当主语）。
_DOC_TALLY_CASES = [
    ("书侧那句没写篇号：沉默（8.4 的标题是「8」，与那句无关）",
     "### 8.4 每篇收尾的三件事\n\n小节级引用 38 处。\n", 0),
    ("书侧那句在本句里写了篇号且数对：沉默",
     "### 8.4 每篇收尾的三件事\n\n第 6 篇的小节级引用 **38 处**。\n", 0),
    ("书侧那句在本句里写了篇号而数错了：要拦",
     "### 8.4 每篇收尾的三件事\n\n第 5 篇的小节级引用 **38 处**。\n", 1),
    ("书侧那句带「全书」：按总数比（623 对）",
     "### 8.4 每篇收尾的三件事\n\n全书合计：小节级引用 623 处。\n", 0),
]


# [体例形状] 导读与练习的两种旧写法各一个反例；两级的章（2.5／2.6／8.5）要沉默。
_SHAPE_HEAD = "# 1.1 标题\n\n## 本章导读\n\n一句话。\n\n## 学习目标\n\n- [ ] x\n\n"
_SHAPE_CASES = [
    ("导读是 `## 本章导读` ＋ 三级练标签有序：沉默",
     _SHAPE_HEAD + "## 练习\n\n- **基础**：跑一遍。\n- **进阶**：加一条夹具。\n- **挑战**：写一张检查单。\n", 0),
    ("导读写成引用块：要拦（53 章曾这么写）",
     "# 1.1 标题\n\n> **本章导读**：一句话。\n\n## 练习\n\n- **基础**：x\n- **进阶**：y\n", 1),
    ("没有导读小节：要拦",
     "# 1.1 标题\n\n## 练习\n\n- **基础**：x\n- **进阶**：y\n", 1),
    ("有一条编号列表没带标签：要拦",
     _SHAPE_HEAD + "## 练习\n\n- **基础**：x\n1. 旧写法\n- **进阶**：y\n", 1),
    ("级别顺序反了（进阶在基础前）：要拦",
     _SHAPE_HEAD + "## 练习\n\n- **进阶**：y\n- **基础**：x\n", 1),
    ("只有「基础」一级：要拦",
     _SHAPE_HEAD + "## 练习\n\n- **基础**：x\n", 1),
    ("两级的章（没有挑战）：沉默（2.5／2.6／8.5 就是这样）",
     _SHAPE_HEAD + "## 练习\n\n- **基础**：x\n- **进阶**：y\n", 0),
    ("没有练习小节：沉默（第 0 篇与求职篇允许裁剪它）",
     _SHAPE_HEAD, 0),
    ("嵌套的列表不算「没带标签」（只查顶层的 `- `）",
     _SHAPE_HEAD + "## 练习\n\n- **基础**：x\n  - 子条目\n- **进阶**：y\n", 0),
    ("标签写在标题行之外（`**基础**` 不带 `- `）：要拦",
     _SHAPE_HEAD + "## 练习\n\n**基础**：x\n**进阶**：y\n", 1),
]


def self_test_total() -> int:
    """这份工具的夹具条数（不跑夹具也能算）——书侧引用对账拿它当实跑值。"""
    return (len(_WIRING_CASES) + len(_CODE_LINE_CASES) + len(_PLAN_CASES)
            + len(_MEASURE_CASES) + len(_GLOSS_LOG_CASES) + len(_REF_TALLY_CASES)
            + len(_LEDGER_TALLY_CASES) + len(_TALLY_HINT_CASES)
            + len(_GLOSS_NUMBER_CASES) + len(_CHAIN_CASES)
            + len(_STYLE_MEASURE_CASES) + len(_DOC_TALLY_CASES)
            + len(_SHAPE_CASES) + len(_INVENTORY_CASES))


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
    for name, prose, plan, body, secs, want in _REF_TALLY_CASES:
        counts, problems = cross_ref_scan(prose, plan, body, secs)
        got = tuple(counts[k] for k in REF_TALLY_KEYS)
        if got == want and len(problems) == want[2]:
            ok += 1
        else:
            print(f"  ✖ [引用复核] {name}：期望 {want}（悬空报错 {want[2]} 条），"
                  f"实得 {got}（报错 {len(problems)} 条）")
    for name, ledger_text, per_part, book, want in _LEDGER_TALLY_CASES:
        issues, _checked = ledger_ref_tally_issues(ledger_text, per_part, book)
        if len(issues) == want:
            ok += 1
        else:
            print(f"  ✖ [台账引用复核] {name}：期望 {want} 条问题，实得 {len(issues)} 条"
                  + ("" if not issues else f"——{issues[0]}"))
    for name, chapter_text, hint, want in _TALLY_HINT_CASES:
        issues, _checked = ledger_ref_tally_issues(
            chapter_text, _T_PART_TOTALS, _T_BOOK_TOTALS, scope_hint=hint)
        if len(issues) == want:
            ok += 1
        else:
            print(f"  ✖ [正文引用复核] {name}：期望 {want} 条问题，实得 {len(issues)} 条"
                  + ("" if not issues else f"——{issues[0]}"))
    for name, text, want in _GLOSS_NUMBER_CASES:
        issues, _n = glossary_number_issues(text, _T_TERM_NUMBERS, "夹具")
        if len(issues) == want:
            ok += 1
        else:
            print(f"  ✖ [书侧术语数] {name}：期望 {want} 条问题，实得 {len(issues)} 条"
                  + ("" if not issues else f"——{issues[0]}"))
    for name, text, start, goal, want in _CHAIN_CASES:
        got = chain_reaches(drift_chains(text), start, goal)
        if got == want:
            ok += 1
        else:
            print(f"  ✖ [漂移链] {name}：期望{'走得到' if want else '走不到'}，"
                  f"实得{'走得到' if got else '走不到'}")
    for name, text, want in _STYLE_MEASURE_CASES:
        issues, _n = style_measure_issues(text, _T_MEASURE_STATS, _T_MEASURE_PLAN,
                                          _T_MEASURE_EST, _T_MEASURE_HISTORY,
                                          drift_chains(text))
        if len(issues) == want:
            ok += 1
        else:
            print(f"  ✖ [8.7 实测条目] {name}：期望 {want} 条问题，实得 {len(issues)} 条"
                  + ("" if not issues else f"——{issues[0]}"))
    for name, text, want_checked, want in _INVENTORY_CASES:
        issues, n = sc.inventory_issues(text, "夹具", _T_INVENTORY)
        if (n, len(issues)) == (want_checked, want):
            ok += 1
        else:
            print(f"  ✖ [书侧库存声明] {name}：期望比过 {want_checked} 处/问题 {want} 条，"
                  f"实得比过 {n} 处/问题 {len(issues)} 条"
                  + ("" if not issues else f"——{issues[0]}"))
    for name, text, want in _SHAPE_CASES:
        got = len(chapter_shape_issues(text))
        if got == want:
            ok += 1
        else:
            print(f"  ✖ [体例形状] {name}：期望 {want} 条问题，实得 {got} 条"
                  + ("" if not got else f"——{chapter_shape_issues(text)[0]}"))
    for name, text, want in _DOC_TALLY_CASES:
        issues, _n = ledger_ref_tally_issues(
            text, _T_PART_TOTALS, _T_BOOK_TOTALS, require_explicit_scope=True)
        if len(issues) == want:
            ok += 1
        else:
            print(f"  ✖ [书侧引用复核] {name}：期望 {want} 条问题，实得 {len(issues)} 条"
                  + ("" if not issues else f"——{issues[0]}"))
    total = self_test_total()
    print(f"自检：{ok}/{total} 通过")
    # 书侧（`STYLE`／`README`）抄的「本工具的夹具条数」也要等于这个 total。
    # 放在自检末尾是因为**这里才知道真实条数**，而它零额外开销：
    # 本来就要跑这一趟（`pre-commit` 第一关）。
    return (0 if ok == total else 1) | sc.report("lint_book", total)


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
    stats: dict[str, tuple[int, int, int]] = {}
    for f in files:
        cid, text = check_chapter(f, ctx)
        if cid:
            chapters[cid] = text
        n = len(re.findall(r"[\u4e00-\u9fff]", text))
        # PLAN.md 的「✅ N 字」一律取这里的**有效字数**（不是汉字数）——
        # 这行注释曾写成「取汉字数」而与实现相反，是又一处「注释与代码各说各话」。
        # 代码行占比用来解释「为什么汉字比计划少并不等于偷工减料」。
        code = code_lines_of(text)
        effective = n + CODE_LINE_EQUIV * len(code)
        if cid:
            stats[cid] = (n, len(code), effective)      # 汉字／围栏行／有效字
        if not args.quiet:
            planned = ctx["plan_chapters"].get(cid)
            tail = f" / 计划 {planned}（达成 {effective / planned:.0%}）" if planned else ""
            print(f"  {f.name}  有效字数 {effective}（汉字 {n} + 代码 {len(code)} 行）{tail}")

    check_duplicates(chapters, rep)
    check_blank_lines(rep)
    ref_counts = check_cross_refs(chapters, rep)
    check_ledger_landings(rep)
    check_project_wiring(rep)
    check_measurement_refs(rep)

    # 书侧那两份文档（`STYLE`／`README`）里抄了一遍的实跑值：逐处与盘上比。
    # `--only` 时实跑值不完整（只有指定的章），比出来的差是假的——同样跳过。
    style_checked = 0
    inventory_checked = 0
    if args.only is None:
        style_checked = check_style_numbers(rep, stats, ctx["plan_chapters"])
        check_style_claims_wired(rep)
        inventory_checked = check_style_inventory(rep)

    ref_by_part = cross_ref_totals(ref_counts)
    ref_total = dict.fromkeys(REF_TALLY_KEYS, 0)
    for c in ref_by_part.values():
        for k in REF_TALLY_KEYS:
            ref_total[k] += c[k]

    # 台账与正文里那三个数（如果写了）与实跑逐处比：**写了就必须相等，没写则沉默**。
    # `--only` 时实跑值不完整（只覆盖指定的章），比出来的差是假的——跳过并如实说明。
    tally_checked = 0
    if args.only is None:
        tally_checked = check_ref_tally(rep, chapters, ref_by_part, ref_total)

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

    # 引用复核的三个数：**实跑**报出来，供篇收尾那一格直接抄。
    # 以前它们是人在一次运行里自己数的（41／38／214 都是这么来的），
    # 而「手写的数」只能靠人复查——与它同族的那些数（篇幅、术语、落点）全都进门了。
    # 台账里写了这三个数的那几句已于上一段逐处比过（`tally_checked` 是比过的断言个数），
    # 所以「抄进台账」这一步不再是凭据之外的动作。
    scope_note = (f"台账与正文里写了 {tally_checked} 个数，逐处相符" if args.only is None
                  else "--only：台账与正文里那几个数不参与对账")
    print()
    print(f"引用复核（本次校验 {len(files)} 章；{scope_note}）：小节级引用 {ref_total['小节级']} 处"
          f" ｜ 章级引用 {ref_total['章级']} 处 ｜ 悬空 {ref_total['悬空']} 处")
    for part in sorted(ref_by_part):
        c = ref_by_part[part]
        if not any(c.values()):
            continue
        print(f"  ↳ 第 {part} 篇：小节级 {c['小节级']} ｜ 章级 {c['章级']} ｜ 悬空 {c['悬空']}")
    if args.only is None:
        print(f"书侧复述（`STYLE`／`README` 里「实跑值的复述」）：本次比过 {style_checked} 处"
              + ("，逐处相符" if not any('书侧' in e for e in rep.errors)
                 else "，其中有不符（见上）"))
        print(f"书侧库存声明（`STYLE`／`README`／`PLAN` 里「目录体积／文件数／唯一链接数」）："
              f"本次比过 {inventory_checked} 处"
              + ("，逐处相符" if not any('库存声明' in e for e in rep.errors)
                 else "，其中有不符（见上）"))
    print()
    print(f"汇总：错误 {len(rep.errors)} ｜ 警告 {len(rep.warnings)}")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
