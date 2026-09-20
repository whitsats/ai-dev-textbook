"""`app/capacity.py` 的用例：**排队不是线性的——利用率从七成到九成，等待从 3 倍涨到 10 倍。**

这一块量的是两件常被当成直觉的事：
「再加一点流量就崩」其实是「利用率过了一条线」；而「预留」买的不是性能，是时间。
"""
from __future__ import annotations

from app import capacity as C


def test_the_queueing_model_is_one_over_one_minus_rho() -> None:
    assert C.wait_factor(0.5) == 2.0
    assert C.wait_factor(0.7) == 3.3
    assert C.wait_factor(0.8) == 5.0
    assert C.wait_factor(0.9) == 10.0
    assert C.wait_factor(0.95) == 20.0


def test_overload_gets_no_number() -> None:
    assert C.shown_wait(1.0) == "过载（∞）"
    assert C.wait_factor(1.0) == float("inf")
    assert C.shown_wait(0.96) == "25×"


def test_five_percent_of_utilization_doubles_the_wait() -> None:
    """**0.9 → 0.95 只差 5 个百分点，等待从 10× 到 20×**——陡坡就在这里。"""
    assert C.wait_factor(0.95) / C.wait_factor(0.9) == 2.0


def test_the_curve_is_not_linear() -> None:
    deltas = [C.wait_factor(r) - C.wait_factor(r - 0.1) for r in (0.6, 0.7, 0.8, 0.9)]
    assert deltas[0] < deltas[1] < deltas[2]


def test_the_seventy_percent_line_is_where_the_wait_starts_to_outrun_traffic() -> None:
    row = C.utilization_table()[1]
    assert row[0] == "70%"
    assert row[2].startswith("**经验线附近**")


def test_the_table_has_five_rows_and_they_are_in_order() -> None:
    rows = C.utilization_table()
    assert [r[0] for r in rows] == ["50%", "70%", "80%", "90%", "95%"]


def test_the_traffic_shape_is_two_numbers() -> None:
    """**峰值与均值都要报**：只报一个会得出相反的结论。"""
    assert C.MEAN_RPS == 120
    assert C.PEAK_RATIO == 3.2
    assert C.peak_rps() == 384.0
    assert C.MONTHLY_GROWTH == 0.12


def test_ceil_is_used_because_half_a_machine_does_not_exist() -> None:
    assert C.nodes_for(C.MEAN_RPS) == 2
    assert C.nodes_for(10) == 1          # ceil(0.1) ＝ 1
    assert C.nodes_for(101) == 2


def test_headroom_is_multiplied_before_ceil() -> None:
    assert C.nodes_for(C.peak_rps()) == 4
    assert C.nodes_for(C.peak_rps(), 0.50) == 6
    assert C.nodes_for(C.peak_rps(), 0.10) == 5


def test_the_three_buying_plans_land_on_different_places_of_the_curve() -> None:
    rows = C.plan_table()
    assert [r[1] for r in rows] == ["2 台", "4 台", "6 台"]
    assert [r[2] for r in rows] == ["192%", "96%", "64%"]


def test_buying_to_the_mean_overloads_on_the_peak_day() -> None:
    """ρ > 1 时等待是无穷大：**队列无上限地涨**，表现就是「一崩到底、恢复很慢」。"""
    row = C.plan_table()[0]
    assert row[3] == "过载（∞）"
    assert "队列无上限地涨" in row[4]


def test_buying_to_the_peak_leaves_nothing_for_a_lost_machine() -> None:
    row = C.plan_table()[1]
    assert row[3] == "25×"
    assert "挂一台后 128%" in row[4]
    assert "挂掉就过载" in row[4] or "就过载" in row[4]


def test_headroom_buys_time_not_speed() -> None:
    """**预留 50% 的真实含义是「扛得住挂一台」**：峰值 2.8×，挂一台后 77%。"""
    row = C.plan_table()[2]
    assert row[3] == "2.8×"
    assert "77%" in row[4]
    assert abs(C.rho(C.peak_rps(), 6) - 0.64) < 1e-9
    assert abs(C.rho(C.peak_rps(), 5) - 0.768) < 1e-9


def test_the_load_test_has_four_steps_and_crosses_the_knee() -> None:
    rows = C.load_test_table()
    assert len(rows) == 4
    assert rows[2][3].startswith("**拐点")
    assert rows[3][3].startswith("过载段")


def test_past_the_knee_more_concurrency_makes_it_worse() -> None:
    """**过载段：并发翻倍而延迟涨了 4 倍多、错误率 14%**——加并发不再加吞吐。"""
    assert C.LOAD_TEST[3][0] > C.LOAD_TEST[2][0]
    assert C.LOAD_TEST[3][1] > 4 * C.LOAD_TEST[2][1]
    assert C.LOAD_TEST[3][2] > C.LOAD_TEST[2][2]


def test_the_linear_section_is_actually_linear() -> None:
    assert C.LOAD_TEST[0][2] == 0.0
    assert C.LOAD_TEST[1][2] < 1.0
    assert C.LOAD_TEST[1][1] / C.LOAD_TEST[0][1] < 2


def test_doubling_comes_in_quarters_not_years() -> None:
    """按 12% 月增，**3 个季度后翻倍**——这就是「下一次评估容量」的时间点。"""
    assert C.quarters_to_grow() == 3
    assert (1 + C.MONTHLY_GROWTH) ** 9 >= 2 > (1 + C.MONTHLY_GROWTH) ** 6
