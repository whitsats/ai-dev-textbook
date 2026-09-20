"""`app/privacy.py` 的用例：期限与执行路径分开、四种脱敏各留下了什么、
识别的两笔账、删除走不到的那几处、审计记录自己的两处自查。"""
from __future__ import annotations

from app import privacy as V


def _rec(kind: str, created: int, text: str = "13800138000") -> V.Record:
    return V.Record(kind=kind, subject="u1", created_day=created, text=text)


# ------------------------------------------------------------ 一、期限与执行路径

def test_age_is_a_subtraction() -> None:
    assert V.age_days(_rec("prompt", 10), 60) == 50


def test_expired_uses_each_kind_own_window() -> None:
    records = (_rec("prompt", 10), _rec("prompt", 40), _rec("cache", 58))
    assert [r.created_day for r in V.expired(records, 60)] == [10, 58]


def test_stale_and_will_delete_are_two_columns() -> None:
    """**过期的条数与会被删的条数不是同一个数**——本模块的第一条判据。"""
    records = (_rec("corpus", -400),)
    rows = V.retention_report(records, V.NOW)
    corpus = next(r for r in rows if r["kind"] == "corpus")
    assert corpus["stale"] == 1 and corpus["will_delete"] == 0


def test_enforced_kind_deletes_everything_stale() -> None:
    records = (_rec("trace", 40), _rec("trace", 50))
    rows = V.retention_report(records, V.NOW)
    trace = next(r for r in rows if r["kind"] == "trace")
    assert trace["will_delete"] == trace["stale"] == 2


def test_orphan_is_the_difference() -> None:
    tally = V.retention_tally(V.sample_records(), V.NOW)
    assert tally["orphan"] == tally["stale"] - tally["will_delete"]


def test_audit_and_corpus_have_no_delete_path() -> None:
    assert V.POLICY_BY_KIND["audit"].enforced is False
    assert V.POLICY_BY_KIND["corpus"].enforced is False


def test_report_has_one_row_per_class() -> None:
    rows = V.retention_report(V.sample_records(), V.NOW)
    assert [r["kind"] for r in rows] == [p.kind for p in V.RETENTION]


def test_worst_points_at_the_farthest_overrun() -> None:
    tally = V.retention_tally(V.sample_records(), V.NOW)
    assert tally["worst"] == "corpus" and tally["worst_over"] == 95


# ------------------------------------------------------------ 二、四种脱敏

def test_mask_keeps_head_and_tail() -> None:
    assert V.apply("mask", "13800138000") == "138****8000"


def test_mask_of_a_short_value_is_all_stars() -> None:
    assert V.apply("mask", "1234") == "****"


def test_placeholder_has_exactly_one_output() -> None:
    assert V.apply("placeholder", "a") == V.apply("placeholder", "b") == "<已隐去>"


def test_hash_is_deterministic_which_is_the_whole_point() -> None:
    assert V.apply("hash", "13800138000") == V.apply("hash", "13800138000")


def test_drop_leaves_nothing() -> None:
    assert V.apply("drop", "13800138000") == ""


def test_unknown_technique_raises() -> None:
    try:
        V.apply("nope", "x")
    except KeyError:
        return
    raise AssertionError("未知手法应当报错")


def test_mask_and_hash_are_joinable() -> None:
    """**脱敏 ≠ 匿名**：这两个手法让同一个人在两份数据里仍然连得起来。"""
    values = ("13800138000", "13900139000", "13800138000")
    table = {r["technique"]: r for r in V.linkability_table(values)}
    assert table["mask"]["joinable"] is True
    assert table["hash"]["joinable"] is True


def test_placeholder_and_drop_collapse() -> None:
    values = ("13800138000", "13900139000", "13800138000")
    table = {r["technique"]: r for r in V.linkability_table(values)}
    assert table["placeholder"]["collapsed"] is True
    assert table["drop"]["collapsed"] is True


def test_exactly_two_of_four_are_joinable() -> None:
    table = V.linkability_table(("13800138000", "13900139000", "13800138000"))
    assert sum(1 for r in table if r["joinable"]) == 2


def test_collapsing_and_joining_are_opposite_failures() -> None:
    table = V.linkability_table(("13800138000", "13900139000", "13800138000"))
    assert all(not (r["joinable"] and r["collapsed"]) for r in table)


# ------------------------------------------------------------ 三、尾号与生日

def test_tail_alone_does_not_identify() -> None:
    t = V.tail_guess(V.SAMPLE_POPULATION)
    assert t["tail_groups"] < t["n"] and t["tail_max"] > 1


