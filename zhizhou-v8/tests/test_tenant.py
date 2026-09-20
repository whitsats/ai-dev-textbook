"""`app/tenant.py` 的用例：**隔离的默认方向**，以及四种落点各自的漏法。"""
from __future__ import annotations

from app import tenant as T


def test_three_isolation_modes_each_answer_four_questions() -> None:
    assert len(T.ISOLATION_MODES) == 3
    for row in T.ISOLATION_MODES:
        assert len(row) == 5, row[0]


def test_isolation_strength_and_operating_cost_move_in_the_same_direction() -> None:
    """强度与代价同向：**这条是这一节的选型判据**——不会「又强又便宜」。"""
    strength = [row[1].count("**") for row in T.ISOLATION_MODES]
    assert strength == sorted(strength), "越往后那道门越硬"


def test_the_layer_table_and_the_answer_table_use_the_same_names() -> None:
    """两张表靠层名相认；名字漂一个字，`leak_table()` 会安静地少算一层。"""
    assert {a[0] for a in T.ANSWERS} == {w[0] for w in T.WHERE_LAYERS}


def test_application_layer_leaks_on_all_three_probes() -> None:
    app_layer = T.WHERE_LAYERS[0][0]
    probes = [p for p in T.probes() if p.layer == app_layer]
    assert len(probes) == 3
    assert all(p.is_leak for p in probes)


def test_the_row_policy_layer_leaks_on_none_of_them() -> None:
    rls = T.WHERE_LAYERS[2][0]
    assert [r[1] for r in T.leak_table() if r[0] == rls] == ["0 / 3"]


def test_the_row_policy_turns_a_missing_tenant_id_into_this_tenants_rows() -> None:
    """行策略兜住的是「少带条件」——它给的是本租户的行，不是报错。"""
    rls = T.WHERE_LAYERS[2][0]
    got = next(p for p in T.probes() if p.layer == rls and p.probe == "忘了带")
    assert got.outcome == "**看到本租户的行**"
    assert got.is_leak is False


def test_the_row_policy_answers_someone_elses_id_with_an_empty_set() -> None:
    """而「带了别人的」得到的是**空**：可用，只是没数据——这是另一种故障。"""
    rls = T.WHERE_LAYERS[2][0]
    got = next(p for p in T.probes() if p.layer == rls and p.probe == "带别人的")
    assert got.outcome == "**一行都看不到**"


def test_the_storage_layer_hides_two_kinds_of_failure_behind_one_parameter() -> None:
    """存储层：写错了是空、写漏了是漏——两类故障落在同一个参数上。"""
    storage = T.WHERE_LAYERS[3][0]
    rows = {p.probe: p for p in T.probes() if p.layer == storage}
    assert rows["忘了带"].is_leak is True
    assert rows["带别人的"].is_leak is True


def test_leak_counts_are_two_two_three_and_zero() -> None:
    assert [r[1] for r in T.leak_table()] == ["3 / 3", "2 / 3", "0 / 3", "2 / 3"]


def test_every_answer_cell_says_what_holds_it_up() -> None:
    for p in T.probes():
        assert p.why, f"{p.layer} × {p.probe}"


def test_the_vector_table_has_five_rows_and_each_names_a_ceiling() -> None:
    assert len(T.VECTOR_MODES) == 5
    for name, good, limit in T.VECTOR_MODES:
        assert limit, name


def test_partition_keys_ceiling_is_not_a_count_but_a_write_shape() -> None:
    """四级里只有它的天花板不是数量：**不支持批量写入**。"""
    pk = next(m for m in T.VECTOR_MODES if "partition key" in m[0])
    assert "不支持批量写入" in pk[2]


def test_the_choice_moves_with_tenant_count() -> None:
    assert T.vector_choice(8, False)[0].startswith("库级")
    assert T.vector_choice(60, False)[0].startswith("集合级 · 一租户一")
    assert T.vector_choice(5_000, False)[0].endswith("partition key")


def test_bulk_import_rules_out_partition_key_above_a_thousand_tenants() -> None:
    """两个输入都是产品决定：要批量导入时，那条限制会把 partition key 否掉。"""
    assert T.vector_choice(5_000, True)[0].startswith("集合级 · 一集合")


def test_each_choice_comes_with_a_reason() -> None:
    for tenants in (8, 60, 5_000):
        for bulk in (False, True):
            pick, why = T.vector_choice(tenants, bulk)
            assert pick and why
