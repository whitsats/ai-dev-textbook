#!/usr/bin/env python
"""10.6 的交付物：**两份移动端题库，拼成一份可核对的索引。**

第 10 篇的每一章都交一份「可核对的考点索引」，而这一章第一次要同时处理**两份**
题库（Android 1,136 道、Flutter-Dart 714 道），并且它们的**格式不一样**：

    Android   `## 1. Android 多线程编程（126 道）` ＋ `**答案**` 另起一段
    Flutter   `## Dart语言特性` ＋ `**答案：** 同一行的正文`

格式不一样这件事本身就是本章的读数之一——**别人整理的题库，连「一道题长什么样」
都不统一**，所以本章的动作不是「搬答案」，而是**先数一遍这三件事**：

    ① 声明数与实数对不对得上（两份都在卷首声明了逐专题的题数）；
    ② 答案里有多少是**模板句**（同一句话被几十道题共用）；
    ③ 题面里混进了多少 OCR 与水印噪声。

    python tools/mobile_index.py --offline     # 两库地形图、处置、素材可用性、反向索引
    python tools/mobile_index.py --check       # 与正文 10.6 的表与读数逐处对账
    python tools/mobile_index.py --self-test   # 夹具（改一个题数／一个处置／一个计数就红）

对账各自对应一种**不会报错**的漂移：

① **专题名集合**——正文的表漏一行，表看上去还是完整的；
② **逐行的题数与章数**——手抄时把 126 抄成 162，没有任何检查看得见；
③ **每个专题的处置**——写错了，读者会去复习一份他不该看的专题；
④ **素材可用性的三个标量**——「模板答案 43 道」是本章立论的一半，它也要能复算；
⑤ **反向索引的每一格**——两列各一个数，抄串列是最容易犯的错；
⑥ **题库自身的声明**——卷首写「126 道」，里面到底有几个 `#### N.`（素材是别人的）。

**这里的两张判据表是原创的、写在脚本里**：专题的处置（`DISPOSITION`）与题面要数的
词（`PROBE_WORDS`）。正文只是它们的投影——改判据要动代码，而代码进提交门。
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BANKS = ROOT / "sources" / "06-求职冲刺"
CHAPTER = ROOT / "book" / "10-求职冲刺" / "10.6-移动端考点：Android 与 Flutter-Dart.md"

ANDROID = "Android面试题合集-1136道.md"
FLUTTER = "Flutter-Dart面试题合集-714道.md"

#: 两份题库各自的声明题数（抄自文件名与卷首；**用于与数出来的题数对账**）。
DECLARED_TOTAL: dict[str, int] = {ANDROID: 1136, FLUTTER: 714}

#: Android 的八个专题（顺序即题库里的顺序；识别靠「这一行含这个串」）。
ANDROID_SECTIONS: tuple[str, ...] = (
    "Android 多线程编程", "Android 架构设计", "Android 内存管理", "Android 视图体系",
    "Android 四大组件", "Android 网络编程", "Android 性能优化", "Kotlin 语言特性",
)

#: Flutter 的六个分类（同上）。
FLUTTER_SECTIONS: tuple[str, ...] = (
    "Dart语言特性", "Flutter框架原理", "Flutter路由与导航", "Flutter性能优化",
    "Widget与状态管理", "原生平台集成",
)

#: 每个专题的处置（**原创判据**：按「AI 应用开发岗会不会问」判，而不是按难度）。
#: 留 ＝ 问法本身就是岗位要的；换视角 ＝ 题留、例子要换成 Python／AI／端侧栈；
#: 弃 ＝ 岗位不问（栈名去掉就不成立的那些，如 View 体系、Activity 生命周期）。
DISPOSITION: dict[str, str] = {
    # Android 八专题
    "Android 多线程编程": "换视角",
    "Android 架构设计": "留",
    "Android 内存管理": "换视角",
    "Android 视图体系": "弃",
    "Android 四大组件": "弃",
    "Android 网络编程": "换视角",
    "Android 性能优化": "留",
    "Kotlin 语言特性": "换视角",
    # Flutter 六分类
    "Dart语言特性": "弃",
    "Flutter框架原理": "换视角",
    "Flutter路由与导航": "弃",
    "Flutter性能优化": "留",
    "Widget与状态管理": "换视角",
    "原生平台集成": "留",
}

#: 题面里要数的词（**本章第二条判据：两列反向索引**——移动端题库问得多的那一列，
#: 与 AI／端侧必问而两份题库几乎都不问的那一列，各数一次）。
PROBE_WORDS: tuple[str, ...] = (
    # 反向：AI 岗必问、移动端题库基本不问
    "大模型", "模型", "推理", "端侧", "on-device", "TFLite", "ML Kit", "词元",
    "Token", "流式", "SSE", "向量", "RAG", "提示", "成本", "评测", "量化", "剪枝",
    # 对照：移动端题库问得多、且跨栈成立
    "异步", "线程", "内存", "泄漏", "生命周期", "状态", "缓存", "网络", "性能", "渲染",
)

#: 判定「模板答案」的阈值：**同一个开场句被多少道题共用**才算模板（PLAN 的预警值是 20）。
TEMPLATE_MIN_REPEAT = 20
#: 少于这个字数的答案不参与模板判定（「略」「同上」这种短句不算模板，是空答）。
TEMPLATE_MIN_LEN = 20
#: 「开场句」取答案的前这个字数。**不按整句比**：同一句模板在 43 道题里有 35 道连
#: 尾巴都逐字相同、另 8 道尾巴被 OCR 截断或接上了别的段落——按整句比会把它们分成两组，
#: 于是「模板 43 道」这句话就复算不出来（两种数都报，见 `template_exact_qs`）。
TEMPLATE_LEAD_LEN = 30

RE_SECTION = re.compile(r"^##\s+(?!#)(.*)$")
RE_CHAPTER = re.compile(r"^###\s*第(\d+)\s*章")
RE_Q = re.compile(r"^####\s*(\d+)\s*[.．]\s*(\S.*)$")
#: 两种写法一起认：`**答案**`（另起一段）与 `**答案：** 正文`（同一行）。
#: 只认前一种的话，Flutter 那 714 道会全部读成空答案（第一次就踩了）。
RE_ANSWER = re.compile(r"^\*\*答案\s*[:：]?\s*\*\*\s*(.*)$")
#: Android 卷首的专题目录：`- Android 多线程编程（126 道）`。
RE_ANDROID_DECL = re.compile(r"^[-*]\s*(.+?)\s*[（(]\s*(\d+)\s*道\s*[）)]\s*$")
#: 题面里的 OCR 与水印噪声（两份题库都有，Flutter 更多）。
RE_OCR = re.compile(r"OCR")
RE_WATERMARK = re.compile(r"[0-9A-F]{5,}|PR-\d+")


class Bank:
    """一份题库的读数：专题、章节、题、答案与它自己的声明。"""

    def __init__(self, name: str, kind: str, text: str | None = None) -> None:
        self.name = name
        self.kind = kind  # "android" | "flutter"
        self.path = BANKS / name
        #: 抽取出来的文本里有 CJK 兼容字与全角括号，**先归一化再数**——
        #: 不归一化的话 `（126 道）` 这种声明行根本匹配不上。
        raw = text if text is not None else self.path.read_text(encoding="utf-8")
        self.lines = [unicodedata.normalize("NFKC", l).strip() for l in raw.splitlines()]
        self.sections_named = ANDROID_SECTIONS if kind == "android" else FLUTTER_SECTIONS
        self.bounds = self._section_bounds()
        self.questions = self._questions()

    @property
    def sections(self) -> tuple[str, ...]:
        return tuple(self.sections_named)

    def _section_bounds(self) -> list[tuple[int, str]]:
        found: list[tuple[int, str]] = []
        for i, l in enumerate(self.lines):
            m = RE_SECTION.match(l)
            if not m:
                continue
            head = m.group(1).strip()
            hit = next((s for s in self.sections_named
                        if s.lower() in head.lower()), None)
            if hit is not None and (not found or found[-1][1] != hit):
                found.append((i, hit))
        return found

    def _questions(self) -> list[dict]:
        starts = [i for i, l in enumerate(self.lines) if RE_Q.match(l)]
        ends = starts[1:] + [len(self.lines)]
        out: list[dict] = []
        for i, end in zip(starts, ends):
            m = RE_Q.match(self.lines[i])
            seg = [l for l in self.lines[i:end] if l]
            answer = ""
            for k, l in enumerate(seg):
                am = RE_ANSWER.match(l)
                if am:
                    # 答案到下一个标题或下一个加粗小标题为止。**不能把整个提问段的尾巴
                    # 都当成答案**：两份题库都是“一节里的最后一题”后面紧跟着
                    # `## 下一节`／`### 第N章`／`### OCR待复核`，不收边界的话这几十道题的
                    # “答案”里全是下一节的标题（模板与中位长度两个读数都会跟着脏）。
                    body: list[str] = []
                    for nxt in seg[k + 1:]:
                        if nxt.startswith("#") or nxt.startswith("**"):
                            break
                        body.append(nxt)
                    answer = " ".join([am.group(1)] + body).strip()
                    break
            chapter = None
            for j in range(i, -1, -1):
                cm = RE_CHAPTER.match(self.lines[j])
                if cm:
                    chapter = int(cm.group(1))
                    break
            section = None
            for b, name in self.bounds:
                if b < i:
                    section = name
            out.append({"section": section, "chapter": chapter,
                        "title": m.group(2) if m else self.lines[i], "answer": answer})
        return out

    def by_section(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {s: [] for s in self.sections_named}
        for q in self.questions:
            if q["section"] in out:
                out[q["section"]].append(q)
        return out

    def chapters_of(self, section: str) -> int:
        """这一专题下有几个 `### 第N章`（**章号不连续**——Flutter 有并列的章号段）。"""
        start = next((i for i, n in self.bounds if n == section), None)
        end = next((i for i, n in self.bounds if i > (start or -1)), len(self.lines))
        if start is None:
            return 0
        return sum(1 for l in self.lines[start:end] if RE_CHAPTER.match(l))

    def section_qs(self) -> int:
        return sum(len(v) for v in self.by_section().values())

    def declared(self) -> dict[str, int]:
        """题库卷首声明出来的逐专题题数（**它的自报数，未必等于实数**）。"""
        out: dict[str, int] = {}
        if self.kind == "android":
            for l in self.lines:
                m = RE_ANDROID_DECL.match(l)
                if m and m.group(1).strip() in self.sections_named:
                    out[m.group(1).strip()] = int(m.group(2))
        else:
            # Flutter 的声明在「整理统计」那张表里：`| Dart语言特性 | 158 | 158 |`
            for l in self.lines:
                if not l.startswith("|"):
                    continue
                cells = [c.strip() for c in l.strip("|").split("|")]
                if len(cells) >= 2 and cells[0] in self.sections_named:
                    num = re.sub(r"[^\d]", "", cells[1])
                    if num:
                        out[cells[0]] = int(num)
        return out

    def answers(self) -> list[str]:
        return [q["answer"] for q in self.questions]

    @staticmethod
    def _lead(answer: str) -> str:
        return answer[:TEMPLATE_LEAD_LEN]

    def templates(self) -> dict[str, int]:
        """被 ≥TEMPLATE_MIN_REPEAT 道题共用的那个开场句（本章的素材质量读数）。"""
        c = Counter(self._lead(a) for a in self.answers() if len(a) >= TEMPLATE_MIN_LEN)
        return {k: n for k, n in c.items() if n >= TEMPLATE_MIN_REPEAT}

    def template_qs(self) -> int:
        return sum(self.templates().values())

    def template_exact_qs(self) -> int:
        """其中整句连尾巴都逐字相同的道数（**同一个模板的两层读数**）。

        只在已经超过阈值的那一组里数——否则「一道题共用一句」也会被报成模板。"""
        leads = self.templates()
        c = Counter(a for a in self.answers() if len(a) >= TEMPLATE_MIN_LEN)
        return max((n for a, n in c.items() if self._lead(a) in leads), default=0)

    def ocr_qs(self) -> int:
        return sum(1 for q in self.questions if RE_OCR.search(q["title"]))

    def watermark_qs(self) -> int:
        return sum(1 for q in self.questions if RE_WATERMARK.search(q["title"]))

    def median_answer(self) -> int:
        lens = sorted(len(a) for a in self.answers())
        return lens[len(lens) // 2] if lens else 0

    def probe(self, word: str) -> int:
        """词出现在多少道**题面**里（题面是「会被问什么」的那一层）。

        **英文词件边界、中文词用子串**——这不是讲究：`Messenger` 里含 `sse`、
        `Fragment` 里含 `rag`，按子串数的话「SSE 2 道、RAG 1 道」这两个数全是假的，
        而反向索引那一列的立论恰恰是「这些词一道都没有」（开发时真踩过，夹具里留着）。"""
        if re.fullmatch(r"[A-Za-z0-9 .\-]+", word):
            pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(word).replace(r"\ ", r"\s*")
                             + r"(?![A-Za-z0-9])", re.I)
            return sum(1 for q in self.questions if pat.search(q["title"]))
        return sum(1 for q in self.questions if word in q["title"])


def both() -> tuple[Bank, Bank]:
    return Bank(ANDROID, "android"), Bank(FLUTTER, "flutter")


def all_sections() -> tuple[str, ...]:
    return ANDROID_SECTIONS + FLUTTER_SECTIONS


# ---- 正文那一侧 ---------------------------------------------------------


def parse_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    tables: list[tuple[list[str], list[list[str]]]] = []
    header: list[str] | None = None
    rows: list[list[str]] = []

    def flush() -> None:
        nonlocal header, rows
        if header is not None:
            tables.append((header, rows))
        header, rows = None, []

    for ln in text.splitlines():
        if not ln.lstrip().startswith("|"):
            flush()
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if header is None:
            header = cells
        else:
            rows.append(cells)
    flush()
    return tables


def pick(tables, *keys: str):
    """找一个表：**keys[0] 落在第一列表头、keys[1] 落在第二列表头**，其余落在任意列。

    识别口径不靠标题里的词猜，是因为本章至少有三张表都以「专题／分类」开头——
    地形图表、处置表与反向索引表都能互相冒充。"""
    for head, rows in tables:
        if len(head) < 2 or keys[0] not in head[0] or keys[1] not in head[1]:
            continue
        if all(any(k in h for h in head) for k in keys[2:]):
            return head, rows
    return None


def _num(cell: str) -> int | None:
    c = re.sub(r"[^\d]", "", cell)
    return int(c) if c else None


def check_banks(a: Bank, f: Bank) -> list[str]:
    problems: list[str] = []
    for bank in (a, f):
        wanted = DECLARED_TOTAL[bank.name]
        if len(bank.questions) != wanted:
            problems.append(
                f"题库自身：{bank.name} 声明 {wanted} 道，而里面数出 {len(bank.questions)} 道")
        miss = [s for s in bank.sections_named if s not in [n for _, n in bank.bounds]]
        if miss:
            problems.append(f"题库自身：{bank.name} 里没找到这些专题标题：{'、'.join(miss)}")
        # **声明数与实数对不上同样是一次发现**：这里只报到人脸上，不判错——
        # 两份题库的卷首目录都是合并 PDF 时抄的，未必与正文里的 `####` 一致。
        for name, n in bank.declared().items():
            got = len(bank.by_section().get(name, []))
            if n != got:
                problems.append(f"题库自身：{bank.name} 声明「{name} {n} 道」，数出 {got} 道")
    for name in DISPOSITION:
        if name not in all_sections():
            problems.append(f"处置表里有不在专题表里的名字：{name}")
    return problems


def check_chapter(a: Bank, f: Bank, path: Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    tables = parse_tables(text)
    by_sec = {**a.by_section(), **f.by_section()}

    # ① 地形图表：两张（Android 按专题、Flutter 按分类），列序 名称 ｜ 题数 ｜ 章数 ｜ 处置
    for bank, key in ((a, "专题"), (f, "分类")):
        got = pick(tables, key, "题数")
        if got is None:
            problems.append(f"没找到{bank.kind} 的地形图表（表头第一列要是「{key}」、第二列「题数」）")
            continue
        head, rows = got
        seen = {r[0]: r for r in rows if len(r) >= 2}
        for s in bank.sections_named:
            r = seen.get(s)
            if r is None:
                problems.append(f"地形图表缺「{s}」（题库里有 {len(by_sec[s])} 道）")
                continue
            if _num(r[1]) != len(by_sec[s]):
                problems.append(f"专题「{s}」题数写 {r[1]}，题库里是 {len(by_sec[s])}")
            if len(r) > 2 and _num(r[2]) != bank.chapters_of(s):
                problems.append(f"专题「{s}」章数写 {r[2]}，题库里是 {bank.chapters_of(s)}")
            if len(r) > 3:
                want = DISPOSITION[s]
                if want not in r[3]:
                    problems.append(f"专题「{s}」的处置写「{r[3]}」，判据里是「{want}」")
        for name in seen:
            if name not in bank.sections_named:
                problems.append(f"地形图表里的「{name}」不在{bank.kind} 的专题里")

    # ② 处置的三堆：**只核「三个取值写在同一句里」的那一行**。
    #    不能见一个 `弃 N 道` 就核：正文里到处是单块读数（「弃 158 道 Dart 语言特性」），
    #    而它们都是对的——第一次实现就是这么报出了两条假阳性（见 self_test 里那条夹具）。
    tally: dict[str, int] = {k: 0 for k in ("留", "换视角", "弃")}
    for s, d in DISPOSITION.items():
        tally[d] += len(by_sec[s])
    combos = re.findall(r"留\s*\d+\s*道[^\n]*?换视角\s*\d+\s*道[^\n]*?弃\s*\d+\s*道", text)
    combo = re.findall(r"留\s*(\d+)\s*道[^\n]*?换视角\s*(\d+)\s*道[^\n]*?弃\s*(\d+)\s*道", text)
    if not combos:
        problems.append("找不到三堆那一行（要把三个取值与三个数写在同一句里，否则检查够不到）")
    for got in combo:
        for k, v in zip(("留", "换视角", "弃"), got):
            if int(v) != tally[k]:
                problems.append(f"三堆：正文写「{k} {v} 道」，算出来是 {tally[k]}")

    # ③ 两库的总账：**只核那一行式**（`两库共 N 道、M 个专题`）——
    #    正文别处会写「Android 一份（1,136 道 / 8 个专题 / 124 章）」，那种单库说法也是对的。
    total = re.search(r"两库共\s*\*{0,2}([\d,]+)\*{0,2}\s*道[、，]\s*\*{0,2}(\d+)\*{0,2}\s*个专题",
                      text)
    if total is None:
        problems.append("读数：找不到两库的总账（要写成「两库共 N 道、M 个专题」）")
    else:
        if total.group(1).replace(",", "") != str(len(a.questions) + len(f.questions)):
            problems.append(f"读数：正文写「两库共 {total.group(1)} 道」，算出来是 "
                            f"{len(a.questions) + len(f.questions)}")
        if int(total.group(2)) != len(all_sections()):
            problems.append(f"读数：正文写「{total.group(2)} 个专题」，算出来是 "
                            f"{len(all_sections())}")

    # ④ 素材可用性的四个标量（本章立论的另一半：**模板答案、OCR、水印**）
    #    **允许三种写法**：两库合计、或其中一份的数（另一份是 0）。这是正文的真实需要——
    #    「Android 一份：模板答案 0 道」是本章要说的一半的话，不能因为它是 0 就报错。
    #    而错一位（枚 44 道、40 写成 43）仍然全报，阀度没有变松。
    for pat, label, per_bank in (
        (r"模板答案\s*\*{0,2}(\d+)\*{0,2}\s*道", "模板答案",
         (a.template_qs(), f.template_qs())),
        (r"逐字相同\s*\*{0,2}(\d+)\*{0,2}\s*道", "模板的逐字相同数",
         (a.template_exact_qs(), f.template_exact_qs())),
        (r"OCR\s*未识别\s*\*{0,2}(\d+)\*{0,2}\s*道", "OCR 未识别",
         (a.ocr_qs(), f.ocr_qs())),
        (r"题面含水印\s*\*{0,2}(\d+)\*{0,2}\s*道", "题面含水印",
         (a.watermark_qs(), f.watermark_qs())),
    ):
        allowed = {per_bank[0], per_bank[1], sum(per_bank)}
        hits = re.findall(pat, text)
        if not hits:
            problems.append(f"读数：正文里找不到「{label}」（要按规范写法写，否则检查够不到）")
            continue
        for got in hits:
            if int(got) not in allowed:
                problems.append(
                    f"读数：正文写「{label} {got}」，两库分别 "
                    f"{per_bank[0]}／{per_bank[1]}（合计 {sum(per_bank)}）")

    # ④ 反向索引：一张两列的表，**每一格都要等于对应题库里数出的值**
    got = pick(tables, "词", "Android")
    if got is None:
        problems.append("没找到反向索引表（表头要是「词 ｜ Android ｜ Flutter」）")
    else:
        _, rows = got
        for r in rows:
            if len(r) < 3:
                continue
            word = r[0].strip("`*")
            if word not in PROBE_WORDS:
                problems.append(f"反向索引表里的「{word}」不在 PROBE_WORDS 里（数不了它就核不了它）")
                continue
            for bank, cell in ((a, r[1]), (f, r[2])):
                if _num(cell) != bank.probe(word):
                    problems.append(
                        f"反向索引：正文写「{word} {cell}」，{bank.kind} 题面里数出来是 "
                        f"{bank.probe(word)}")
    return problems


def print_index(a: Bank, f: Bank) -> None:
    print(f"两库共 {len(a.questions) + len(f.questions):,} 道 "
          f"（{a.name[:a.name.find('面试题')]} {len(a.questions):,} ＋ "
          f"{f.name[:f.name.find('面试题')]} {len(f.questions):,}）、"
          f"{len(all_sections())} 个专题\n")
    for bank, head in ((a, "专题"), (f, "分类")):
        print(f"{head:<22}{'题数':>6}{'章数':>6}{'声明':>6}   处置")
        for s in bank.sections_named:
            n = len(bank.by_section()[s])
            d = bank.declared().get(s)
            flag = "" if d == n else f"（声明 {d}）"
            print(f"{s:<22}{n:>6}{bank.chapters_of(s):>6}{d if d is not None else '-':>6}   "
                  f"{DISPOSITION[s]}{flag}")
        print(f"{'合计':<22}{bank.section_qs():>6}"
              f"{sum(bank.chapters_of(s) for s in bank.sections_named):>6}"
              f"{DECLARED_TOTAL[bank.name]:>6}\n")
    tally: dict[str, int] = {}
    for s, d in DISPOSITION.items():
        n = len(a.by_section().get(s, []) or f.by_section().get(s, []))
        tally[d] = tally.get(d, 0) + n
    print("三堆：" + "、".join(f"{k} {v:,} 道" for k, v in tally.items()))
    print("\n素材可用性：")
    for bank in (a, f):
        for lead, n in bank.templates().items():
            print(f"  {bank.kind:<8}模板答案 {n} 道（共用这一句开场：{lead}⋯）"
                  f"；逐字相同 {bank.template_exact_qs()} 道")
    for name, fn in (    ("模板答案", lambda b: b.template_qs()),
                     ("逐字相同", lambda b: b.template_exact_qs()),
                     ("OCR 未识别", lambda b: b.ocr_qs()),
                     ("题面含水印", lambda b: b.watermark_qs()),
                     ("答案中位长度", lambda b: b.median_answer())):
        print(f"  {name:<12}{fn(a):>6}（android）{fn(f):>6}（flutter）")
    print(f"\n题面关键词（提到它的有几道）：")
    for w in PROBE_WORDS:
        print(f"  {w:<12}{a.probe(w):>5}{f.probe(w):>6}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="只读两份题库，不联网")
    ap.add_argument("--check", action="store_true", help="与正文 10.6 的表与读数对账")
    ap.add_argument("--self-test", action="store_true", help="只跑夹具")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    a, f = both()
    problems = check_banks(a, f)

    if not args.check:
        print_index(a, f)
        if problems:
            print("\n题库自身的对账：")
            for p in problems:
                print(f"  ✖ {p}")
            return 1
        return 0

    if not CHAPTER.exists():
        print(f"未找到 {CHAPTER.relative_to(ROOT).as_posix()}：本章还没有正文，索引要等正文落地")
        return 0
    problems += check_chapter(a, f, CHAPTER)
    if problems:
        for p in problems:
            print(f"  ✖ {p}")
        print(f"\n汇总：{len(problems)} 处与题库不一致。修法：跑 --offline 取真值，再改正文。")
        return 1
    print(f"✔ 移动端索引对账通过：两份题库共 {len(a.questions) + len(f.questions):,} 道、"
          f"{len(all_sections())} 个专题，地形图表／章数／处置／素材可用性／反向索引逐处等于算出来的值。")
    return 0


# ---- 夹具 --------------------------------------------------------------

FAKE_ANDROID = """# 假 Android 题库

