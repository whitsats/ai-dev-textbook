"""`app/sse.py` 的用例：帧、三个头、心跳、续传与背压。

这一块的每一条都对着一个「不会报错」的现场：协议写对了而代理把它攒成一块、
心跳没写而连接被掐、补发接不上而用户看到回答从头再来。
"""
from __future__ import annotations

from app import sse as S


def _journal(keep: int) -> S.Journal:
    j = S.Journal(keep=keep)
    for e in S.chat_stream():
        j.add(e)
    return j


def test_a_frame_ends_with_a_blank_line() -> None:
    assert S.frame(S.Event("x")) == "data: x\n\n"


def test_data_is_the_only_required_field() -> None:
    """最小的事件就是一行 `data:` 加一个空行。"""
    assert S.EVENT_FIELDS[0] == "event" and "data" in S.EVENT_FIELDS
    assert S.frame(S.Event("")).count("\n") == 2


def test_multi_line_data_is_written_line_by_line_and_restored_with_newlines() -> None:
    text = S.frame(S.Event("第一行\n第二行"))
    assert text.count("data: ") == 2
    evs, _ = S.parse(text)
    assert evs[0].data == "第一行\n第二行"


def test_two_data_lines_inside_one_event_are_joined_by_a_newline() -> None:
    evs, _ = S.parse("data: 一\ndata: 二\n\n")
    assert len(evs) == 1 and evs[0].data == "一\n二"


def test_a_comment_line_is_not_an_event() -> None:
    """心跳用注释行的写法：它占位、却进不了事件列表。"""
    evs, comments = S.parse(": keep-alive\n\n")
    assert evs == [] and comments == 1


def test_a_field_without_data_does_not_form_an_event() -> None:
    assert S.parse("event: ping\n\n")[0] == []


def test_retry_is_parsed_as_a_number() -> None:
    evs, _ = S.parse("retry: 3000\ndata: x\n\n")
    assert evs[0].retry == 3000


def test_the_whole_answer_round_trips_field_by_field() -> None:
    evs = S.chat_stream()
    back, comments = S.parse("".join(S.frame(e) for e in evs))
    assert [(e.name, e.data, e.id) for e in back] == [(e.name, e.data, e.id) for e in evs]
    assert comments == 0 and len(evs) == 12


def test_the_answer_is_the_sentence_the_book_quotes() -> None:
    assert "".join(e.data for e in S.chat_stream()) == "知舟是一个把文档变成可问的系统：它先切分、再检索"


def test_ids_are_sequence_numbers_not_timestamps() -> None:
    assert [e.id for e in S.chat_stream()] == [str(i) for i in range(1, 13)]


def test_locally_it_streams_and_behind_default_nginx_it_does_not() -> None:
    rows = S.buffer_table()
    assert rows[0]["looks"] == "像流"
    assert rows[1]["looks"] != "像流"
    assert rows[1]["buffering"] == "on（默认）"


def test_one_header_makes_it_stream_without_touching_the_global_config() -> None:
    rows = S.buffer_table()
    assert rows[2]["buffering"] == "on" and rows[2]["looks"] == "像流"
    assert "X-Accel-Buffering" in rows[2]["headers"]


def test_the_three_headers_are_all_explicit() -> None:
    names = [h[0] for h in S.HEADERS]
    assert names == ["Content-Type", "Cache-Control", "X-Accel-Buffering", "Connection"]
    assert all(why for _, _, why in S.HEADERS)


def test_heartbeat_has_to_beat_the_proxy_timeout() -> None:
    assert S.IDLE_TIMEOUT_S == 60
    assert [h.survives for h in S.HEARTBEATS] == [False, True, True, False, False]


def test_no_heartbeat_means_the_connection_is_cut_at_the_timeout() -> None:
    assert "掐断" in S.HEARTBEATS[0].seen


def test_a_heartbeat_as_rare_as_the_timeout_loses() -> None:
    assert not S.HEARTBEATS[3].survives and S.HEARTBEATS[3].gap_s == S.IDLE_TIMEOUT_S


def test_only_the_frames_that_fit_the_window_are_counted() -> None:
    rows = S.heartbeat_table()
    assert [r["frames_5min"] for r in rows] == [0, 20, 10, 5, 2]


def test_a_reconnect_with_a_kept_id_replays_only_the_tail() -> None:
    j = _journal(5)
    r = j.resume("10")
    assert r["count"] == 2 and not r["evicted"] and r["lost"] == 0
    assert r["replayed"] == ["、再", "检索"]


def test_a_reconnect_on_the_last_id_replays_nothing() -> None:
    assert _journal(5).resume("12")["count"] == 0


def test_an_evicted_id_can_only_be_replayed_from_the_oldest_kept_frame() -> None:
    j = _journal(5)
    r = j.resume("3")
    assert r["evicted"] and r["lost"] is None
    assert r["replayed"] == j.data and "第 8 条" in r["seen"]


def test_without_an_id_the_browser_treats_it_as_a_brand_new_subscription() -> None:
    r = _journal(5).resume("")
    assert r["count"] == 0 and r["lost"] == 12


def test_the_buffer_length_decides_whether_a_reconnect_can_continue() -> None:
    assert _journal(3).resume("8")["evicted"] is True
    assert _journal(5).resume("8")["evicted"] is False
    assert _journal(12).resume("8")["count"] == 4


def test_the_first_kept_index_moves_with_eviction() -> None:
    assert _journal(5).first_index == 8
    assert _journal(12).first_index == 1
    assert _journal(3).first_index == 10


def test_a_fast_consumer_never_builds_a_queue() -> None:
    assert S.slow_consumer_table()[0]["peak_queue"] == 0


def test_without_a_queue_limit_the_queue_grows_to_the_end() -> None:
    row = S.slow_consumer_table()[4]
    assert row["peak_queue"] == 450 and "内存" not in row["outcome"]
    assert "一直涨" in row["outcome"]


def test_with_zero_buffer_the_slow_consumer_is_cut_off() -> None:
    row = S.slow_consumer_table()[5]
    assert row["peak_queue"] == 0 and "断开" in row["outcome"]


def test_a_bounded_queue_turns_a_memory_incident_into_a_bounded_delay() -> None:
    assert S.slow_consumer_table()[1]["peak_queue"] == 32
    assert "上限" in S.slow_consumer_table()[1]["outcome"]


def test_thirty_seconds_of_production_is_six_hundred_frames() -> None:
    assert S.PRODUCED_PER_SEC == 20 and S.PRODUCED_PER_SEC * 30 == 600


def test_the_protocol_table_separates_what_the_framework_covers() -> None:
    rows = {r["topic"]: r for r in S.protocol_table()}
    assert "不自动重连" in rows["断线重连"]["ai_sdk"]
    assert "增量" in rows["部分片段"]["ai_sdk"]
    assert len(rows) == 6
