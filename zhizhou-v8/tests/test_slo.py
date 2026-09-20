"""`app/slo.py` 的用例：**四个数各自能算，而它们合起来才叫「这个月怎么样」。**

重点是两条容易写成一句口号的等式：
错误预算 ＝ (1 − SLO) × 请求数；四个 9 各自的停机时长 ＝ (1 − SLO) × 一个月。
两处都是算出来的——所以「SLO 定多少」这件事可以直接换算成「每次发布能停多久」。
"""
from __future__ import annotations

from app import slo as S

MONTH_MIN = 30 * 24 * 60


def test_four_nines_and_each_has_a_downtime() -> None:
    assert len(S.NINES) == 4
    assert [n[0] for n in S.NINES] == ["三个 9", "三个半 9", "四个 9", "五个 9"]


def test_the_downtime_is_computed_not_copied() -> None:
    """(1 − SLO) × 一个月 ＝ 那一档买到的时间。**前三个档位都是这么来的。**"""
    for _, val, downtime in S.NINES[:3]:
        shown = float(downtime.split(" ")[0])
        assert abs(shown - (1 - val) * MONTH_MIN) < 0.05, f"{val}：{downtime}"


def test_five_nines_is_twenty_six_seconds() -> None:
    seconds = (1 - S.NINES[3][1]) * MONTH_MIN * 60
    assert abs(seconds - 26) < 1
    assert S.NINES[3][2].startswith("26 秒")


def test_four_nines_to_five_nines_shrinks_the_window_tenfold() -> None:
    """4.32 分钟 → 26 秒：**差的是 10 倍，而它买的是「每次发布能停多久」。**"""
    four = (1 - S.NINES[2][1]) * MONTH_MIN * 60
    five = (1 - S.NINES[3][1]) * MONTH_MIN * 60
    assert abs(four - 259.2) < 0.05 and abs(five - 26) < 0.5
    assert abs(four / five - 10) < 0.05
    assert S.NINES[3][1] == 1 - (1 - S.NINES[2][1]) / 10


def test_four_slis_and_each_one_is_blind_to_something() -> None:
    assert len(S.SLIS) == 4
    assert [s[0] for s in S.SLIS] == ["可用性", "延迟", "正确性", "新鲜度"]
    for name, how, blind, note in S.SLIS:
        assert blind and note, f"{name} 那一行缺了「抓不到什么」或「它的一句话」"


def test_availability_cannot_see_the_timeout() -> None:
    """**超时不是服务端报的错**——所以在只看 5xx 的面板上它是看不见的。"""
    blind = S.SLIS[0][2]
    assert "超时" in blind
    assert "200" in blind


def test_latency_only_reports_the_fast_ninety_five() -> None:
    assert "5%" in S.SLIS[1][2]


def test_correctness_needs_another_data_source_and_gets_skipped() -> None:
    assert "另一套数据源" in S.SLIS[2][2]
    assert "最容易被跳过" in S.SLIS[2][2]


def test_freshness_is_not_on_the_request_path() -> None:
    assert "不在请求链路上" in S.SLIS[3][2]
    assert "答旧文档" in S.SLIS[3][3]


def test_the_error_budget_is_a_count_not_a_percentage() -> None:
    b = S.budget()
    assert b.allowed == 5_000
    assert b.allowed == round((1 - S.SLO) * S.MONTH_REQUESTS)


def test_the_month_used_eighty_six_percent_of_its_budget() -> None:
    b = S.budget()
    assert b.failures == 4_321
    assert b.used == 86.42
    assert b.remaining == 679
    assert b.remaining + b.failures == b.allowed


def test_the_availability_passed_while_the_budget_was_almost_spent() -> None:
    """**「达标」与「还有余量」是两个数**：前者 0.999568 过了，后者只剩 679 条。"""
    b = S.budget()
    assert b.availability >= S.SLO
    assert b.remaining / b.allowed < 0.15


def test_the_four_incidents_split_the_budget() -> None:
    assert [r[2] for r in S.incident_table()] == ["48.0%", "32.0%", "0.0%", "6.4%"]
    assert abs(48.0 + 32.0 + 6.4 - S.budget().used) < 0.05


