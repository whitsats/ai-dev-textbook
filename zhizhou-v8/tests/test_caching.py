"""`app/caching.py` 的用例：命中哪一条、靠哪条规则、不可改、清理，以及产物的搬运。"""
from __future__ import annotations

from app import caching as K

ROWS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("A", "feat/rag", "pip-3.12-cccc", ()),
    ("B", "feat/rag", "pip-3.12-dddd", ("pip-3.12-", "pip-")),
    ("C", "main", "pip-3.11", ("pip-3.12-",)),
    ("D", "main", "pip-3.12-e500", ("pip-",)),
    ("E", "feat/rag", "pip-3.11-aaaa", ()),
    ("F", "main", "pip-3.12-cccc", ()),
)


def _hit(tag: str) -> dict:
    _, branch, key, rk = next(r for r in ROWS if r[0] == tag)
    return K.restore(key, rk, branch=branch)


def test_an_exact_match_on_the_same_branch_is_the_only_cache_hit() -> None:
    r = _hit("A")
    assert r["cache_hit"] is True and r["rule"] == "精确匹配 key @feat/rag"


def test_a_restore_key_restores_the_files_while_cache_hit_stays_false() -> None:
    """官方：`cache-hit` 只在 exact 匹配时为真——而前缀命中会真的恢复文件。"""
    r = _hit("B")
    assert r["matched"] == "pip-3.12-cccc" and r["cache_hit"] is False


def test_the_keys_own_partial_match_runs_before_the_restore_keys() -> None:
    r = _hit("C")
    assert r["rule"].startswith("key 的部分匹配")
    assert len(r["tries"]) == 2, "只试了两步：写的那条 restore-key 根本没轮到"


def test_a_partial_match_picks_the_most_recently_created_entry() -> None:
    r = _hit("D")
    assert r["matched"] == "pip-3.12-bbbb" and r["cache_hit"] is False


def test_cache_sharing_across_branches_is_one_way() -> None:
    outward = _hit("E")
    inward = _hit("F")
    assert outward["matched"] == "pip-3.11-aaaa" and outward["scope"] == "main"
    assert outward["cache_hit"] is False, "跨分支命中也是 cache-hit＝false"
    assert inward["matched"] is None, "默认分支看不到子分支建的缓存"


def test_six_rows_yield_exactly_one_true_cache_hit() -> None:
    assert sum(1 for tag in "ABCDEF" if _hit(tag)["cache_hit"]) == 1


def test_an_exact_match_reports_only_one_try() -> None:
    assert len(_hit("A")["tries"]) == 1
    assert len(_hit("F")["tries"]) == 4


def test_seven_days_without_access_is_a_silent_eviction() -> None:
    dead = [e.key for e in K.STORE if not K.alive(e)]
    assert dead == ["pip-3.9-aaaa", "wheel-ubuntu-aaaa"]
    assert K.alive(K.STORE[0]), "6 天前访问过的那条还活着"


def test_an_existing_cache_cannot_be_rewritten_only_rekeyed() -> None:
    seq = K.save_sequence((("pip-cache", 180_000), ("pip-cache", 260_000),
                           ("pip-cache", 310_000)))
    assert seq[0]["saved"] is True
    assert seq[1]["saved"] is False and seq[2]["saved"] is False
    assert seq[2]["held_kb"] == 180_000, "缓存里留的还是第一份"


def test_a_static_cache_key_keeps_looking_like_a_hit() -> None:
    assert K.restore("pip-cache", branch="main", store=K.STORE)["matched"] is None
    seq = K.save_sequence((("pip-cache", 180_000), ("pip-cache", 260_000),
                           ("pip-cache", 310_000)))
    assert all("内容不可改" in row["why"] for row in seq[1:])


def test_a_fingerprinted_key_saves_every_time() -> None:
    seq = K.save_sequence((("pip-3.12-h1", 180_000), ("pip-3.12-h2", 260_000)))
    assert [row["saved"] for row in seq] == [True, True]


def test_the_ten_gib_limit_evicts_oldest_last_access_first() -> None:
    free, evicted = K._evict(K.MONOREPO, 0)
    assert evicted == ("gradle", "cargo-registry")
    assert free > 0
    assert K.LIMIT_KB // 1024 == 10_240


def test_every_monorepo_entry_is_within_seven_days_so_that_rule_does_not_apply() -> None:
    assert all(K.alive(e) for e in K.MONOREPO)
    assert sum(e.kb for e in K.MONOREPO) > K.LIMIT_KB


def test_needs_is_what_makes_an_artifact_reachable() -> None:
    assert not K.fetch(K.REPORT, needs=("lint",))["ok"]
    got = K.fetch(K.REPORT, needs=("lint", "test"))
    assert got["ok"] and got["dir"] == "test-report" and len(got["files"]) == 3


def test_artifacts_are_immutable_so_the_name_has_to_change() -> None:
    assert not K.reupload(("test-report",), "test-report")["saved"]
    assert K.reupload(("test-report",), "test-report-v2")["saved"]


def test_a_digest_mismatch_is_a_warning_not_a_failure() -> None:
    v = K.verify(K.REPORT, tampered=("report/junit.xml",))
    assert v["match"] is False and v["level"] == "warning" and v["green"] is True


def test_a_clean_artifact_produces_no_message_at_all() -> None:
    v = K.verify(K.REPORT)
    assert v["match"] is True and v["level"] == "—"
