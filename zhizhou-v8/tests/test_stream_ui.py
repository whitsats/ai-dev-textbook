"""`app/stream_ui.py` 的用例：状态机、五种「卡住／显示错」、取消与重试。

这一组里最要紧的两条：**「没有事件」不是事件**（所以 `closed`／`timeout` 必须自己造），
以及**状态机对了不等于显示对了**（两条现场只在 `mismatch` 上显形）。
"""
from __future__ import annotations

from app import stream_ui as U


def _case(name: str) -> dict:
    return next(r for r in U.stuck_table() if r["case"].startswith(name))


def test_the_six_states_start_with_the_three_transitions() -> None:
    assert U.STATES == ("idle", "submitting", "streaming", "done", "error", "aborted")
    assert U.TERMINALS == ("done", "error", "aborted")


def test_the_first_byte_ends_the_wait() -> None:
    assert U.step("submitting", "start")[0] == "streaming"


def test_delta_is_a_self_loop_while_streaming() -> None:
    assert U.step("streaming", "delta")[0] == "streaming"


def test_only_done_can_finish_a_stream() -> None:
    assert U.step("streaming", "done")[0] == "done"


def test_a_closed_connection_without_done_lands_in_aborted() -> None:
    assert U.step("streaming", "closed")[0] == "aborted"


def test_the_two_edges_the_client_makes_itself_are_in_the_table() -> None:
    events = {m.event for s in U.STATES for m in U.moves_from(s)}
    assert {"closed", "timeout"} <= events


def test_a_transition_that_is_not_in_the_table_leaves_the_state_alone() -> None:
    assert U.step("idle", "delta")[0] == "idle"
    assert U.step("streaming", "submit")[0] == "streaming"


def test_the_first_scene_gets_stuck_streaming() -> None:
    r = _case("服务端断了、`done` 没来")
    assert r["stuck"] and not r["terminal"] and not r["mismatch"]


def test_the_same_break_lands_immediately_when_closed_is_fed_in() -> None:
    r = _case("同一条断线")
    assert not r["stuck"] and r["terminal"] and r["state"] == "aborted"


def test_a_late_frame_after_abort_shows_more_than_it_accumulated() -> None:
    r = _case("`abort` 之后又来了一帧")
    assert r["state"] == "aborted" and r["mismatch"] and r["shown"] == r["text"] + "·"


def test_clearing_the_partial_before_a_retry_is_the_normal_case() -> None:
    r = _case("错误之后清了 partial")
    assert r["mismatch"] is False and r["state"] == "streaming"


def test_not_clearing_the_partial_shows_the_old_answer_next_to_the_new_one() -> None:
    r = _case("同一次重试，但 partial 没清")
    assert r["mismatch"] is True and r["shown"] == "···" and r["text"] == "·"


def test_no_scene_leaves_the_state_machine_in_a_state_it_cannot_exit() -> None:
    for r in U.stuck_table():
        assert r["state"] in U.STATES, r["case"]
        if r["state"] == "streaming":
            assert r["stuck"] is True


def test_a_terminal_state_is_exactly_the_done_error_aborted_trio() -> None:
    for r in U.stuck_table():
        assert r["terminal"] == (r["state"] in U.TERMINALS)


def test_abort_has_three_levels_and_only_one_of_them_stops_the_billing() -> None:
    rows = U.abort_table()
    assert len(rows) == 3
    assert "算力照付" in rows[0]["cost"]
    assert "不再计费" in rows[1]["guaranteed"]


def test_closing_the_connection_is_a_result_not_an_operation() -> None:
    row = U.abort_table()[2]
    assert "不是操作" in row["cost"] and "两边都停" in row["stops"]


def test_retrying_the_whole_request_starts_the_answer_over() -> None:
    assert "从头再来" in U.retry_table()[0]["seen"]


def test_client_side_continue_duplicates_what_the_server_already_sent() -> None:
    row = U.retry_table()[2]
    assert row["repeats"] == 3 and "两遍" in row["seen"]


def test_only_the_last_event_id_variant_can_continue_a_sentence() -> None:
    assert "接着长" in U.retry_table()[1]["seen"]


def test_a_full_snapshot_mode_needs_no_ids_to_recover() -> None:
    assert U.chunk_table()[1]["reconnect"].startswith("**不需要 id")


def test_incremental_mode_loses_a_sentence_and_keeps_going() -> None:
    assert "少一句" in U.chunk_table()[0]["lost"]


def test_a_session_keeps_the_accumulated_text_and_the_shown_text_apart() -> None:
    s = U.Session()
    for ev in ("submit", "start", "delta", "delta"):
        s.feed(ev)
    assert s.text == "··" and s.state == "streaming"


def test_feeding_a_scene_through_a_session_matches_replay() -> None:
    events = ("submit", "start", "delta", "abort", "delta")
    s = U.Session()
    for ev in events:
        s.feed(ev)
    r = U.replay(events)
    assert s.state == r["state"] == "aborted"
