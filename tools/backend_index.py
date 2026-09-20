#!/usr/bin/env python
"""10.5 的交付物：**把一份 Java 体系的后端题库，换成 Python／AI 岗位的视角。**

第 10 篇的每一章都交一份「可核对的考点索引」（10.1–10.3 是题与账、10.4 交了题库
索引的形状），而这一章的题目**换了体系**：题库是 Java 的（JVM／Spring 占比高），
岗位是 Python／AI 的。所以这一章多一道动作——**每个板块都要先判一次处置**
（留／换视角／弃），读数由这个脚本从题库算出来。

    python tools/backend_index.py --offline     # 板块题数、难度分布、处置与题面关键词
    python tools/backend_index.py --check       # 与正文 10.5 的表逐处对账
    python tools/backend_index.py --self-test   # 夹具（改一个题数／一个处置／一个★就红）

对账各自对应一种**不会报错**的漂移：

① **板块名集合**——题库有十二个板块，正文的表漏一个，表看上去还是完整的；
② **逐行的题数与 ≥4★ 数**——手抄时把 35 抄成 53，没有任何检查看得见；
③ **每个板块的处置判定**——写错了，读者会去复习一份他不该看的板块；
④ **难度分布与三个标量**——`4★ 56` 写成 `4★ 65` 这种，人眼对不出来；
⑤ **题面关键词的计数**——「Python 0 道」这句话是本章立论的一半，它也要能被复算；
⑥ **题库自身**——标题说 165 道，里面到底有多少道 `N-` 题（素材是别人的）。

**这里的两张判据表是原创的、写在脚本里**：板块的处置（`DISPOSITION`）与
题面要数的词（`PROBE_WORDS`）。正文只是它们的投影——改判据要动代码，而代码进提交门。
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BANKS = ROOT / "sources" / "06-求职冲刺"
CHAPTER = ROOT / "book" / "10-求职冲刺" / "10.5-后端高频考点：Python 与 AI 岗位视角.md"
PLAN = ROOT / "PLAN.md"

DEFAULT_BANK = "后端高频面试题大集合.md"
DECLARED_QUESTIONS = 165

#: 十二个板块的标题（**顺序即题库里的顺序**；识别靠「这一行含这个串」）。
BOARDS: tuple[str, ...] = (
    "JAVASE核心", "JUC并发编程", "JVM虚拟机", "Spring框架", "MQ消息队列",
    "分布式缓存板块", "微服务和RPC", "系统设计板块", "Mysql数据库板块",
    "业务稳定性运行-监控告警体系", "海量数据处理", "容器和K8S",
)

#: 每个板块的处置（**原创判据**：按「AI 岗会不会问」而不是按「这一块难不难」）：
#: 留 ＝ 直接可用；换视角 ＝ 题要留、例子要换成 Python／AI 栈；弃 ＝ 岗位不问。
DISPOSITION: dict[str, str] = {
    "JAVASE核心": "换视角",
    "JUC并发编程": "留",
    "JVM虚拟机": "弃",
    "Spring框架": "换视角",
    "MQ消息队列": "留",
    "分布式缓存板块": "留",
    "微服务和RPC": "留",
    "系统设计板块": "换视角",
    "Mysql数据库板块": "留",
    "业务稳定性运行-监控告警体系": "留",
    "海量数据处理": "换视角",
    "容器和K8S": "留",
}

#: 题面里要数的词（**本章第二条判据：反向索引**——AI 岗必问而这份题库一道都没有的
#: 那些词，与这份题库大量问而岗位几乎不用的那些词，各数一次）。
PROBE_WORDS: tuple[str, ...] = (
    "Python", "asyncio", "GIL", "协程", "多进程", "FastAPI", "Pydantic",
    "向量", "embedding", "RAG", "词元", "gRPC", "SSE", "流式", "成本", "评测",
    "Docker", "K8s", "幂等", "死信", "事务", "索引", "锁",
    "JVM", "GC", "垃圾回收", "Spring", "ThreadLocal", "线程池", "类加载",
)

RE_TOPIC_TITLE = re.compile(r"^#\s+\S")
RE_Q = re.compile(r"^(\d+)[-－]\s*(\S.*)$")
#: 难度那一行：`难度【 * * * 】`——**星号之间有空白**，所以不能用「星号串」去匹配，
#: 只能先认「这一行有难度标记」，再把这一行里的 `*` 数出来（第一次就踩了前一种写法）。
RE_DIFF = re.compile(r"难度【")
#: 难度读数的规范写法：`3★ 79 道`／`无标记 6 道`。**星号前那个数字要一起抓住**——
#: 只写 `★` 的话会把 `3★` 认成 1★（夹具第一次就报了这个错）。
#: 而 `4★ 及以上共 67 道` 这种写法故意不被它匹配（中间隔了字），由下面那个标量管。
#: `≥4★` 这种写法要排除在难度分布之外：本章多处写「缓存 18 道（≥4★ 8 道）」——
#: 那是**单个板块**的读数，不是全库分布（夹具与正文都报过这个冲突）。
RE_STARS_READING = re.compile(r"(无标记|(?<![≥>])\d\s*★|\*{1,5})\s*(\d+)\s*道")
RE_HARD_SCALAR = re.compile(r"4★\s*及以上共\s*\*{0,2}(\d+)\*{0,2}\s*道")


def _stars_of(label: str) -> int:
    label = label.strip()
    if label == "无标记":
        return 0
    if label.endswith("★"):
        return int(label[:-1].strip())
    return len(label)


class Bank:
    """一份题库的读数：板块、每题的难度、题面。"""

    def __init__(self, name: str = DEFAULT_BANK, text: str | None = None) -> None:
        self.name = name
        self.path = BANKS / name
        #: 提取出来的文本里有 CJK 兼容字（`⼼`＝康熙部首心），**先归一化再数**——
        #: 不归一化的话「JAVASE核心」这个板块标题根本匹配不上（第一次就踩过）。
        raw = text if text is not None else self.path.read_text(encoding="utf-8")
        self.lines = [unicodedata.normalize("NFKC", l).strip() for l in raw.splitlines()]
        self.bounds = self._board_bounds()
        self.qs = self._questions()

    def _board_bounds(self) -> list[tuple[int, str]]:
        found: list[tuple[int, str]] = []
        for b in BOARDS:
            hit = next((i for i, l in enumerate(self.lines) if b.lower() in l.lower()), None)
            if hit is not None:
                found.append((hit, b))
        return sorted(found)

    def _questions(self) -> list[dict]:
        starts = [i for i, l in enumerate(self.lines) if RE_Q.match(l)]
        ends = starts[1:] + [len(self.lines)]
        out: list[dict] = []
        for i, end in zip(starts, ends):
            m = RE_Q.match(self.lines[i]) or re.match(r"^(\d+)[-－]\s*(\S.*)$", self.lines[i])
            stars = 0
            for j in range(i, end):
                if RE_DIFF.search(self.lines[j]):
                    stars = self.lines[j].count("*")
                    break
            board = None
            for b, name in self.bounds:
                if b < i:
                    board = name
            out.append({"board": board, "stars": stars,
                        "title": m.group(2) if m else self.lines[i]})
        return out

    def by_board(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {b: [] for b in BOARDS}
        for q in self.qs:
            if q["board"] in out:
                out[q["board"]].append(q)
        return out

    def star_hist(self) -> dict[int, int]:
        hist: dict[int, int] = {}
        for q in self.qs:
            hist[q["stars"]] = hist.get(q["stars"], 0) + 1
        return hist

    def mean_stars(self) -> float:
        return sum(q["stars"] for q in self.qs) / len(self.qs) if self.qs else 0.0

    def hard(self) -> int:
        return sum(1 for q in self.qs if q["stars"] >= 4)

    def probe(self, word: str) -> int:
        """词出现在多少道**题面**里（题面是「会被问什么」的那一层）。"""
        return sum(1 for q in self.qs if word.lower() in q["title"].lower())


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

    前两条不是苛刻，是被撞出来的：本章有三张表都带「板块」二字——
    处置表（10.5.1 那张「处置 ｜ 判据 ｜ ⋯」）与板块表（含「处置」列）都能冒充对方。
    所以识别口径固定成「第一列是板块、第二列是题数／处置」，不靠标题里的词猜。"""
    for head, rows in tables:
        if len(head) < 2 or keys[0] not in head[0] or keys[1] not in head[1]:
            continue
        if all(any(k in h for h in head) for k in keys[2:]):
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
    c = re.sub(r"[^\d]", "", cell)
    return int(c) if c else None


