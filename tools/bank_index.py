#!/usr/bin/env python
"""第 10 篇的交付物：**把题库收敛成一份可核对的考点索引。**

第 10 篇交出去的不是一个服务，是**题与账**——所以 10.4 的考点索引由这个脚本
从 `sources/06-求职冲刺/` 的题库里算出来，**进门核对**，落在这里而不是新树的 `app/` 里。

    python tools/bank_index.py --offline        # 九专题的题数与考点数 ＋ 专题归到哪些章
    python tools/bank_index.py --counts         # 两张「密度表」：2-gram 词频 ＋ 逐专题的考点词计数
    python tools/bank_index.py --check          # 与正文 10.4 的表与读数逐处对账
    python tools/bank_index.py --self-test      # 夹具（改一个条数／一个归属／一个词频就红）

对账各自对应一种**不会报错**的漂移：

① **专题名集合**——题库有九个专题，正文的表漏一个，表看上去还是完整的；
② **逐行的题数与考点数**——手抄时把 86 抄成 68，没有任何检查看得见；
③ **归到哪几章**——列错了章号，读者照着去翻，翻不到（而翻不到的人不会来问你）；
④ **题库自身**——文件标题声明 1,038 道，而里面到底有多少道 `###` 题（素材是别人的，
   声明与内容不符也要看得见）；
⑤ **考点词的计数**——正文里写「工具 30、并发 0」这类数，抄错一位没有任何人看得见。
   这一条连两种写法一起盖：**盲区表里的 `词 N` 格**与**围栏里那些读数块**（`工具 30 调用 30`）。
   口径写在脚本这头（`KEYWORDS`／`NGRAM_TOP`），正文只是它的投影。

「归到哪几章」那张映射表**写在这个脚本里**（它是原创判据，不是从题库里数出来的）——
放在这里而不是正文里，是因为正文会漂、脚本不会：改映射要动代码，而代码进提交门。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BANKS = ROOT / "sources" / "06-求职冲刺"
CHAPTER = ROOT / "book" / "10-求职冲刺" / "10.4-AI Agent 面试考点手册.md"
PLAN = ROOT / "PLAN.md"

DEFAULT_BANK = "AI-Agent面试题合集-1038道.md"

#: 九个专题各自归到本书的哪几章（**原创判据**：按章标题与题库专题名对齐，
#: 而不是按题面里出现了哪个词——那种数法会把「策略」「方法」这种词全捞进来）。
TOPIC_MAP: dict[str, tuple[str, ...]] = {
    "Agent规划与决策策略": ("3.4", "3.2"),
    "安全防护与对齐约束": ("3.8", "7.4"),
    "大语言模型原理与应用": ("3.1", "6.1", "6.2"),
    "多Agent协作框架设计": ("3.7",),
    "工具调用与函数编排": ("3.5", "6.3"),
    "记忆与上下文管理机制": ("3.6", "6.4"),
    "检索增强生成架构": ("5.1", "5.2", "5.3", "5.4"),
    "提示工程与链式推理": ("3.2", "3.3"),
    "系统可观测性与评估": ("3.9", "7.1", "7.2"),
}

#: 逐专题要数的考点词（**原创判据**：这一列是「面试会追问、而题库可能不问」的两类词，
#: 所以它们不是从语料里挑的，而是从本书第 3／5／6／7 篇的章目录里挑的）。
#: 正文里任何一个 `词 N` 都要在在这里登记，否则 --check 会当成「引用了未登记的词」报错。
KEYWORDS: dict[str, tuple[str, ...]] = {
    "Agent规划与决策策略": ("规划", "状态", "搜索", "目标", "反思", "决策", "动作"),
    "安全防护与对齐约束": ("攻击", "注入", "对齐", "权限", "越狱", "护栏", "泄露", "审核"),
    "大语言模型原理与应用": ("模型", "参数", "训练", "微调", "推理"),
    "多Agent协作框架设计": ("通信", "协作", "冲突", "多Agent", "成本", "角色", "编排"),
    "工具调用与函数编排": ("工具", "调用", "参数", "函数", "权限", "失败", "并发", "幂等"),
    "记忆与上下文管理机制": ("记忆", "上下文", "窗口", "压缩", "遗忘", "召回", "摘要"),
    "检索增强生成架构": ("检索", "向量", "评估", "重排", "召回", "分块", "切分"),
    "提示工程与链式推理": ("提示", "推理", "链", "思维"),
    "系统可观测性与评估": ("指标", "评估", "日志", "监控", "回归", "轨迹"),
}

#: 2-gram 词频实验只看榜首七个；其中被判为**虚词**的就在这里（判据 =「它指不出一个具体考点」）。
NGRAM_TOP = 7
STOPWORDS = ("理解", "考察", "设计", "中的", "方法", "机制")

RE_TOPIC = re.compile(r"^##\s+(.+?)（(\d+)道）\s*$")
RE_Q = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$")
RE_KP = re.compile(r"^\*\*考点\*\*\s*$")
RE_ANS = re.compile(r"^\*\*答案\*\*\s*$")


class Bank:
    """一份题库的读数：专题、题数、考点。"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.path = BANKS / name
        self.declared = 0
        self.topics: list[dict] = []
        self.answers: list[str] = []
        self._read()

    def _read(self) -> None:
        text = self.path.read_text(encoding="utf-8")
        head = next((l for l in text.splitlines() if l.startswith("# ")), "")
        m = re.search(r"(\d[\d,]*)\s*道", head)
        self.declared = int(m.group(1).replace(",", "")) if m else 0
        cur: dict | None = None
        want_kp = False
        want_ans = False
        for ln in text.splitlines():
            mt = RE_TOPIC.match(ln)
            if mt:
                cur = {"name": mt.group(1), "declared": int(mt.group(2)),
                       "qs": 0, "kp": []}
                self.topics.append(cur)
                want_kp = False
                continue
            if cur is None:
                continue
            if RE_Q.match(ln):
                cur["qs"] += 1
                want_kp = False
                continue
            if RE_KP.match(ln):
                want_kp = True
                want_ans = False
                continue
            if RE_ANS.match(ln):
                want_ans = True
                want_kp = False
                continue
            if want_kp and ln.strip():
                cur["kp"].append(ln.strip())
                want_kp = False
            elif want_ans and ln.strip():
                self.answers.append(ln.strip())
                want_ans = False

    @property
    def questions(self) -> int:
        return sum(t["qs"] for t in self.topics)

    @property
    def kp_count(self) -> int:
        return sum(len(t["kp"]) for t in self.topics)

    def distinct_kps(self) -> int:
        return len({k for t in self.topics for k in t["kp"]})

    def mean_kp_len(self) -> float:
        ks = [k for t in self.topics for k in t["kp"]]
        return sum(len(k) for k in ks) / len(ks) if ks else 0.0

    def mapping(self, topic: str) -> tuple[str, ...]:
        return TOPIC_MAP.get(topic, ())

    def ngram_top(self, n: int = 2, k: int = NGRAM_TOP) -> list[tuple[str, int]]:
        """按字面切 n-gram 数词——**这是本章第一条判据的那个失败实验**，不是索引方法。"""
        from collections import Counter
        c: Counter = Counter()
        for t in self.topics:
            for kp in t["kp"]:
                for i in range(len(kp) - n + 1):
                    c[kp[i:i + n]] += 1
        return c.most_common(k)

    def kw_counts(self, topic: str) -> list[tuple[str, int]]:
        """某个专题里，每个登记过的词出现在多少条考点里（一条只算一次）。"""
        kps = next((t["kp"] for t in self.topics if t["name"] == topic), [])
        return [(w, sum(1 for kp in kps if w in kp)) for w in KEYWORDS.get(topic, ())]

    def kp_len_of(self, topic: str) -> int:
        return next((len(t["kp"]) for t in self.topics if t["name"] == topic), 0)

    def mean_ans_len(self) -> float:
        return (sum(len(a) for a in self.answers) / len(self.answers)) if self.answers else 0.0

    def ans_with_digit(self) -> int:
        return sum(1 for a in self.answers if re.search(r"\d", a))

    def ans_with(self, word: str) -> int:
        return sum(1 for a in self.answers if word in a)


