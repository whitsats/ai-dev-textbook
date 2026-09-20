"""`app/graph.py` 的用例：`needs` 决定关键路径，槽位只能填满它，`matrix` 的格数就是账单。"""
from __future__ import annotations

from app import graph as G


def test_the_flat_graph_violates_every_ordering_rule() -> None:
    assert G.violations(G.FLAT) == G.MUST_PRECEDE
    assert len(G.violations(G.FLAT)) == 5


def test_a_chain_violates_nothing_because_it_says_everything() -> None:
    assert G.violations(G.CHAIN) == ()


def test_the_correct_graph_only_leaves_the_harmless_pair_unstated() -> None:
    assert G.violations(G.GRAPH) == (("lint", "unit"),)


def test_the_flat_graph_is_the_fastest_and_the_worst_gate() -> None:
    assert G.makespan(G.FLAT, 4) == 12
    assert G.makespan(G.FLAT, 4) < G.makespan(G.GRAPH, 4)
    assert len(G.violations(G.FLAT)) > len(G.violations(G.GRAPH))


def test_a_chain_costs_the_same_no_matter_how_many_slots_you_give_it() -> None:
    assert G.makespan(G.CHAIN, 1) == G.makespan(G.CHAIN, 2) == G.makespan(G.CHAIN, 4) == 32


def test_slots_only_fill_the_critical_path() -> None:
    """正确的图：从 1 个槽到 2 个槽省 11 分钟，从 2 个槽到 4 个槽一分钟不省。"""
    assert G.makespan(G.GRAPH, 1) == 32
    assert G.makespan(G.GRAPH, 2) == 21
    assert G.makespan(G.GRAPH, 4) == 21


def test_the_critical_path_is_a_chain_through_needs() -> None:
    path, minutes = G.critical_path(G.GRAPH)
    assert path == ("unit", "e2e", "deploy") and minutes == 21


def test_the_chain_graph_critical_path_is_the_whole_chain() -> None:
    path, minutes = G.critical_path(G.CHAIN)
    assert path == ("lint", "unit", "integration", "e2e", "deploy") and minutes == 32


def test_reachability_is_transitive_but_not_sideways() -> None:
    assert G.reaches(G.CHAIN, "lint", "deploy")
    assert not G.reaches(G.GRAPH, "lint", "deploy")
    assert not G.reaches(G.GRAPH, "integration", "e2e")


def test_six_matrix_cells_cost_six_cells_of_billing() -> None:
    rows = G.matrix_table()
    assert rows[0]["cells"] == 6 and rows[0]["billable"] == 6 * G.PER_CELL_MINUTES


def test_excluding_two_cells_saves_a_third_of_the_bill() -> None:
    rows = G.matrix_table()
    assert rows[1]["cells"] == 4 and rows[1]["billable"] == 16
    assert ("3.11", "frontend") not in G.matrix_cells()


def test_fail_fast_cancels_the_siblings_and_they_get_no_verdict() -> None:
    row = G.matrix_table()[2]
    assert row["cancelled"] == 3
    assert row["verdicts"].count("cancelled") == 3
    assert "failure" in row["verdicts"]


def test_cancelled_is_neither_success_nor_failure() -> None:
    row = G.matrix_table()[2]
    assert set(row["verdicts"]) == {"failure", "cancelled"}
    assert "success" not in row["verdicts"]


def test_cancelling_in_progress_saves_two_full_runs() -> None:
    rows = G.concurrency_table()
    assert rows[0]["billable"] == 27 and rows[0]["killed"] == 2
    assert rows[1]["billable"] == 63 and rows[1]["killed"] == 0
    assert rows[0]["billable"] * 2 + 9 == rows[1]["billable"]


def test_queueing_keeps_running_runs_whose_verdict_is_already_stale() -> None:
    rows = G.concurrency_table()
    assert "过期" in rows[1]["last_word"]


def test_a_group_key_without_a_ref_makes_branches_cancel_each_other() -> None:
    row = G.concurrency_table()[2]
    assert row["billable"] == G.concurrency_table()[0]["billable"]
    assert "main" in row["note"]


def test_the_table_has_exactly_three_shapes() -> None:
    assert len(G.concurrency_table()) == 3
    assert {r["shape"][:6] for r in G.concurrency_table()} == {"cancel", "不写 can", "group "}