def test_tail_plus_birthday_identifies_most_of_the_population() -> None:
    t = V.tail_guess(V.SAMPLE_POPULATION)
    assert t["both_singletons"] == 3200
    assert abs(t["singleton_rate"] - 0.8) < 1e-9


def test_empty_population_is_not_a_crash() -> None:
    t = V.tail_guess(())
    assert t["n"] == 0 and t["singleton_rate"] == 0.0


# ------------------------------------------------------------ 四、识别码

def test_luhn_accepts_a_real_test_card() -> None:
    assert V.luhn_ok("4111111111111111") is True


def test_luhn_rejects_a_plain_order_number() -> None:
    assert V.luhn_ok("1234567890123456") is False


def test_luhn_accepts_the_order_number_that_happens_to_pass() -> None:
    """**假阳的活标本**：一个订单号碰巧通过了卡号校验。"""
    assert V.luhn_ok("1234567890123452") is True


def test_luhn_rejects_non_digits() -> None:
    assert V.luhn_ok("abcdefghijklmnop") is False


def test_cn_id_checksum_both_ways() -> None:
    assert V.cn_id_ok("11010519491231002X") is True
    assert V.cn_id_ok("110105194912310021") is False


def test_cn_id_rejects_wrong_length() -> None:
    assert V.cn_id_ok("1101051949123100") is False


def test_only_two_classes_have_a_checksum() -> None:
    assert V.has_checksum("card") and V.has_checksum("cn_id")
    assert not V.has_checksum("phone") and not V.has_checksum("email")


def test_shape_rule_matches_inside_an_id_number() -> None:
    """正则的经典副作用：18 位身份证里那一段也被当成了手机号。"""
    hits = V.detect(V.SAMPLE_TEXT)
    assert any(h["kind"] == "phone" and h["value"] == "19491231002" for h in hits)


def test_tally_separates_the_two_accounts() -> None:
    t = V.detect_tally(V.SAMPLE_TEXTS)
    assert t["hits"] == t["confirmed"] + t["false_pos"] + t["no_checksum"]


def test_false_positives_are_all_checksum_capable() -> None:
    t = V.detect_tally(V.SAMPLE_TEXTS)
    assert t["false_pos"] == 2
    assert t["confirmed"] == 4


def test_clean_text_reports_nothing() -> None:
    assert V.detect(V.SAMPLE_TEXTS[10]) == []


# ------------------------------------------------------------ 五、删除

def test_deletion_reaches_exactly_three_stores() -> None:
    d = V.deletion_tally("u1001")
    assert d["stores"] == 6 and d["reached"] == 3 and d["leftover"] == 3


def test_append_only_stores_are_not_reachable() -> None:
    plan = {p["store"]: p for p in V.deletion_plan("u1")}
    assert plan["trace"]["reachable"] is False
    assert plan["log"]["reachable"] is False
    assert plan["backup"]["reachable"] is False


def test_business_stores_are_reachable() -> None:
    plan = {p["store"]: p for p in V.deletion_plan("u1")}
    assert plan["primary"]["reachable"] and plan["cache"]["reachable"] and plan["vector"]["reachable"]


def test_unreachable_stores_say_why_instead_of_pretending() -> None:
    for p in V.deletion_plan("u1"):
        if not p["reachable"]:
            assert "轮转" in p["action"]


# ------------------------------------------------------------ 六、内容捕获与审计

def test_capture_on_stores_everything() -> None:
    rows = {r["mode"]: r for r in V.capture_report(V.sample_records(), V.SAMPLE_TEXTS)}
    assert rows["on"]["stored"] == rows["on"]["records"] == 6


def test_capture_off_stores_nothing_and_replays_nothing() -> None:
    rows = {r["mode"]: r for r in V.capture_report(V.sample_records(), V.SAMPLE_TEXTS)}
    assert rows["off"]["stored"] == 0 and rows["off"]["replayable"] == 0


def test_capture_has_no_middle_position() -> None:
    """**这个旋钮没有中间档**：能回放的条数与盘上留下的识别码同时变。"""
    rows = V.capture_report(V.sample_records(), V.SAMPLE_TEXTS)
    assert len(rows) == 2


def test_audit_entries_without_a_purpose_are_counted() -> None:
    a = V.access_tally(V.SAMPLE_ACCESS)
    assert a["blank_purpose"] == 4 and abs(a["blank_rate"] - 1 / 3) < 1e-9


def test_audit_record_leaks_identifiers_itself() -> None:
    a = V.access_tally(V.SAMPLE_ACCESS)
    assert a["leaked_hits"] == 3


def test_audit_tally_on_an_empty_log() -> None:
    a = V.access_tally(())
    assert a["entries"] == 0 and a["blank_rate"] == 0.0 and a["leaked_hits"] == 0
