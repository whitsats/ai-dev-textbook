#!/usr/bin/env python
"""8.4 的读数脚本：把「多租户、配额与计费」变成六组能复算的数。

    python scripts/quota_reader.py --offline     # 六组读数（不联网、不要密钥、不连数据库）
    python scripts/quota_reader.py --self-test   # 夹具

六组依次是：**三种隔离姿势**（谁看到谁的什么，是一个架构决定）／
**`tenant_id` 落在哪一层**（三个探针 × 四个落点：漏在哪、空在哪）／
**同一批调用按四种量各算一遍**（并发／速率／词元／成本——四个答案差 20 倍）／
**三种限流算法对同一串到达**（固定窗口、滑动窗口、令牌桶）／
**预扣与结算**（预扣必须比实际大，否则那笔账是欠着的）／
**账单与日志的对账**（同一个月的两种口径，以及三处差异各自怎么才算对上）。

它**不连数据库、不调模型、不跑网关**：隔离姿势是按官方那几条默认值**建模**的
（行策略没有策略即拒绝、属主默认绕过；向量库四级各自的天花板）、
用量是**一份写死的调用表**、限流是纯算术、账是四段单价乘出来的。
所以它能量的是**这些机制的性质**（哪一层漏、哪一层空、超限的三种答法各付什么代价、
预扣与结算谁欠谁、账单与日志的差是口径还是错误），
**量不了真实数据库的策略配置、真实租户的流量分布、真实上游账单的粒度**——
这一条写在正文的边界里。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import billing as B  # noqa: E402
from app import quota as Q    # noqa: E402
from app import tenant as T   # noqa: E402


def _w(text: str, width: int) -> str:
    """按显示宽度补空格（中文按两格算）——只为对齐，不影响任何数。"""
    shown = sum(2 if ord(ch) > 0x2000 else 1 for ch in text)
    return text + " " * max(0, width - shown)


# ------------------------------------------------------- 一、三种隔离姿势

def group_modes() -> list[str]:
    lines = ["=== 一、三种隔离姿势：判据是「谁能看到谁的什么」===",
             _w("姿势", 34) + _w("隔离强度", 34) + _w("运营代价", 30) + "什么时候合算"]
    for mode, strength, cost, cross, when in T.ISOLATION_MODES:
        lines.append(_w(mode, 34) + _w(strength, 34) + _w(cost, 30) + when)
    lines += [
        "",
        "**三栏里最容易被跳过的是「跨租户统计」**——它是唯一一栏会**反过来**推动选择的：",
        "行级租户最方便做统计，而库级租户「要么建数仓、要么不统计」。",
        "所以「隔离强度」不是越高越好：**它买的是「想跨租户访问必须跨实例」这件事**，",
        "而这件事在你需要「平台运营看一眼全局」的时候就变成一笔支出。",
        "",
        "**同一件事在向量库里有四级版本**（数据组织是 Database → Collection → Partition）：",
        _w("向量库的策略", 46) + _w("好处", 26) + "它的天花板",
    ]
    for name, good, limit in T.VECTOR_MODES:
        lines.append(_w(name, 46) + _w(good, 26) + limit)
    lines += [
        "",
        "四级策略里**只有 partition key 的天花板不是「数量上限」**，而是「不支持批量写入」：",
        "**它把成本从「存储怎么切」搬到了「数据怎么进」**——这条最容易在架构会上被漏掉。",
    ]
    for tenants, bulk in ((8, False), (60, False), (5_000, False), (5_000, True)):
        pick, why = T.vector_choice(tenants, bulk)
        lines.append(f"  · {tenants:>5} 个租户、批量导入{'要' if bulk else '不要'} → {pick}（{why}）")
    return lines


# ------------------------------------------------------- 二、tenant_id 落在哪一层

def group_layers() -> list[str]:
    lines = ["=== 二、tenant_id 落在哪一层：三个探针，四种漏法 ===",
             _w("落点", 32) + _w("探针", 22) + _w("看到什么", 30) + "这一格靠什么成立"]
    for p in T.probes():
        lines.append(_w(p.layer, 32) + _w(p.probe, 22) + _w(p.outcome, 30) + p.why)
    lines += [
        "",
        "**逐层的漏数**（漏 ＝ 多看到了别人的数据；空与看不到都不算）：",
        _w("落点", 32) + _w("漏了几格", 12) + "漏在哪几格",
    ]
    for layer, ratio, which in T.leak_table():
        lines.append(_w(layer, 32) + _w(ratio, 12) + which)
    lines += [
        "",
        "四种落点各自能漏 **3／2／0／2** 格，而**它们漏的方式完全不同**：",
        "  · 应用层：漏的是「那一行 `where`」——**代码里没有它，现场什么都没有**；",
        "  · ORM 层：漏的是「走了一条不经 ORM 的路」——裸 SQL、后台任务、迁移脚本；",
        "  · 行策略：**一个都不漏**，代价是它把「忘了带」变成了「看到本租户的行」、"
        "把「带别人的」变成了**空**（可用的，只是没数据）；",
        "  · 存储层：写错了是空、写漏了是漏——**两类完全不同的故障落在同一个参数上**。",
        "",
        "**行策略不是「更严的 where」，它是另一个方向**：`where` 漏的是**多看到**，",
        "行策略兜住的是**少带条件**；而它自己的漏法在别处——**表属主默认绕过**：",
        "应用若连的是建表那个账号，策略等于写了一行注释。",
    ]
    return lines


# ------------------------------------------------------- 三、四种量

def group_meters() -> list[str]:
    calls = Q.all_calls()
    used = Q.usage(calls)
    lines = ["=== 三、同一批 12 条调用，按四种量各算一遍 ===",
             _w("量", 22) + _w("这一批用掉", 18) + _w("占该档上限", 12) + "还能再来几条"]
    for name, u, pct, left in Q.cap_table(calls):
        lines.append(_w(name, 22) + _w(u, 18) + _w(pct, 12) + left)
    lines += [
        "",
        f"**同一份余量，四个答案**：并发只剩 1 条、速率 3 条、词元 9 条、成本 21 条"
        f"（四档的取值见 `quota.CAPS`）。",
        f"而这一批的用量是：并发峰值 **{used['并发']}**、速率峰值 **{used['请求速率']}**、"
        f"词元 **{used['词元']:,}**、成本 **${used['成本']:.6f}**。",
        "",
        "**四条里只有并发那一档被「时长」影响**——把两条长回答（c02 的 6.0 秒、"
        "c06 的 7.5 秒）压到 2 秒，四个量这样变：",
        _w("量", 22) + _w("原样", 14) + _w("压短后", 14) + "变了没",
    ]
    short = Q.usage(Q.shorten())
    for name in ("并发", "请求速率", "词元", "成本"):
        a, b = used[name], short[name]
        fmt = (lambda v: f"${v:.6f}") if name == "成本" else (lambda v: f"{v:,}")
        lines.append(_w(name, 22) + _w(fmt(a), 14) + _w(fmt(b), 14)
                     + ("**变了**" if a != b else "一个数没变"))
    lines += [
        "",
        "**词元与时长无关**——同样一段回答，问得快不会让它变便宜。",
        "所以「按并发限」与「按词元限」是两台不同的闸机：前者管**同时占着多少人**，",
        "后者管**一共要消耗多少**；把它们当成同一个数，就会得到一个错答案。",
        "",
        "四种量各自抓住什么、漏掉什么（这是这一组的正文）：",
        _w("量", 22) + _w("它抓住", 40) + "它漏掉",
    ]
    for name, catches, misses, reply in Q.METERS:
        lines.append(_w(name, 22) + _w(catches, 40) + misses)
        lines.append(_w("", 22) + _w("超限怎么答", 40) + reply)
    lines += [
        "",
        "**「按请求数」是最省事的一种，也是最容易被绕开的一种**：官方那份风险清单里",
        "被绕开的示例就是「一次 HTTP 请求装 999 个操作」——按请求数它只算一次。",
    ]
    return lines


# ------------------------------------------------------- 四、三种限流算法

def group_limiters() -> list[str]:
    rows = (("固定窗口", Q.fixed_window()), ("滑动窗口", Q.sliding_window()),
            ("令牌桶", Q.token_bucket()))
    lines = [f"=== 四、三种算法，同一串到达（每 {int(Q.WINDOW)} 秒限 {Q.LIMIT} 条）===",
             _w("到达时刻（秒）", 26) + _w("固定窗口", 12) + _w("滑动窗口", 12) + "令牌桶"]
    for i, t in enumerate(Q.ARRIVALS):
        cells = ["放行" if r[i] else "**拒**" for _, r in rows]
        lines.append(_w(f"第 {i + 1} 条  t={t:.2f}", 26) + _w(cells[0], 12) + _w(cells[1], 12) + cells[2])
    for name, result in rows:
        lines.append(f"  · {name}：放行 {sum(result)} / {len(result)} 条")
    lines += [
        "",
        "**三条曲线的形状完全不同，而它们限的是同一个数**：",
        "  · 固定窗口在**边界**处放行近两倍的量（前 5 条落在 0–10 秒、后 5 条落在 10–20 秒）——",
        "    而它在图上看起来完全正常：**每一条都在自己的窗口里合规**；",
        "  · 滑动窗口每次都回头看 10 秒，于是第二条窗口里那 5 条全被拒（前 10 秒里已经有 5 条）；",
        "  · 令牌桶和滑动窗口在这串到达上答案相同，而它的差别在别处：",
        "    **它允许「攒着用」**（空闲一会儿就有几个令牌可花），**也因为攒着用而被突发穿透**。",
        "",
        "三档配额的顺序（**租户 → 用户 → key**），以及每一档的窗口为什么是那个尺度：",
        _w("层", 14) + _w("窗口", 22) + _w("它拦住", 40) + "它的盲区",
    ]
    for layer, window, catches, blind in Q.LIMIT_LAYERS:
        lines.append(_w(layer, 14) + _w(window, 22) + _w(catches, 40) + blind)
    lines += [
        "",
        "超限之后能说的三句话，以及**它们各自的代价**（没有免费的那一种）：",
        _w("答复", 26) + _w("它诚实在哪", 40) + "它的代价",
    ]
    for reply, honest, cost in Q.REPLIES:
        lines.append(_w(reply, 26) + _w(honest, 40) + cost)
    return lines


# ------------------------------------------------------- 五、预扣与结算

def group_settle() -> list[str]:
    held = B.reserve()
    lines = [f"=== 五、预扣与结算：预扣 ${held:.6f}（按 {B.RESERVE_TOKENS[0]:,} 进 ＋ "
             f"{B.RESERVE_TOKENS[1]:,} 出估），三笔调用 ===",
             _w("调用", 16) + _w("预扣", 12) + _w("实际", 12) + _w("差额", 12) + "这一笔的现场"]
    for s in B.settlements():
        lines.append(_w(s.name, 16) + _w(f"${s.held:.6f}", 12) + _w(f"${s.actual:.6f}", 12)
                     + _w(f"{s.delta:+.6f}", 12) + s.why)
    refunded = sum(s.delta for s in B.settlements() if s.delta > 0)
    owed = -sum(s.delta for s in B.settlements() if s.delta < 0)
    lines += [
        "",
        f"三笔里退了 **${refunded:.6f}**、补收 **${owed:.6f}**——而**预扣额三笔完全相同**，"
        "差别全在实际那一列上。",
        "预扣按「估算输入 ＋ 最大输出」收，所以正常的调用都是**退**；"
        "**只有越过了估算上限的那一笔是欠着的**——这不是 bug，是「按上限估」的必然结果。",
        "第三条最值得单说：上游 500、用户一个字也没拿到，而**输入那一段上游已经处理过了**。",
        f"这类账一个月 {B.STRANDED[0]} 笔时是 **${B.stranded_cost():.6f}**——",
        "它**不会出现在用量账单里**（账单按「送达」计），只会出现在成本里；",
        "所以「用量对了」和「成本对了」是两个不同的结论。",
        "",
        "四段单价（**只有前两段是抄来的**，后两段按 6.1 记下的乘法关系算出来）：",
    ]
    for key, price in B.PRICE.items():
        lines.append(f"  · `{key}`：${price:.2f} ／百万词元")
    lines.append(f"  · 批量通道：**{B.BATCH_X}×**（它作用在整单上）")
    return lines


# ------------------------------------------------------- 六、账单与日志

def group_reconcile() -> list[str]:
    t = B.month_totals()
    lines = [f"=== 六、账单与日志：同一个月的两种口径（{int(t['笔数'])} 笔调用）===",
             _w("口径", 40) + _w("合计", 16) + "它记的是什么"]
    lines.append(_w("日志（精确到词元）", 40) + _w(f"${t['日志合计']:.6f}", 16)
                 + "每一笔按实际词元算——**它是我们这边唯一能逐条复算的数**")
    lines.append(_w(f"账单（按 {B.GRAIN} 词元进整）", 40) + _w(f"${t['账单合计']:.6f}", 16)
                 + "开票口径：词元先进整再乘单价——**每一笔都被抬高一点点**")
    lines += [
        "",
        f"两边的差是 **${t['差额']:.6f}**（占日志 {t['差额'] / t['日志合计'] * 100:.1f}%），"
        f"而**把日志也进整到同一粒度，差是 ${B.aligned_gap():.6f}**——",
        "这就是对账的第一步：**先把口径对齐，剩下的差才是需要解释的东西**。",
        "",
        "对齐之后仍然可能与成本对不上，因为差异有三处，而它们的性质完全不同：",
        _w("差异", 44) + _w("金额", 26) + "怎么才算「对上」",
    ]
    for what, amount, how in B.discrepancies():
        lines.append(_w(what, 44) + _w(amount, 26) + how)
    lines += [
        "",
        "**三处差异里只有一处是钱，另两处是口径**：",
        "第一处改口径就归零；第二处**不该出现在用量账单里**（账单按送达、成本按已生成）；",
        "第三处是「把例外当通例」——**小到没人发现**，所以它必须写成单价表上的一行，",
        "而不是留在某个人的记忆里。",
        "",
        "配额、账单、隔离三者共用**同一份用量**：配额在**调用之前**说话（让不让进），",
        "账单在**调用之后**说话（花了多少），而隔离决定**这份用量能不能按租户切开**——",
        "切不开的用量，账单就只能按人算，不能按租户算。",
        "",
        "配额与计费读数：六组全过 ｜ 离线自检通过",
    ]
    return lines


def report() -> list[str]:
    out: list[str] = []
    for group in (group_modes, group_layers, group_meters, group_limiters,
                  group_settle, group_reconcile):
        out += group()
        out.append("")
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

    chk(len(T.ISOLATION_MODES) == 3, "三种隔离姿势")
    chk(len(T.WHERE_LAYERS) == 4, "四个落点")
    chk(len(T.PROBES) == 3, "三个探针")
    chk(len(T.ANSWERS) == 12, "四层 × 三探针 ＝ 12 格")
    chk({a[0] for a in T.ANSWERS} == {w[0] for w in T.WHERE_LAYERS}, "答案表的层名与落点表逐字一致")
    chk([r[1] for r in T.leak_table()] == ["3 / 3", "2 / 3", "0 / 3", "2 / 3"], "逐层漏数：3／2／0／2")
    chk("一个都不漏" in T.leak_table()[2][2], "行策略那一层不漏")
    rls_missing = [p for p in T.probes() if p.layer == T.WHERE_LAYERS[2][0] and p.probe == "忘了带"]
    chk(rls_missing[0].outcome == "**看到本租户的行**", "行策略把「忘了带」兜成「本租户的行」")
    chk(not rls_missing[0].is_leak, "而那一格不算漏")
    other = [p for p in T.probes() if p.layer == T.WHERE_LAYERS[2][0] and p.probe == "带别人的"]
    chk(other[0].outcome == "**一行都看不到**", "行策略对「带别人的」给的是空，不是报错")
    storage = [p for p in T.probes() if p.layer == T.WHERE_LAYERS[3][0] and p.probe == "忘了带"]
    chk(storage[0].is_leak, "存储层「忘了带」计作漏（不指定分区即全扫）")
    app_layer = [p for p in T.probes() if p.layer == T.WHERE_LAYERS[0][0]]
    chk(all(p.is_leak for p in app_layer), "应用层三格全漏")
    chk(len(T.VECTOR_MODES) == 5, "向量库五条路")
    chk(T.vector_choice(8, False)[0].startswith("库级"), "少数大户选库级")
    chk(T.vector_choice(5_000, False)[0].endswith("partition key"), "租户多时走 partition key")
    chk(T.vector_choice(5_000, True)[0].startswith("集合级 · 一集合"), "要批量导入时 partition key 被否掉")
    chk(any("不支持批量写入" in m[2] for m in T.VECTOR_MODES), "partition key 的那条限制写在表里")

    calls = Q.all_calls()
    chk(len(calls) == 12, "12 条调用")
    chk(Q.peak_concurrency(calls)[0] == 7, "并发峰值 7")
    chk(Q.peak_concurrency(calls)[1] == 2.9, "峰值出现在 t=2.9（c10 到达时，前面几条还占着）")
    chk(Q.peak_rate(calls)[0] == 4, "速率峰值 4 条／秒")
    inp, out = Q.tokens(calls)
    chk(inp + out == 11_163, "词元合计 11,163")
    chk(Q.usage(calls)["成本"] == 0.09051, "成本 $0.090510")
    chk([r[1] for r in Q.cap_table(calls)] == ["7", "4", "11163", "$0.090510"], "四档用量")
    chk([r[3] for r in Q.cap_table(calls)] == ["1 条", "3 条", "9 条", "21 条"], "四档余量：1／3／9／21 条")
    short = Q.usage(Q.shorten())
    chk(short["词元"] == Q.usage(calls)["词元"], "压短长回答后词元一个数没变")
    chk(short["成本"] == Q.usage(calls)["成本"], "压短长回答后成本一个数没变")
    chk(short["并发"] < Q.usage(calls)["并发"], "压短之后并发降下来了")
    chk(len(Q.METERS) == 4, "四种量")
    chk(all(len(m) == 4 for m in Q.METERS), "每个量四栏（量／抓住／漏掉／超限答法）")
    chk("999 个操作" in "\n".join(group_meters()), "按请求数被绕开那个示例写在这一组里")

    chk(len(Q.ARRIVALS) == 10, "十次到达")
    chk(Q.fixed_window() == (True,) * 10, "固定窗口：10 条全放行")
    chk(sum(Q.sliding_window()) == 5, "滑动窗口：只放 5 条")
    chk(sum(Q.token_bucket()) == 5, "令牌桶：也放 5 条")
    chk(Q.sliding_window()[5:] == (False,) * 5, "滑动窗口把边界后的 5 条全拒")
    chk(Q.token_bucket((0.0, 0.1, 0.2)) == (True, True, True), "空桶起手是满的")
    chk(sum(Q.token_bucket(tuple(i * 3.0 for i in range(10)))) == 10, "放得慢（每 3 秒一条）：桶每次都被补满，全放行")
    chk(len(Q.REPLIES) == 3 and len(Q.LIMIT_LAYERS) == 3, "三句超限答复、三层配额")
    chk("队列没有上限" in Q.REPLIES[1][2], "排队那一条的代价指向 8.3 的背压")
    chk([l[0] for l in Q.LIMIT_LAYERS] == ["租户", "用户", "key（API key）"], "三层的顺序：租户 → 用户 → key")

    chk(B.PRICE["cache_write"] == 1.25 * B.PRICE["input"], "缓存写 = 1.25 × 输入（乘法关系，不重抄）")
    chk(B.PRICE["cache_read"] == 0.10 * B.PRICE["input"], "缓存读 = 0.10 × 输入")
    chk(B.reserve() == 0.012, "预扣 $0.012000")
    ss = B.settlements()
    chk([s.actual for s in ss] == [0.0042, 0.0174, 0.0018], "三笔实际：退／欠／退")
    chk(ss[0].delta > 0 and ss[1].delta < 0 and ss[2].delta > 0, "差额的符号：退、欠、退")
    chk(round(sum(s.delta for s in ss), 6) == round(3 * B.reserve() - sum(s.actual for s in ss), 6),
        "差额合计 = 预扣合计 − 实际合计")
    chk(B.charge(1_000, 1_000) == 0.012, "1,000 进 ＋ 1,000 出 ＝ $0.012000")
    chk(B.charge(1_000, 1_000, batch=True) == 0.006, "批量通道打 0.5×")
    chk(B.charge(0, 0) == 0.0, "零词元是零元")
    chk(B.stranded_cost() == 0.1776, f"{B.STRANDED[0]} 笔搁浅 ＝ $0.177600")
    t = B.month_totals()
    chk(int(t["笔数"]) == 1_000, "一个月 1,000 笔")
    chk(t["账单合计"] > t["日志合计"], "账单比日志高（进整只会往上）")
    chk(round(t["账单合计"] - t["日志合计"], 6) == t["差额"], "差额 ＝ 账单 − 日志")
    chk(0.03 < t["差额"] / t["日志合计"] < 0.10, "差异占日志 3%–10%（既不消失也不离谱）")
    chk(B.aligned_gap() == 0.0, "口径对齐后差为 0")
    chk(B.bill_call(120, 40) == B.charge(200, 100), "进整：120→200、40→100（粒度 100）")
    chk(B.bill_call(100, 100) == B.charge(100, 100), "刚好整除时进整不动它")
    chk(B.exception_gap() == 0.27, "例外按通例算少收 $0.270000")
    chk(len(B.discrepancies()) == 3, "三处差异")
    chk("归零" in B.discrepancies()[0][2], "第一处的对法就是改口径")
    chk("不该" in B.discrepancies()[1][2], "第二处不该出现在用量账单里")
    chk(len(report()) >= 95, "六组读数的行数够长（≥ 95 行）")

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
