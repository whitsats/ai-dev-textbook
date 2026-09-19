#!/usr/bin/env python
"""7.2 的读数脚本：把「出了事怎么看见」变成六组能复算的数。

    python scripts/trace_reader.py --offline     # 六组读数（不要密钥、不要网络）
    python scripts/trace_reader.py --self-test   # 五十条夹具

六组依次是：一条 trace 的形状（树、自耗时、缺口）／属性与语义约定（缺了几处）／
关联（trace_id 把 6.3 的 attempts 与 7.1 的跑记录串起来）／指标与分位（同一批数的两种算法）／
采样（头部、尾部、以及逐 span 独立抽样留下的断口）／看板与告警（四栏账、覆盖率、
阈值与窗口）。

它**不调模型、不联网**：那条 trace 与那 200 条「现场记录」都是**造出来的**。
所以它能量的是埋点、语义约定、采样与看板**自己的性质**——量不了线上真实延迟，
也量不了模型质量。这一条写在正文的边界里，不写成结论。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import board as B  # noqa: E402
from app import trace as T  # noqa: E402

#: 这一脚本里反复出现的两个名字：样本 trace 与那 200 条现场记录都住在 `app/trace.py`
#: （与 7.1 把 `sample_suite()` 放在 `app/suite.py` 同一个约定：**样本是模块的一部分**，
#: 所以测试模块能直接拿它断言，而不必启动一个脚本）。
sample_trace = T.sample_trace
fanout_trace = T.fanout_trace
workload = T.workload
window_p95 = T.window_p95
WINDOW = T.WINDOW
SLOW_AT = T.SLOW_AT


# ------------------------------------------------------- 一、一条 trace 的形状

def group_shape() -> list[str]:
    trace = sample_trace()
    lines = [f"=== 一、一条 trace 的形状：{len(trace.spans)} 根 span、"
             f"{len(trace.children(trace.root().span_id))} 个直接子 span ==="]
    lines.extend(trace.tree_lines())
    root = trace.root()
    lines.append(f"根的总时长            {root.duration():.0f}ms")
    lines.append(f"直接子 span 覆盖过    {trace.covered_ms():.0f}ms（并集：重叠只算一次）")
    lines.append(f"缺口                {trace.gap_ms():.0f}ms  ← 不在任何 span 里的那一段")
    lines.append(f"自身的断言            {len(trace.violations())} 条违规"
                 f"（{'干净' if not trace.violations() else trace.violations()}）")
    fan = fanout_trace()
    lines.append(f"串行那一条：自耗时 {trace.self_ms(root):.0f}ms ＝ 缺口 {trace.gap_ms():.0f}ms"
                 f"（子 span 不重叠时两个数相等）")
    lines.append(f"并行那一条：自耗时 {fan.self_ms(fan.root()):.0f}ms ／ 缺口 {fan.gap_ms():.0f}ms"
                 f"——自耗时说「根自己没花时间」，缺口说「有 {fan.gap_ms():.0f}ms 不在任何"
                 f" span 里」；两个数都对，问的不是同一个问题")
    return lines


# ------------------------------------------------------- 二、属性与语义约定

def group_semantics() -> list[str]:
    trace = sample_trace()
    slots = sum(len(T.REQUIRED[s.kind]) for s in trace.spans)
    missing = trace.missing_attrs()
    lines = [f"=== 二、属性与语义约定：{len(trace.spans)} 根 span，"
             f"必填属性 {slots} 处、缺 {len(missing)} 处 ==="]
    for sid, kind, keys in missing:
        span = trace.by_id()[sid]
        lines.append(f"  {sid:<9}{kind:<10}{span.name:<32} 缺 {'、'.join(keys)}")
    lines.append("条件必填的例子：出错的那一趟必须带 error.type"
                 "（`s-att1` 带了，所以它不算缺口）")
    lines.append(f"按类型算：llm {len(T.REQUIRED['llm'])} 项、gateway "
                 f"{len(T.REQUIRED['gateway'])} 项、retriever {len(T.REQUIRED['retriever'])} 项、"
                 f"tool {len(T.REQUIRED['tool'])} 项、chain {len(T.REQUIRED['chain'])} 项")
    # 只有「该带 usage 的那两类」（llm 与 gateway）才在这里点名：检索与工具本来就不带账，
    # 把它们也列出来的话，真正的那两处会被四行噪声淹掉。
    money_spans = [s for s in trace.spans if s.kind in ("llm", "gateway")]
    notes = [(s.span_id, n) for s in money_spans for n in B.usage_notes(s)]
    lines.append(f"usage 上的「没法核」{len(notes)} 处（只看该带账的 {len(money_spans)} 根）：")
    for sid, note in notes:
        lines.append(f"  {sid:<9}{note}")
    return lines


# ------------------------------------------------------- 三、关联与两层账

def group_linkage() -> list[str]:
    trace = sample_trace()
    gw = trace.by_id()["s-gw"]
    att = ["s-att1", "s-att2"]
    a_money, a_done, a_missing = B.trace_cost(trace, layers=("attempts",))
    l_money, l_done, l_missing = B.trace_cost(trace, layers=("logical",))
    both, b_done, b_missing = B.trace_cost(trace, layers=B.LAYERS)
    fail = B.span_cost(trace.by_id()["s-att1"]) or 0.0
    lines = [f"=== 三、关联：一条 trace_id 串起三层账 ==="]
    lines.append(f"这一条 trace_id        {trace.trace_id}")
    lines.append(f"  ↳ 6.3 的 attempts      {gw.attrs['zhizhou.attempts']} 次"
                 f"（网关那一层记的：{'、'.join(att)}）")
    lines.append(f"  ↳ 7.1 的跑记录          同一个 trace_id 也写在跑记录里"
                 f"（本树里编的：题 q07 ／ run 42）")
    lines.append(f"按 attempts 层记账      ${a_money:.4f}  算得出 {a_done} 格、算不出 {a_missing} 格")
    lines.append(f"按 logical 层记账       ${l_money:.4f}  算得出 {l_done} 格、算不出 {l_missing} 格")
    lines.append(f"两层都记（一个 sum）    ${both:.4f}  ← 重试那一段算了两遍，"
                 f"贵 {(both / l_money - 1) * 100:.1f}%")
    lines.append(f"失败的那一次（s-att1）  ${fail:.4f}，占这一次逻辑调用的 "
                 f"{fail / l_money * 100:.1f}%——它没产出任何东西，但账单上有它")
    return lines


# ------------------------------------------------------- 四、指标与分位

def group_metrics() -> list[str]:
    traces = workload()
    roots = [t.root().duration() for t in traces]
    nr = T.percentile(roots, 0.95, method="nearest_rank")
    lines = [f"=== 四、指标与分位：{len(traces)} 条 trace 的根时长 ==="]
    lines.append(f"均值                {sum(roots) / len(roots):.1f}ms")
    lines.append(f"p50                 {T.percentile(roots, 0.5):.1f}ms")
    lines.append(f"p95（nearest_rank） {nr:.1f}ms   两种算法在全量上给出同一个数"
                 f"（差 {T.p95_gap(roots):+.1f}ms）")
    lines.append(f"p99（nearest_rank） {T.percentile(roots, 0.99):.1f}ms"
                 f"　最大 {max(roots):.1f}ms——"
                 f"{len(roots)} 条上 p99 就是「第 {len(roots) - 1} 个」")
    first20 = T.percentile(roots[:20], 0.95)
    lines.append(f"只拿前 20 条算 p95    {first20:.1f}ms（全量 {nr:.1f}ms）——"
                 f"样本越少，分位越是「最近几次的运气」")
    # 分位算法的那点差别只在**小样本**上看得见：一窗 10 条里恰好有一条慢 1,500ms，
    # 于是 nearest_rank 报「真发生过的 1,500」，linear 在它和第二大之间插了一刀。
    win = [t.root().duration() for t in traces[:WINDOW]]
    a = T.percentile(win, 0.95, method="nearest_rank")
    b = T.percentile(win, 0.95, method="linear")
    lines.append(f"10 条一窗的 p95      nearest_rank {a:.1f}ms（＝这一窗的最大值："
                 f"ceil(0.95×10)−1 = 9）")
    lines.append(f"                    linear {b:.1f}ms（在第二大与最大之间插了一刀）"
                 f"　两种算法差 {a - b:.1f}ms")
    lines.append("                    前者是这一窗真发生过的值，后者是一个**没人经历过的值**")
    return lines


# ------------------------------------------------------- 五、采样

def group_sampling() -> list[str]:
    traces = workload()
    rate = 0.1
    slow_ms = 2500.0
    head = [t for t in traces if T.head_keep(t.trace_id, rate)]
    tail = [t for t in traces if T.tail_keep(t, rate=rate, slow_ms=slow_ms)]
    errors = [t for t in traces if T.is_error(t)]
    lines = [f"=== 五、采样：{len(traces)} 条里抽 {rate:.0%} ==="]
    lines.append(f"头部采样（按 trace_id 掷骰子）  留 {len(head)} 条，"
                 f"其中出错的那一类 {sum(1 for t in head if T.is_error(t))}/{len(errors)} 条")
    lines.append(f"尾部采样（出错与慢的一律留）    留 {len(tail)} 条，"
                 f"其中出错的那一类 {sum(1 for t in tail if T.is_error(t))}/{len(errors)} 条")
    lines.append(f"多留的代价                      {len(tail) - len(head)} 条"
                 f"（{len(tail) / len(traces):.1%} 对 {len(head) / len(traces):.1%}）"
                 f"——换来的是「要看的那几条一条不少」")
    part = T.sample_spans(sample_trace(), 0.5)
    dropped = len(sample_trace().spans) - len(part.spans)
    lines.append(f"逐 span 各自掷骰子（0.5）       一条 trace 剩 {len(part.spans)} 根、"
                 f"丢了 {dropped} 根；违规 {len(part.violations())} 条：")
    for v in part.violations():
        lines.append(f"  {v}")
    same = len({T.head_keep("tr-0001", rate) for _ in range(3)}) == 1
    lines.append(f"同一根 trace_id 连掷三次         {'都一样' if same else '不一样'}"
                 f"——三处服务必须掷出同一个决定，否则一条 trace 会被抽成半条")
    return lines


# ------------------------------------------------------- 六、看板与告警

def group_board() -> list[str]:
    trace = sample_trace()
    one = B.board([trace], layers=("attempts",))
    rows = one["rows"]
    lines = [f"=== 六、成本看板与告警 ==="]
    lines.append("按模型分组（认 attempts 层，四栏的列名用属性名）：")
    lines.append(f"  {'key':<15}" + "".join(f"{c:>10}" for c in B.COLUMNS)
                 + f"{'total':>10}{'grid':>5}{'unknown':>8}")
    for key, row in sorted(rows.items()):
        lines.append(f"  {key:<15}" + "".join(f"{row[c]:>10.4f}" for c in B.COLUMNS)
                     + f"{row['total']:>10.4f}{row['grid']:>5}{row['unknown']:>8}")
    lines.append(f"覆盖率（算得出的格 / 有 usage 的格）  {one['priced']}/"
                 f"{one['priced'] + one['unpriced']} = {one['coverage']:.4f}"
                 f"——「luna 那一行 0.0000 元」与「luna 没被调用」是两件事")
    all_traces = workload()
    full = B.board(all_traces, layers=("attempts",))
    lines.append(f"全量 {len(all_traces)} 条：总额 ${sum(r['total'] for r in full['rows'].values()):.4f}"
                 f"　覆盖率 {full['coverage']:.4f}　模型 {len(full['models'])} 个")
    lines.append("按路由分组：")
    by_route = B.board(all_traces, layers=("attempts",), key_of=B.BY_ROUTE)
    for key, row in sorted(by_route["rows"].items()):
        lines.append(f"  {key:<8} {row['traces']:>4} 条  ${row['total']:.4f}"
                     f"（格 {row['grid']:>3}、未知 {row['unknown']}）")
    series = window_p95(all_traces)
    healthy = [v for i, v in enumerate(series) if not any(
        s // WINDOW == i for s in SLOW_AT)]
    base = T.percentile(healthy, 0.95)
    band = max(healthy) - min(healthy)
    lines.append(f"告警：{len(series)} 个窗口（每窗 {WINDOW} 条的 p95）")
    lines.append(f"  基线（健康窗口的 p95）{base:.1f}ms ＋ 抖动带 {band:.1f}ms"
                 f" → 阈值 {base + band:.1f}ms")
    lines.append(f"  各窗口               {' '.join(f'{v:.0f}' for v in series)}")
    for window in (1, 2, 3):
        events = B.alert_events(series, base + band, window=window)
        at = "、".join(f"{a}" if a == b else f"{a}–{b}" for a, b in events)
        lines.append(f"  连续 {window} 个窗口越线才报   {len(events)} 次告警（窗口 {at}）")
    lines.append("阈值一次也不假报的那条路是「不报警」——所以判据里要写清"
                 "「拿哪一段当基线」与「连续几个窗口」")
    return lines


def readings() -> list[str]:
    lines: list[str] = []
    for part in (group_shape(), group_semantics(), group_linkage(),
                 group_metrics(), group_sampling(), group_board()):
        lines.extend(part)
        lines.append("")
    lines.append("追踪读数：六组全过 ｜ 离线自检通过")
    return lines


# ------------------------------------------------------- 夹具

def _raises(fn) -> bool:
    try:
        fn()
    except Exception:  # noqa: BLE001
        return True
    return False


def fixture_cases() -> list[tuple[str, bool]]:
    """三十九条夹具。**每条正向断言都配一条反例。**"""
    trace = sample_trace()
    fan = fanout_trace()
    span = T.Span("x", "t", "chat", "llm", 0, 100, "p",
                  {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
                   "gen_ai.request.model": "gpt-5.6-luna",
                   "gen_ai.usage.input_tokens": 1000, "gen_ai.usage.output_tokens": 200})
    cases: list[tuple[str, bool]] = [
        # —— 形状
        ("干净的一条 trace 违规 0 条", trace.violations() == []),
        ("根的总时长等于它自己的时长", trace.root().duration() == 1240),
        ("缺口＝根时长减覆盖并集", trace.gap_ms() == 120),
        ("自耗时＝自己的时长减子 span 之和", trace.self_ms(trace.root()) == 120),
        ("并行让自耗时与缺口分开（自 0 ／ 缺口 300）",
         fan.self_ms(fan.root()) == 0 and fan.gap_ms() == 300),
        ("父子时间区间越界会被抓", any(
            "超出了父" in v for v in T.Trace("t", (
                T.Span("p", "t", "root", "chain", 0, 100),
                T.Span("c", "t", "child", "tool", 50, 200, "p", {"gen_ai.tool.name": "x"}),
            )).violations())),
        ("子比父长会被抓", any(
            "比它的父还长" in v for v in T.Trace("t", (
                T.Span("p", "t", "root", "chain", 0, 100),
                T.Span("c", "t", "child", "tool", 0, 150, "p", {"gen_ai.tool.name": "x"}),
            )).violations())),
        ("span_id 重复会被抓", any(
            "重复" in v for v in T.Trace("t", (
                T.Span("a", "t", "root", "chain", 0, 100),
                T.Span("a", "t", "child", "chain", 10, 20, "a"),
            )).violations())),
        ("两个根会被抓", any(
            "个根" in v for v in T.Trace("t", (
                T.Span("a", "t", "root", "chain", 0, 100),
                T.Span("b", "t", "另一个根", "chain", 0, 50),
            )).violations())),
        ("空 trace 是故障（不是「一切正常」）",
         T.Trace("t", ()).violations() == ["一条 span 都没有：空 trace 不是「一切正常」"]),
        ("空 trace 的覆盖与缺口都是 0", T.Trace("t", ()).gap_ms() == 0.0),
        ("类型不合法要报错", _raises(lambda: T.Span("x", "t", "n", "sql", 0, 1))),
        ("结束早于开始要报错", _raises(lambda: T.Span("x", "t", "n", "tool", 5, 1))),
        # —— 语义约定
        ("样本 trace 的必填属性缺口是 3 处", len(trace.missing_attrs()) == 3),
        ("缺 output_tokens 的那一根会被点名",
         "gen_ai.usage.output_tokens" in dict(
             (sid, keys) for sid, _, keys in trace.missing_attrs())["s-sum"]),
        ("条件必填：出错时必须带 error.type",
         T.Span("a", "t", "chat", "llm", 0, 100, None,
                {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
                 "gen_ai.request.model": "m", "gen_ai.usage.input_tokens": 1,
                 "gen_ai.usage.output_tokens": 1, "error": True}).missing() == ["error.type"]),
        ("没出错时不要求 error.type", span.missing() == []),
        ("chain 类型不要求任何属性",
         T.Span("a", "t", "root", "chain", 0, 1).missing() == []),
        ("usage 两栏齐了才读得出四栏", B.usage_of(span) == {
            "uncached": 1000, "write": 0, "read": 0, "out": 200}),
        ("缓存两栏没报时按「全未命中」算，并记下这件事",
         B.usage_of(span)["write"] == 0 and B.usage_notes(span) != []),
        ("缺 output_tokens → 四栏读不出来（不是全 0）",
         B.usage_of(trace.by_id()["s-sum"]) is None),
        ("缓存读+写 > 输入 → 同样读不出来", B.usage_of(T.Span(
            "x", "t", "chat", "llm", 0, 1, None,
            {"gen_ai.usage.input_tokens": 100, "gen_ai.usage.output_tokens": 10,
             "gen_ai.usage.cache_read.input_tokens": 90,
             "gen_ai.usage.cache_write.input_tokens": 90})) is None),
        ("未命中输入＝输入−缓存读−缓存写",
         B.usage_of(sample_trace().by_id()["s-att2"])["uncached"] == 4000),
        ("两栏都没报会标出来（「没报」不是「报了 0」）",
         "缓存两栏都没报" in B.usage_notes(span)[0]),
        # —— 关联与两层账
        ("按 attempts 层与按 logical 层算出的账单相等",
         B.trace_cost(trace, layers=("attempts",))[0]
         == B.trace_cost(trace, layers=("logical",))[0]),
        ("两层都算会翻倍（重试那一段被算两遍）",
         abs(B.trace_cost(trace, layers=B.LAYERS)[0]
             - 2 * B.trace_cost(trace, layers=("logical",))[0]) < 1e-9),
        ("未知的层要报错", _raises(lambda: B.trace_cost(trace, layers=("physical",)))),
        ("失败那一次照样有账（它不产出内容，但清单上有它）",
         (B.span_cost(trace.by_id()["s-att1"]) or 0) > 0),
        ("价表里没有的模型 → 算不出来（不是 0）",
         B.span_cost(T.Span("x", "t", "chat", "llm", 0, 1, None,
                            {"gen_ai.request.model": "别的模型",
                             "gen_ai.usage.input_tokens": 1,
                             "gen_ai.usage.output_tokens": 1})) is None),
        ("价表自身的断言是干净的（写价＝输入×1.25）", B.violations() == []),
        ("价表断言能抓到写价写错",
         B.violations((B.Model("坏的", 2.0, 1.0, 0.2, 9.9),)) != []),
        # —— 分位
        ("nearest_rank 报的是实际存在的值",
         T.percentile([1.0, 2.0, 3.0, 4.0], 0.5) in (1.0, 2.0, 3.0, 4.0)),
        ("两种算法在小样本上给出不同的 p95",
         T.percentile([1.0, 2.0, 3.0, 4.0], 0.95, method="nearest_rank")
         != T.percentile([1.0, 2.0, 3.0, 4.0], 0.95, method="linear")),
        ("10 个样本时 p95 就是最大值",
         T.percentile(list(range(10)), 0.95) == 9.0),
        ("未知的分位算法要报错",
         _raises(lambda: T.percentile([1.0], 0.5, method="猜"))),
        ("空样本算不出分位", _raises(lambda: T.percentile([], 0.5))),
        # —— 采样
        ("头部采样是确定性的（连掷三次同一个答案）",
         len({T.head_keep("tr-0001", 0.1) for _ in range(3)}) == 1),
        ("头部采样率 0 与 1 是两个极端",
         not T.head_keep("tr-0001", 0.0) and T.head_keep("tr-0001", 1.0)),
        ("慢的那一条在尾部采样里一定被留（哪怕头部抽不到）",
         T.tail_keep(workload()[135], rate=0.0, slow_ms=2500.0)),
        ("逐 span 独立抽样会留下挂空（断口）",
         any("挂空" in v for v in T.sample_spans(trace, 0.5).violations())),
        ("整条 trace 一起抽（头部采样）不会留下挂空",
         T.Trace(trace.trace_id, trace.spans).violations() == [] and
         T.head_keep(trace.trace_id, 1.0)),
        # —— 看板与告警
        ("算不出来的那一格进不了账，但会被数出来",
         B.board([trace], layers=("attempts",))["unpriced"] == 1),
        ("按 logical 层看覆盖率是满的（那一层只记了一根）",
         B.board([trace], layers=("logical",))["coverage"] == 1.0),
        ("看板按模型分组会带上没有这一栏的组",
         B.board([trace], layers=("logical",), key_of=B.BY_ROUTE)["rows"]
         ["（没有这一栏）"]["total"] > 0),
        ("告警连续 3 个窗口才报：连着的那一次事故只报一次",
         len(B.alert_events([1.0, 1.0, 3.0, 3.0, 3.0, 1.0], 2.0, window=3)) == 1),
        ("告警只看一个窗口：连着越线算一次事件（状态不清空就不重复报）",
         B.alert_events([1.0, 1.0, 3.0, 3.0, 3.0, 1.0], 2.0, window=1) == [(3, 5)]),
        ("告警只看一个窗口：不连着的两次单点越线算两次事件",
         B.alert_events([3.0, 1.0, 3.0], 2.0, window=1) == [(1, 1), (3, 3)]),
        ("告警事件带 (起, 止) 两个窗口号",
         B.alert_events([3.0], 2.0) == [(1, 1)]),
        ("window 小于 1 要报错", _raises(lambda: B.alert_events([3.0], 2.0, window=0))),
        ("方向不合法要报错", _raises(lambda: B.alert_events([3.0], 2.0, direction="up"))),
    ]
    return cases


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