> 来源：合并整理。

## 专题目录

- 假A（2 道）
- 假B（1 道）

---

## 1. 假A(2 道)

### 第1章 线程基础

#### 1. 缓存怎么用？

**考点**

略

**解答过程**

略

**答案**

这一句是模板：应结合题目所涉及的机制进行处理，明确对象职责与生命周期，采用框架推荐的 API。

#### 2. 异步怎么做？

**答案**

这一句是模板：应结合题目所涉及的机制进行处理，明确对象职责与生命周期，采用框架推荐的 API。

## 2. 假B(1 道)

### 第2章 内存

#### 3. Messenger 通信怎么做？ AB12C3

**答案**

先看引用链，再用工具抓快照，最后比对两次快照的差集。
"""

FAKE_FLUTTER = """# 假 Flutter 题库

## 整理统计

| 分类 | 题目数 | 已匹配答案 |
|---|---:|---:|
| 假C | 1 | 1 |
| 假D | 1 | 1 |
| **合计** | **2** | **2** |

---

## 假C

### 第1章 状态

#### 1. 状态管理怎么选？

**考点：** 略

**解答过程：** 略

**答案：** 这一句是模板：应结合题目所涉及的机制进行处理，明确对象职责与生命周期，采用框架推荐的 API。

## 假D

