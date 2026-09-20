"""`app/runtime.py` 的用例：上下文外发多少、四种姿态各能写哪里。"""
from __future__ import annotations

from app import runtime as R

IGNORED = ("/app/.git", "/app/.venv", "/app/tests")


# ------------------------------------------------------------ 一、上下文外发

def test_the_context_is_what_sits_on_disk() -> None:
    ctx = R.context_report()
    assert ctx["sent_kb"] == ctx["total_kb"] == 53_042
    assert ctx["sent_files"] == ctx["total_files"] == 7


def test_dockerignore_changes_what_leaves_not_what_exists() -> None:
    ctx = R.context_report(IGNORED)
    assert ctx["total_kb"] == 53_042 and ctx["sent_kb"] == 10_242


def test_everything_blocked_is_named() -> None:
    ctx = R.context_report(IGNORED)
    assert set(ctx["blocked"]) == set(IGNORED) and ctx["blocked_kb"] == 42_800


def test_the_git_history_is_one_of_the_things_that_should_not_leave() -> None:
    assert any(path == "/app/.git" for path, _ in R.IGNORE_REASONS)


def test_blocking_nothing_sends_everything() -> None:
    assert R.context_report(("nope",))["sent_kb"] == 53_042


# ------------------------------------------------------------ 二、四种姿态

def test_the_three_write_needs_are_listed_once() -> None:
    assert [p for p, _, _ in R.NEEDS] == ["/tmp", "/app/.cache", "/app/logs"]


def test_two_of_the_three_are_hard_requirements() -> None:
    assert [required for _, _, required in R.NEEDS] == [True, True, False]


def test_root_and_non_root_can_both_write() -> None:
    seats = {r["seat"]: r for r in R.seat_table()}
    assert seats["root-rw"]["ok"] == seats["app-rw"]["ok"] == 3


def test_the_difference_between_them_is_the_identity_not_the_access() -> None:
    seats = {r["seat"]: r for r in R.seat_table()}
    assert seats["root-rw"]["root"] is True and seats["app-rw"]["root"] is False
    assert seats["root-rw"]["ok"] == seats["app-rw"]["ok"]


def test_a_read_only_rootfs_blocks_all_three_without_mounts() -> None:
    assert R.seat_tally(R.SEATS[2])["ok"] == 0


def test_declaring_the_two_hard_paths_is_enough_to_start() -> None:
    tally = R.seat_tally(R.SEATS[3])
    assert tally["required_ok"] is True and tally["ok"] == 2 and tally["declared"] == 2


def test_the_logs_path_is_the_one_that_can_be_skipped() -> None:
    writes = {w.path: w for w in R.seat_writes(R.SEATS[3])}
    assert writes["/app/logs"].ok is False and writes["/app/logs"].required is False


def test_a_root_write_is_flagged_in_the_note() -> None:
    writes = {w.path: w for w in R.seat_writes(R.SEATS[0])}
    assert "root" in writes["/tmp"].note


def test_a_blocked_write_says_why() -> None:
    writes = {w.path: w for w in R.seat_writes(R.SEATS[2])}
    assert "只读" in writes["/tmp"].note


def test_the_read_only_seat_is_still_not_root() -> None:
    assert R.seat_tally(R.SEATS[3])["root"] is False


def test_seat_table_has_four_rows() -> None:
    assert len(R.seat_table()) == 4
