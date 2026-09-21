#!/usr/bin/env python
"""10.7 的交付物：**把一场 45 分钟的模拟面试，变成四组能复算的数。**

前六章的读数都是从**外部**算出来的（简历的字数、题库存了多少道、两库各缺什么词）；
这一章没有外部题源，它交的是**一套自己的口径**——时间怎么分、追问分几层、评分看哪几维、
复盘数哪几种失败。口径若要能被别人用，就得**能复算**，所以这一章的剧本写在这个文件里：

    python tools/mock_round.py --offline     # 时间账、追问穿透、评分与失败模式
    python tools/mock_round.py --check       # 与正文 10.7 的四张表逐处对账
    python tools/mock_round.py --self-test   # 夹具（改一个分钟数／一个命中／一个得分就红）

对账各自对应一种**不会报错**的漂移：

① **五个段落的时间预算与实测**——把 12 抄成 21 分钟，表看上去仍然完整；
② **追问三层的命中数**——「第一层全中」这句话是本章立论的一半，它也要能复算；
③ **四个维度的得分与及格线**——分数是这一章自己定的口径，**改一处分就应当红**；
④ **四种失败模式的次数**——复盘清单的用处全在「哪一类最多」上，数错了清单就指错方向；
⑤ **十日冲刺表的十条**——它收的是 10.4–10.6 三张反向索引的并集，少一条就漏一个缺口；
⑥ **剧本自身**——16 道题的时间预算要加起来等于 45 分钟（**改一道题就得重算总账**）。

**这里的两张判据表是原创的、写在脚本里**：五个段落的时间预算（`SEGMENTS`）与四个评分维度
（`DIMENSIONS`）。正文只是它们的投影——改口径要动代码，而代码进提交门。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
CHAPTER = ROOT / "book" / "10-求职冲刺" / "10.7-模拟面试与复盘清单.md"

#: 五个段落的预算（分钟）——**45 分钟就是这五个数加起来**，而它是本章的第一条口径。
SEGMENTS: tuple[tuple[str, int], ...] = (
    ("自我介绍", 3),
    ("项目讲述", 12),
    ("系统设计", 15),
    ("岗位知识", 10),
    ("反问", 5),
)

#: 一场模拟面试的剧本：每道题一个记录。
#: `layer` 是追问的层（1 问事实／2 问边界／3 问反事实）；`hit` 是这一问答没答上来；
#: `number` 是有没有给出数；`boundary` 是有没有说清边界；`off` 是答偏了（答的不是被问的那件事）。
MOCK: tuple[dict, ...] = (
    # 第一段：自我介绍
    dict(seg="自我介绍", qid="A1", prompt="用三分钟讲你自己", budget=3, actual=3.5,
         layer=1, hit=True, number=True, boundary=True, off=False),
    # 第二段：项目讲述（一问 ＋ 三层追问）
    dict(seg="项目讲述", qid="P1", prompt="挑一个项目讲清楚它解决了什么", budget=4, actual=5,
         layer=1, hit=True, number=True, boundary=True, off=False),
    dict(seg="项目讲述", qid="P2", prompt="那个数是怎么量出来的", budget=3, actual=3,
         layer=2, hit=True, number=True, boundary=True, off=False),
    dict(seg="项目讲述", qid="P3", prompt="如果流量翻十倍，先坏的是哪一段", budget=3, actual=3,
         layer=2, hit=True, number=False, boundary=True, off=False),
    dict(seg="项目讲述", qid="P4", prompt="如果不用检索，这一套还成立吗", budget=2, actual=2,
         layer=3, hit=False, number=False, boundary=False, off=True),
    # 第三段：系统设计（澄清 → 范围 → 请求线 → 失败 → 收尾）
    dict(seg="系统设计", qid="S1", prompt="澄清：谁用、多大规模、多久要出", budget=2, actual=2,
         layer=1, hit=True, number=True, boundary=True, off=False),
    dict(seg="系统设计", qid="S2", prompt="范围表：这一版做什么、不做什么", budget=3, actual=4,
         layer=1, hit=True, number=True, boundary=True, off=False),
    dict(seg="系统设计", qid="S3", prompt="请求线：从入口到答案要经过哪几跳", budget=4, actual=5,
         layer=2, hit=True, number=True, boundary=True, off=False),
    dict(seg="系统设计", qid="S4", prompt="四类失败各怎么处置", budget=4, actual=3,
         layer=3, hit=True, number=True, boundary=True, off=False),
    dict(seg="系统设计", qid="S5", prompt="收尾：这一版的钱花在哪", budget=2, actual=1,
         layer=1, hit=True, number=True, boundary=True, off=False),
    # 第四段：岗位知识
    dict(seg="岗位知识", qid="K1", prompt="并发数怎么定，超了怎么办", budget=3, actual=3,
         layer=2, hit=True, number=True, boundary=True, off=False),
    dict(seg="岗位知识", qid="K2", prompt="缓存与状态的区别在哪", budget=3, actual=3,
         layer=2, hit=False, number=True, boundary=True, off=False),
    dict(seg="岗位知识", qid="K3", prompt="你怎么知道这次改动没变差", budget=2, actual=2,
         layer=1, hit=True, number=False, boundary=True, off=False),
    dict(seg="岗位知识", qid="K4", prompt="为什么不用最大的那个模型", budget=2, actual=2,
         layer=3, hit=False, number=False, boundary=True, off=False),
    # 第五段：反问
    dict(seg="反问", qid="Q1", prompt="你们怎么评测一次改动", budget=2, actual=2,
         layer=1, hit=True, number=True, boundary=True, off=False),
    dict(seg="反问", qid="Q2", prompt="上线流程与回滚的口径是什么", budget=3, actual=3,
         layer=2, hit=True, number=True, boundary=True, off=False),
)

#: 四个评分维度（**原创口径**：每一维 0–5 分，各有一条扣分规则，而规则只用剧本里的四个标记）。
DIMENSIONS: tuple[tuple[str, str], ...] = (
    ("表达", "5 − 答偏的题数 × 1 − 超时段落数 × 0.5"),
    ("证据", "5 − 答上来却没给数的题数 × 1"),
    ("取舍", "5 − 第三层未命中的题数 × 1"),
    ("边界", "5 − 第三层里没说边界的题数 × 1"),
)

#: 及格线：总分 20 分里的这个数（**它是一条判据，不是一个观测值**）。
PASS_LINE = 14.0

#: 十日冲刺表（收的是 10.4–10.6 三张反向索引的并集；顺序即冲刺顺序）。
SPRINT: tuple[tuple[str, str], ...] = (
    ("幂等", "3.5、6.3"),
    ("成本", "6.4、10.3.4"),
    ("评测", "7.1、10.3.6"),
    ("向量与检索", "5.2–5.6"),
    ("词元与上下文", "3.6、6.4"),
    ("流式与 SSE", "8.3"),
    ("端侧与量化", "6.1、9.2"),
    ("推理延迟", "7.1、7.2"),
    ("提示与配置版本化", "7.3"),
    ("容器与发布", "8.1、8.2、8.5"),
)

#: 问答的规范写法：`3★ 79 道` 那一类读数的先例在这里换成「段 ｜ 预算 ｜ 实测 ｜ 差」。
#: 「总分 13 分（及格线 14 分）」这两句要**分开抓**：抓「N 分」再回头看上下文的话，
#: 「总分 13 分，及格线 14 分」里的 14 会被当成总分（第一次实现就报了两条假阳性）。
RE_TIME = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*分钟")


def total_budget() -> int:
    return sum(b for _, b in SEGMENTS)


def segment_rows() -> list[dict]:
    """每一段的预算与实测（实测 ＝ 这一段里每道题的 actual 之和）。"""
    out: list[dict] = []
    for name, budget in SEGMENTS:
        qs = [q for q in MOCK if q["seg"] == name]
        actual = round(sum(q["actual"] for q in qs), 1)
        out.append({"seg": name, "budget": budget, "actual": actual,
                    "diff": round(actual - budget, 1),
                    "over": actual > budget, "under": actual < budget})
    return out


def actual_total() -> float:
    return round(sum(q["actual"] for q in MOCK), 1)


def layer_rows() -> list[dict]:
    out: list[dict] = []
    for layer in (1, 2, 3):
        qs = [q for q in MOCK if q["layer"] == layer]
        hit = sum(1 for q in qs if q["hit"])
        out.append({"layer": layer, "hit": hit, "total": len(qs)})
    return out


def scores() -> dict[str, float]:
    over_segments = sum(1 for r in segment_rows() if r["over"])
    off = sum(1 for q in MOCK if q["off"])
    #: **「无据」只数答上来的那些**：没答上来是「取舍」那一维的扣分，
    #: 两处都扣会把同一道题罚两次（第一次实现就是这么把证据算成了 1 分）。
    no_number = sum(1 for q in MOCK if q["hit"] and not q["number"])
    layer3 = [q for q in MOCK if q["layer"] == 3]
    miss3 = sum(1 for q in layer3 if not q["hit"])
    weak3 = sum(1 for q in layer3 if not q["boundary"])
    return {
        "表达": round(5 - off * 1 - over_segments * 0.5, 1),
        "证据": round(5 - no_number * 1, 1),
        "取舍": round(5 - miss3 * 1, 1),
        "边界": round(5 - weak3 * 1, 1),
    }


def score_total() -> float:
    return round(sum(scores().values()), 1)


def failures() -> dict[str, int]:
    """四种失败模式（另有「欠时」一种，单列——把时间留错地方同样是失败）。"""
    rows = segment_rows()
    return {
        "超时": sum(1 for q in MOCK if q["actual"] > q["budget"]),
        "无据": sum(1 for q in MOCK if q["hit"] and not q["number"]),
        "缺边界": sum(1 for q in MOCK if q["layer"] == 3 and not q["boundary"]),
        "失焦": sum(1 for q in MOCK if q["off"]),
        "欠时": sum(1 for q in MOCK if q["actual"] < q["budget"]),
        "超时段落": sum(1 for r in rows if r["over"]),
    }


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
    """找一个表：**keys[0] 落在第一列表头、keys[1] 落在第二列表头**，其余落在任意列。"""
    for head, rows in tables:
        if len(head) < 2 or keys[0] not in head[0] or keys[1] not in head[1]:
            continue
        if all(any(k in h for h in head) for k in keys[2:]):
            return head, rows
    return None


def _num(cell: str) -> float | None:
    m = re.search(r"[+-]?\d+(?:\.\d+)?", cell)
    return float(m.group(0)) if m else None


def check_spec() -> list[str]:
    """剧本自身的对账：**16 道题的预算加起来必须等于 45 分钟**。"""
    problems: list[str] = []
    per_q = sum(q["budget"] for q in MOCK)
    if per_q != total_budget():
        problems.append(f"剧本自身：逐题预算加起来 {per_q} 分钟，段落预算是 {total_budget()} 分钟")
    for name, budget in SEGMENTS:
        got = sum(q["budget"] for q in MOCK if q["seg"] == name)
        if got != budget:
            problems.append(f"剧本自身：「{name}」逐题预算是 {got} 分钟，段预算写的是 {budget}")
    unknown = [q["qid"] for q in MOCK if q["seg"] not in [s for s, _ in SEGMENTS]]
    if unknown:
        problems.append(f"剧本自身：这些题不属于任何一段：{'、'.join(unknown)}")
    return problems


def check_chapter(path: Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    tables = parse_tables(text)
    segs = segment_rows()
    layers = layer_rows()
    sc = scores()
    fl = failures()

    # ① 时间账：段 ｜ 预算 ｜ 实测（差由前两列算出来，不必在表里再抄一遍）
    got = pick(tables, "段", "预算")
    if got is None:
        problems.append("没找到时间账表（表头第一列要是「段」、第二列「预算」）")
    else:
        head, rows = got
        seen = {r[0]: r for r in rows if len(r) >= 3}
        for r in segs:
            row = seen.get(r["seg"])
            if row is None:
                problems.append(f"时间账表缺「{r['seg']}」这一段")
                continue
            if _num(row[1]) != float(r["budget"]):
                problems.append(f"时间账：「{r['seg']}」预算写 {row[1]}，口径里是 {r['budget']}")
            if _num(row[2]) != float(r["actual"]):
                problems.append(f"时间账：「{r['seg']}」实测写 {row[2]}，算出来是 {r['actual']}")
        for name in seen:
            if name not in [s for s, _ in SEGMENTS]:
                problems.append(f"时间账表里的「{name}」不是五个段落之一")

    # ② 追问穿透：层 ｜ 命中
    got = pick(tables, "层", "命中")
    if got is None:
        problems.append("没找到追问穿透表（表头第一列要是「层」、第二列「命中」）")
    else:
        head, rows = got
        seen = {r[0]: r for r in rows if len(r) >= 3}
        for r in layers:
            key = f"第{r['layer']}层"
            row = next((v for k, v in seen.items() if key in k or str(r["layer"]) in k), None)
            if row is None:
                problems.append(f"追问穿透表缺{key}")
                continue
            if _num(row[1]) != float(r["hit"]):
                problems.append(f"追问穿透：第 {r['layer']} 层命中写 {row[1]}，算出来是 {r['hit']}")
            if _num(row[2]) != float(r["total"]):
                problems.append(f"追问穿透：第 {r['layer']} 层总数写 {row[2]}，算出来是 {r['total']}")

    # ③ 评分表：维度 ｜ 得分
    got = pick(tables, "维度", "得分")
    if got is None:
        problems.append("没找到评分表（表头第一列要是「维度」、第二列「得分」）")
    else:
        head, rows = got
        seen = {r[0]: r[1] for r in rows if len(r) >= 2}
        for dim, _rule in DIMENSIONS:
            if dim not in seen:
                problems.append(f"评分表缺「{dim}」")
            elif _num(seen[dim]) != sc[dim]:
                problems.append(f"评分：「{dim}」写 {seen[dim]}，按规则算出来是 {sc[dim]}")
        for name in seen:
            if name not in [d for d, _ in DIMENSIONS]:
                problems.append(f"评分表里的「{name}」不是四个维度之一")
    for pat, label, want in (
        (r"总分\s*\*{0,2}(\d+(?:\.\d+)?)\*{0,2}\s*分", "总分", score_total()),
        (r"及格线\s*\*{0,2}(\d+(?:\.\d+)?)\*{0,2}\s*分", "及格线", PASS_LINE),
    ):
        hits = re.findall(pat, text)
        if not hits:
            problems.append(f"评分：正文里找不到「{label}」（要按规范写法写，否则检查够不到）")
            continue
        for got in hits:
            if float(got) != want:
                problems.append(f"评分：正文写{label} {got} 分，口径里是 {want:g}")

    # ④ 四种失败模式的次数：模式 ｜ 次数
    got = pick(tables, "模式", "次数")
    if got is None:
        problems.append("没找到失败模式表（表头第一列要是「模式」、第二列「次数」）")
    else:
        head, rows = got
        for r in rows:
            if len(r) < 2 or r[0].strip("`*") not in fl:
                continue
            if _num(r[1]) != float(fl[r[0].strip("`*")]):
                problems.append(
                    f"失败模式：「{r[0]}」写 {r[1]} 次，数出来是 {fl[r[0].strip('`*')]}")
    for name in ("超时", "无据", "缺边界", "失焦"):
        if not re.search(re.escape(name) + r"\s*\*{0,2}\s*\|", text) and name not in " ".join(
                r[0] for _, rows in tables for r in rows):
            problems.append(f"失败模式：正文里找不到「{name}」那一类")

    # ⑤ 十日冲刺表：词 ｜ 补课处（条数与十个词都要对上）
    got = pick(tables, "缺口", "补课")
    if got is None:
        problems.append("没找到十日冲刺表（表头第一列要是「缺口」、第二列「补课」）")
    else:
        head, rows = got
        words = [r[0].strip("`*") for r in rows if len(r) >= 2]
        if len(words) != len(SPRINT):
            problems.append(f"十日冲刺表有 {len(words)} 条，口径里是 {len(SPRINT)} 条")
        for want, _where in SPRINT:
            if want not in words:
                problems.append(f"十日冲刺表缺「{want}」")

    # ⑥ 总账：实测合计与预算合计
    m = re.search(r"实测合计\s*\*{0,2}(\d+(?:\.\d+)?)\s*\*{0,2}\s*分钟", text)
    if m is None:
        problems.append("找不到总账那一句（要写成「实测合计 N 分钟」）")
    elif float(m.group(1)) != actual_total():
        problems.append(f"总账：正文写实测合计 {m.group(1)} 分钟，算出来是 {actual_total():g}")
    if not re.search(r"预算\s*\*{0,2}45\*{0,2}\s*分钟", text):
        problems.append(f"总账：正文里找不到预算 {total_budget()} 分钟")
    return problems


def report() -> None:
    print(f"一场模拟面试：{len(MOCK)} 道题、五个段落，预算 {total_budget()} 分钟"
          f"／实测 {actual_total():g} 分钟\n")
    print(f"{'段':<10}{'预算':>5}{'实测':>7}{'差':>7}   判定")
    for r in segment_rows():
        flag = "超时" if r["over"] else ("欠时" if r["under"] else "准")
        print(f"{r['seg']:<10}{r['budget']:>5}{r['actual']:>7}{r['diff']:>+7}   {flag}")
    print(f"{'合计':<10}{total_budget():>5}{actual_total():>7}"
          f"{round(actual_total() - total_budget(), 1):>+7}")
    print("\n追问穿透：")
    for r in layer_rows():
        print(f"  第{r['layer']}层  {r['hit']}/{r['total']}"
              f"（{r['hit'] / r['total']:.0%}）")
    print("\n评分（满分 20，及格线 14）：")
    sc = scores()
    for dim, rule in DIMENSIONS:
        print(f"  {dim:<4}{sc[dim]:>5}   {rule}")
    print(f"  总分{score_total():>6}")
    print("\n失败模式：")
    for k, v in failures().items():
        print(f"  {k:<10}{v:>4}")
    print("\n十日冲刺表：")
    for i, (w, where) in enumerate(SPRINT, 1):
        print(f"  {i:>2}. {w:<16}{where}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="只读剧本，不联网")
    ap.add_argument("--check", action="store_true", help="与正文 10.7 的四张表对账")
    ap.add_argument("--self-test", action="store_true", help="只跑夹具")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    problems = check_spec()
    if not args.check:
        report()
        if problems:
            print("\n剧本自身的对账：")
            for p in problems:
                print(f"  ✖ {p}")
            return 1
        return 0

    if not CHAPTER.exists():
        print(f"未找到 {CHAPTER.relative_to(ROOT).as_posix()}：本章还没有正文，清单要等正文落地")
        return 0
    problems += check_chapter(CHAPTER)
    if problems:
        for p in problems:
            print(f"  ✖ {p}")
        print(f"\n汇总：{len(problems)} 处与剧本不一致。修法：跑 --offline 取真值，再改正文。")
        return 1
    print(f"✔ 模拟面试的四组读数对账通过：{len(MOCK)} 道题／{total_budget()} 分钟／"
          f"总分 {score_total():g}（及格线 {PASS_LINE:g}），时间账、追问穿透、评分、"
          f"失败模式与十日冲刺表逐处等于算出来的值。")
    return 0


# ---- 夹具 --------------------------------------------------------------


def self_test() -> int:
    import tempfile
    from pathlib import Path as _P

    cases: list[tuple[str, str, bool, str]] = []
    real_mock = tuple(MOCK)
    real_segments = tuple(SEGMENTS)
    real_pass = globals()["PASS_LINE"]

    def run(name: str, expect: str, mutate=None, mock=None, segments=None,
            pass_line: float = 14.0) -> None:
        globals()["MOCK"] = tuple(mock if mock is not None else real_mock)
        globals()["SEGMENTS"] = tuple(segments if segments is not None else real_segments)
        globals()["PASS_LINE"] = pass_line
        with tempfile.TemporaryDirectory() as td:
            bad = check_chapter(_fake_chapter(_P(td), mutate)) + check_spec()
            good = (not bad) if expect == "应通过" else bool(bad)
            cases.append((name, expect, good, bad[0] if bad else "（没有报错）"))

    run("干净的一份", "应通过")
    run("时间账：实测抄错", "应报错",
        lambda t: t.replace("| 自我介绍 | 3 | 3.5 |", "| 自我介绍 | 3 | 4.5 |"))
    run("时间账：预算抄错", "应报错",
        lambda t: t.replace("| 项目讲述 | 12 | 13 |", "| 项目讲述 | 21 | 13 |"))
    run("时间账：漏一段", "应报错", lambda t: t.replace("| 反问 | 5 | 5 |\n", ""))
    run("时间账：多一段不在口径里", "应报错",
        lambda t: t.replace("| 反问 | 5 | 5 |", "| 闲聊 | 5 | 5 |"))
    run("追问穿透：第二层命中抄错", "应报错",
        lambda t: t.replace("| 第2层 | 5 | 6 |", "| 第2层 | 6 | 6 |"))
    run("追问穿透：第三层总数抄错", "应报错",
        lambda t: t.replace("| 第3层 | 1 | 3 |", "| 第3层 | 1 | 4 |"))
    run("评分：某一维抄错", "应报错",
        lambda t: t.replace("| 证据 | 3 |", "| 证据 | 4 |"))
    run("评分：总分抄错", "应报错", lambda t: t.replace("总分 13 分", "总分 14 分"))
    run("评分：及格线抄错", "应报错", lambda t: t.replace("及格线 14 分", "及格线 12 分"))
    run("失败模式：超时次数抄错", "应报错",
        lambda t: t.replace("| 超时 | 4 |", "| 超时 | 5 |"))
    run("失败模式：失焦次数抄错", "应报错",
        lambda t: t.replace("| 失焦 | 1 |", "| 失焦 | 0 |"))
    run("十日冲刺表：少一条", "应报错", lambda t: t.replace("| 容器与发布 | 8.1、8.2、8.5 |\n", ""))
    run("十日冲刺表：换成不在口径里的缺口", "应报错",
        lambda t: t.replace("| 幂等 | 3.5、6.3 |", "| 限流 | 8.4 |"))
    run("总账：实测合计抄错", "应报错",
        lambda t: t.replace("实测合计 46.5 分钟", "实测合计 45 分钟"))
    run("总账：预算那一句丢了", "应报错", lambda t: t.replace("预算 45 分钟", "预算四十五分钟"))
    # 剧本自身：把一道题改成超预算，逐题之和就不再等于段预算
    broken = [dict(q) for q in real_mock]
    broken[0]["budget"] = 4
    run("剧本自身：逐题预算之和不再等于段预算", "应报错", mock=broken)
    # 及格线是一条判据：改口径（而不是改正文）不算错
    run("口径自己改了及格线（正文也写 12）", "应通过",
        lambda t: t.replace("及格线 14 分", "及格线 12 分"), pass_line=12.0)

    globals()["MOCK"], globals()["SEGMENTS"], globals()["PASS_LINE"] = (
        real_mock, real_segments, real_pass)
    real = check_spec()
    cases.append(("真实剧本自洽（16 道题的预算加起来 45 分钟）", "应通过",
                  not real, real[0] if real else "（没有报错）"))
    real_ch = check_chapter(CHAPTER) if CHAPTER.exists() else []
    cases.append(("真实正文（10.7）与剧本逐处一致", "应通过",
                  not real_ch, real_ch[0] if real_ch else "（没有报错／本章还没有正文）"))

    ok = sum(1 for _, _, good, _ in cases if good)
    for name, expect, good, msg in cases:
        print(f"  {'✔' if good else '✖'} {name}（{expect}）"
              + ("" if good else f"  ← {msg}"))
    print(f"自检：{ok}/{len(cases)} 通过")
    return 0 if ok == len(cases) else 1


FAKE_CHAPTER = """# 10.7 假章