# ---- 正文那一侧：按表头认表 --------------------------------------------


def parse_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """把正文里的 Markdown 表读成 [(表头, 数据行), ...]。**按表头认表，不按列型猜。**"""
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


def pick(tables: list[tuple[list[str], list[list[str]]]], *keys: str):
    for head, rows in tables:
        if all(any(k in h for h in head) for k in keys):
            return head, rows
    return None


def plan_chapters() -> set[str]:
    found: set[str] = set()
    for ln in PLAN.read_text(encoding="utf-8").splitlines():
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if cells and re.fullmatch(r"\d+\.\d+", cells[0]):
            found.add(cells[0])
    return found


def _num(cell: str) -> int | None:
    c = cell.replace(",", "").replace("道", "").strip()
    return int(c) if re.fullmatch(r"\d+", c) else None


#: 正文里一个考点词的写法：`工具 30`（也可加粗：`**工具 30**`）。
RE_KW = re.compile(r"([\u4e00-\u9fa5A-Za-z]{1,8})\s*\*{0,2}\s*(\d+)\s*\*{0,2}")


def _strip_note(cell: str) -> str:
    """去掉首格里的「（114）」这类夹注，留下专题名——**每行对账靠的就是这个首格**。"""
    return re.sub(r"（.*?）", "", cell).strip()