def test_two_of_the_four_incidents_are_invisible_to_the_panel() -> None:
    rows = S.incident_table()
    assert "看不见" in rows[1][3]
    assert rows[2][1] == "0" and "看不见" in rows[2][3]


def test_the_invisible_ones_are_a_third_of_the_budget() -> None:
    """客户端超时那一次占 32%——**一个只看 5xx 的面板会把这个月报成「零事故」**。"""
    assert abs(float(S.incident_table()[1][2].rstrip("%")) - 32.0) < 1e-9


def test_three_decisions_and_each_pays_something() -> None:
    assert len(S.DECISIONS) == 3
    for name, when, cost in S.DECISIONS:
        assert when and cost
    assert "被写下来" in S.DECISIONS[2][2]


def test_freezing_the_release_costs_a_release_line() -> None:
    assert "发布线" in S.DECISIONS[0][2]


def test_degrading_needs_a_list_that_already_exists() -> None:
    assert "清单" in S.DECISIONS[1][1]
    assert "现场发明" in S.DECISIONS[1][2]


def test_the_same_slo_gives_a_different_budget_at_a_different_traffic() -> None:
    """**错误预算是「流量 × 时间 × (1 − SLO)」**，不是一个百分比：

    2 rps 的一个月允许 2,592 条失败，而 `MONTH_REQUESTS` 那一档允许 5,000 条。
    """
    w = S.month_window()
    assert w.total_requests == 5_184_000
    assert w.allowed == 2_592
    assert w.allowed == round((1 - S.SLO) * w.total_requests)
    assert w.allowed != S.budget().allowed


def test_the_incident_has_four_phases_and_the_requests_are_arithmetic() -> None:
    """每一段的请求数都等于**时长 × 60 × 2 rps**——不受错误率影响。"""
    rows = S.timeline_table()
    assert [r[2] for r in rows] == ["6 分钟", "4 分钟", "9 分钟", "11 分钟"]
    assert [r[4] for r in rows] == ["720", "480", "1,080", "1,320"]
    for row in rows:
        minutes = int(row[2].split(" ")[0])
        assert int(row[4].replace(",", "")) == minutes * 60 * S.INCIDENT_RPS


def test_each_phase_fails_in_proportion_to_its_error_rate() -> None:
    for row in S.timeline_table():
        reqs = int(row[4].replace(",", ""))
        rate = float(row[3].rstrip("%")) / 100
        assert abs(int(row[5].replace(",", "")) - round(reqs * rate)) < 1


def test_the_half_hour_burned_fifty_nine_point_eight_percent() -> None:
    minutes, fails, share, why = S.timeline_totals()
    assert (minutes, fails, share) == (30, 1_550, 59.8)
    assert sum(int(r[5].replace(",", "")) for r in S.timeline_table()) == fails


def test_discovering_and_confirming_cost_more_than_fixing() -> None:
    """**头两段（发现＋确认）占 46.3% 的预算，而它们一条请求都没救回来。**"""
    _, _, _, why = S.timeline_totals()
    assert "46.3%" in why
    assert "一条请求都没救回来" in why


def test_a_slow_burn_at_the_same_traffic_is_comparable() -> None:
    """同一份流量下 0.1% 持续三天是 518 条／20.0%——**与那半小时可比**。"""
    fails, share = S.slow_burn_same_traffic()
    assert (fails, share) == (518, 20.0)
    assert share < S.timeline_totals()[2]
    assert fails < 1_000 < S.timeline_totals()[1]


def test_the_timeline_is_not_the_same_as_the_month_incidents() -> None:
    """两套现场各自量一件事：`INCIDENTS` 量一个月的四次事故，`INCIDENT_TIMELINE` 量一次事故的四个时刻。"""
    assert len(S.INCIDENTS) == 4 and len(S.INCIDENT_TIMELINE) == 4
    assert [r[0][:2] for r in S.INCIDENT_TIMELINE] == ["① ", "② ", "③ ", "④ "]
    assert S.budget().failures != S.timeline_totals()[1]
