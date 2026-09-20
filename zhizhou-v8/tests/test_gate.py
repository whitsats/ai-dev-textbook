"""`app/gate.py` 的用例：同样是「没跑」，写在 `if:` 上放行、写在 `paths:` 上卡住。"""
from __future__ import annotations

from app import gate as Q


def _shape(name: str) -> Q.Shape:
    return next(s for s in Q.SHAPES if s.name.startswith(name))


def test_a_skipped_job_reports_success_and_does_not_block() -> None:
    """官方：被跳过的 job 报 Success，即使它是必需检查也不阻止合并。"""
    s = _shape("job 级 `if:`")
    assert s.reported == "success" and s.blocks is False


def test_a_path_filtered_workflow_leaves_the_check_pending_and_blocks() -> None:
    """官方：因路径过滤被跳过时检查停在 Pending，要求它的 PR 被挡住。"""
    s = _shape("workflow 级 `paths`")
    assert s.reported is None and s.blocks is True and s.seen == "Pending"


def test_a_skip_marker_behaves_like_the_path_filter() -> None:
    assert _shape("提交信息带 `[skip ci]`").category == _shape("workflow 级 `paths`").category


def test_continue_on_error_is_green_outside_red_inside() -> None:
    s = _shape("`continue-on-error: true`")
    assert s.level == "step" and s.reported == "success" and s.blocks is False


def test_a_cancelled_matrix_sibling_blocks_because_it_never_ran() -> None:
    s = _shape("矩阵里被 `fail-fast`")
    assert s.reported == "cancelled" and s.blocks is True


def test_a_cancelled_run_also_blocks() -> None:
    assert _shape("被 `concurrency` 取消").blocks is True


def test_only_one_of_the_seven_shapes_actually_verified_anything() -> None:
    counts = Q.groups()
    assert len(counts["真绿"]) == 1
    assert counts["真绿"] == ("job 跑完并通过",)


def test_the_two_kinds_of_not_running_are_two_groups() -> None:
    counts = Q.groups()
    assert len(counts["绿而没验"]) == 2
    assert len(counts["停在 Pending（挡）"]) == 2
    assert len(counts["跑了却被取消（挡）"]) == 2


def test_the_groups_partition_the_table() -> None:
    counts = Q.groups()
    assert sum(len(v) for v in counts.values()) == len(Q.SHAPES) == 7


def test_success_and_cancelled_are_the_only_two_verdict_kinds() -> None:
    verdicts = {Q.verdict(s)["verdict"] for s in Q.SHAPES}
    assert verdicts == {"放行", "挡"}


def test_a_cancelled_shape_is_not_one_of_the_three_acceptable_states() -> None:
    """官方给必需检查的合格状态只有 successful / skipped / neutral 三种。"""
    reported = {s.reported for s in Q.SHAPES}
    assert "cancelled" in reported
    assert reported & {"success", None, "cancelled"} == reported


def test_every_shape_carries_the_mechanism_that_produced_it() -> None:
    for shape in Q.SHAPES:
        assert shape.why, shape.name
    assert "即使它是必需检查" in _shape("job 级 `if:`").why


def test_the_table_keeps_the_order_of_the_book() -> None:
    assert [s.category for s in Q.SHAPES] == [
        "真绿", "绿而没验", "绿而没验",
        "停在 Pending（挡）", "停在 Pending（挡）",
        "跑了却被取消（挡）", "跑了却被取消（挡）",
    ]