def _declared(bank: Bank) -> dict[str, set[int]]:
    """登记过的词 → 它在**任一**专题里的计数值（散文里的读数允许等于其中任一个：
    「评估」在检索与可观测两组里各有一条，两处写法不同而都对）。"""
    want: dict[str, set[int]] = {}
    for t in bank.topics:
        for w, n in bank.kw_counts(t["name"]):
            want.setdefault(w, set()).add(n)
    for w, n in bank.ngram_top():
        want.setdefault(w, set()).add(n)
    return want


#: 正文里三个标量读数各自的**规范写法**（正则里的第二组是那个数）。
#: 它们在正文里必须长成这个样子，否则这一道检查够不到它——
#: 所以改口径时要连它一起改，而不是在正文里换一种说法。
STAT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"覆盖\s*\*{0,2}(\d+)\*{0,2}\s*个章号", "归属表覆盖的章号数"),
    (r"平均每条\s*\*{0,2}([\d.]+)\*{0,2}\s*字", "考点平均字数"),
    (r"逐字重复\s*\*{0,2}(\d+)\*{0,2}\s*条", "逐字重复的考点数"),
    (r"答案平均\s*\*{0,2}([\d.]+)\*{0,2}\s*字", "答案平均字数"),
    (r"答案里带数字的\s*\*{0,2}(\d+)\*{0,2}\s*条", "答案里带数字的条数"),
    (r"答案里带「可以」的\s*\*{0,2}(\d+)\*{0,2}\s*条", "答案里带「可以」的条数"),
)


def check_stats(bank: Bank, text: str) -> list[str]:
    """三个标量读数：覆盖章号数／考点平均字数／逐字重复条数（都由题库现算）。"""
    chaps = {c for t in bank.topics for c in TOPIC_MAP.get(t["name"], ())}
    want = {
        "归属表覆盖的章号数": str(len(chaps)),
        "考点平均字数": f"{bank.mean_kp_len():.1f}",
        "逐字重复的考点数": str(bank.kp_count - bank.distinct_kps()),
        "答案平均字数": f"{bank.mean_ans_len():.1f}",
        "答案里带数字的条数": str(bank.ans_with_digit()),
        "答案里带「可以」的条数": str(bank.ans_with("可以")),
    }
    problems: list[str] = []
    for pat, label in STAT_PATTERNS:
        hits = re.findall(pat, text)
        if not hits:
            problems.append(f"读数：正文里找不到「{label}」（它要按规范写法写，否则这一道检查够不到）")
            continue
        for got in hits:
            if got != want[label]:
                problems.append(f"读数：正文写「{label} {got}」，算出来是 {want[label]}")
    return problems


