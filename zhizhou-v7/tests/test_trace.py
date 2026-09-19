# tests/test_trace.py —— 不需要密钥、不联网：span 树、语义约定、采样与分位
"""这一份测的是 7.2 前半段的契约。五组：

1. **树的形状**：一个根、父子时间区间包含关系、自耗时、覆盖并集与缺口；
   子比父长与挂空**都算违规**（前者让自耗时被截到 0，而报表上看不出来）；
2. **结构干净 ≠ 属性齐**：`violations()` 管结构，`missing()` 管语义约定，
   两条断言分开——样本 trace 结构 0 违规而属性缺 3 处；
3. **条件必填**：出错的那一趟必须带 `error.type`（没出错时不要求）；
4. **采样**：头部采样确定性（同一 trace_id 处处一致）、尾部采样留住出错与慢的、
   逐 span 独立抽样会留下挂空（断口与真断链在报表上长得一样）；
5. **分位**：两种算法在小样本上给出两个不同的值——报分位必须连算法一起报。
"""
from app import trace as T


def test_tree_shape_of_the_sample_trace():
    """一个根、5 个直接子、0 条违规——**结构那一侧是干净的**。"""
    trace = T.sample_trace()
    assert trace.violations() == []
    assert len(trace.spans) == 8
    assert trace.root().duration() == 1240
    assert len(trace.children("s-root")) == 5


def test_self_time_is_own_duration_minus_children():
    trace = T.sample_trace()
    # 网关那一根 640ms 里，两次尝试占了 260 + 360，自己只等了 20ms。
    assert trace.self_ms(trace.by_id()["s-gw"]) == 20
    assert trace.self_ms(trace.root()) == 120


def test_gap_is_root_minus_covered_union():
    """缺口 ＝ 根时长 − 子 span 覆盖过的并集；串行时它与自耗时相等。"""
    trace = T.sample_trace()
    assert trace.covered_ms() == 1120
    assert trace.gap_ms() == 120


def test_parallel_makes_gap_and_self_time_two_numbers():
    """两路并发：自耗时 0ms（根自己没花时间）、缺口 300ms（那一段不在任何 span 里）。"""
    fan = T.fanout_trace()
    assert fan.self_ms(fan.root()) == 0
    assert fan.gap_ms() == 300


def test_child_outside_parent_window_is_a_violation():
    bad = T.Trace("t", (T.Span("p", "t", "root", "chain", 0, 100),
                         T.Span("c", "t", "child", "tool", 50, 200, "p",
                                {"gen_ai.tool.name": "x"})))
    assert any("超出了父" in v for v in bad.violations())


def test_child_longer_than_parent_is_a_violation():
    """子比父长会让自耗时被截到 0——**截了要说**，不许安静地变成 0。"""
    bad = T.Trace("t", (T.Span("p", "t", "root", "chain", 0, 100),
                        T.Span("c", "t", "child", "tool", 0, 150, "p",
                               {"gen_ai.tool.name": "x"})))
    assert any("比它的父还长" in v for v in bad.violations())
    assert bad.self_ms(bad.by_id()["p"]) == 0


def test_empty_trace_is_a_failure_not_a_pass():
    """空 trace 与「一切正常」在报表上长得一样——所以它是故障，有夹具守着。"""
    empty = T.Trace("t", ())
    assert empty.violations() == ["一条 span 都没有：空 trace 不是「一切正常」"]
    assert empty.gap_ms() == 0.0


def test_duplicate_span_id_and_two_roots_are_caught():
    dup = T.Trace("t", (T.Span("a", "t", "root", "chain", 0, 100),
                        T.Span("a", "t", "child", "chain", 10, 20, "a")))
    assert any("重复" in v for v in dup.violations())
    two = T.Trace("t", (T.Span("a", "t", "root", "chain", 0, 100),
                        T.Span("b", "t", "另一个根", "chain", 0, 50)))
    assert any("个根" in v for v in two.violations())


def test_semantic_conventions_are_missing_in_three_places():
    """结构干净而属性缺 3 处：两条断言管的是两件事。"""
    trace = T.sample_trace()
    gaps = dict((sid, keys) for sid, _, keys in trace.missing_attrs())
    assert len(gaps) == 3
    assert "gen_ai.usage.output_tokens" in gaps["s-sum"]
    assert "db.collection.name" in gaps["s-retr"]


def test_conditional_attribute_error_type():
    """条件必填：出错时要 `error.type`，没出错时不要。"""
    attrs = {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
             "gen_ai.request.model": "m", "gen_ai.usage.input_tokens": 1,
             "gen_ai.usage.output_tokens": 1}
    assert T.Span("a", "t", "chat", "llm", 0, 1, None, attrs).missing() == []
    assert T.Span("a", "t", "chat", "llm", 0, 1, None,
                  attrs | {"error": True}).missing() == ["error.type"]


def test_span_kind_and_time_validations():
    """类型不在约定里、结束早于开始——两个都当场报错，不留到看板上。"""
    for bad in (lambda: T.Span("x", "t", "n", "sql", 0, 1),
                lambda: T.Span("x", "t", "n", "tool", 5, 1)):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("这一根 span 本该报错")


def test_head_sampling_is_deterministic():
    """同一根 trace_id 掷三次都该是同一个答案：三处服务掷出两个决定＝半条 trace。"""
    assert len({T.head_keep("tr-0001", 0.1) for _ in range(3)}) == 1
    assert T.head_keep("tr-0001", 1.0) and not T.head_keep("tr-0001", 0.0)
    try:
        T.head_keep("tr-0001", 1.5)
    except ValueError:
        pass
    else:
        raise AssertionError("采样率越界本该报错")


def test_tail_sampling_keeps_what_head_sampling_drops():
    """尾部采样把出错与慢的一律留住——代价是先把整条 trace 缓住。"""
    work = T.workload()
    errors = [t for t in work if T.is_error(t)]
    assert errors, "样本里应当有出错的 trace"
    assert all(T.tail_keep(t, rate=0.0, slow_ms=2500.0) for t in errors)
    assert T.tail_keep(work[135], rate=0.0, slow_ms=2500.0)


def test_per_span_sampling_leaves_dangling_children():
    """逐 span 各自掷骰子 → 留下的树里有「父不在」的子 span（断口）。"""
    part = T.sample_spans(T.sample_trace(), 0.5)
    assert any("挂空" in v for v in part.violations())
    assert len(part.spans) < len(T.sample_trace().spans)


def test_percentiles_name_their_algorithm():
    """nearest_rank 报实际存在的值，linear 可能报出一个没人经历过的值。"""
    small = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 1500.0]
    assert T.percentile(small, 0.95, method="nearest_rank") == 1500.0
    assert T.percentile(small, 0.95, method="linear") < 1500.0
    assert T.p95_gap(small) > 0
    assert T.percentile(list(range(10)), 0.95) == 9.0     # 10 条上 p95 就是最大值
    for bad in (lambda: T.percentile([1.0], 0.5, method="猜"), lambda: T.percentile([], 0.5)):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("这一调用本该报错")
