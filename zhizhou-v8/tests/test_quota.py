"""`app/quota.py` 的用例：**同一份余量，四种量给出四个答案**，以及三种算法的分界。"""
from __future__ import annotations

from app import quota as Q


def test_twelve_calls_and_four_meters() -> None:
    assert len(Q.all_calls()) == 12
    assert len(Q.METERS) == 4
    assert [m[0].split("（")[0] for m in Q.METERS] == ["请求数 / 秒", "并发", "词元", "成本"]
    assert set(Q.CAPS) == {"并发", "请求速率", "词元", "成本"}


def test_the_concurrency_peak_is_where_the_long_answer_overlaps() -> None:
    best, at = Q.peak_concurrency(Q.all_calls())
    assert (best, at) == (7, 2.9)


def test_concurrency_counts_overlap_and_rate_counts_arrivals() -> None:
    """两条量数的是两件事：一条 7.5 秒的长回答会横跨七条短调用。"""
    calls = Q.all_calls()
    assert Q.peak_concurrency(calls)[0] == 7
    assert Q.peak_rate(calls)[0] == 4


def test_tokens_are_reported_as_two_numbers() -> None:
    inp, out = Q.tokens(Q.all_calls())
    assert (inp, out) == (3_240, 7_923)
    assert inp != out


def test_four_meters_read_the_same_batch_very_differently() -> None:
    used = Q.usage(Q.all_calls())
    assert used["并发"] == 7 and used["请求速率"] == 4
    assert used["词元"] == 11_163
    assert used["成本"] == 0.09051


def test_the_remaining_room_differs_by_an_order_of_magnitude() -> None:
    """四档说「还能再来几条」：1／3／9／21——**它们说的是同一份余量**。"""
    assert [r[3] for r in Q.cap_table(Q.all_calls())] == ["1 条", "3 条", "9 条", "21 条"]


def test_only_concurrency_moves_when_the_long_answers_get_shorter() -> None:
    """把两条长回答压到 2 秒：**只有并发那一档变**（词元与时长无关）。"""
    before = Q.usage(Q.all_calls())
    after = Q.usage(Q.shorten())
    assert after["并发"] < before["并发"]
    assert (after["请求速率"], after["词元"], after["成本"]) == (
        before["请求速率"], before["词元"], before["成本"])


def test_the_shorten_helper_only_touches_the_named_calls() -> None:
    before = {c.id: c.secs for c in Q.all_calls()}
    after = {c.id: c.secs for c in Q.shorten()}
    changed = {i for i, secs in before.items() if after[i] != secs}
    assert changed == set(Q.LONG_CALLS)


def test_fixed_window_lets_the_boundary_burst_through() -> None:
    """固定窗口：10 条全放行——**每一条都在自己的窗口里合规**。"""
    assert Q.fixed_window() == (True,) * 10
    assert Q.fixed_window()[5:] == (True,) * 5


def test_sliding_window_looks_back_and_blocks_the_same_burst() -> None:
    assert Q.sliding_window()[:5] == (True,) * 5
    assert Q.sliding_window()[5:] == (False,) * 5


def test_token_bucket_matches_sliding_window_on_this_arrival_series() -> None:
    """这串到达上两者答案相同；差异在「攒着用」那一侧（见下一条）。"""
    assert Q.token_bucket() == Q.sliding_window()


def test_a_slow_arrival_series_never_exhausts_the_bucket() -> None:
    """放得慢（每 3 秒一条）：桶每次都被补满——**它允许攒着用**。"""
    assert sum(Q.token_bucket(tuple(i * 3.0 for i in range(10)))) == 10


def test_a_fresh_bucket_starts_full() -> None:
    assert Q.token_bucket((0.0, 0.1, 0.2)) == (True, True, True)


def test_the_three_replies_all_cost_something() -> None:
    assert len(Q.REPLIES) == 3
    for reply, honest, cost in Q.REPLIES:
        assert honest and cost, reply


def test_queuing_is_the_one_that_has_to_borrow_a_ceiling_from_elsewhere() -> None:
    """排队那一条的代价指向 8.3 的背压：**没有上限的队列就是内存事故**。"""
    queue_reply = next(r for r in Q.REPLIES if r[0].startswith("排队"))
    assert "队列没有上限" in queue_reply[2]


def test_limit_layers_go_from_tenant_to_user_to_key() -> None:
    assert [l[0] for l in Q.LIMIT_LAYERS] == ["租户", "用户", "key（API key）"]
    windows = [l[1] for l in Q.LIMIT_LAYERS]
    assert windows[0].startswith("月") and windows[2].startswith("秒")


def test_each_layer_names_what_it_misses() -> None:
    for layer, window, catches, blind in Q.LIMIT_LAYERS:
        assert catches and blind, layer