def check_readings(bank: Bank, text: str) -> list[str]:
    """正文里那些 `词 N` 逐处对账（**抄错一位就红的那一条**）。

    两层口径：① **首格是专题名的表格行**按那一行的专题严核（同一格里两个不同的
    专题都登记过的词，各按各的值）；② 其余地方（散文与围栏）只要等于**某个**
    专题算出的值就算对——它们不分专题，而这个宽容度不会放过一个真正的错数。"""
    problems: list[str] = []
    declared = _declared(bank)
    known_words = {w for ws in KEYWORDS.values() for w in ws} | {w for w, _ in bank.ngram_top()}

    def check(pairs, where: str, strict: dict[str, int] | None = None) -> None:
        for w, n in pairs:
            if w not in known_words:
                continue
            if strict is not None and w in strict:
                if strict[w] != int(n):
                    problems.append(f"读数：{where}写「{w} {n}」，专题里数出来是 {strict[w]}")
            elif declared.get(w) and int(n) not in declared[w]:
                problems.append(
                    f"读数：{where}写「{w} {n}」，数出来是 "
                    + "／".join(str(v) for v in sorted(declared[w])))

    # ① 表格格：只看首格是专题名（或「专题（N）」）的行
    by_name = {t["name"]: dict(t2 for t2 in bank.kw_counts(t["name"])) for t in bank.topics}
    for _head, rows in parse_tables(text):
        for row in rows:
            if not row:
                continue
            topic = _strip_note(row[0])
            if topic not in by_name:
                continue
            for cell in row[1:]:
                check(RE_KW.findall(cell), f"表里的「{topic}」行", by_name[topic])

    # ② 围栏与散文：不分专题，只要等于某一个专题的值就算对
    in_fence = False
    cur_topic: str | None = None
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            cur_topic = None
            continue
        if in_fence:
            stripped = _strip_note(ln.strip())
            if stripped in by_name:
                cur_topic = stripped
                continue
            check(RE_KW.findall(ln), "围栏里", by_name[cur_topic] if cur_topic else None)
        else:
            check(RE_KW.findall(ln), "正文里")
    return problems


def _chap_set(cell: str) -> set[str]:
    return set(re.findall(r"\d+\.\d+", cell))


def check_bank(bank: Bank) -> list[str]:
    problems: list[str] = []
    if bank.declared != bank.questions:
        problems.append(
            f"题库自身：标题声明 {bank.declared:,} 道，而里面数出 {bank.questions:,} 道")
    for t in bank.topics:
        if t["declared"] != t["qs"]:
            problems.append(
                f"题库自身：专题「{t['name']}」声明 {t['declared']} 道、数出 {t['qs']} 道")
    missing = [t["name"] for t in bank.topics if t["name"] not in TOPIC_MAP]
    if missing:
        problems.append(f"映射表里没有这些专题：{'、'.join(missing)}（映射要随题库一起长）")
    return problems


