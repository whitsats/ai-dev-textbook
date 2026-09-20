"""`app/policy.py` 的用例：三道关各测各的、最小权限的两种落点、审计链的三种篡改。"""
from __future__ import annotations

from app import policy as P

NOW = 1_500.0


def _tok(scopes: tuple[str, ...], audience: str = P.CANONICAL_URI) -> P.Token:
    return P.Token("user-7", audience, scopes, 2_000.0)


def _call(tool: str, **args) -> P.Call:
    return P.Call("user-7", tool, args)


# ------------------------------------------------------------ 一、三道关

def test_missing_token_is_401() -> None:
    assert P.decide(_call("get_order", order_id="42"), None, NOW).code == "401"


def test_expired_token_is_401() -> None:
    t = P.Token("user-7", P.CANONICAL_URI, ("orders:read",), 1_000.0)
    assert P.decide(_call("get_order", order_id="42"), t, NOW).code == "401"


def test_wrong_audience_is_401() -> None:
    t = _tok(("orders:read",), audience="https://elsewhere/mcp")
    assert P.decide(_call("get_order", order_id="42"), t, NOW).code == "401"


def test_insufficient_scope_is_403_not_401() -> None:
    assert P.decide(_call("get_order", order_id="42"), _tok(("docs:read",)), NOW).code == "403"


def test_unknown_tool_is_403() -> None:
    assert P.decide(_call("nope"), _tok(("docs:read",)), NOW).code == "403"


def test_write_tool_needs_approval_not_allow() -> None:
    d = P.decide(_call("refund", order_id="42"), _tok(("orders:write:42",)), NOW)
    assert d.action == "approve" and d.code == "approve"


def test_data_plane_blocks_someone_elses_resource() -> None:
    d = P.decide(_call("get_order", order_id="99"), _tok(("orders:read",)), NOW)
    assert d.action == "deny" and "资源" in d.rule


def test_decision_carries_three_fields_not_a_bool() -> None:
    d = P.decide(_call("search_docs", q="x"), _tok(("docs:read",)), NOW)
    assert (d.action, d.code, d.rule) == ("allow", "200", "三道都过")


# ------------------------------------------------------------ 二、最小权限

def test_both_granularities_deny_three_of_three() -> None:
    split = P.least_privilege_split()
    assert all(v[0] == 3 for v in split.values())


def test_the_difference_is_which_layer_refuses() -> None:
    wide = P.least_privilege_split()["宽 scope（orders:read）"]
    narrow = P.least_privilege_split()["实例 scope（orders:read:42）"]
    assert wide[1] == 0 and wide[2] == 3
    assert narrow[1] == 3 and narrow[2] == 0


def test_instance_scope_allows_your_own_resource() -> None:
    assert P.decide(_call("get_order", order_id="42"), _tok(("orders:read:42",)), NOW).passed


def test_scope_forms_are_not_interchangeable_for_writes() -> None:
    assert P.TOOLS["refund"].write and not P.TOOLS["get_order"].write
    assert P.TOOLS["refund"].scope != P.TOOLS["search_docs"].scope


def test_twelve_calls_split_into_three_actions() -> None:
    counts = P.tally(P.run_calls())
    assert sum(counts.values()) == 12 and counts["approve"] == 2


# ------------------------------------------------------------ 三、审计链

def test_untouched_chain_verifies_clean() -> None:
    log = P.AuditLog()
    log.append({"action": "allow"})
    assert log.verify() == []


def test_delete_one_row_is_detected() -> None:
    log = P.AuditLog()
    for i in range(5):
        log.append({"i": i})
    del log.entries[2]
    assert log.verify()


def test_edit_one_field_is_detected() -> None:
    log = P.AuditLog()
    for i in range(5):
        log.append({"i": i})
    log.entries[3]["payload"]["i"] = 99
    assert log.verify()


def test_reorder_is_detected() -> None:
    log = P.AuditLog()
    for i in range(5):
        log.append({"i": i})
    log.entries[1], log.entries[2] = log.entries[2], log.entries[1]
    assert log.verify()


def test_plain_journal_detects_nothing() -> None:
    j = P.PlainJournal()
    for i in range(5):
        j.append({"i": i})
    del j.rows[2]
    j.rows[1]["payload"]["i"] = 99
    assert j.verify() == []


def test_digest_is_key_order_independent() -> None:
    assert P._digest("x", {"a": 1, "b": 2}) == P._digest("x", {"b": 2, "a": 1})


def test_digest_changes_with_previous_hash() -> None:
    assert P._digest("x", {"a": 1}) != P._digest("y", {"a": 1})
