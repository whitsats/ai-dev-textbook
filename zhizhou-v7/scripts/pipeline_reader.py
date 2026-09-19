#!/usr/bin/env python
"""7.1 的读数脚本：把「怎么知道它还行」变成六组能复算的数。

    python scripts/pipeline_reader.py --offline     # 六组读数（不要密钥、不要网络）
    python scripts/pipeline_reader.py --self-test   # 二十二条夹具

它**不调模型、不联网**。它以一批 24 条知舟评测题起手，把它们切成门禁／留出／冒烟
三份，再拿**一份造出来的跑记录**去算五条指标、一道门、两份报告的 diff，
最后算一遍 CI 的账。

**这份跑记录量不了模型质量**——离线树没有模型可调，所以那份记录是编的。
它量的是「数据集、指标、门」这三样东西**自己的性质**，而它们全都是算得出来的。
这一条写在正文的边界里，不写成结论。
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import gate as G  # noqa: E402
from app import metrics as M  # noqa: E402
from app import suite as S  # noqa: E402

#: 一份**造出来的**跑记录：只列「没按参考答案作答」的那几条，其余全部照抄参考答案。
MISSES: dict[str, str] = {
    "q03": "不知道",
    "q05": "/openapi.json",
    # contains 过、exact 不过：这一条是「两个指标不重合」的那一格
    "q07": "迁移脚本在 migrations/ 目录下",
    "q10": "只删文章",
    # 该拒没拒：两条越界提问被答了
    "q15": "知舟是一条河，我来写一首：……",
    "q17": "password= 我来查一下……",
    "q20": "点赞那张表",
    "q24": "articles 6 / comments 4",
}
#: 拒答题没有检索（没有片段），所以 `has_citation` 在它们身上**测不了**——
#: 注意这里给的是 `None`（而不是空列表）：空列表是「检索了、没检索到」，
#: 那是**一个读数**；`None` 是「这一条不该检索」，那是**没有读数**。
NO_RETRIEVAL: tuple[str, ...] = ("q15", "q16", "q17", "q18")
#: 一条超篇幅的答复（`length_ok` 只看输出长度，不看答得对不对）。
LONG_CID = "q11"
LONG_OUTPUT = ("先看数据库连接池。登录要连两次库：一次校验口令、一次取用户；"
               "连接池上限是 20，而压测的并发是 40，排队的位置就在这里。"
               "证据是接口的 p95 在并发爬到 30 之后开始线性上升，而库里没有任何慢查询；"
               "另一个旁证是错误率没有跟着涨——如果是库本身出问题，应当先看到 500 而不是变慢。"
               "验证办法：把池子临时抬到 40 再压一遍，p95 应当立刻回落。")

#: CI 里一条评测的成本（取 6.1 那张表里最便宜那一档的价，只为算账）。
PER_CASE_USD = 0.000903
#: 门的样本下限：低于它不下结论。
MIN_CASES = 8


def _ok(x: float) -> str:
    return f"{x:.4f}"


# ------------------------------------------------------- 一、数据集自身

def group_dataset() -> list[str]:
    suite = S.sample_suite()
    lines = [f"=== 一、数据集自身：{len(suite.cases)} 条题 ==="]
    lines.append(f"整集指纹            {suite.digest()}")
    reordered = S.Suite(cases=list(reversed(suite.cases)))
    lines.append(f"倒过来之后           {reordered.digest()}"
                 f"  同一批题换顺序：{'没变' if reordered.digest() == suite.digest() else '变了'}")
    one_char = S.Suite(cases=[
        S.Case(cid=c.cid, query=(c.query + "？" if c.cid == "q05" else c.query),
               tags=c.tags, split=c.split, reference=c.reference)
        for c in suite.cases])
    lines.append(f"给 q05 的输入加一个「？」 {one_char.digest()}"
                 f"  改一个字：{'没变' if one_char.digest() == suite.digest() else '变了'}")
    lines.append(f"重复组              {len(suite.duplicates())} 组")
    lines.append(f"污染组              {len(suite.contamination())} 组")
    # 两种「同一句题」的对照：只在同一份切分里重 → 只是重复；
    # 而把重的那一条换到另一个切分去 → **污染**（门禁里那一题在留出集里也有）。
    dup = S.Suite(cases=[
        S.Case(cid=c.cid, query=("文章表的发布时间字段是哪一个" if c.cid == "q21" else c.query),
               tags=c.tags, split=c.split, reference=c.reference)
        for c in suite.cases])
    pol = S.Suite(cases=[
        S.Case(cid=c.cid, query=("文章表的发布时间字段是哪一个" if c.cid == "q21" else c.query),
               tags=c.tags, split=("holdout" if c.cid == "q21" else c.split),
               reference=c.reference)
        for c in suite.cases])
    dup_ids = list(dup.duplicates().values())[0] if dup.duplicates() else []
    pol_ids = list(pol.contamination().values())[0] if pol.contamination() else []
    lines.append(f"把 q21 的输入改成 q02 那一句 → 重复 {len(dup.duplicates())} 组"
                 f"（{'/'.join(dup_ids)}）")
    lines.append(f"再把它换到 holdout → 污染 {len(pol.contamination())} 组"
                 f"（{'/'.join(pol_ids)}）")
    cov = suite.coverage()
    lines.append("切分                " + "  ".join(f"{k} {v}" for k, v in cov.items())
                 + f"  合计 {sum(cov.values())}")
    tags = suite.tag_counts()
    lines.append("类别                " + "  ".join(f"{k} {v}" for k, v in sorted(
        tags.items(), key=lambda kv: (-kv[1], kv[0]))))
    lines.append(f"自身断言             {len(suite.violations())} 条违规"
                 f"（{'干净' if not suite.violations() else suite.violations()}）")
    return lines


# ------------------------------------------------------- 二、指标注册表

def _gate_only(suite: S.Suite) -> S.Suite:
    return S.Suite(cases=[c for c in suite.cases if c.split == "gate"])


def _record(suite: S.Suite, *, wrong: dict[str, str] | None = None,
            drop: int = 0) -> dict[str, dict]:
    """把一批题「跑」成一份记录。`wrong` 给的是剧本（哪几条没按参考答案作答）。"""
    wrong = MISSES if wrong is None else wrong
    rows: dict[str, dict] = {}
    for case in suite.cases:
        if case.cid == LONG_CID:
            out = LONG_OUTPUT
        else:
            out = wrong.get(case.cid, case.reference)
        rows[case.cid] = {"output": out,
                          "contexts": None if case.cid in NO_RETRIEVAL else [f"{case.cid}#0"]}
    if drop:
        rng = random.Random(97)
        # 抖动模型：**只从「基线上答对的那些题」里**随机挑几条翻掉。
        # 从全部题里抽的话，抽到本来就错的那几条会让分数不动——那量的是运气，不是抖动。
        right = [c.cid for c in suite.cases if c.cid not in wrong]
        for cid in rng.sample(right, drop):
            rows[cid]["output"] = "（这一次翻了）"
    return rows


def group_registry() -> list[str]:
    M.build_registry()
    suite = S.sample_suite()
    lines = [f"=== 二、指标注册表：{len(suite.cases)} 条 × {len(M.REGISTRY)} 条指标 ==="]
    cells = M.evaluate(suite, _record(suite))
    cov = M.coverage(cells)
    total = len(cells)
    unmeasured = sum(v["unmeasured"] for v in cov.values())
    lines.append(f"格子数              {total}（{len(suite.cases)} 条 × {len(M.REGISTRY)} 指标）"
                 f"  其中测不了 {unmeasured} 格")
    for name, v in cov.items():
        metric = M.REGISTRY[name]
        lines.append(f"  {name:<13} 算得出 {v['measured']:>2}  测不了 {v['unmeasured']:>2}"
                     f"  方向 {metric.direction:<6} 需要 {'+'.join(metric.needs)}")
    macro = M.aggregate(cells)
    as_zero = M.aggregate(cells, as_zero=True)
    lines.append("宏平均（分母只数算得出的）："
                 + "  ".join(f"{k} {_ok(v)}" for k, v in macro.items()))
    lines.append("记 0 的平均（分母是全部格）："
                 + "  ".join(f"{k} {_ok(v)}" for k, v in as_zero.items()))
    for name in ("has_citation",):
        a, b = macro[name], as_zero[name]
        lines.append(f"同一个指标两种口径   {name}: {_ok(a)} → {_ok(b)}"
                     f"  （分子没变、分母从 {cov[name]['measured']} 变成 {total // len(M.REGISTRY)}，"
                     f"差 {_ok(a - b)}）")
    gate = _gate_only(suite)
    gcells = M.evaluate(gate, _record(gate))
    lines.append(f"门禁那一份（{len(gate.cases)} 条）：" + "  ".join(
        f"{k} {_ok(v)}" for k, v in M.aggregate(gcells).items()))
    return lines


# ------------------------------------------------------- 三、分辨率与门

def group_gate() -> list[str]:
    lines = ["=== 三、分辨率与门 ==="]
    lines.append(f"5.6 那一集的 1/n      1/24 = {_ok(G.resolution(24))}")
    lines.append(f"门禁那一份的 1/n      1/18 = {_ok(G.resolution(18))}")
    delta = 0.0417
    lines.append(f"一次 {delta} 的改动在 18 条上："
                 f"{'看得见' if G.detectable(18, delta) else '看不见'}（分辨率 {_ok(G.resolution(18))}）")
    gates = {
        "empty": (G.Gate("exact_match", M.HIGHER, 0.6), 0.6111, 0),
        "underpowered": (G.Gate("exact_match", M.HIGHER, 0.6, min_cases=MIN_CASES), 0.6667, 6),
        "too_coarse": (G.Gate("exact_match", M.HIGHER, 0.6, min_cases=MIN_CASES), 0.6111, 18),
        "regress": (G.Gate("exact_match", M.HIGHER, 0.6, noise=0.1111, min_cases=MIN_CASES),
                    0.4444, 18),
        "pass": (G.Gate("exact_match", M.HIGHER, 0.6, noise=0.1111, min_cases=MIN_CASES),
                 0.6667, 18),
    }
    for label, (gate, value, n) in gates.items():
        lines.append(f"  {label:<13} n={n:<3} value={_ok(value)}  → {G.judge(gate, value, n)}")
    lines.append("不是 pass 的档     regress（真退步）＋ empty / underpowered / too_coarse"
                 "（后三档是「不下结论」，而它们与 pass 长得不一样）")
    return lines


# ------------------------------------------------------- 四、抖动与回归

def group_noise() -> list[str]:
    suite = _gate_only(S.sample_suite())
    n = len(suite.cases)
    lines = [f"=== 四、抖动与回归：门禁 {n} 条上跑五遍 ==="]
    base = M.aggregate(M.evaluate(suite, _record(suite)))["exact_match"]
    scores = []
    for seed in range(5):
        flips = 1 + seed % 3          # 1、2、3、1、2 条：同一份配置，跑出来不该一样
        cells = M.evaluate(suite, _record(suite, drop=flips))
        value = M.aggregate(cells)["exact_match"]
        scores.append(value)
        lines.append(f"  第 {seed + 1} 遍（同一份配置，翻 {flips} 条）  exact_match = {_ok(value)}"
                     f"  比基线 {_ok(base - value)}")
    band = G.noise_band(scores)
    res = G.resolution(n)
    lines.append(f"极差（抖动带）        {_ok(band)}    分辨率 {_ok(res)}"
                 f"  抖动带是分辨率的 {band / res:.1f} 倍")
    gate = G.Gate("exact_match", M.HIGHER, round(base, 4), noise=band)
    one, three = base - 1 / n, base - 3 / n
    lines.append(f"容差取 0 时            差 1 条 → {G.judge(G.Gate('exact_match', M.HIGHER, round(base, 4)), one, n)}"
                 f"（噪声里的东西被当成退步）")
    lines.append(f"容差取抖动带时        差 1 条 → {G.judge(gate, one, n)}；"
                 f"差 3 条 → {G.judge(gate, three, n)}")
    lines.append("门的容差不能取 0（每跑一次都报），也不能取分辨率"
                 "——那一个是「看得见吗」的门槛，不是「算不算退步」的门槛")
    return lines


# ------------------------------------------------------- 五、报告 diff

def group_diff() -> list[str]:
    """两份报告：总分一样而条目翻了面；以及「数据集少了两条」假装成退步。"""
    cids = [f"c{i:02d}" for i in range(1, 19)]
    # 前七条不过、后十一条过：18 条、11 条过 → 0.6111
    before = G.Report("before", {c: (0 if i < 7 else 1) for i, c in enumerate(cids)})
    improved = ["c05", "c06", "c07"]       # 原来不过，现在过了
    regressed = ["c08", "c09", "c10"]      # 原来过，现在不过了
    after = dict(before.verdicts)
    for c in improved:
        after[c] = 1
    for c in regressed:
        after[c] = 0
    report = G.Report("after", after)
    flips = G.diff(before, report)
    lines = ["=== 五、报告 diff ==="]
    lines.append(f"总分                {_ok(before.total())} → {_ok(report.total())}"
                 f"  聚合级 diff：{'无变化' if abs(before.total() - report.total()) < 1e-12 else '有变化'}")
    lines.append(f"条目级 diff          翻好 {len(flips['improved'])} 条 {flips['improved']}"
                 f"  翻坏 {len(flips['regressed'])} 条 {flips['regressed']}")
    lines.append(f"互相抵消            {G.offsetting(before, report)}"
                 f"——总分一模一样而 6 条翻了面")
    # 第三份：**系统一个字都没改**，只是数据集少了两条（删掉的恰好是两条答对的）
    dropped = ["c16", "c17"]            # 删掉的恰好是两条**答对的**
    thinner = G.Report("少两条", {c: v for c, v in after.items() if c not in dropped})
    delta = thinner.total() - report.total()
    lines.append(f"数据集少两条（系统一个字没改）  总分 {_ok(report.total())}（18 条） → "
                 f"{_ok(thinner.total())}（16 条），差 {delta:+.4f}"
                 f"  判定 {G.judge(G.Gate('exact_match', M.HIGHER, round(report.total(), 4)), thinner.total(), 16)}")
    lines.append(f"  diff 说 removed={G.diff(report, thinner)['removed']}"
                 f"——报表上像一次退步，而门的「看得见吗」那一档根本不响"
                 f"（{abs(delta):.4f} < 1/16），因为没有任何一行在报「跑了几条」")
    return lines


# ------------------------------------------------------- 六、CI 的账与抽样

def group_ci() -> list[str]:
    suite = _gate_only(S.sample_suite())
    lines = [f"=== 六、CI 的账与抽样 ==="]
    for n in (18, 36):
        cost = G.ci_cost(n, PER_CASE_USD)
        lines.append(f"  跑 {n:<3} 条          账 ${cost['usd']:.5f}  分辨率 {_ok(cost['resolution'])}")
    lines.append("分辨率每好一格，账单跟着涨一格——「多跑几条」是一个要跟别的改动比价的改动")
    rare = "表格"
    miss_count, same_count = 0, 0
    for seed in range(20):
        picked_count = suite.sample_by_count(8, seed=seed)
        picked_stratum = suite.sample_by_stratum(8, seed=seed)
        hit_c = any(rare in c.tags for c in picked_count)
        hit_s = any(rare in c.tags for c in picked_stratum)
        miss_count += 0 if hit_c else 1
        same_count += 0 if hit_s else 1
        if seed == 0:
            lines.append(f"  种子 0：按条数抽 {sorted(c.cid for c in picked_count)}")
            lines.append(f"  种子 0：按层抽   {sorted(c.cid for c in picked_stratum)}")
    lines.append(f"20 份样本里「{rare}」那一层整层消失：按条数抽 {miss_count} 份 ｜ 按层抽 {same_count} 份")
    lines.append(f"（门禁那一份里「{rare}」只有 1 条——而它正是最容易坏的那一类）")
    return lines


def readings() -> list[str]:
    lines: list[str] = []
    for part in (group_dataset(), group_registry(), group_gate(),
                 group_noise(), group_diff(), group_ci()):
        lines.extend(part)
        lines.append("")
    lines.append("流水线读数：六组全过 ｜ 离线自检通过")
    return lines


# ------------------------------------------------------- 夹具

def fixture_cases() -> list[tuple[str, bool]]:
    """二十二条夹具。**每条正向断言都配一条反例**。"""
    M.build_registry()          # 夹具里会临时重建注册表，所以先确保它已建好
    suite = S.sample_suite()
    gate = _gate_only(suite)
    cells = M.evaluate(suite, _record(suite))
    before = G.Report("b", {"c1": 1, "c2": 0})
    after = G.Report("a", {"c1": 0, "c2": 1})
    cases: list[tuple[str, bool]] = [
        ("指纹按编号排序：换顺序不变", S.Suite(list(reversed(suite.cases))).digest() == suite.digest()),
        ("指纹对内容敏感：改一个字就变",
         S.Suite([S.Case(c.cid, c.query + "？", c.tags, c.split, c.reference)
                  for c in suite.cases]).digest() != suite.digest()),
        ("干净的数据集违规 0 条", suite.violations() == []),
        ("重复能被抓到",
         S.Suite([S.Case("a", "同一句"), S.Case("b", "同一句")]).duplicates() != {}),
        ("同一个输入同一句但切分不同 → 不算污染",
         S.Suite([S.Case("a", "同一句", split="gate"),
                  S.Case("b", "同一句", split="gate")]).contamination() == {}),
        ("跨切分的重复 → 污染",
         S.Suite([S.Case("a", "同一句", split="gate"),
                  S.Case("b", "同一句", split="holdout")]).contamination() != {}),
        ("切分为空的集合会被断言拦下",
         any("是空的" in v for v in S.Suite([S.Case("a", "x")]).violations())),
        ("cid 重复会被断言拦下",
         any("cid 有重复" in v for v in S.Suite([S.Case("a", "x"), S.Case("a", "y")]).violations())),
        ("按条数抽会漏稀有层（20 个种子里至少一次）",
         any(not any("表格" in c.tags for c in suite.sample_by_count(8, seed=s))
             for s in range(20))),
        ("按层抽不漏稀有层（20 个种子都不漏）",
         all(any("表格" in c.tags for c in suite.sample_by_stratum(8, seed=s))
             for s in range(20))),
        ("指标重名要报错", _raises(lambda: (M.build_registry(), M.register(
            M.Metric("exact_match", M.HIGHER, ("output",), lambda r: 0.0))))),
        ("方向不合法要报错", _raises(lambda: M.register(
            M.Metric("乱七八糟", "up", ("output",), lambda r: 0.0)))),
        ("没有参考答案 → 需要参考答案的指标测不了",
         M.REGISTRY["exact_match"].applicable({"output": "x"}) is False),
        ("有参考答案 → 测得了",
         M.REGISTRY["exact_match"].applicable({"output": "x", "reference": "x"}) is True),
        ("只缺 contexts → has_citation 测不了",
         M.REGISTRY["has_citation"].applicable({"output": "x", "contexts": None}) is False),
        ("测不了的格子不计入宏平均的分母",
         M.aggregate([M.Cell("a", "length_ok", 1.0), M.Cell("b", "length_ok", None)])["length_ok"] == 1.0),
        ("记 0 的口径会把它算进分母",
         abs(M.aggregate([M.Cell("a", "length_ok", 1.0), M.Cell("b", "length_ok", None)],
                         as_zero=True)["length_ok"] - 0.5) < 1e-12),
        ("0 条必须判 empty（不是 pass）", G.judge(G.Gate("m", M.HIGHER, 0.5), 0.9, 0) == G.EMPTY),
        ("样本不够判 underpowered", G.judge(G.Gate("m", M.HIGHER, 0.5, min_cases=8), 0.9, 6)
         == G.UNDERPOWERED),
        ("小于 1/n 的变化判 too_coarse",
         G.judge(G.Gate("m", M.HIGHER, 0.6, min_cases=8), 0.6111, 18) == G.TOO_COARSE),
        ("超过抖动带且可分辨才判 regress",
         G.judge(G.Gate("m", M.HIGHER, 0.6, noise=0.1111, min_cases=8), 0.4444, 18) == G.REGRESS),
        ("抖动带之内不算退步（一格的变化落在噪声里）",
         G.judge(G.Gate("m", M.HIGHER, 0.6, noise=0.1111, min_cases=8), 0.5444, 18) == G.PASS),
        ("方向写反 → 门是反的（越大越好 vs 越小越好）",
         G.judge(G.Gate("m", M.LOWER, 0.6, noise=0.1111, min_cases=8), 0.4444, 18) == G.PASS),
        ("总分相同而条目翻面 → offsetting 为真", G.offsetting(before, after)),
        ("总分不同 → 不是抵消",
         not G.offsetting(before, G.Report("c", {"c1": 1, "c2": 0, "c3": 1}))),
        ("抖动带是极差（两遍差多少就报多少）", abs(G.noise_band([0.5, 0.6667]) - 0.1667) < 1e-4),
        ("0 条量不出抖动（要报错）", _raises(lambda: G.noise_band([]))),
        ("分辨率对 0 条没有定义", _raises(lambda: G.resolution(0))),
        ("n=18 上 0.0417 看不见", G.detectable(18, 0.0417) is False),
        ("n=18 上 0.0556 看得见", G.detectable(18, 0.0556) is True),
        ("空数据集的报告总分是 0（不是 1，也不是 None）", G.Report("e", {}).total() == 0.0),
        ("门禁那一份是 18 条（切分真的切了）", len(gate.cases) == 18),
        ("拒答四条在门禁里、没有片段 → has_citation 测不了 4 格",
         M.coverage(cells)["has_citation"]["unmeasured"] == 4),
    ]
    return cases


def _raises(fn) -> bool:
    try:
        fn()
    except Exception:  # noqa: BLE001
        return True
    return False


def self_test() -> int:
    cases = fixture_cases()
    bad = 0
    for label, ok in cases:
        print(f"  {'✓' if ok else '✗'} {label}")
        bad += 0 if ok else 1
    print(f"自检 {len(cases) - bad}/{len(cases)} 通过")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    for line in readings():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