def check_bank(bank: Bank) -> list[str]:
    problems: list[str] = []
    if bank.qs and len(bank.qs) != DECLARED_QUESTIONS:
        problems.append(f"题库自身：声明 {DECLARED_QUESTIONS} 道，而里面数出 {len(bank.qs)} 道")
    missing = [b for b in BOARDS if b not in [n for _, n in bank.bounds]]
    if missing:
        problems.append(f"题库自身：这些板块标题没找到：{'、'.join(missing)}（标题变了要改 BOARDS）")
    unknown = [b for b in DISPOSITION if b not in BOARDS]
    if unknown:
        problems.append(f"处置表里有不在板块表里的名字：{'、'.join(unknown)}")
    return problems


def check_chapter(bank: Bank, path: Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    tables = parse_tables(text)
    by_board = bank.by_board()

    # ① 板块表：板块 ｜ 题数 ｜ 4★ 以上
    got = pick(tables, "板块", "题数")
    if got is None:
        problems.append("没找到板块表（表头要含「板块／题数」）")
    else:
        _, rows = got
        seen = {r[0]: r for r in rows if len(r) >= 2}
        for b in BOARDS:
            r = seen.get(b)
            if r is None:
                problems.append(f"板块表缺「{b}」（题库里有 {len(by_board[b])} 道）")
                continue
            if _num(r[1]) != len(by_board[b]):
                problems.append(f"板块「{b}」题数写 {r[1]}，题库里是 {len(by_board[b])}")
            if len(r) > 2:
                want_hard = sum(1 for q in by_board[b] if q["stars"] >= 4)
                if _num(r[2]) != want_hard:
                    problems.append(f"板块「{b}」的 ≥4★ 写 {r[2]}，题库里是 {want_hard}")
        for name in seen:
            if name not in BOARDS:
                problems.append(f"板块表里的「{name}」不在题库的十二个板块里")

    # ② 处置：**优先用板块表里那一列**（本章就是这种写法），没有这一列时
    #    再找一张单独的处置表（凡是「板块 ｜ 处置」两张表都允许，不强制一种）。
    got2 = None
    if got is not None:
        head, rows = got
        col = next((n for n, h in enumerate(head) if "处置" in h), None)
        if col is not None:
            got2 = (head, [[r[0], r[col]] for r in rows if len(r) > col])
    if got2 is None:
        got2 = pick(tables, "板块", "处置")
    if got2 is None:
        problems.append("没找到处置列／处置表（板块表里要有一列处置，或单独一张「板块 ｜ 处置」表）")
    else:
        _, rows = got2
        seen = {r[0]: r[1] for r in rows if len(r) >= 2}
        for b in BOARDS:
            want = DISPOSITION[b]
            if b not in seen:
                problems.append(f"处置表缺「{b}」")
            elif want not in seen[b]:
                problems.append(f"板块「{b}」的处置写「{seen[b]}」，判据里是「{want}」")
        for name in seen:
            if name not in BOARDS:
                problems.append(f"处置表里的「{name}」不在板块表里")

    # ③ 难度分布（正文里凡写 `N★ M 道` 的地方都核）
    hist = bank.star_hist()
    for label, n in RE_STARS_READING.findall(text):
        #: 某一档一道都没有时，hist 里根本没有那个键——**「无标记 0 道」是正确写法**。
        want = hist.get(_stars_of(label), 0)
        if int(n) != want:
            problems.append(f"难度：正文写「{label} {n} 道」，数出来是 {want}")

    # ④ 题面关键词（只在登记过的词上核）
    for w in PROBE_WORDS:
        for m in re.finditer(re.escape(w) + r"\s*\*{0,2}\s*(\d+)\s*\*{0,2}\s*道", text):
            if int(m.group(1)) != bank.probe(w):
                problems.append(
                    f"关键词：正文写「{w} {m.group(1)} 道」，题面里数出来是 {bank.probe(w)}")

    # ⑤ 四个标量
    for pat, label, want in (
        # 题数那一句要写成「全库共 165 道」——**不能只写「共 N 道」**：
        # 章里还有「4★ 及以上共 67 道」这种句子，两者会撞（夹具报过）。
        (r"全库共\s*\*{0,2}(\d+)\*{0,2}\s*道", "题数", str(len(bank.qs))),
        (r"\*{0,2}(\d+)\*{0,2}\s*个板块", "板块数", str(len(BOARDS))),
        (r"平均\s*([\d.]+)\s*★", "平均难度", f"{bank.mean_stars():.2f}"),
        (RE_HARD_SCALAR.pattern, "4★ 及以上", str(bank.hard())),
    ):
        hits = re.findall(pat, text)
        if not hits:
            problems.append(f"读数：正文里找不到「{label}」（要按规范写法写，否则检查够不到）")
            continue
        for got in hits:
            if got != want:
                problems.append(f"读数：正文写「{label} {got}」，算出来是 {want}")
    return problems


def print_index(bank: Bank) -> None:
    by_board = bank.by_board()
    print(f"题库：{bank.name}（声明 {DECLARED_QUESTIONS} 道 / 数出 {len(bank.qs)} 道）")
    print(f"\n{'板块':<30}{'题数':>5}{'≥4★':>6}{'均★':>7}   处置")
    for b in BOARDS:
        qs = by_board[b]
        mean = sum(q["stars"] for q in qs) / len(qs) if qs else 0.0
        hard = sum(1 for q in qs if q["stars"] >= 4)
        print(f"{b:<30}{len(qs):>5}{hard:>6}{mean:>7.2f}   {DISPOSITION[b]}")
    print(f"{'合计':<30}{len(bank.qs):>5}{bank.hard():>6}{bank.mean_stars():>7.2f}")
    hist = bank.star_hist()
    print("\n难度分布：" + "  ".join(f"{k}★ {hist.get(k, 0)} 道" if k
                                    else f"无标记 {hist.get(0, 0)} 道"
                                    for k in sorted(hist)))
    print(f"\n题面关键词（提到它的有几道）：")
    for w in PROBE_WORDS:
        print(f"  {w:<12}{bank.probe(w):>4} 道")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default=DEFAULT_BANK)
    ap.add_argument("--offline", action="store_true", help="只读题库，不联网")
    ap.add_argument("--check", action="store_true", help="与正文 10.5 的表与读数对账")
    ap.add_argument("--self-test", action="store_true", help="只跑夹具")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    bank = Bank(args.bank)
    problems = check_bank(bank)

    if not args.check:
        print_index(bank)
        if problems:
            print("\n题库自身的对账：")
            for p in problems:
                print(f"  ✖ {p}")
            return 1
        return 0

    if not CHAPTER.exists():
        print(f"未找到 {CHAPTER.relative_to(ROOT).as_posix()}：本章还没有正文，索引要等正文落地")
        return 0
    problems += check_chapter(bank, CHAPTER)
    if problems:
        for p in problems:
            print(f"  ✖ {p}")
        print(f"\n汇总：{len(problems)} 处与题库不一致。修法：跑 --offline 取真值，再改正文。")
        return 1
    print(f"✔ 岗位视角索引对账通过：{len(BOARDS)} 个板块、{len(bank.qs):,} 道题，"
          f"板块表／处置表／难度分布／题面关键词逐处等于题库算出来的值。")
    return 0


