"""`app/release.py` 的用例：钉法、审批，以及两门判据下金丝雀的差额。"""
from __future__ import annotations

from app import release as R


def test_only_a_digest_answers_the_rollback_question() -> None:
    assert [p.same_bytes_after for p in R.PINS] == [False, False, True]


def test_both_tags_are_mutable_and_the_digest_is_not() -> None:
    assert R.PINS[0].mutable is True and R.PINS[1].mutable is True
    assert R.PINS[2].mutable is False


def test_a_silent_retag_can_change_one_place_twice_and_zero_once() -> None:
    assert [p["silent_spots"] for p in R.pin_table()] == [1, 1, 0]


def test_the_digest_kind_leaves_its_change_in_the_manifest() -> None:
    assert R.pin_table()[2]["trace"].startswith("清单里")


def test_the_floating_tag_leaves_the_change_nowhere() -> None:
    assert R.pin_table()[0]["trace"] == "不留在任何地方"


def test_an_approval_buys_a_name_and_costs_four_minutes() -> None:
    ap = R.approval_report()
    assert ap["auto_wait_s"] == 0 and ap["human_wait_s"] == 240
    assert ap["day_wait_s"] == R.RELEASES_PER_DAY * R.HUMAN_APPROVE_S


def test_a_pending_approval_still_holds_the_concurrency_group() -> None:
    assert "concurrency" in R.approval_report()["side_effect"]


def test_the_canary_steps_run_at_fifty_two_hundred_and_a_thousand_rps() -> None:
    assert [row["rps"] for row in R.canary_table()] == [50, 250, 1000]


def test_a_fixed_sample_gate_exposes_the_same_number_of_bad_requests_everywhere() -> None:
    """判据一是「攒够 N 个错误」：N ÷ 真实错误率，与档位无关。"""
    rows = R.canary_table()
    assert [row["count_bad"] for row in rows] == [1333, 1333, 1333]
    assert rows[0]["count_bad"] == int(R.GATE_COUNT / R.BAD_ERROR_RATE)


def test_a_small_step_only_stretches_the_detection_time() -> None:
    rows = R.canary_table()
    assert rows[0]["count_s"] == 26.7 and rows[2]["count_s"] == 1.3
    assert rows[0]["count_s"] > 20 * rows[2]["count_s"]


def test_a_fixed_window_gate_does_reduce_the_bad_requests_by_the_step_ratio() -> None:
    rows = R.canary_table()
    assert [row["window_bad"] for row in rows] == [90, 450, 1800]
    assert rows[2]["window_bad"] // rows[0]["window_bad"] == 20


def test_the_window_has_to_be_long_enough_to_see_anything() -> None:
    assert all(row["min_window_s"] == R.WINDOW_S for row in R.canary_table())
    assert R.WINDOW_RATE * R.TOTAL_RPS * R.WINDOW_S < R.BAD_ERROR_RATE * R.TOTAL_RPS * R.WINDOW_S


def test_rollback_costs_two_stages_and_far_more_than_detection() -> None:
    roll = R.rollback_report()
    assert roll["total_s"] == roll["approve_s"] + roll["effect_s"] == 330
    assert roll["bad_requests"] == roll["total_s"] * R.TOTAL_RPS
    assert roll["ratio"] > 200


def test_the_rollback_is_exactly_twenty_times_cheaper_at_five_percent() -> None:
    roll = R.rollback_report()
    assert roll["at_canary"] * 20 == roll["bad_requests"]


def test_detection_and_rollback_are_measured_in_different_units() -> None:
    """判红看「放过了多少坏请求」，回滚看「以当前档位的全量流量撑多久」。"""
    roll = R.rollback_report()
    assert roll["detect_bad"] == 1333 and roll["bad_requests"] == 330_000
    assert roll["ratio"] == round(roll["bad_requests"] / roll["detect_bad"], 1)
