"""`app/compose.py` 的用例：四种等法各等到哪一刻、有重试与没重试是两个世界。"""
from __future__ import annotations

from app import compose as C


# ------------------------------------------------------------ 一、四种等法

def test_without_depends_on_the_app_starts_at_zero() -> None:
    assert C.app_start(C.DRAFTS[0]) == 0


def test_service_started_waits_for_the_container_not_for_readiness() -> None:
    assert C.app_start(C.DRAFTS[1]) == C.DB.start_s == 2
    assert C.DB.start_s < C.DB.ready_s


def test_service_healthy_waits_for_the_first_green_probe() -> None:
    assert C.app_start(C.DRAFTS[2]) == C.DB.healthy_s == 15


def test_the_completed_condition_waits_on_another_service() -> None:
    """它等的是迁移，不是数据库——两种等待不是同一次等待的变体。"""
    assert C.waited_on(C.DRAFTS[3]) is C.MIGRATE
    assert C.waited_on(C.DRAFTS[2]) is C.DB


def test_unknown_condition_raises() -> None:
    try:
        C.app_start(C.Draft("x", "x", "service_whatever"))
        assert False, "未知条件应当报错"
    except KeyError:
        pass


# ------------------------------------------------------------ 二、两种前提

def test_with_retries_every_draft_eventually_succeeds() -> None:
    for row in C.startup_table(retry_s=3):
        assert row["first_ok"] is not None


def test_without_retries_only_the_last_two_come_up() -> None:
    up = [r["draft"] for r in C.startup_table(retry_s=None) if r["first_ok"] is not None]
    assert up == ["healthy", "completed"]


def test_service_started_is_slower_than_not_waiting_at_all() -> None:
    rows = {r["draft"]: r for r in C.startup_table(retry_s=3)}
    assert rows["started"]["first_ok"] > rows["none"]["first_ok"]


def test_service_started_does_not_reduce_the_failure_count() -> None:
    rows = {r["draft"]: r for r in C.startup_table(retry_s=3)}
    assert rows["started"]["failures"] == rows["none"]["failures"] == 4


def test_waiting_for_health_costs_zero_failures() -> None:
    for row in C.startup_table(retry_s=3):
        if row["draft"] in ("healthy", "completed"):
            assert row["failures"] == 0


def test_failure_count_comes_from_the_retry_interval() -> None:
    """重试间隔越长，同一次等待里失败的次数越少——**而那不是变好了**。"""
    slow = C.startup(C.DRAFTS[0], retry_s=6)
    fast = C.startup(C.DRAFTS[0], retry_s=3)
    assert slow["failures"] < fast["failures"]
    assert slow["first_ok"] == fast["first_ok"]


def test_attempts_are_one_more_than_failures() -> None:
    for row in C.startup_table(retry_s=3):
        assert row["attempts"] == row["failures"] + 1


def test_dependency_times_are_carried_in_the_row() -> None:
    row = C.startup(C.DRAFTS[1], retry_s=3)
    assert (row["dep"], row["dep_running"], row["dep_ready"]) == ("db", 2, 12)


# ------------------------------------------------------------ 三、健康检查的账

def test_healthy_is_the_first_probe_after_the_service_is_ready() -> None:
    s = C.Service("x", "x", start_s=2, ready_s=12, interval=5)
    assert s.healthy_s == 15 and s.probes == 3


def test_a_shorter_interval_sees_health_earlier_but_pays_in_probes() -> None:
    fast = C.Service("x", "x", 2, 12, interval=1)
    slow = C.Service("x", "x", 2, 12, interval=5)
    assert fast.healthy_s < slow.healthy_s and fast.probes > slow.probes


def test_start_period_does_not_delay_health() -> None:
    warm = C.Service("x", "x", 2, 12, interval=5, start_period=30)
    assert warm.healthy_s == 15


def test_start_period_does_delay_the_unhealthy_verdict() -> None:
    warm = C.Service("x", "x", 2, 12, interval=5, retries=5, start_period=30)
    assert warm.unhealthy_after == 55 == 30 + 5 * 5


def test_more_retries_means_a_later_verdict() -> None:
    patient = C.Service("x", "x", 2, 12, interval=5, retries=10)
    hasty = C.Service("x", "x", 2, 12, interval=5, retries=2)
    assert patient.unhealthy_after == 50 and hasty.unhealthy_after == 10


def test_healthcheck_table_is_four_combinations() -> None:
    rows = C.healthcheck_table()
    assert len(rows) == 4 and len({(r["interval"], r["retries"], r["start_period"])
                                   for r in rows}) == 4


def test_a_service_ready_before_its_first_probe_is_healthy_at_that_probe() -> None:
    quick = C.Service("x", "x", start_s=0, ready_s=1, interval=5)
    assert quick.healthy_s == 5
