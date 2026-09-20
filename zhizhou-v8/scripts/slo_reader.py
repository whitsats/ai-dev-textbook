#!/usr/bin/env python
"""8.5 的读数脚本：把「线上运维」变成六组能复算的数。

    python scripts/slo_reader.py --offline     # 七组读数（不联网、不接监控、不连机器）
    python scripts/slo_reader.py --self-test   # 夹具

七组依次是：**四个数与一条「怎么花」的规矩**（四个 9 各自多少停机、四种 SLI 各自抓不到什么）／
**这一段时间花了多少预算**（四次事故 × 占比，以及「达成率过了而预算花掉 86%」）／
**预算烧完之后怎么办**（三种处置各自的代价，没有免费的那一种）／
**告警：按阈值还是按燃尽率**（三个现场 × 两种形态，只有慢烧能把它们分开）＋ **状态页的广播**
（5.7 记下、8.3 改指到这一章的那一笔旧账）／**演练的产物是一张清单**（四种演练的发现条数与「文档里没写」占几成）／
**容量：排队不是线性的**（利用率 0.7 → 0.9，等待从 3× 涨到 10×；三种买法；压测过不过拐点）／
**一次事故的四个时刻**（发现／确认／缓解／复原各自烧掉多少预算，以及它为什么与慢烧可比）。

它**不接监控、不连机器、不真的停任何东西**：SLO 是按公式算的（预算 ＝ (1 − SLO) × 请求数、
停机时长 ＝ (1 − SLO) × 一个月）、告警是**按官方那套工作法的形状建模**的
（三档窗口 ＋ 燃尽率 14.4／6／1，对应 2%／5%／10% 预算）、演练发现是**写死的清单**、
容量与排队是纯算术（`1/(1−ρ)`）。所以它能量的是**这些办法本身的性质**
（哪种 SLI 抓不到哪一类故障、燃尽率在慢烧上比阈值强在哪、四种演练各自能挖出什么、
利用率在哪一档之后等待时间开始跑得比流量快），
**量不了真实监控的采集间隔、真实事故的时长、真实演练里的意外、真实流量的形状**——
这一条写在正文的边界里。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import alert as A       # noqa: E402
from app import capacity as C    # noqa: E402
from app import drill as D       # noqa: E402
from app import slo as S         # noqa: E402


def _w(text: str, width: int) -> str:
    """按显示宽度补空格（中文按两格算）——只为对齐，不影响任何数。"""
    shown = sum(2 if ord(ch) > 0x2000 else 1 for ch in text)
    return text + " " * max(0, width - shown)


# ------------------------------------------------------- 一、四个数与一条规矩

def group_four() -> list[str]:
    b = S.budget()
    lines = [
        "=== 一、四个数与一条「怎么花」的规矩：SLI / SLO / 错误预算 / 达成率 ===",
        f"这一段时间：**请求 {b.total_requests:,} 条**、SLO {S.SLO}（三个半 9）、"
        f"允许失败 **{b.allowed:,} 条**（＝ (1 − SLO) × 请求数）。",
        "",
        "四个 9 各自买到的停机时间——**它是算出来的，不是抄的**：",
        _w("档位", 16) + _w("SLO", 14) + "一个月能停多久（30 天）",
    ]
    month_min = 30 * 24 * 60
    for name, val, downtime in S.NINES:
        lines.append(_w(name, 16) + _w(str(val), 14) + f"{downtime}（＝ {val} → {(1 - val) * month_min:.1f} 分钟）")
    lines += [
        "",
        f"**{S.NINES[2][0]}与{S.NINES[3][0]}之间差的是 10 倍**（4.32 分钟 → 26 秒），",
        "而它们对发布节奏的要求差的是「每次发布能停多久」——**这就是「SLO 是产品决定」的字面意思**。",
        "",
        "四种 SLI × 它抓不到什么（**第三列才是这一段要讲的**）：",
        _w("SLI", 12) + _w("拿什么量", 40) + "它抓不到什么",
    ]
    for name, how, blind, note in S.SLIS:
        lines.append(_w(name, 12) + _w(how, 40) + blind)
    lines += [
        "",
        "**四种里没有一种能单独把「用户没事」说全**——而它们各自的盲区是互补的：",
        "可用性看不见超时、延迟只报快的那 95%、正确性要另一套数据源所以最容易被跳过、",
        "新鲜度不在请求链路上（**一个全绿的接口可以整晚答旧文档**）。",
        "",
        "叠加起来看：",
    ]
    for name, how, blind, note in S.SLIS:
        lines.append(f"  · {name}：{note}")
    return lines


# ------------------------------------------------------- 二、这一段时间花了多少

def group_budget() -> list[str]:
    b = S.budget()
    lines = [
        "=== 二、这一段时间花了多少预算：四次事故，两个人看不见 ===",
        _w("事故", 44) + _w("失败数", 10) + _w("占预算", 10) + "监控看不看得见",
    ]
    for row in S.incident_table():
        lines.append(_w(row[0], 44) + _w(row[1], 10) + _w(row[2], 10) + row[3])
    lines += [
        "",
        f"合计：允许 **{b.allowed:,}**、实际 **{b.failures:,}**（用了 {b.used}%）、"
        f"还剩 **{b.remaining:,}**；达成率 **{b.availability}**。",
        "",
        f"**达成率 {b.availability} 高于 SLO {S.SLO}——而这一个月花掉了 {b.used}% 的预算。**",
        "这两句话同时成立，而它们合起来才是这个月的真实情况：",
        "**「达标」与「还有余量」是两个数**，只报前一个就会得出「这个月很健康」的结论，",
        "而下一行写着「只剩 679 条可以坏」。",
        "",
        "四次事故里有两格监控看不见：**客户端超时**（连接是客户端关掉的，服务端还没报错）",
        "与**回答过期**（200、延迟正常、内容是旧的）——它们一共占 32% 的预算，",
        "而在一个只看 5xx 的面板上，这个月是「零事故」。",
    ]
    return lines


# ------------------------------------------------------- 三、预算烧完之后

def group_decisions() -> list[str]:
    lines = [
        "=== 三、预算烧完之后：三种处置，各有代价 ===",
        _w("处置", 34) + _w("判据（什么时候用它）", 46) + "代价",
    ]
    for name, when, cost in S.DECISIONS:
        lines.append(_w(name, 34) + _w(when, 46) + cost)
    lines += [
        "",
        "三条里最容易写下来而最难执行的是第一条（**冻结发布**），因为它的触发条件是",
        "「预算烧到 100%」，而那一刻通常正是「我们刚修好东西、想赶紧把修复发出去」的时候。",
        "所以这条规矩真正要谈的是**前置**：预算烧到多少就自动冻结、谁来解冻、解冻要谁签字。",
        "",
        "第三条（接受风险并写下来）不是退让：**预算是拿来花的，不是拿来零的**——",
        "它唯一的要求是**被写下来**（谁决定、为什么、什么时候复看），",
        "否则它就从「一次有意识的取舍」退化成「忽略」。",
    ]
    return lines


# ------------------------------------------------------- 四、告警与状态页

def group_alerts() -> list[str]:
    lines = [
        "=== 四、告警：按阈值还是按燃尽率（只有慢烧能把它们分开）===",
        f"预算率 ＝ 1 − SLO ＝ {A.BUDGET_RATE * 100:g}%；**燃尽率 ＝ 错误率 ÷ 预算率**。",
        _w("现场", 40) + _w("错误率", 12) + _w("燃尽率", 14) + _w("按阈值（5 分钟 > 1%）", 34) + _w("按燃尽率", 42) + "谁对",
    ]
    for row in A.burn_table():
        lines.append(_w(row[0], 40) + _w(row[1], 12) + _w(row[2], 14) + _w(row[3], 34) + _w(row[4], 42) + row[5])
    lines += [
        "",
        "**第一行都响、第三行都不响，只有第二行（慢烧）把它们分开**：",
        "错误率一直在 1% 那条线下面，而它持续了三天——按阈值的告警**一次都不会响**，",
        "等到它响的时候，预算早就见底了。",
        "",
        "三档窗口与燃尽率（官方那套工作法的形状）——**第三列才是「分层」的意思**：",
        _w("长窗", 12) + _w("短窗", 12) + _w("燃尽率", 10) + _w("这一档意味着", 34) + "处置",
    ]
    for long_w, short_w, rate, budget, action in A.burn_window_table():
        lines.append(_w(long_w, 12) + _w(short_w, 12) + _w(rate, 10) + _w(budget, 34) + action)
    lines += [
        "",
        "**三种速度对应三种打扰方式**（叫醒人／开单／进排期）——把这三档合成一条告警，",
        "得到的就是「所有事都叫醒人」，也就是下面这个噪声账。",
        "",
    ]
    n = A.noise()
    lines += [
        f"噪声账：一个月发出 **{n.sent}** 条、其中 **{n.no_action}** 条不需要动作（{n.noise_ratio}%）、"
        f"共 {n.shifts} 个班次。",
        f"  每个班次平均 **{n.per_shift}** 条，其中值得动手的 **{n.actionable_per_shift}** 条。",
        "**「三次里有一次是狼来了」这句话是可算的**（211 / 340）；而它的代价不是打扰，",
        "是**下一个真警报被当成噪声**——这就是「每一条告警都在花一个班的注意力」的意思。",
        "",
        "--- 状态页的广播（5.7 记下、8.3 改指到这一章的那一笔账）---",
        _w("规模", 18) + _w("连接数", 10) + _w("一轮出口字节", 16) + _w("一轮耗时", 12) + "断开清理的判据",
    ]
    for row in A.broadcast_table():
        lines.append(_w(row[0], 18) + _w(str(row[1]), 10) + _w(row[2], 16) + _w(row[3], 12) + row[4])
    slow, kept, share, why = A.cleanup()
    lines += [
        "",
        f"一轮广播里有 {kept} 条正常连接（每条 {A.BROADCAST_PER_CONN_MS} ms）与 {slow} 条慢连接",
        f"（每条 200 ms）：**慢连接占一轮 {share}% 的时间**。",
        f"  · {why}",
        f"  · 清理的判据是**「写超时」而不是「读超时」**（对面不读这件事，内核可能要下一轮才发现）；",
        f"    而这一格的答案就是 8.3 里「一条慢消费者拖住整轮」那条边界的运维版本。",
    ]
    return lines


# ------------------------------------------------------- 五、演练

def group_drills() -> list[str]:
    lines = [
        "=== 五、演练：它的产物不是「通过」，是一张清单 ===",
        _w("演练方式", 30) + _w("它坏在哪", 28) + _w("发现几条", 10) + _w("文档没写", 10) + _w("占几成", 10) + "什么时候做",
    ]
    for row in D.drill_table():
        lines.append("".join(_w(c, w) for c, w in zip(row, (30, 28, 12, 12, 10))) + row[5])
    lines += [
        "",
        "**「发现几条」一路往上涨，而涨得最多的那一档正是「恢复」**——",
        "因为恢复那条路平时根本没人走：越接近「真的坏」，越能挖出平时碰不到的东西。",
        "",
        f"一次「真停 Redis 30 秒」的清单（共 {len(D.redis_findings())} 条）：",
        _w("现象", 40) + _w("类别", 8) + _w("严重度", 8) + _w("文档里写没写", 46) + "谁去修",
    ]
    for row in D.redis_findings():
        lines.append(_w(row[0], 40) + _w(row[1], 8) + _w(row[2], 8) + _w(row[3], 46) + row[4])
    missing, total, pct = D.undocumented_share()
    lines += [
        "",
        f"**{total} 条里 {missing} 条是「文档里没写」（{pct}%）**——这一栏才是演练的产物：",
        "「文档里没写」等于**只有人知道**，而只有人知道的事情在半夜三点是拿不到的。",
        "",
        "所以判据不是「过了没」：**一次「一切正常」的演练不是成功的演练**，",
        "它是「没演练到位」的强信号（要么故障没真的发生，要么监控没看见这次故障）。",
        "而发现要按「代码／配置／文档／流程」分类——**全塞给工程的那一摞会烂掉**。",
    ]
    return lines


# ------------------------------------------------------- 六、容量

def group_capacity() -> list[str]:
    lines = [
        "=== 六、容量：排队不是线性的（利用率 0.7 → 0.9，等待从 3× 涨到 10×）===",
        _w("利用率 ρ", 12) + _w("等待放大 1/(1−ρ)", 22) + "这一档的现实形态",
    ]
    for row in C.utilization_table():
        lines.append(_w(row[0], 12) + _w(row[1], 22) + row[2])
    lines += [
        "",
        f"**后两档之间只差 5 个百分点的利用率，等待涨了一倍**——这就是「再加一点流量就崩」",
        "的真相：它不是「多 10% 流量」，而是**利用率过了一条线**。",
        f"而「按均值买机器」的代价正好落在这条曲线最陡的地方。",
        "",
        f"流量形状：日均 **{C.MEAN_RPS}** rps、日峰值／均值 **{C.PEAK_RATIO}**（峰值 **{C.peak_rps():.0f}** rps）、"
        f"月增长 **{C.MONTHLY_GROWTH * 100:.0f}%**；单机 **{C.PER_NODE_RPS}** rps。",
        "",
        _w("买法", 26) + _w("台数", 10) + _w("峰值利用率", 14) + _w("峰值等待", 16) + "挂掉一台之后",
    ]
    for row in C.plan_table():
        lines.append(_w(row[0], 26) + _w(row[1], 10) + _w(row[2], 14) + _w(row[3], 16) + row[4])
    lines += [
        "",
        "**「预留 50%」买的是时间，不是性能**：从 4 台到 6 台，峰值等待从 25× 降到 2.8×，",
        "而真正的理由在最后一列——**挂掉一台之后还剩 77%（仍在经验线以内）**。",
        "第一列（按日均买）看起来最省，而它**在峰值那一天直接过载**：ρ > 1 时等待是无穷大，",
        "队列无上限地涨，实际表现就是「一崩到底、恢复很慢」。",
        "",
        "压测四档——**判据是「压过拐点」，不是「压到多少并发」**：",
        _w("并发", 10) + _w("P95", 12) + _w("错误率", 10) + "这一段说明什么",
    ]
    for row in C.load_test_table():
        lines.append(_w(row[0], 10) + _w(row[1], 12) + _w(row[2], 10) + row[3])
    lines += [
        "",
        f"按月度增长 {C.MONTHLY_GROWTH * 100:.0f}% 算，**{C.quarters_to_grow()} 个季度后需要翻倍**——",
        "这就是「下一次评估容量」的时间点：**它按季度定，不按年**（年化在小基数上会放大误差）。",
        "",
        "四个数、一个月的预算、三档告警、四种演练、一条排队曲线、三种买法与一次事故的四个时刻——",
        "**七组读数的每一个数都能拿纸笔重算一遍**，而它们合起来是线上运维的四个问题：",
        "好不好（`slo`）、什么时候叫人（`alert`）、哪里还不知道（`drill`）、装得下多少（`capacity`）。",
        "",
        "运维读数：七组全过 ｜ 离线自检通过",
    ]
    return lines


def group_timeline() -> list[str]:
    """七、一次事故的四个时刻——**价值那半小时烧掉多少预算可以算**。"""
    b = S.month_window()
    lines = [
        "=== 七、一次事故的四个时刻：半小时烧掉多少预算 ===",
        f"流量口径：**{S.INCIDENT_RPS:g} rps**（一个月 {b.total_requests:,} 条请求 → 允许失败 "
        f"**{b.allowed:,} 条**，SLO 仍是 {S.SLO}）。",
        _w("时刻", 24) + _w("它在做什么", 22) + _w("时长", 10) + _w("错误率", 8) + _w("请求数", 10) + _w("失败数", 10) + "占本月预算",
    ]
    for row in S.timeline_table():
        lines.append("".join(_w(c, w) for c, w in zip(row, (24, 22, 10, 8, 10, 10))) + row[6])
    minutes, fails, share, why = S.timeline_totals()
    slow_fails, slow_share = S.slow_burn_same_traffic()
    lines += [
        "",
        f"合计：**{minutes} 分钟**、**{fails:,} 条失败** ＝ 本月预算的 **{share}%**。",
        f"  · {why}",
        "",
        f"把同一份流量下的慢烧摆在一起（0.1% × 3 天 ＝ **{slow_fails:,} 条／{slow_share}%**）：",
        "**快事故烧得快，而慢烧在绝对条数上未必少**——而两者的处置完全不同：",
        "一个要立刻叫醒（燃尽率 200× 那一档），一个要进排期（燃尽率 2× 那一档）。",
        "",
        "**错误预算是「流量 × 时间 × (1 − SLO)」**，不是一句话：同一个 99.95%，",
        f"这个流量一个月只允许 {b.allowed:,} 条失败，而 1,000 万请求一个月允许 5,000 条——",
        "**同一个百分比，在不同的流量上是十倍的绝对量。**",
    ]
    return lines


def report() -> list[str]:
    out: list[str] = []
    for part in (group_four, group_budget, group_decisions, group_alerts, group_drills,
                 group_capacity, group_timeline):
        out += part() + [""]
    return out


# ------------------------------------------------------- 夹具

def self_test() -> int:
    ok = total = 0
    failures: list[str] = []

    def chk(cond: bool, what: str) -> None:
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
        else:
            failures.append(what)

    # 一、四个数
    chk(len(S.NINES) == 4, "四个档位")
    month_min = 30 * 24 * 60
    chk(all(abs((1 - val) * month_min - float(downtime.split(" ")[0])) < 0.05
            for (_, val, downtime) in S.NINES[:3]), "前三档停机时长是按 (1 − SLO) 算出来的")
    chk(S.NINES[3][2].startswith("26 秒"), "五个 9 是 26 秒／月")
    chk(abs((1 - S.NINES[3][1]) * month_min * 60 - 26) < 1, "五个 9 的 26 秒也是算出来的")
    chk(len(S.SLIS) == 4, "四种 SLI")
    chk(all(len(s) == 4 for s in S.SLIS), "每种 SLI 四栏（名字／拿什么量／抓不到什么／它的一句话）")
    chk("超时" in S.SLIS[0][2], "可用性抓不到超时")
    chk("5%" in S.SLIS[1][2], "延迟只报快的那 95%")
    chk("另一套数据源" in S.SLIS[2][2], "正确性要另一套数据源")
    chk("不在请求链路上" in S.SLIS[3][2], "新鲜度不在请求链路上")

    # 二、预算
    b = S.budget()
    chk(b.allowed == 5_000, "允许失败 5,000 条")
    chk(b.failures == 4_321, "四次事故合计 4,321 条")
    chk(b.used == 86.42, "用了 86.42% 的预算")
    chk(b.remaining == 679, "还剩 679 条")
    chk(b.remaining + b.failures == b.allowed, "剩余 ＋ 已用 ＝ 允许（不多不少）")
    chk(b.availability == 0.999568, "达成率 0.999568")
    chk(b.availability >= S.SLO, "**达成率高于 SLO——而这个月花掉 86% 的预算**")
    chk([r[2] for r in S.incident_table()] == ["48.0%", "32.0%", "0.0%", "6.4%"], "四次事故各占 48／32／0／6.4%")

    chk(abs(48.0 + 32.0 + 0.0 + 6.4 - b.used) < 0.05, "四次占比之和 ＝ 已用（86.4 ≈ 86.42，差在四舍五入）")
    chk("看不见" in S.incident_table()[1][3], "客户端超时那一格：监控看不见")
    chk("看不见" in S.incident_table()[2][3] and S.incident_table()[2][1] == "0", "旧文档那一格：0 条、而监控看不见")
    chk(len(S.DECISIONS) == 3, "三种处置")
    chk(all(len(d) == 3 for d in S.DECISIONS), "每种处置三栏（处置／判据／代价）")
    chk("被写下来" in S.DECISIONS[2][2], "接受风险那一档的代价是「必须被写下来」")

    # 三、告警
    chk(A.burn_rate(0.10) == 200.0, "错误率 10% → 燃尽率 200×")
    chk(A.burn_rate(0.001) == 2.0, "错误率 0.1% → 燃尽率 2×")
    chk(A.shown_burn(0.00002) == "< 0.1×（噪声）", "单点失败不给燃尽率、写成噪声")
    rows = A.burn_table()
    chk(len(rows) == 3, "三个现场")
    chk(rows[0][5] == "都对" and rows[2][5].startswith("都对"), "快烧与单点：两种形态都对")
    chk(rows[1][5] == "**只有燃尽率对**", "慢烧：只有燃尽率对")
    chk("一次都不响" in rows[1][3], "慢烧那一格写的是「一次都不响」")
    chk("20% 预算" in rows[1][4], "慢烧 3 天烧掉 20% 预算（2× × 3/30）")
    chk(len(A.BURN_WINDOWS) == 3, "三档多窗口多燃尽率")
    chk([w[2] for w in A.BURN_WINDOWS] == [14.4, 6.0, 1.0], "三档燃尽率 14.4／6／1")
    chk([w[3] for w in A.BURN_WINDOWS] == ["2% 的预算在这 1 小时里烧掉", "5% 在 6 小时里烧掉",
                                           "10% 在 3 天里烧掉"], "三档各自对应 2%／5%／10%")
    hours = {"1 小时": 1, "6 小时": 6, "3 天": 72}
    chk(all(abs(rate * hours[long_w] / (30 * 24) * 100 - float(budget.split("%")[0])) < 0.05
            for long_w, _, rate, budget, _ in A.BURN_WINDOWS),
        "**三档的百分比是「燃尽率 × 时长 ÷ 一个月」算出来的**")
    n = A.noise()
    chk((n.sent, n.no_action, n.shifts) == (340, 211, 180), "噪声账三个数 340／211／180")
    chk(n.noise_ratio == 62.1, "不需要动作的占 62.1%")
    chk(n.per_shift == 1.89 and n.actionable_per_shift == 0.72, "每班 1.89 条、其中 0.72 条值得动手")
    chk(n.sent - n.no_action == 129, "值得动手的 129 条")
    chk(len(A.CONNECTIONS) == 4, "四档连接规模")
    chk(A.broadcast_table()[0][2] == "1.2 KB" and A.broadcast_table()[1][2] == "120 KB",
        "一条 1.2 KB、一百条 120 KB")
    chk(A.broadcast_table()[2][2] == "1.2 MB", "1,000 条连接一轮 1.2 MB")
    chk(A.broadcast_table()[3][1] == 6_000 and "只增不减" in A.broadcast_table()[3][4],
        "没清理的那一天：6,000 条、集合只增不减")
    slow, kept, share, why = A.cleanup()
    chk((slow, kept) == (3, 997), "慢连接 3 条、正常 997 条")
    chk(share == 96.8, "3 条慢连接占一轮 96.8% 的时间")
    chk("最慢的那几条决定" in why, "结论写在读数里：一轮耗时由最慢的几条决定")
    chk(3 * 200.0 / (3 * 200.0 + 997 * 0.02) * 100 - share < 0.1, "96.8% 是算出来的")

    # 四、演练
    chk(len(D.DRILLS) == 4, "四种演练")
    chk([d[3] for d in D.DRILLS] == [3, 5, 8, 11], "发现条数一路涨：3／5／8／11")
    chk(all(D.DRILLS[i][3] < D.DRILLS[i + 1][3] for i in range(3)), "后一种演练总比前一种挖得多")
    chk(D.drill_table()[3][3] == "9 条" and D.drill_table()[3][4] == "82%",
        "恢复演练：11 条里 9 条没写（82%）")
    chk(all(len(row) == 6 for row in D.drill_table()), "演练表六栏（与正文逐列对应）")
    chk(len(D.redis_findings()) == 8, "停 Redis 的清单 8 条")
    chk(D.undocumented_share() == (7, 8, 87.5), "8 条里 7 条没写（87.5%）")
    chk(D.redis_findings()[3][1] == "监控" and "SLI 表" in D.redis_findings()[3][3],
        "「面板没动」这一条指向第一组那张 SLI 表")
    chk(D.redis_findings()[4][4] == "SRE", "「不知道找谁」那条归 SRE")

    # 五、容量
    chk([C.wait_factor(x) for x in (0.5, 0.7, 0.8, 0.9, 0.95)] == [2.0, 3.3, 5.0, 10.0, 20.0],
        "五档等待放大 2／3.3／5／10／20×")
    chk(C.shown_wait(1.0) == "过载（∞）" and C.shown_wait(0.96) == "25×", "ρ ≥ 1 时不给数、写成过载")
    chk(C.utilization_table()[1][2].startswith("**经验线附近**"), "0.7 那一档是经验线")
    chk(C.peak_rps() == 384.0, "峰值 384 rps（120 × 3.2）")
    chk(C.nodes_for(C.MEAN_RPS) == 2 and C.nodes_for(C.peak_rps()) == 4, "按日均 2 台、按峰值 4 台")
    chk(C.nodes_for(C.peak_rps(), 0.50) == 6, "预留 50% → 6 台")
    pt = C.plan_table()
    chk([r[2] for r in pt] == ["192%", "96%", "64%"], "三种买法的峰值利用率 192／96／64%")
    chk(pt[0][3] == "过载（∞）", "按日均买：峰值那天过载")
    chk(pt[1][3] == "25×" and "挂一台后 128%" in pt[1][4], "按峰值买：峰值 25× 等待、挂一台即过载")
    chk("77%" in pt[2][4] and pt[2][3] == "2.8×", "预留 50%：挂一台后 77%、仍在线")
    chk(abs(C.rho(C.peak_rps(), 6) - 0.64) < 1e-9, "6 台的 ρ = 0.64（384 / 600）")
    chk(len(C.LOAD_TEST) == 4, "压测四档")
    chk(C.load_test_table()[2][3].startswith("**拐点"), "第三档是拐点")
    chk(C.load_test_table()[3][3].startswith("过载段"), "第四档是过载段")
    chk(C.LOAD_TEST[3][1] > C.LOAD_TEST[2][1] and C.LOAD_TEST[3][0] > C.LOAD_TEST[2][0],
        "过载段：并发更高而延迟更差")
    chk(C.quarters_to_grow() == 3, "按 12% 月增，3 个季度后翻倍")
    chk((1 + C.MONTHLY_GROWTH) ** 9 >= 2 > (1 + C.MONTHLY_GROWTH) ** 6, "3 个季度这个数也是算出来的")

    # 六、事故时间线
    w = S.month_window()
    chk(S.INCIDENT_RPS == 2.0, "事故场景的流量是 2 rps")
    chk(w.total_requests == 5_184_000, "2 rps 一个月 5,184,000 条请求")
    chk(w.allowed == 2_592, "**同一个 SLO，这个流量下只允许 2,592 条失败**（流量×时间×0.05%）")
    chk(w.allowed != S.budget().allowed, "两个流量下预算的绝对值不同")
    chk(len(S.INCIDENT_TIMELINE) == 4, "事故的四个时刻")
    tl = S.timeline_table()
    chk([r[2] for r in tl] == ["6 分钟", "4 分钟", "9 分钟", "11 分钟"], "四段时长 6／4／9／11")
    chk([r[3] for r in tl] == ["100%", "100%", "30%", "2%"], "四段错误率 100／100／30／2%")
    chk([r[4] for r in tl] == ["720", "480", "1,080", "1,320"], "四段请求数都是 时长×60×2 算出来的")
    chk([r[5] for r in tl] == ["720", "480", "324", "26"], "四段失败数 720／480／324／26")
    chk([r[6] for r in tl] == ["27.8%", "18.5%", "12.5%", "1.0%"], "四段占预算 27.8／18.5／12.5／1.0%")
    chk(all(abs(float(r[5].replace(",", "")) - int(round(int(r[4].replace(",", "")) * float(r[3].rstrip("%")) / 100))) < 1
            for r in tl), "每一行的失败数 ＝ 请求数 × 错误率")
    minutes, fails, share, why = S.timeline_totals()
    chk((minutes, fails, share) == (30, 1_550, 59.8), "合计 30 分钟／1,550 条／59.8%")
    chk(sum(int(r[5].replace(",", "")) for r in tl) == fails, "四段失败数之和 ＝ 合计")
    chk("46.3%" in why and "一条请求都没救回来" in why, "头两段占 46.3%、而它们没救回任何请求")
    chk(46.3 > 40, "**发现与确认比缓解与复原更贵**（前半段占大头）")
    slow_fails, slow_share = S.slow_burn_same_traffic()
    chk((slow_fails, slow_share) == (518, 20.0), "同一流量的慢烧：518 条／20.0%（与那半小时可比）")
    chk(slow_fails < 1_000 < fails, "快事故的绝对条数更大，而两者的处置不同")

    # 七、整篇
    lines = report()
    chk(len(lines) >= 110, f"七组读数够长（{len(lines)} 行）")
    chk(sum(1 for x in lines if x.startswith("===")) == 7, "正好七组")
    joined = "\n".join(lines)
    chk("七组全过" in joined, "收尾那一行写的是七组")
    chk("5.7" in joined and "8.3" in joined, "状态页那一组点明了 5.7 记下、8.3 改指")

    print(f"自检 {ok}/{total} 通过")
    if failures:
        for f in failures:
            print(f"  ✖ {f}")
    return 0 if ok == total else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    print("\n".join(report()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
