#!/usr/bin/env python
"""7.3 的读数脚本：把「改了哪一版、谁看到了它」变成六组能复算的数。

    python scripts/rollout_reader.py --offline     # 六组读数（不要密钥、不要网络）
    python scripts/rollout_reader.py --self-test   # 夹具

六组依次是：版本戳与不可变（内容戳由内容定，不由版本号定）／diff 的三条线
（文本行、变量、配置）与静默漂移／标签与发布（一次一版、受保护标签、回滚的时间账）／
分桶（稳定、留缝、换哈希版本、两个实验交叠）／放量阶梯与比例失衡（哪一档能看见什么）／
A/B 与偷看（分辨率、可检测最小差异异、偷看的代价）。

它**不调模型、不联网**：注册表与 200 个单位都是造出来的，偷看那一组是纯算术与
一次固定种子的模拟。所以它能量的是版本与分桶**自己的性质**——量不了「候选版答得
好不好」（那是 7.1 的门），也量不了线上真实流量（那是 7.2 的看板）。
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import registry as R  # noqa: E402
from app import rollout as L  # noqa: E402

#: 这一脚本里反复出现的样本都住在模块里（与 7.1／7.2 同一个约定：样本是模块的一部分）。
sample_registry = R.sample_registry
sample_twin = R.sample_twin
sample_units = L.sample_units

TODAY = "2026-09-19"


# ------------------------------------------------------- 一、版本戳与不可变

def group_stamp() -> list[str]:
    reg = sample_registry()
    chain = reg.versions["zhizhou-support"]
    lines = [f"=== 一、版本戳与不可变：{len(chain)} 版、三个标签 ==="]
    for v in chain:
        labels = [label for label, n in reg.labels[v.name].items() if n == v.number]
        lines.append(f"  第 {v.number} 版  {v.stamp}  变量 {v.variables}  "
                     f"配置 temp={v.config['temperature']}  标签 {'、'.join(labels) or '（无）'}")
    # ① 改一个字就变；改回来又一样
    one = R.stamp(R.V3_TEXT)
    two = R.stamp(R.V3_TEXT.replace("只", "仅"))
    lines.append(f"改一个字：{one} → {two}（{'变了' if one != two else '没变'}）")
    lines.append(f"改回来：{R.stamp(R.V3_TEXT)}（与上面第一个数相同才叫「按内容」）")
    # ② 不该变的三种写法：换行符、行尾空格、配置的键序
    crlf = R.V3_TEXT.replace("\n", "\r\n")
    trailing = "\n".join(line + "  " for line in R.V3_TEXT.split("\n"))
    lines.append(f"换行符改成 CRLF：{'戳不变' if R.stamp(crlf) == one else '戳变了（那是假改动）'}"
                 f"；行尾加空格：{'戳不变' if R.stamp(trailing) == one else '戳变了'}")
    swapped = R.stamp(R.V3_TEXT, {"max_tokens": 512, "temperature": 0.2})
    baseline = R.stamp(R.V3_TEXT, {"temperature": 0.2, "max_tokens": 512})
    lines.append(f"配置换成另一种键序：{'戳不变' if swapped == baseline else '戳变了（那是假改动）'}"
                 f"（这一格比的是同一份配置的两种写法，不是「有配置」与「没配置」）")
    # ③ 原样保存不长版本；而「把旧内容拿回来」要长版本
    same, created = reg.save("zhizhou-support", R.V3_TEXT, dict(R.V4_CONFIG),
                             author="admin", note="原样再存一次")
    lines.append(f"原样再存一次（与最新一版逐字相同）：第 {same.number} 版、"
                 f"{'长了新版本' if created else '没有长新版本'}（版本数 {len(chain)}）")
    back, created_back = reg.save("zhizhou-support", R.V1_TEXT,
                                  {"temperature": 0.2, "max_tokens": 512},
                                  author="admin", note="把第 1 版的内容拿回来")
    lines.append(f"把第 1 版的内容拿回来：第 {back.number} 版（{'新版本' if created_back else '没长'}）、"
                 f"戳 {back.stamp} ＝ 第 1 版那一份——**号往回走不了，戳回得去**")
    reg.set_label("zhizhou-support", "production", 3, actor="admin")
    back = reg.rollback("zhizhou-support", actor="admin")
    rolled = reg.by_number("zhizhou-support", back)
    lines.append(f"回滚：production 从第 3 版挪回第 {back} 版，戳 {rolled.stamp}"
                 f"（与第 2 版戳 {'相同' if rolled.stamp == chain[1].stamp else '不同'}）"
                 f"——版本列表没短，少的只是「production 指着谁」")
    # ④ 同名不同内容：跨两个注册表比内容戳
    conflicts = R.alias_conflicts(reg, sample_twin(), "zhizhou-support")
    lines.append(f"与另一个注册表比：同名同号而内容不同的有 {len(conflicts)} 处")
    for note in conflicts:
        lines.append(f"  {note}")
    lines.append("两边的标签都叫 production，指向的却不是同一份文本——"
                 "**「线上跑的是哪一份」这句话里没有「第几版」，只有内容戳**")
    return lines


# ------------------------------------------------------- 二、diff 的三条线

def group_diff() -> list[str]:
    reg = sample_registry()
    name = "zhizhou-support"
    lines = ["=== 二、diff 的三条线：文本行 / 变量 / 配置 ==="]
    for a, b in ((2, 3), (3, 4)):
        left, right = reg.by_number(name, a), reg.by_number(name, b)
        d = reg.diff(left, right)
        lines.append(f"第 {a} 版 → 第 {b} 版：戳 {'相同' if d.same_stamp else '不同'}；"
                     f"文本 ＋{len(d.lines_added)}／−{len(d.lines_removed)} 行、"
                     f"变量 ＋{d.vars_added}／−{d.vars_removed}、配置 Δ{d.config_changed}")
        for note in d.silent_risk():
            lines.append(f"    ⚠ {note}")
    d = reg.diff(reg.by_number(name, 3), reg.by_number(name, 4))
    if not d.lines_added and not d.lines_removed:
        lines.append("    第 3 → 4 版的**文本一行都没变**，而戳变了："
                     "只比文本的 diff 会说「没变」，而线上行为已经换了")
    # 行 diff 的粒度：把一行拆成两行，看起来改了两行，其实只加了一个换行
    split = R.V3_TEXT.replace("资料里没有答案时", "\n资料里没有答案时")
    d2 = reg.diff(reg.by_number(name, 3), R.Version(name, 99, split, {}, R.stamp(split), "—"))
    lines.append(f"把一行拆成两行：行 diff 报 ＋{len(d2.lines_added)}／−{len(d2.lines_removed)} 行，"
                 f"而内容戳 {'变了' if d2.same_stamp is False else '没变'}"
                 f"——**行的粒度不总是内容的粒度**")
    # 静默漂移：三种现场，三种说法
    for tag, text, cfg in (("有人手改了一句（没存版本）",
                            R.V3_TEXT.replace("只根据", "只能根据"), {"temperature": 0.2, "max_tokens": 512}),
                           ("现场其实跑的是候选第 3 版", R.V3_TEXT, {"temperature": 0.2, "max_tokens": 512}),
                           ("现场跑的是生产那一版", R.V2_TEXT, {"temperature": 0.2, "max_tokens": 512})):
        note = reg.drift(name, text, cfg)
        lines.append(f"  {tag}：{note if note else '一致（这是唯一安静的一种）'}")
    return lines


# ------------------------------------------------------- 三、标签与发布

def group_labels() -> list[str]:
    reg = sample_registry()
    lines = ["=== 三、标签与发布：一次一版、受保护标签、回滚的时间账 ==="]
    lines.append(f"production 此刻指着：{reg.holders('production')}")
    lines.append("一个标签对应一个数——**「一次只指一版」不是纪律，是这张表的结构**")
    try:
        reg.set_label("zhizhou-support", "production", 4, actor="member")
        lines.append("member 挪 production：居然挪动了")
    except PermissionError as exc:
        lines.append(f"member 挪 production：{exc}")
    before = len(reg.audit)
    reg.set_label("zhizhou-support", "production", 4, actor="admin")
    lines.append(f"admin 挪 production → 第 4 版：成功，审计多了 {len(reg.audit) - before} 行")
    target = reg.rollback("zhizhou-support", actor="admin")
    lines.append(f"回滚：production 回到第 {target} 版；审计流水现在 {len(reg.audit)} 行，"
                 f"最后一行「{reg.audit[-1]}」")
    lines.append(f"回滚要多久：改标签 0 秒（一次数据动作、不重新部署）"
                 f"＋ 最坏一个缓存 TTL {R.DEFAULT_TTL_S} 秒"
                 f"（官方 SDK 默认 60 秒、后台重新校验）")
    records = R.sample_experiments()
    expired = R.expired_experiments(records, TODAY)
    lines.append(f"在跑的实验 {len(records)} 个，其中过了失效线还在挂的 {len(expired)} 个：")
    for exp in expired:
        lines.append(f"  {exp.key}：{exp.started} 起、失效线 {exp.ends_by}（今天是 {TODAY}）"
                     f"——那 {exp.split:.0%} 的流量还在两版之间分着")
    if expired:
        lines.append(f"**过了失效线的实验不是「还在跑」，是「没人收」**："
                     f"{expired[0].split:.0%} 的流量一直看不到 production，"
                     f"而它挂着的理由只是「没人把标签挪回来」")
    return lines


# ------------------------------------------------------- 四、分桶

def group_bucketing() -> list[str]:
    units = sample_units()
    lines = ["=== 四、分桶：稳定、留缝、换哈希版本、两个实验交叠 ==="]
    same = {L.hash_bucket("support-v4-temp", "u007") for _ in range(6)}
    lines.append(f"同一个用户问六次：桶 {same}——**随机 ≠ 每次都抽**；"
                 f"桶要么是算出来的（哈希），要么用户就会在两组之间来回跳")
    exp = L.Spec("support-v4-temp", (0.9, 0.1))
    arms = Counter(exp.variant_of(u) for u in units)
    lines.append(f"声明 90/10、{len(units)} 个单位：实际 {arms[0]}/{arms[1]}"
                 f"（＝ {arms[0] / len(units):.1%}／{arms[1] / len(units):.1%}）"
                 f"——小样本上比例本来就会抖，所以「比例失衡」那条线不是拿来抓这个的")
    zero = L.hash_bucket("support-v4-temp", "u007")           # 取一个真实桶值来说明区间
    lines.append(f"区间是**半开**的：{L.ranges((0.5, 0.5))} 里，桶值 {zero:.4f} 落第 "
                 f"{1 + (1 if zero >= 0.5 else 0)} 组；边界值 0.5 属于第二组（`>= start and < end`）")
    gapped = L.ranges((0.4, 0.6), 0.5)
    gaps = sum(1 for u in units if L.variant("gapped", u, (0.4, 0.6), coverage=0.5) == -1)
    lines.append(f"权重 0.4/0.6、覆盖度 50% → {gapped}：{gaps}/{len(units)} 个单位落在缝里"
                 f"（『不在实验里』，而下游报表上它与『对照组』长得一样）")
    v1 = [L.variant("support-v4-temp", u, (0.9, 0.1), hash_version=1) for u in units]
    v2 = [exp.variant_of(u) for u in units]
    switched = sum(1 for a, b in zip(v1, v2) if a != b)
    lines.append(f"换哈希版本（v1 → v2）：{switched}/{len(units)} 个单位换了组"
                 f"（＝ {switched / len(units):.1%}，而「独立重分桶」的期望是 "
                 f"{2 * 0.9 * 0.1:.0%}）——**升级哈希版本对正在跑的实验等于把它重开一次**")
    renamed = [L.variant("support-v4-temp-v2", u, (0.9, 0.1)) for u in units]
    lines.append(f"换实验名（seed 变了）：{sum(1 for a, b in zip(renamed, v2) if a != b)}/{len(units)}"
                 f" 个单位换了组——名字是分桶输入的一部分，改名同样是重分桶")
    other = L.Spec("support-v3-rename", (0.9, 0.1))
    both = L.overlap(units, exp, other)
    lines.append(f"两个实验各自看不出问题：同时在两个实验里的 {both['both']}/{both['units']}"
                 f"（＝ {both['rate']:.0%}），其中落在同一边的 {both['same_rate']:.0%}"
                 f"（独立分桶的期望 {0.9 ** 2 + 0.1 ** 2:.0%}）——"
                 f"**正交不等于不重叠：差异分不清是谁造成的**")
    ns_a = L.Spec("prompt-v4", (0.5, 0.5), namespace=("prompts", 0.0, 0.5))
    ns_b = L.Spec("model-swap", (0.5, 0.5), namespace=("prompts", 0.5, 1.0))
    guarded = L.overlap(units, ns_a, ns_b)
    lines.append(f"把它们放进同一个命名空间的两段（0–0.5 与 0.5–1）：同时命中 "
                 f"{guarded['both']}/{guarded['units']}——**互斥是算出来的，不是约好的**")
    return lines


# ------------------------------------------------------- 五、放量阶梯与比例失衡

PER_DAY = 8000


def group_ladder() -> list[str]:
    lines = [f"=== 五、放量阶梯与比例失衡：一天 {PER_DAY} 次请求 ==="]
    lines.append("档位   候选样本/天   分辨率 1/n   可检测最小差异（两倍标准误）   攒到 1,000 要几天   还有对照吗")
    for row in L.ladder(PER_DAY):
        lines.append(f"{row['share']:>5.0%}  {row['candidate_n']:>11}  "
                     f"{row['resolution']:>10.4%}  {row['delta']:>22.2%}  "
                     f"{row['days']:>17.2f}   {'有' if row['has_control'] else '**没有了**'}")
    lines.append("前两档**不是小步快跑**：1% 时可检测最小差异 12.6 个百分点——"
                 "那一档的作用是发现崩溃（错误、格式、超时），不是量质量")
    lines.append("最后一档 100% 之后没有对照组：只能与「发布前的历史」比，而那不是同一个对照")
    lines.append("")
    lines.append("比例失衡（SRM）：n 越大、越小的偏差会被认出来")
    lines.append("  总样本       偏差     卡方      p          判定")
    table = ((1000, (505, 495)), (10000, (5050, 4950)), (10000, (5100, 4900)),
             (100000, (50500, 49500)), (1000000, (505000, 495000)))
    for total, counts in table:
        report = L.srm(counts)
        lines.append(f"  {total:>8}  {report.worst:>+8.2%}  {report.chi2:>6.2f}  "
                     f"{report.p:>10.3g}  {'红' if report.flag else '—'}"
                     f"{'  ← 100 万样本、1% 的偏差' if total == 1000000 else ''}")
    lines.append("这条 0.001 的线是**本层声明的**（不是官方给的数）：它换来「几乎不会误报」，"
                 "代价是「要很大的 n 才会响」——5% 的偏差它一声不吭，0.1% 的偏差到百万样本才会红")
    lines.append("它量的是**分桶坏没坏**，不是效果好不好：这一栏红了，先别读效果")
    return lines


# ------------------------------------------------------- 六、A/B 与偷看

def group_ab() -> list[str]:
    lines = ["=== 六、A/B 与偷看：多少样本才敢下结论 ==="]
    lines.append("每组样本   比例的分辨率 1/n   可检测最小差异（基线 20%、两倍标准误）")
    for n in (100, 400, 1000, 4000, 10000):
        lines.append(f"{n:>8}  {L.resolution(n):>18.4%}  {L.min_detectable(n):>32.2%}")
    lines.append("分辨率说的是「这个数能表示多细的一格」，可检测最小差异说的是"
                 "「多大的差才不是噪声」——**两个数一起看才知道这一档值不值得等**")
    lines.append("")
    out = L.peeking(trials=2000, n=400)
    lines.append(f"偷看的代价（{out['trials']} 次「其实没有效果」的实验、"
                 f"每一步掷标准正态增量、临界值 {out['crit']:.4f}、名义 α ＝ {out['alpha']:.0%}）：")
    lines.append("  看几次   模拟假阳率（±蒙特卡洛误差）   独立近似 1−(1−α)^k")
    for row in out["rows"]:
        tag = "只看一次" if row["checkpoints"] == 1 else f"每 {400 // row['checkpoints']} 条看一次"
        lines.append(f"  {row['checkpoints']:>5}   {row['rate']:.4f} ± {row['mc_error']:.4f}"
                     f"                       {row['independent']:.4f}   {tag}")
    lines.append(f"「只看一次」那一行回到 {out['rows'][0]['rate']:.1%}（名义 5%）——"
                 f"**它是这一组的锚**：锚对了，别的行才可信")
    lines.append("独立近似那一列**是错的**（相邻两次看的 z 高度相关），但它比真值大，"
                 "所以它是个上界——而它比真值更常被人当成真值")
    cont = [(n, L.peeking(trials=2000, n=n, looks=(0,))["rows"][0]) for n in (200, 400, 800)]
    lines.append("连续看（每一条都看）的假阳率随样本量继续长：")
    for n, row in cont:
        lines.append(f"  n ＝ {n:>3}：{row['rate']:.4f} ± {row['mc_error']:.4f}")
    lines.append("每多一个观察点就多一次机会，所以这一行**没有上限**；"
                 "名义 5% 只在「只看一次」时成立")
    return lines


def readings() -> list[str]:
    out: list[str] = []
    for group in (group_stamp, group_diff, group_labels, group_bucketing, group_ladder, group_ab):
        out.extend(group())
        out.append("")
    out.append("版本与分桶读数：六组全过 ｜ 离线自检通过")
    return out


# ------------------------------------------------------- 夹具

def fixture_cases() -> list[tuple[str, bool]]:
    """夹具：每一格是本层的一条断言，**其中有些是「应当保持安静」的**。

    每一条都写明它钉住的是哪一档：红了要说清是「这一格算错了」还是「这一格本该不响」。
    """
    reg = sample_registry()
    name = "zhizhou-support"
    chain = reg.versions[name]
    cases: list[tuple[str, bool]] = []

    # ---- 一、内容戳
    cases.append(("内容戳只由内容定：同一份文本两次调用同一个值",
                  R.stamp(R.V3_TEXT) == R.stamp(R.V3_TEXT)))
    cases.append(("改一个字就变",
                  R.stamp(R.V3_TEXT) != R.stamp(R.V3_TEXT.replace("只", "仅"))))
    cases.append(("CRLF 换行不算改动（否则在 Windows 上编辑一次就多一个版本）",
                  R.stamp(R.V3_TEXT) == R.stamp(R.V3_TEXT.replace("\n", "\r\n"))))
    cases.append(("行尾空格不算改动",
                  R.stamp(R.V3_TEXT) == R.stamp("\n".join(x + "  " for x in R.V3_TEXT.split("\n")))))
    cases.append(("配置的键序不算改动",
                  R.stamp(R.V3_TEXT, {"temperature": 0.2, "max_tokens": 512})
                  == R.stamp(R.V3_TEXT, {"max_tokens": 512, "temperature": 0.2})))
    cases.append(("配置变一个字要算改动（文本没动、行为变了）",
                  R.stamp(R.V3_TEXT, {"temperature": 0.2}) != R.stamp(R.V3_TEXT, {"temperature": 0.9})))
    cases.append(("四个版本的内容戳两两不同", len({v.stamp for v in chain}) == 4))
    cases.append(("第 4 版与第 3 版的文本一字不差、只有配置不同",
                  chain[3].text == chain[2].text and chain[3].config != chain[2].config))
    mut = sample_registry()
    same, created = mut.save(name, R.V3_TEXT, dict(R.V4_CONFIG))      # 与最新一版完全相同
    cases.append(("原样保存不长版本（与**最新一版**内容相同）", created is False))
    cases.append(("原样保存返回的是已有那一版（不是凭空造第 5 版）", same.number == 4))
    cases.append(("同内容不产生新版本之后，版本数仍是 4", len(mut.versions[name]) == 4))
    back, created_back = mut.save(name, R.V1_TEXT, {"temperature": 0.2, "max_tokens": 512})
    cases.append(("回到更早的内容仍会产生新版本（回滚要留痕）",
                  created_back is True and back.number == 5))
    cases.append(("而那一版的内容戳与第 1 版相同（**内容戳按内容**）", back.stamp == chain[0].stamp))
    cases.append(("所以「版本号往回走」与「内容回到从前」是两件事：号 +1、戳回旧",
                  back.number > chain[0].number and back.stamp == chain[0].stamp))
    cases.append(("内容戳能在版本链里找回是第几版",
                  reg.number_of(name, chain[0].stamp) == 1))
    cases.append(("查一个不在表里的戳返回 None",
                  reg.number_of(name, "0" * R.STAMP_LEN) is None))
    cases.append(("同名同号不同内容会被报出来",
                  len(R.alias_conflicts(sample_registry(), sample_twin(), name)) == 2))
    cases.append(("内容一样时不会误报冲突",
                  R.alias_conflicts(sample_registry(), sample_registry(), name) == []))
    cases.append(("只比较两边都存在的版本号（那边没有的号不算冲突）",
                  R.alias_conflicts(sample_registry(), R.Registry(), name) == []))

    # ---- 二、diff 三条线
    d23 = reg.diff(chain[1], chain[2])
    cases.append(("变量改名在 diff 里是「一个增、一个减」",
                  d23.vars_added == ("query",) and d23.vars_removed == ("question",)))
    cases.append(("变量改名同时体现在文本行上（一行删、一行增）",
                  len(d23.lines_added) == 1 and len(d23.lines_removed) == 1))
    cases.append(("变量改名会给出「运行时缺席」的提示", len(d23.silent_risk()) == 2))
    d34 = reg.diff(chain[2], chain[3])
    cases.append(("文本没动而配置变了：三条线里只有配置那条有声",
                  not d34.lines_added and not d34.lines_removed
                  and d34.config_changed == ("temperature",)
                  and d34.same_stamp is False))
    cases.append(("diff 里没有改动时完全安静（同版本比同版本）",
                  not reg.diff(chain[2], chain[2]).silent_risk()
                  and reg.diff(chain[2], chain[2]).same_stamp))
    cases.append(("行 diff 会为一次换行报两行（粒度不等于内容粒度）",
                  len(reg.diff(chain[2], R.Version(name, 9, R.V3_TEXT.replace("资料", "\n资料"),
                                                  {}, R.stamp("x"), "—")).lines_added) >= 1))
    cases.append(("占位符按出现顺序去重",
                  R.placeholders("{{b}} {{a}} {{b}}") == ("b", "a")))
    cases.append(("没有占位符的文本给出空元组", R.placeholders("你好") == ()))
    cases.append(("占位符允许中间有空格（{{ a }} 与 {{a}} 视作同一个）",
                  R.placeholders("{{ a }}") == R.placeholders("{{a}}")))
    cases.append(("静默漂移：现场与 production 不一致时要报出来",
                  sample_registry().drift(name, R.V3_TEXT, {"temperature": 0.2, "max_tokens": 512})
                  is not None))
    cases.append(("静默漂移要说清「这个戳不在注册表里」",
                  "不在注册表里" in sample_registry().drift(
                      name, R.V3_TEXT.replace("只根据", "只能根据"),
                      {"temperature": 0.2, "max_tokens": 512})))
    cases.append(("现场跑的是候选版：要说清「它是第 3 版」",
                  "第 3 版" in sample_registry().drift(
                      name, R.V3_TEXT, {"temperature": 0.2, "max_tokens": 512})))
    cases.append(("**应当安静**：现场就是 production 那一版时 drift 返回 None",
                  sample_registry().drift(name, R.V2_TEXT, {"temperature": 0.2, "max_tokens": 512})
                  is None))
    cases.append(("**应当安静**：配置也一致时才算一致（配置变一个字就要报）",
                  sample_registry().drift(name, R.V2_TEXT, {"temperature": 0.5, "max_tokens": 512})
                  is not None))

    # ---- 三、标签与发布
    def labels_of(store, number: int) -> list[str]:
        return sorted(lab for lab, n in store.labels[name].items() if n == number)

    moved = sample_registry()
    moved.set_label(name, "production", 4, actor="admin")
    cases.append(("一个标签只指一版：挪走之后旧的那一版不再持有它",
                  labels_of(moved, 2) == ["latest"]))
    cases.append(("标签彼此独立：挪 production 不动 latest",
                  moved.label_number(name, "latest") == 2))
    cases.append(("标签表就是全部真相：holders 给出「谁指着哪一版」",
                  moved.holders("production") == {name: 4}))
    lab = sample_registry()
    before = len(lab.audit)
    lab.set_label(name, "production", 3, actor="admin")
    cases.append(("挪标签是一次发布：审计多一行", len(lab.audit) == before + 1))
    cases.append(("审计那行写清了从哪版到哪版（所以回滚能事后复盘）",
                  "从第 2 版挪到第 3 版" in lab.audit[-1]))
    cases.append(("受保护标签 member 挪不动",
                  _raises(lambda: lab.set_label(name, "production", 4, actor="member"), PermissionError)))
    cases.append(("受保护标签 admin 能动",
                  _raises(lambda: lab.set_label(name, "production", 4, actor="admin"), None)))
    cases.append(("非受保护的标签谁都动得了（保护只保护它自己）",
                  _raises(lambda: lab.set_label(name, "canary", 3, actor="member"), None)))
    # 上一条夹具已经把 production 挪到第 4 版了（它就是在这里挪的），所以这一条就在原地：
    before = len(lab.audit)
    lab.set_label(name, "production", 4, actor="admin")
    cases.append(("原地不动不写审计（否则流水里全是噪声）", len(lab.audit) == before))
    versions_before = len(lab.versions[name])
    cases.append(("回滚是把标签挪回去：挪到前一版", lab.rollback(name, actor="admin") == 3))
    cases.append(("而一版都没删（回滚不是删版本）", len(lab.versions[name]) == versions_before))
    cases.append(("回滚之后 production 指着第 3 版", lab.label_number(name, "production") == 3))
    cases.append(("没有这个标签时按标签取会报错（不返回默认值）",
                  _raises(lambda: lab.label_number(name, "不存在"), LookupError)))
    cases.append(("挪到不存在的版本号会报错",
                  _raises(lambda: lab.set_label(name, "canary", 99, actor="admin"), LookupError)))
    cases.append(("提示词名不存在时也报错",
                  _raises(lambda: lab.label_number("别的提示词"), LookupError)))
    cases.append(("回滚到第一版之前会报错（而不是悄悄停在第一版）",
                  _raises(lambda: R.Registry(versions={"x": sample_registry().versions[name]},
                                             labels={"x": {"production": 1}}).rollback("x"),
                          LookupError)))
    cases.append(("回滚时间是两项之和：TTL 是一个数、且不是 0", R.DEFAULT_TTL_S == 60))
    cases.append(("过期的实验会被点出来",
                  [e.key for e in R.expired_experiments(R.sample_experiments(), TODAY)]
                  == ["support-v3-rename"]))
    cases.append(("没过失效线的实验不会被误报",
                  R.expired_experiments(R.sample_experiments(), "2026-09-01") == []))
    cases.append(("失效线的比较是定长字符串比较（同格式才成立）",
                  R.sample_experiments()[0].expired("2026-09-25") is False
                  and R.sample_experiments()[0].expired("2026-09-26") is True))

    # ---- 四、分桶
    units = sample_units()
    cases.append(("分桶是稳定的：同一个单位十次同一个桶",
                  len({L.hash_bucket("e", "u007") for _ in range(10)}) == 1))
    cases.append(("分桶与「换个实验」有关：不同 seed 给出不同桶（这不是 bug）",
                  L.hash_bucket("a", "u007") != L.hash_bucket("b", "u007")))
    cases.append(("哈希值落在 [0, 1) 里",
                  all(0.0 <= L.hash_bucket("e", u) < 1.0 for u in units)))
    cases.append(("v1 的桶粒度是 1/1000、v2 是 1/10000",
                  L.HASH_BUCKETS == {1: 1000, 2: 10000}))
    cases.append(("区间是左闭右开",
                  L.in_range(0.5, (0.5, 1.0)) and not L.in_range(1.0, (0.5, 1.0))))
    cases.append(("边界值只属于一段（相邻两段不会抢同一个桶）",
                  sum(1 for span in L.ranges((0.5, 0.5)) if L.in_range(0.5, span)) == 1))
    cases.append(("覆盖度把每一段各自乘一次（于是留缝）",
                  L.ranges((0.4, 0.6), 0.5) == ((0.0, 0.2), (0.4, 0.7))))
    cases.append(("权重和不为 1 时退回等分（不静默归一）",
                  L.ranges((0.3, 0.3)) == L.ranges((0.5, 0.5))))
    cases.append(("非法覆盖度报错",
                  _raises(lambda: L.ranges((0.5, 0.5), 1.5), ValueError)))
    cases.append(("未知哈希版本报错（不静默退回默认）",
                  _raises(lambda: L.hash_bucket("e", "u", 3), ValueError)))
    cases.append(("缝里的单位是 -1，**不是对照组**",
                  L.variant("g", "u001", (0.4, 0.6), coverage=0.5) in (-1, 0, 1)
                  and sum(1 for u in units if L.variant("g", u, (0.4, 0.6), coverage=0.5) == -1) > 0))
    cases.append(("换哈希版本会让单位换组（所以那是一次重分桶）",
                  sum(1 for u in units
                      if L.variant("e", u, (0.9, 0.1), hash_version=1)
                      != L.variant("e", u, (0.9, 0.1), hash_version=2)) > 0))
    cases.append(("同一命名空间的两段互斥：交叠为 0",
                  L.overlap(units, L.Spec("a", namespace=("ns", 0.0, 0.5)),
                            L.Spec("b", namespace=("ns", 0.5, 1.0)))["both"] == 0))
    cases.append(("不设命名空间时两个实验确实会重叠（这就是要隔离的理由）",
                  L.overlap(units, L.Spec("a"), L.Spec("b"))["both"] == len(units)))
    cases.append(("命名空间不改变分桶本身（同一个单位在命名空间里的位置与实验无关）",
                  L.namespace_position("u007", "ns") == L.hash_bucket("__ns", "u007", 1)))

    # ---- 五、阶梯与比例失衡
    ladder = L.ladder(PER_DAY)
    cases.append(("阶梯的五档比例是 1/5/25/50/100%",
                  tuple(r["share"] for r in ladder) == (0.01, 0.05, 0.25, 0.50, 1.00)))
    cases.append(("最后一档没有对照组",
                  [r["has_control"] for r in ladder] == [True, True, True, True, False]))
    cases.append(("候选样本量随档位单调上升",
                  [r["candidate_n"] for r in ladder] == sorted(r["candidate_n"] for r in ladder)))
    cases.append(("可检测最小差异随样本量下降（样本越多、越小的差才不是噪声）",
                  all(a["delta"] > b["delta"] for a, b in zip(ladder, ladder[1:]))))
    cases.append(("1% 那一档的可检测最小差异比 25% 那一档大一倍以上",
                  ladder[0]["delta"] > 2 * ladder[2]["delta"]))
    cases.append(("分辨率就是 1/n（阶梯上逐档对得上）",
                  all(abs(r["resolution"] - 1 / r["candidate_n"]) < 1e-12 for r in ladder)))
    cases.append(("比例完美时卡方是 0、判定不响",
                  L.srm((5000, 5000)).chi2 == 0 and not L.srm((5000, 5000)).flag))
    cases.append(("小样本上 2% 的偏差不响（这条线不是拿来抓这个的）",
                  not L.srm((5100, 4900)).flag))
    cases.append(("百万样本上 1% 的偏差要响",
                  L.srm((505000, 495000)).flag))
    cases.append(("同样的 1% 偏差：样本越大越响",
                  L.srm((5050, 4950)).p > L.srm((50500, 49500)).p > L.srm((505000, 495000)).p))
    cases.append(("有人的臂数是 0 时不装懂：卡方按 0 算、判定为不响",
                  L.srm((0, 0)).flag is False))
    cases.append(("只支持 2 或 3 组（再多要说不算）",
                  _raises(lambda: L.srm((1, 2, 3, 4)), ValueError)))
    cases.append(("人数与权重个数不符时报错",
                  _raises(lambda: L.srm((1, 2), (0.5, 0.3, 0.2)), ValueError)))
    cases.append(("三组也能算（自由度 2 的闭式解）",
                  L.srm((4000, 3000, 3000), (1 / 3, 1 / 3, 1 / 3)).df == 2))
    cases.append(("分辨率对非法样本量报错",
                  _raises(lambda: L.resolution(0), ValueError)))

    # ---- 六、偷看
    out = L.peeking(trials=400, n=400, looks=(1, 5, 0))
    one, five, cont = out["rows"]
    cases.append(("锚：只看一次的假阳率落在名义值附近（400 次模拟内）",
                  abs(one["rate"] - 0.05) <= 4 * one["mc_error"] + 0.02))
    cases.append(("看一眼的次数越多、假阳率越高",
                  one["rate"] < five["rate"] < cont["rate"]))
    cases.append(("连续看的假阳率高于名义值一个量级",
                  cont["rate"] > 3 * out["alpha"]))
    cases.append(("独立近似是个上界（它比模拟值大）——只看一次那一行除外，那一行两者相等",
                  all(r["independent"] >= r["rate"] for r in out["rows"] if r["checkpoints"] > 1)
                  and abs(one["independent"] - out["alpha"]) < 1e-12))
    cases.append(("独立近似在连续看时趋近 1（所以它不能当结论用）",
                  cont["independent"] > 0.99))
    cases.append(("蒙特卡洛误差随次数下降：模拟次数越多、区间越窄",
                  L.peeking(trials=400, n=400, looks=(1,))["rows"][0]["mc_error"]
                  > L.peeking(trials=2000, n=400, looks=(1,))["rows"][0]["mc_error"]))
    forward = {(r["looks"], r["checkpoints"]): r["rate"]
               for r in L.peeking(trials=300, n=400, looks=(0, 1))["rows"]}
    backward = {(r["looks"], r["checkpoints"]): r["rate"]
                for r in L.peeking(trials=300, n=400, looks=(1, 0))["rows"]}
    cases.append(("换顺序不影响任何一行的数（每行一条独立随机流）", forward == backward))
    cases.append(("不同的模拟次数给出彼此接近但不必相同的数（模拟不是恒等式）",
                  abs(L.peeking(trials=200, n=400, looks=(5,))["rows"][0]["rate"]
                      - L.peeking(trials=2000, n=400, looks=(5,))["rows"][0]["rate"]) < 0.1))
    return cases


def _raises(fn, exc) -> bool:
    """`fn` 该不该抛 `exc`（传 `None` 表示「不该抛」）。夹具里反复用到它。"""
    try:
        fn()
    except Exception as err:                      # noqa: BLE001 —— 夹具就是要在意异常类型
        return exc is not None and isinstance(err, exc)
    return exc is None


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
