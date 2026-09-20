"""`app/trigger.py` 的用例：过滤器写窄一格，就是一类改动从此没有门。"""
from __future__ import annotations

from app import trigger as T


def test_eleven_commits_and_exactly_one_of_them_should_not_run() -> None:
    assert len(T.CASES) == 11
    assert sum(1 for c in T.CASES if not c.should_run) == 1
    assert T.SHOULD_RUN == 10


def test_no_filter_lets_everything_through() -> None:
    row = next(r for r in T.filter_table() if r["filter"] == "不写过滤器")
    assert row["ran"] == 11 and row["missed"] == 0


def test_a_narrow_allowlist_drops_the_commit_that_edits_the_gate_itself() -> None:
    row = next(r for r in T.filter_table() if r["filter"].startswith("白名单·窄"))
    assert row["ran"] == 3 and row["missed"] == 7
    assert row["worst"] == "chore: 顺手改一下门自己"
    assert "chore: 顺手改一下门自己" in row["missed_labels"]


def test_an_allowlist_is_an_enumeration_and_an_enumeration_always_misses_one() -> None:
    row = next(r for r in T.filter_table() if r["filter"].startswith("白名单·宽"))
    assert row["missed"] == 1
    assert row["worst"] == "chore: 新增一个部署目录"


def test_a_blocklist_is_default_allow_so_today_it_misses_nothing() -> None:
    row = next(r for r in T.filter_table() if r["filter"].startswith("黑名单"))
    assert row["ran"] == 10 and row["missed"] == 0


def test_paths_and_paths_ignore_cannot_be_written_together() -> None:
    try:
        T.Workflow("坏", paths=("app/**",), paths_ignore=("docs/**",))
    except ValueError:
        return
    raise AssertionError("两种过滤器同时写应该报错")


def test_glob_semantics_the_book_relies_on() -> None:
    assert T.matches(("app/**",), "app/main.py")
    assert T.matches(("app/**",), "app/rag/store.py")
    assert not T.matches(("app/**",), "web/src/App.tsx")
    assert T.matches(("**.md",), "README.md")
    assert T.matches(("Dockerfile",), "Dockerfile")


def test_a_paths_filter_is_default_deny() -> None:
    wf = T.Workflow("窄", paths=("app/**",))
    assert T.passes(wf, T.Change("x", ("app/rag.py",)))[0] is True
    assert T.passes(wf, T.Change("x", ("Dockerfile",)))[0] is False


def test_a_paths_ignore_filter_is_default_allow() -> None:
    wf = T.Workflow("宽", paths_ignore=("docs/**",))
    assert T.passes(wf, T.Change("x", ("Dockerfile",)))[0] is True
    assert T.passes(wf, T.Change("x", ("docs/guide.md",)))[0] is False


def test_one_commit_on_a_branch_in_this_repo_starts_two_runs() -> None:
    """`push` 与 `pull_request` 两个事件都成立——同一份提交两份账单。"""
    rows = T.skip_table()
    assert rows[0]["runs"] == 2 and "push" in rows[0]["why"]


def test_a_fork_pull_request_starts_one_run() -> None:
    rows = T.skip_table()
    assert rows[1]["runs"] == 1 and "fork" in rows[1]["why"]


def test_a_skip_marker_starts_no_run_and_leaves_the_check_pending() -> None:
    rows = T.skip_table()
    assert rows[2]["runs"] == 0 and rows[2]["check"] == "Pending"


def test_the_five_official_skip_markers() -> None:
    for mark in T.SKIP_MARKS:
        assert T.Change("x", ("app/main.py",), message=f"fix: 一点东西\n\n{mark} 本地跑过了").skips
    assert len(T.SKIP_MARKS) == 5


def test_a_hyphenated_marker_is_not_one_of_them() -> None:
    assert not T.Change("x", ("app/main.py",), message="[skip-ci] 写法不对").skips


def test_the_skip_marker_wins_over_the_event_count() -> None:
    change = T.Change("x", ("app/rag.py",), fork=True, message="[no ci]")
    assert T.runs_for(change, T.Workflow("CI")) == (0, "[skip ci]：两个事件都不起（检查停在 Pending）")


def test_a_filtered_out_commit_says_it_will_leave_a_pending_check() -> None:
    n, why = T.runs_for(T.Change("x", ("README.md",)),
                        T.Workflow("窄", paths=("app/**",)))
    assert n == 0 and "Pending" in why


def test_filter_table_is_a_full_cross_product() -> None:
    assert len(T.filter_table()) == len(T.FILTERS) == 4


def test_only_three_cases_carry_a_note_and_they_are_the_three_that_matter() -> None:
    noted = [c.change.label for c in T.CASES if c.note]
    assert len(noted) == 3
    assert "docs: 补一段说明" in noted
    assert "chore: 新增一个部署目录" in noted