# ---- 夹具 --------------------------------------------------------------

FAKE_BANK = """# 假后端题库

> 共 4 道

JAVASE核心
1-String 与 StringBuilder 的区别？
题目分析和考点
难度【 * * 】
答案
略

2-hash 冲突怎么解决？
题目分析和考点
难度【 * * * 】
答案
略

MQ消息队列
3-消息重复消费怎么办？
题目分析和考点
难度【 * * * * 】
答案
略

4-死信队列是什么？
题目分析和考点
难度【 * * * * * 】
答案
略
"""

FAKE_CHAPTER = """# 10.5 假章

全库共 4 道，分 2 个板块，平均 3.50★，其中 2 道在 4★ 以上。

| 板块 | 题数 | ≥4★ |
| --- | ---: | ---: |
| JAVASE核心 | 2 | 0 |
| MQ消息队列 | 2 | 2 |

| 板块 | 处置 | 为什么 |
| --- | --- | --- |
| JAVASE核心 | 换视角 | 换成 Python 语言核心 |
| MQ消息队列 | 留 | 岗位也在用 |

正文里的两处读数：3★ 1 道、无标记 0 道，4★ 及以上共 2 道。

题面关键词：死信 1 道、幂等 0 道。
"""


def _fake_bank(tmp: Path) -> Bank:
    return Bank("假后端题库.md", text=FAKE_BANK)