def check_chapter(bank: Bank, path: Path, plan: set[str]) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:                      # 夹具用临时文件，不在仓库里
        rel = path.name
    tables = parse_tables(text)

    # ① 索引表：专题 ｜ 题数 ｜ 考点数（＋合计）
    got = pick(tables, "专题", "题数", "考点数")
    if got is None:
        problems.append(f"{rel}：没找到索引表（表头要含「专题／题数／考点数」）")
    else:
        _, rows = got
        by_name = {r[0]: r for r in rows if len(r) >= 3}
        for t in bank.topics:
            r = by_name.get(t["name"])
            if r is None:
                problems.append(f"{rel}：索引表缺专题「{t['name']}」（题库里有 {t['qs']} 道）")
                continue
            if _num(r[1]) != t["qs"]:
                problems.append(f"{rel}：专题「{t['name']}」题数写 {r[1]}，题库里是 {t['qs']}")
            if _num(r[2]) != len(t["kp"]):
                problems.append(f"{rel}：专题「{t['name']}」考点数写 {r[2]}，题库里是 {len(t['kp'])}")
        for name in by_name:
            if name != "合计" and name not in [t["name"] for t in bank.topics]:
                problems.append(f"{rel}：索引表里的专题「{name}」不在题库里")
        total = by_name.get("合计")
        if total is None:
            problems.append(f"{rel}：索引表少了「合计」行")
        elif _num(total[1]) != bank.questions or _num(total[2]) != bank.kp_count:
            problems.append(
                f"{rel}：合计写 {total[1]}／{total[2]}，题库里是 {bank.questions}／{bank.kp_count}")

    # ② 归属表：专题 ｜ 归到本书的哪几章
    got2 = pick(tables, "专题", "归到")
    if got2 is None:
        problems.append(f"{rel}：没找到归属表（表头要含「专题／归到」）")
    else:
        _, rows = got2
        by_name = {r[0]: r for r in rows if len(r) >= 2}
        for t in bank.topics:
            want = set(bank.mapping(t["name"]))
            r = by_name.get(t["name"])
            if r is None:
                problems.append(f"{rel}：归属表缺专题「{t['name']}」")
                continue
            got_chaps = _chap_set(r[1])
            if got_chaps != want:
                problems.append(
                    f"{rel}：专题「{t['name']}」归到 {'、'.join(sorted(got_chaps)) or '（空）'}"
                    f"，映射表里是 {'、'.join(sorted(want))}")
            for c in got_chaps:
                if c not in plan:
                    problems.append(f"{rel}：归属表里的章号「{c}」不在 PLAN.md 中")
        for name in by_name:
            if name not in [t["name"] for t in bank.topics]:
                problems.append(f"{rel}：归属表里的专题「{name}」不在题库里")
    problems += check_readings(bank, text)
    problems += check_stats(bank, text)
    return problems


def print_index(bank: Bank) -> None:
    print(f"题库：{bank.name}（声明 {bank.declared:,} 道 / 数出 {bank.questions:,} 道）")
    print(f"\n{'专题':<26}{'题数':>6}{'考点数':>8}   归到本书")
    for t in bank.topics:
        where = "、".join(bank.mapping(t["name"])) or "（未映射）"
        print(f"{t['name']:<26}{t['qs']:>6}{len(t['kp']):>8}   {where}")
    print(f"{'合计':<26}{bank.questions:>6}{bank.kp_count:>8}")
    print(f"\n考点：{bank.kp_count:,} 条（每题一条），去重后 {bank.distinct_kps():,} 条，"
          f"平均每条 {bank.mean_kp_len():.1f} 字")


