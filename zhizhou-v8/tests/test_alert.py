"""`app/alert.py` 的用例：**「响了没有」不是判据，「该不该响」才是。**

三组断言对应这一块的三件事：阈值告警在慢烧上完全失明、三种烧法对应三种打扰方式、
以及每一条告警都在花一个班的注意力（噪声是可算的）。
最后四组是 5.7 记下、8.3 改指到这一章的旧账：状态页的广播。
"""
from __future__ import annotations

from app import alert as A


def test_the_budget_rate_is_one_minus_slo() -> None:
    assert A.BUDGET_RATE == 0.05 / 100


def test_burn_rate_divides_by_the_budget_rate() -> None:
    assert A.burn_rate(0.10) == 200.0
    assert A.burn_rate(0.001) == 2.0
    assert A.burn_rate(A.BUDGET_RATE) == 1.0


def test_a_single_failure_is_noise_not_a_rate() -> None:
    assert A.burn_rate(0.00002) < 0.1
    assert A.shown_burn(0.00002) == "< 0.1×（噪声）"


def test_three_scenarios_and_only_the_slow_burn_separates_them() -> None:
    rows = A.burn_table()
    assert len(rows) == 3
    assert rows[0][5] == "都对"
    assert rows[1][5] == "**只有燃尽率对**"
    assert rows[2][5].startswith("都对")


def test_the_threshold_alert_never_fires_on_a_slow_burn() -> None:
    """**0.1% 一直在 1% 那条线下面**：按阈值的告警一次都不响，而三天烧掉 20% 预算。"""
    row = A.burn_table()[1]
    assert "一次都不响" in row[3]
    assert "20% 预算" in row[4]


def test_the_three_windows_are_built_from_the_official_rates() -> None:
    assert [w[2] for w in A.BURN_WINDOWS] == [14.4, 6.0, 1.0]


def test_each_window_percentage_is_rate_times_hours_over_a_month() -> None:
    """**2%／5%／10% 不是抄的**：燃尽率 × 时长 ÷ 一个月 ＝ 那一档烧掉多少。"""
    hours = {"1 小时": 1, "6 小时": 6, "3 天": 72}
    for long_w, _, rate, budget, _ in A.BURN_WINDOWS:
        expect = rate * hours[long_w] / (30 * 24) * 100
        assert abs(expect - float(budget.split("%")[0])) < 0.05


def test_the_three_windows_wake_people_up_differently() -> None:
    assert "叫醒" in A.BURN_WINDOWS[0][4]
    assert "工单" in A.BURN_WINDOWS[1][4]
    assert "排期" in A.BURN_WINDOWS[2][4]


def test_the_noise_ratio_is_computable() -> None:
    n = A.noise()
    assert (n.sent, n.no_action, n.shifts) == (340, 211, 180)
    assert n.noise_ratio == 62.1
    assert n.sent - n.no_action == 129


def test_each_shift_has_two_alerts_and_point_seven_worth_acting_on() -> None:
    n = A.noise()
    assert n.per_shift == 1.89
    assert n.actionable_per_shift == 0.72


def test_connection_scales_and_the_broadcast_payload() -> None:
    rows = A.broadcast_table()
    assert len(rows) == 4
    assert rows[0][2] == "1.2 KB" and rows[1][2] == "120 KB"
    assert rows[2][2] == "1.2 MB"


def test_the_uncleared_set_keeps_growing() -> None:
    """1,000 条连接重连 6 次而集合只增不减——**内存事故与广播风暴是同一件事**。"""
    last = A.broadcast_table()[3]
    assert last[1] == 6_000
    assert "只增不减" in last[4]
    assert "内存事故" in last[4]


def test_a_round_is_paced_by_the_slowest_connections() -> None:
    """**997 条正常连接 0.02 ms、3 条慢连接 200 ms，慢的占了一轮 96.8% 的时间。**"""
    slow, kept, share, why = A.cleanup()
    assert (slow, kept) == (3, 997)
    assert share == 96.8
    assert "最慢的那几条决定" in why


def test_the_share_is_computed_from_the_two_speeds() -> None:
    expect = 3 * 200.0 / (3 * 200.0 + 997 * A.BROADCAST_PER_CONN_MS) * 100
    assert abs(expect - A.cleanup()[2]) < 0.1


def test_the_cleanup_criterion_is_the_write_timeout() -> None:
    assert A.WRITE_TIMEOUT_MS == 50.0
    assert all(ms > A.WRITE_TIMEOUT_MS for ms, _ in A.CONN_SPEEDS if ms != A.BROADCAST_PER_CONN_MS)