一场模拟面试：16 道题，预算 45 分钟／实测合计 46.5 分钟。

| 段 | 预算 | 实测 |
| --- | ---: | ---: |
| 自我介绍 | 3 | 3.5 |
| 项目讲述 | 12 | 13 |
| 系统设计 | 15 | 15 |
| 岗位知识 | 10 | 10 |
| 反问 | 5 | 5 |

| 层 | 命中 | 共 |
| --- | ---: | ---: |
| 第1层 | 7 | 7 |
| 第2层 | 5 | 6 |
| 第3层 | 1 | 3 |

| 维度 | 得分 | 判据 |
| --- | ---: | --- |
| 表达 | 3 | 5 − 答偏 × 1 − 超时段落 × 0.5 |
| 证据 | 3 | 5 − 不给数 × 1 |
| 取舍 | 3 | 5 − 第三层未命中 × 1 |
| 边界 | 4 | 5 − 第三层缺边界 × 1 |

总分 13 分，及格线 14 分。

| 模式 | 次数 | 处置 |
| --- | ---: | --- |
| 超时 | 4 | 把预算写进稿子 |
| 无据 | 2 | 每个结论配一个数 |
| 缺边界 | 1 | 第三层先答边界 |
| 失焦 | 1 | 复述一遍再答 |

| 缺口 | 补课 |
| --- | --- |
| 幂等 | 3.5、6.3 |
| 成本 | 6.4、10.3.4 |
| 评测 | 7.1、10.3.6 |
| 向量与检索 | 5.2–5.6 |
| 词元与上下文 | 3.6、6.4 |
| 流式与 SSE | 8.3 |
| 端侧与量化 | 6.1、9.2 |
| 推理延迟 | 7.1、7.2 |
| 提示与配置版本化 | 7.3 |
| 容器与发布 | 8.1、8.2、8.5 |
"""


def _fake_chapter(tmp: Path, mutate=None) -> Path:
    p = tmp / "10.7-假章.md"
    text = FAKE_CHAPTER
    if mutate:
        text = mutate(text)
    p.write_text(text, encoding="utf-8")
    return p


if __name__ == "__main__":
    sys.exit(main())