def print_counts(bank: Bank) -> None:
    """两张密度表：① 2-gram 词频（榜首七个，说明为什么不能按字面数词）；
    ② 每个专题里登记词的出现条数（**九专题的「问得多／几乎不问」就是从这一张里读的**）。"""
    top = bank.ngram_top()
    stop = [w for w, _ in top if w in STOPWORDS]
    print(f"2-gram 词频（考点 {bank.kp_count:,} 条，取榜首 {len(top)} 个）")
    print("  " + "  ".join(f"{w} {n}" for w, n in top))
    print(f"  其中虚词 {len(stop)} 个：{'、'.join(stop)}")
    print(f"\n逐专题的考点词计数（一条考点只计一次）")
    for t in bank.topics:
        pairs = "  ".join(f"{w} {n}" for w, n in bank.kw_counts(t["name"]))
        print(f"  {t['name']}（{len(t['kp'])}）\n    {pairs}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default=DEFAULT_BANK)
    ap.add_argument("--offline", action="store_true", help="只读题库，不联网")
    ap.add_argument("--counts", action="store_true", help="两张密度表（不比对正文）")
    ap.add_argument("--check", action="store_true", help="与正文 10.4 的表与读数对账")
    ap.add_argument("--self-test", action="store_true", help="只跑夹具")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    bank = Bank(args.bank)
    problems = check_bank(bank)

    if args.counts:
        print_counts(bank)
        return 1 if problems else 0

    if not args.check:
        print_index(bank)
        if problems:
            print("\n题库自身的对账：")
            for p in problems:
                print(f"  ✖ {p}")
            return 1
        return 0

    if not CHAPTER.exists():
        print(f"未找到 {CHAPTER.relative_to(ROOT).as_posix()}：本章还没有正文，索引表要等正文落地")
        return 0
    problems += check_chapter(bank, CHAPTER, plan_chapters())
    if problems:
        for p in problems:
            print(f"  ✖ {p}")
        print(f"\n汇总：{len(problems)} 处与题库不一致。修法：跑 --offline 取真值，再改正文。")
        return 1
    print(f"✔ 索引对账通过：{len(bank.topics)} 个专题、{bank.questions:,} 道题、"
          f"{bank.kp_count:,} 条考点，两张表与每处 `词 N` 逐处等于题库算出来的值。")
    return 0


# ---- 夹具 --------------------------------------------------------------

FAKE_BANK = """# 假题库（6道）

## 工具调用与函数编排（3道）

### 1. 第一题？

**考点**

工具的并发与幂等。

**答案**

见本章。

### 2. 第二题？

**考点**

工具的失败与重试。

**答案**

见本章。

### 3. 第三题？

**考点**

参数校验与权限。

**答案**

见本章。

## 记忆与上下文管理机制（3道）

### 1. 第四题？

**考点**

记忆写入与遗忘。

**答案**

见本章。

### 2. 第五题？

**考点**

记忆压缩与召回。

**答案**

见本章。

### 3. 第六题？

**考点**

上下文窗口与摘要。

**答案**

见本章。
"""

FAKE_CHAPTER = """# 10.4 假章

| 专题 | 题数 | 考点数 |
| --- | ---: | ---: |
| 工具调用与函数编排 | 3 | 3 |
| 记忆与上下文管理机制 | 3 | 3 |
| 合计 | 6 | 6 |

| 专题 | 归到本书 |
| --- | --- |
| 工具调用与函数编排 | 3.5、6.3 |
| 记忆与上下文管理机制 | 3.6、6.4 |

两张表加起来覆盖 4 个章号；考点平均每条 8.5 字；逐字重复 0 条；答案平均 4.0 字；答案里带数字的 0 条；答案里带「可以」的 0 条。

| 专题（条数） | 题库问得多 | 题库几乎不问 |
| --- | --- | --- |
| 工具调用与函数编排（3） | 工具 2、参数 1 | 调用 0、函数 0 |
| 记忆与上下文管理机制（3） | 记忆 2、上下文 1 | 摘要 1、召回 1 |

```
工具调用与函数编排（3）
  工具 2  参数 1  权限 1
  并发 1  幂等 1  失败 1
```
"""


def _fake_bank(tmp: Path) -> Bank:
    p = tmp / "假题库.md"
    p.write_text(FAKE_BANK, encoding="utf-8")
    b = Bank.__new__(Bank)
    b.name, b.path, b.declared, b.topics, b.answers = "假题库.md", p, 0, [], []
    b._read()
    return b


def _fake_chapter(tmp: Path, mutate=None) -> Path:
    p = tmp / "10.4-假章.md"
    text = FAKE_CHAPTER
    if mutate:
        text = mutate(text)
    p.write_text(text, encoding="utf-8")
    return p


def self_test() -> int:
    import tempfile

    #: （名字，期望，出错时的第一句话）——**期望写成「应通过／应报错」而不是布尔**，
    #: 因为这一层自己也曾把期望搞反过：夹具"报错"当成了失败（实为成功）。
    cases: list[tuple[str, str, bool, str]] = []
    saved = dict(TOPIC_MAP)

    def run(name: str, expect: str, mutate=None, map_ok: bool = True,
            plan_ok: bool = True) -> None:
        TOPIC_MAP.clear()
        TOPIC_MAP.update({"工具调用与函数编排": ("3.5", "6.3")})
        if map_ok:
            TOPIC_MAP["记忆与上下文管理机制"] = ("3.6", "6.4")
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bad = check_chapter(_fake_bank(tmp), _fake_chapter(tmp, mutate),
                                {"3.5", "6.3", "3.6", "6.4"} if plan_ok else {"3.5", "6.3"})
            bad += check_bank(_fake_bank(tmp))
            good = (not bad) if expect == "应通过" else bool(bad)
            cases.append((name, expect, good, bad[0] if bad else "（没有报错）"))

    run("干净的一份", "应通过")
    run("题数抄错", "应报错",
        lambda t: t.replace("| 工具调用与函数编排 | 3 | 3 |", "| 工具调用与函数编排 | 8 | 3 |"))
    run("考点数抄错", "应报错",
        lambda t: t.replace("| 记忆与上下文管理机制 | 3 | 3 |", "| 记忆与上下文管理机制 | 3 | 5 |"))
    run("漏一个专题", "应报错", lambda t: t.replace("| 记忆与上下文管理机制 | 3 | 3 |\n", ""))
    run("合计行抄错", "应报错", lambda t: t.replace("| 合计 | 6 | 6 |", "| 合计 | 6 | 7 |"))
    run("归属写错", "应报错",
        lambda t: t.replace("| 工具调用与函数编排 | 3.5、6.3 |", "| 工具调用与函数编排 | 3.9 |"))
    run("归属里的章号不在 PLAN 里", "应报错", plan_ok=False)
    run("映射表漏了一个专题", "应报错", map_ok=False)
    run("表里的词频抄错", "应报错", lambda t: t.replace("| 工具 2、参数 1 |", "| 工具 4、参数 1 |"))
    run("围栏里的词频抄错", "应报错", lambda t: t.replace("  工具 2  参数 1  权限 1", "  工具 2  参数 2  权限 1"))
    run("把「几乎不问」的词写成它其实不为 0", "应报错",
        lambda t: t.replace("| 调用 0、函数 0 |", "| 调用 2、函数 0 |"))
    run("覆盖章号数抄错", "应报错", lambda t: t.replace("覆盖 4 个章号", "覆盖 5 个章号"))
    run("考点平均字数抄错", "应报错", lambda t: t.replace("平均每条 8.5 字", "平均每条 8.6 字"))
    run("标量读数写成了别种说法", "应报错",
        lambda t: t.replace("逐字重复 0 条", "一条重复都没有"))
    run("答案平均字数抄错", "应报错", lambda t: t.replace("答案平均 4.0 字", "答案平均 4.2 字"))
    run("答案里带数字的条数抄错", "应报错",
        lambda t: t.replace("答案里带数字的 0 条", "答案里带数字的 3 条"))

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = tmp / "假题库.md"
        p.write_text(FAKE_BANK.replace("（6道）", "（9道）"), encoding="utf-8")
        b = Bank.__new__(Bank)
        b.name, b.path, b.declared, b.topics, b.answers = "假题库.md", p, 0, [], []
        b._read()
        bad = check_bank(b)
        cases.append(("题库声明 9 道而只有 6 道", "应报错", bool(bad),
                      bad[0] if bad else "（没有报错）"))

    TOPIC_MAP.clear()
    TOPIC_MAP.update(saved)
    real = check_bank(Bank(DEFAULT_BANK))
    cases.append((f"真实题库（{DEFAULT_BANK}）自洽且专题都在映射表里", "应通过",
                  not real, real[0] if real else "（没有报错）"))

    ok = sum(1 for _, _, good, _ in cases if good)
    for name, expect, good, msg in cases:
        print(f"  {'✔' if good else '✖'} {name}（{expect}）"
              + ("" if good else f"  ← {msg}"))
    print(f"自检：{ok}/{len(cases)} 通过")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