### 第2章 平台

#### 2. 【第 2 题 OCR 未完整识别，请对照原 PDF 复核】

**答案：** 插件通道是两端唯一的正式接口，参数与生命周期都要在两端各写一次。
"""

FAKE_CHAPTER = """# 10.6 假章

两库共 5 道、4 个专题。素材可用性：模板答案 2 道、逐字相同 2 道、OCR 未识别 1 道、题面含水印 1 道。

三堆：留 3 道、换视角 1 道、弃 1 道。

| 专题 | 题数 | 章数 | 处置 |
| --- | ---: | ---: | --- |
| 假A | 2 | 1 | 留 |
| 假B | 1 | 1 | 弃 |

| 分类 | 题数 | 章数 | 处置 |
| --- | ---: | ---: | --- |
| 假C | 1 | 1 | 换视角 |
| 假D | 1 | 1 | 留 |

| 词 | Android | Flutter |
| --- | ---: | ---: |
| 缓存 | 1 | 0 |
| 大模型 | 0 | 0 |
| SSE | 0 | 0 |
"""


def _fake_android(text: str | None = None) -> Bank:
    return Bank(ANDROID, "android", text=text or FAKE_ANDROID)


def _fake_flutter(text: str | None = None) -> Bank:
    return Bank(FLUTTER, "flutter", text=text or FAKE_FLUTTER)


def _fake_chapter(tmp: Path, mutate=None) -> Path:
    p = tmp / "10.6-假章.md"
    text = FAKE_CHAPTER
    if mutate:
        text = mutate(text)
    p.write_text(text, encoding="utf-8")
    return p


def self_test() -> int:
    import tempfile
    from pathlib import Path as _P

    saved = (ANDROID_SECTIONS, FLUTTER_SECTIONS, dict(DISPOSITION),
             DECLARED_TOTAL[ANDROID], DECLARED_TOTAL[FLUTTER], PROBE_WORDS,
             globals()["TEMPLATE_MIN_REPEAT"])
    cases: list[tuple[str, str, bool, str]] = []

    def run(name: str, expect: str, mutate=None, declared=(3, 2),
            probe=("缓存", "大模型", "SSE")) -> None:
        globals()["ANDROID_SECTIONS"] = ("假A", "假B")
        globals()["FLUTTER_SECTIONS"] = ("假C", "假D")
        globals()["PROBE_WORDS"] = tuple(probe)
        globals()["TEMPLATE_MIN_REPEAT"] = 2
        DECLARED_TOTAL[ANDROID], DECLARED_TOTAL[FLUTTER] = declared
        DISPOSITION.clear()
        DISPOSITION.update({"假A": "留", "假B": "弃", "假C": "换视角", "假D": "留"})
        with tempfile.TemporaryDirectory() as td:
            tmp = _P(td)
            a, f = _fake_android(), _fake_flutter()
            bad = check_chapter(a, f, _fake_chapter(tmp, mutate)) + check_banks(a, f)
            good = (not bad) if expect == "应通过" else bool(bad)
            cases.append((name, expect, good, bad[0] if bad else "（没有报错）"))

    run("干净的一份", "应通过")
    run("Android 专题题数抄错", "应报错",
        lambda t: t.replace("| 假A | 2 | 1 | 留 |", "| 假A | 3 | 1 | 留 |"))
    run("Flutter 分类题数抄错", "应报错",
        lambda t: t.replace("| 假C | 1 | 1 | 换视角 |", "| 假C | 2 | 1 | 换视角 |"))
    run("章数抄错", "应报错", lambda t: t.replace("| 假B | 1 | 1 | 弃 |", "| 假B | 1 | 2 | 弃 |"))
    run("地形图表漏一行", "应报错", lambda t: t.replace("| 假B | 1 | 1 | 弃 |\n", ""))
    run("处置判定写错", "应报错", lambda t: t.replace("| 假A | 2 | 1 | 留 |", "| 假A | 2 | 1 | 弃 |"))
    run("三堆里留的题数抄错", "应报错", lambda t: t.replace("留 3 道", "留 2 道"))
    run("模板答案读数抄错", "应报错", lambda t: t.replace("模板答案 2 道", "模板答案 3 道"))
    run("逐字相同抄错", "应报错", lambda t: t.replace("逐字相同 2 道", "逐字相同 1 道"))
    run("OCR 读数抄错", "应报错", lambda t: t.replace("OCR 未识别 1 道", "OCR 未识别 2 道"))
    run("水印读数抄错", "应报错", lambda t: t.replace("题面含水印 1 道", "题面含水印 2 道"))
    # 单库的 0 是合法写法（“Android 一份：模板答案 0 道”是本章要说的一半的话）——
    # 这一条守着「允许集合」那条口径不走偏成「只认合计」。
    run("单库的 0 是合法写法（多写一句 Android 模板答案 0 道）", "应通过",
        lambda t: t + "\nAndroid 一份：模板答案 0 道、题面含水印 0 道。\n")
    run("专题数抄错", "应报错", lambda t: t.replace("两库共 5 道、4 个专题", "两库共 5 道、3 个专题"))
    run("反向索引抄串列", "应报错",
        lambda t: t.replace("| 缓存 | 1 | 0 |", "| 缓存 | 0 | 1 |"))
    run("反向索引里的词没登记", "应报错",
        lambda t: t.replace("| 大模型 | 0 | 0 |", "| 推理 | 0 | 0 |"))
    run("英文词不在词内匹配：把 Messenger 里的 sse 记成 1 道就要红", "应报错",
        lambda t: t.replace("| SSE | 0 | 0 |", "| SSE | 1 | 0 |"))
    run("两库题数标量抄错", "应报错", lambda t: t.replace("两库共 5 道", "两库共 4 道"))
    run("专题名对不上题库", "应报错",
        lambda t: t.replace("| 假C | 1 | 1 | 换视角 |", "| 假E | 1 | 1 | 换视角 |"))
    run("题库声明与数出的题数不符", "应报错", declared=(1136, 714))

    # 两份题库的卷首都自己声了一名“本专题多少道”，而它是合并 PDF 时抄的——
    # 所以“声明与实数对不上”本身是一条要报出来的发现（夹具里改卷首那一行）。
    saved_total = (DECLARED_TOTAL[ANDROID], DECLARED_TOTAL[FLUTTER])
    globals()["ANDROID_SECTIONS"] = ("假A", "假B")
    globals()["FLUTTER_SECTIONS"] = ("假C", "假D")
    DECLARED_TOTAL[ANDROID], DECLARED_TOTAL[FLUTTER] = 3, 2
    bad = check_banks(_fake_android(FAKE_ANDROID.replace("- 假A（2 道）", "- 假A（3 道）")),
                      _fake_flutter())
    cases.append(("题库卷首声明「假A 3 道」而里面只有 2 道", "应报错", bool(bad),
                  bad[0] if bad else "（没有报错）"))
    bad = check_banks(_fake_android(FAKE_ANDROID.split("## 2. 假B")[0]), _fake_flutter())
    cases.append(("题库被截断（假B 整节没了）", "应报错", bool(bad),
                  bad[0] if bad else "（没有报错）"))

    (globals()["ANDROID_SECTIONS"], globals()["FLUTTER_SECTIONS"],
     DECLARED_TOTAL[ANDROID], DECLARED_TOTAL[FLUTTER],
     globals()["PROBE_WORDS"], globals()["TEMPLATE_MIN_REPEAT"]) = saved[:2] + saved_total + saved[5:]
    globals()["TEMPLATE_MIN_REPEAT"] = saved[6]
    DISPOSITION.clear()
    DISPOSITION.update(saved[2])
    a, f = both()
    real = check_banks(a, f)
    cases.append(("真实两份题库自洽（题数、专题名、卷首声明）", "应通过",
                  not real, real[0] if real else "（没有报错）"))
    real_ch = check_chapter(a, f, CHAPTER) if CHAPTER.exists() else []
    cases.append(("真实正文（10.6）与两份题库逐处一致", "应通过",
                  not real_ch, real_ch[0] if real_ch else "（没有报错／本章还没有正文）"))
    two_layer = (f.template_qs(), f.template_exact_qs())
    cases.append(("真实 Flutter 题库的两层模板读数（开场句 43 道、逐字相同 40 道）", "应通过",
                  two_layer == (43, 40), f"数出来是 {two_layer[0]}/{two_layer[1]}"))

    ok = sum(1 for _, _, good, _ in cases if good)
    for name, expect, good, msg in cases:
        print(f"  {'✔' if good else '✖'} {name}（{expect}）"
              + ("" if good else f"  ← {msg}"))
    print(f"自检：{ok}/{len(cases)} 通过")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