def _fake_chapter(tmp: Path, mutate=None) -> Path:
    p = tmp / "10.5-假章.md"
    text = FAKE_CHAPTER
    if mutate:
        text = mutate(text)
    p.write_text(text, encoding="utf-8")
    return p


def self_test() -> int:
    import tempfile
    from pathlib import Path as _P

    saved_boards = BOARDS
    saved_disp = dict(DISPOSITION)
    saved_declared = globals()["DECLARED_QUESTIONS"]
    cases: list[tuple[str, str, bool, str]] = []

    def run(name: str, expect: str, mutate=None, boards=("JAVASE核心", "MQ消息队列"),
            disp=None, declared: int = 4) -> None:
        globals()["BOARDS"] = tuple(boards)
        globals()["DECLARED_QUESTIONS"] = declared
        DISPOSITION.clear()
        DISPOSITION.update(disp if disp is not None else
                           {"JAVASE核心": "换视角", "MQ消息队列": "留"})
        with tempfile.TemporaryDirectory() as td:
            tmp = _P(td)
            bad = check_chapter(_fake_bank(tmp), _fake_chapter(tmp, mutate))
            bad += check_bank(_fake_bank(tmp))
            good = (not bad) if expect == "应通过" else bool(bad)
            cases.append((name, expect, good, bad[0] if bad else "（没有报错）"))

    run("干净的一份", "应通过")
    run("板块题数抄错", "应报错",
        lambda t: t.replace("| JAVASE核心 | 2 | 0 |", "| JAVASE核心 | 3 | 0 |"))
    run("≥4★ 数抄错", "应报错",
        lambda t: t.replace("| MQ消息队列 | 2 | 2 |", "| MQ消息队列 | 2 | 1 |"))
    run("板块表漏一行", "应报错", lambda t: t.replace("| MQ消息队列 | 2 | 2 |\n", ""))
    run("处置判定写错", "应报错",
        lambda t: t.replace("| JAVASE核心 | 换视角 |", "| JAVASE核心 | 留 |"))
    run("难度分布改一位", "应报错", lambda t: t.replace("3★ 1 道", "3★ 2 道"))
    run("关键词计数抄错", "应报错", lambda t: t.replace("死信 1 道", "死信 2 道"))
    run("标量抄错", "应报错", lambda t: t.replace("全库共 4 道", "全库共 5 道"))
    run("板块名对不上题库", "应报错",
        lambda t: t.replace("| MQ消息队列 | 2 | 2 |", "| Spring框架 | 2 | 2 |"))
    run("处置表把两列写反了（识别不到）", "应报错",
        lambda t: t.replace("| 板块 | 处置 | 为什么 |", "| 处置 | 板块 | 为什么 |"))
    run("题库声明与数出的题数不符", "应报错", declared=165)

    with tempfile.TemporaryDirectory() as td:
        bank = Bank("假后端题库.md", text=FAKE_BANK.replace("1-String", "9-String"))
        bad = check_bank(bank)
        cases.append(("题库声明 165 道而只有 4 道", "应报错", bool(bad),
                      bad[0] if bad else "（没有报错）"))

    globals()["BOARDS"] = saved_boards
    globals()["DECLARED_QUESTIONS"] = saved_declared
    DISPOSITION.clear()
    DISPOSITION.update(saved_disp)
    real = check_bank(Bank(DEFAULT_BANK))
    cases.append((f"真实题库（{DEFAULT_BANK}）自洽且十二个板块都在", "应通过",
                  not real, real[0] if real else "（没有报错）"))

    ok = sum(1 for _, _, good, _ in cases if good)
    for name, expect, good, msg in cases:
        print(f"  {'✔' if good else '✖'} {name}（{expect}）"
              + ("" if good else f"  ← {msg}"))
    print(f"自检：{ok}/{len(cases)} 通过")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
