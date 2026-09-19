# tests/test_board.py —— 不需要密钥、不联网：四栏账、覆盖率、两层记账与告警
"""这一份测的是 7.2 后半段的契约。四组：

1. **四栏账**：`uncached / write / read / out` 之和就是这一格的账，
   而「未命中输入」是**算出来的差**（输入 − 缓存读 − 缓存写）；
   缓存两栏自相矛盾、或者缺 usage 两项 → **算不出来（`None`），不是 0**；
2. **两层记账**：`attempts`（每一次物理尝试）与 `logical`（一次逻辑调用）
   是同一笔钱的两种记法——所以两层的和相等，而**两层都加**会翻倍；
   失败的那一次照样有账（6.4 那条「失败不会从账单上消失」在 trace 上的形态）；
3. **覆盖率**：看板必须同时报「多少格的账算得出来」，否则
   「这一行 0.0000 元」会与「这一行没被调用」长得一样；
4. **告警**：`window` 是那个 `for`——连续越线算**一次**事件（状态不清空就不重复报），
   而窗口变大买到的是「假报变少」、付出去的是「真报变晚」。
"""
from app import board as B
from app import trace as T


def test_price_table_is_self_consistent():
    """价表自身的断言：写价 ＝ 输入 × 1.25、读价 ＝ 输入 × 0.10。"""
    assert B.violations() == []
    assert B.violations((B.Model("坏的", 2.0, 1.0, 0.2, 9.9),)) != []
    assert B.BY_NAME["gpt-5.6-terra"].cache_write == 2.5


def test_four_columns_sum_to_the_grid_charge():
    """四栏各自是钱，合起来是这一格的账。"""
    span = T.Span("x", "t", "chat", "llm", 0, 1, None,
                  {"gen_ai.request.model": "gpt-5.6-luna",
                   "gen_ai.usage.input_tokens": 5200, "gen_ai.usage.output_tokens": 900,
                   "gen_ai.usage.cache_read.input_tokens": 1000,
                   "gen_ai.usage.cache_write.input_tokens": 200})
    usage = B.usage_of(span)
    assert usage == {"uncached": 4000, "write": 200, "read": 1000, "out": 900}
    cols = B.BY_NAME["gpt-5.6-luna"].columns(usage)
    assert abs(sum(cols.values()) - B.span_cost(span)) < 1e-12


def test_missing_usage_is_not_zero():
    """缺 output_tokens 的 span 读不出四栏——**`None` 与「花了 0 元」是两件事**。"""
    trace = T.sample_trace()
    assert B.usage_of(trace.by_id()["s-sum"]) is None
    assert B.span_cost(trace.by_id()["s-sum"]) is None
    assert any("缺项" in n for n in B.usage_notes(trace.by_id()["s-sum"]))


def test_contradictory_cache_columns_are_refused():
    """缓存读+写 > 输入：不静默取绝对值，直接算不出来。"""
    bad = T.Span("x", "t", "chat", "llm", 0, 1, None,
                 {"gen_ai.usage.input_tokens": 100, "gen_ai.usage.output_tokens": 10,
                  "gen_ai.usage.cache_read.input_tokens": 90,
                  "gen_ai.usage.cache_write.input_tokens": 90})
    assert B.usage_of(bad) is None
    assert any("自相矛盾" in n or "口径" in n for n in B.usage_notes(bad))


def test_cache_columns_absent_is_recorded_not_assumed():
    """官方把缓存两栏写成「适用时才有」：没报不等于报了 0，所以要标出来。"""
    span = T.Span("x", "t", "chat", "llm", 0, 1, None,
                  {"gen_ai.usage.input_tokens": 1000, "gen_ai.usage.output_tokens": 200})
    assert B.usage_of(span)["write"] == 0
    assert any("缓存两栏都没报" in n for n in B.usage_notes(span))


def test_the_two_layers_are_the_same_money():
    """`attempts` 与 `logical` 是同一笔钱的两种记法：两层的和必须相等。"""
    trace = T.sample_trace()
    a = B.trace_cost(trace, layers=("attempts",))
    l = B.trace_cost(trace, layers=("logical",))
    assert a[0] == l[0] == 0.0275
    assert a[1] == 2 and a[2] == 1        # attempts 层：2 格算得出、1 格算不出
    assert l[1] == 1 and l[2] == 0


def test_counting_both_layers_doubles_the_bill():
    """两层都加（也就是任何一张「把所有 span 加起来」的看板）会把重试算两遍。"""
    trace = T.sample_trace()
    assert B.trace_cost(trace, layers=B.LAYERS)[0] \
        == 2 * B.trace_cost(trace, layers=("logical",))[0]
    try:
        B.trace_cost(trace, layers=("physical",))
    except ValueError:
        pass
    else:
        raise AssertionError("未知的层本该报错")


def test_failed_attempt_still_costs_money():
    """失败的那一次不产出任何东西，但账单上有它（6.4 那条纪律的现场）。"""
    trace = T.sample_trace()
    fail = B.span_cost(trace.by_id()["s-att1"])
    assert fail == 0.008
    assert fail / B.trace_cost(trace, layers=("logical",))[0] > 0.25


def test_unknown_model_is_unpriced_not_free():
    span = T.Span("x", "t", "chat", "llm", 0, 1, None,
                  {"gen_ai.request.model": "别的模型",
                   "gen_ai.usage.input_tokens": 1, "gen_ai.usage.output_tokens": 1})
    assert B.span_cost(span) is None


def test_board_reports_coverage_alongside_money():
    """看板必须两个数一起报：钱，以及多少格的账算得出来。"""
    one = B.board([T.sample_trace()], layers=("attempts",))
    assert one["unpriced"] == 1
    assert abs(one["coverage"] - 2 / 3) < 1e-12
    assert one["rows"]["gpt-5.6-luna"]["total"] == 0.0
    assert one["rows"]["gpt-5.6-luna"]["unknown"] == 1
    assert B.board([T.sample_trace()], layers=("logical",))["coverage"] == 1.0


def test_board_counts_traces_per_group():
    """按路由分组时那一列「几条 trace」也在：没有条数的看板看不出「数据少了」。"""
    full = B.board(T.workload(), layers=("attempts",), key_of=B.BY_ROUTE)
    rows = full["rows"]
    assert rows["/ask"]["traces"] == 190 and rows["/export"]["traces"] == 10
    assert full["coverage"] == 1.0
    assert B.usage_of(T.workload()[0].by_id()["t0-retr"]) is None   # 检索不带账


def test_alert_window_trades_noise_for_delay():
    series = [1.0, 1.0, 3.0, 3.0, 3.0, 1.0]
    assert B.alert_events(series, 2.0, window=1) == [(3, 5)]
    assert B.alert_events(series, 2.0, window=3) == [(5, 5)]
    # 不连着的两次单点越线是两次事件：状态清空之后才允许再报。
    assert B.alert_events([3.0, 1.0, 3.0], 2.0) == [(1, 1), (3, 3)]


def test_alert_lower_direction_and_bad_arguments():
    """方向也要能反过来（成功率是 `lower` 才该报的那种指标也一样）。"""
    assert B.alert_events([5.0, 1.0], 2.0, direction="lower") == [(2, 2)]
    for bad in (lambda: B.alert_events([1.0], 2.0, window=0),
                lambda: B.alert_events([1.0], 2.0, direction="up")):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("这一调用本该报错")
