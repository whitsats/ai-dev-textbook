"""`app/billing.py` 的用例：**同一笔调用要在三个时刻各说一遍账**（预扣、结算、对账）。"""
from __future__ import annotations

from app import billing as B


def test_the_cache_prices_are_derived_not_copied() -> None:
    """只有 input／output 是抄的；另两段按 6.1 记下的乘法关系算——**不重抄**。"""
    assert B.PRICE["cache_write"] == 1.25 * B.PRICE["input"]
    assert B.PRICE["cache_read"] == 0.10 * B.PRICE["input"]


def test_charge_is_four_parts_then_the_batch_multiplier() -> None:
    assert B.charge(1_000, 1_000) == 0.012
    assert B.charge(1_000, 1_000, batch=True) == 0.006
    assert B.charge(0, 0) == 0.0


def test_cached_tokens_are_cheaper_than_input_tokens() -> None:
    plain = B.charge(1_000, 0)
    cached = B.charge(0, 0, cache_read=1_000)
    assert cached < plain
    assert round(plain - cached, 6) == 0.0018


def test_the_reservation_is_computed_from_the_estimate_ceiling() -> None:
    assert B.reserve() == B.charge(*B.RESERVE_TOKENS) == 0.012


def test_three_settlements_share_one_reservation() -> None:
    """预扣额三笔相同——差别全在实际那一列上。"""
    ss = B.settlements()
    assert len({s.held for s in ss}) == 1
    assert [s.actual for s in ss] == [0.0042, 0.0174, 0.0018]


def test_the_deltas_have_both_signs() -> None:
    ss = B.settlements()
    assert [s.delta > 0 for s in ss] == [True, False, True]


def test_a_call_over_its_estimate_owes_money_at_settlement() -> None:
    """按上限估的必然结果：越过了上限的那一笔是**欠着的**。"""
    owed = next(s for s in B.settlements() if s.delta < 0)
    assert owed.actual > owed.held


def test_the_refunds_and_the_amount_owed_add_up() -> None:
    ss = B.settlements()
    assert round(sum(s.held for s in ss) - sum(s.actual for s in ss), 6) == round(
        sum(s.delta for s in ss), 6)


def test_a_failed_call_still_has_a_cost() -> None:
    """上游 500：用户一个字没拿到，而**输入那一段上游已经处理过了**。"""
    failed = B.settlements()[-1]
    assert failed.actual > 0
    assert "上游已经处理过" in failed.why


def test_the_stranded_cost_is_the_one_that_never_shows_up_in_usage() -> None:
    assert B.stranded_cost() == 0.1776
    assert "不该" in B.discrepancies()[1][2]


def test_billing_granularity_rounds_up_only() -> None:
    assert B.bill_call(120, 40) == B.charge(200, 100)
    assert B.bill_call(100, 100) == B.charge(100, 100)


def test_the_month_is_reproducible_from_its_seed() -> None:
    assert B.month_calls() == B.month_calls()
    assert B.month_totals() == B.month_totals()


def test_the_bill_is_higher_than_the_log_and_that_is_not_an_error() -> None:
    t = B.month_totals()
    assert t["账单合计"] > t["日志合计"]
    assert round(t["账单合计"] - t["日志合计"], 6) == t["差额"]


def test_aligning_the_granularity_makes_the_gap_zero() -> None:
    """对账的第一步不是查错，是**把口径对齐**。"""
    assert B.aligned_gap() == 0.0


def test_the_gap_is_small_enough_to_survive_a_review() -> None:
    t = B.month_totals()
    assert 0.03 < t["差额"] / t["日志合计"] < 0.10


def test_an_exception_counted_as_the_rule_loses_a_small_amount() -> None:
    """把 0.025× 的例外按全局 0.10× 算：少收的钱**小到没人发现**。"""
    assert B.exception_gap() == 0.27
    assert "0.025×" in B.EXCEPTION_ROW[0]


def test_there_are_three_discrepancies_and_only_one_of_them_is_money() -> None:
    rows = B.discrepancies()
    assert len(rows) == 3
    assert "归零" in rows[0][2]
    assert "不该" in rows[1][2]
    assert "例外" in rows[2][2]
