"""`app/drill.py` 的用例：**演练的产物不是「通过」，是一张写着发现了什么的清单。**

两条断言撑起这一块：越接近「真的坏」发现越多（3／5／8／11），
以及发现里最贵的一类是「文档里没写」——它等于「只有人知道」。
"""
from __future__ import annotations

from app import drill as D


def test_four_kinds_of_drill() -> None:
    assert len(D.DRILLS) == 4
    assert [d[0] for d in D.DRILLS] == [
        "桌面推演", "注入一个故障（测试环境）", "真停一个依赖（生产 30 秒）", "恢复演练（切到备份并恢复）"]


def test_each_drill_says_where_it_breaks() -> None:
    """**「它坏在哪」是四种演练的分界线**：从「什么都不坏」到「坏的是恢复路径本身」。"""
    assert D.DRILLS[0][1].startswith("什么也不坏")
    assert "测试环境" in D.DRILLS[1][1]
    assert "生产" in D.DRILLS[2][1]
    assert "恢复路径" in D.DRILLS[3][1]


def test_the_closer_to_real_breakage_the_more_it_finds() -> None:
    counts = [d[3] for d in D.DRILLS]
    assert counts == [3, 5, 8, 11]
    assert all(counts[i] < counts[i + 1] for i in range(3))


def test_the_restore_drill_is_the_richest_one() -> None:
    """**恢复那条路平时根本没人走**——所以它是发现最多的一档。"""
    assert D.DRILLS[3][3] == max(d[3] for d in D.DRILLS)
    assert "没人走" in D.DRILLS[3][2]


def test_the_table_has_six_columns_matching_the_prose() -> None:
    assert all(len(row) == 6 for row in D.drill_table())


def test_the_undocumented_share_is_the_product_of_a_drill() -> None:
    """**8 条里 7 条是「文档里没写」（87.5%）**——不是「通过／不通过」。"""
    assert D.undocumented_share() == (7, 8, 87.5)


def test_the_share_is_counted_from_the_list_not_declared() -> None:
    rows = D.redis_findings()
    missing = [r for r in rows if "没写" in r[3]]
    assert len(missing) == D.undocumented_share()[0]
    assert all("写了" not in r[3] or "没写" in r[3] for r in missing)


def test_every_finding_has_a_category_and_an_owner() -> None:
    for row in D.redis_findings():
        assert row[1] in {"代码", "配置", "监控", "流程", "文档"}
        assert row[2] in {"高", "中", "低"}
        assert row[4]


def test_the_findings_split_across_four_kinds_of_owner() -> None:
    cats = {r[1] for r in D.redis_findings()}
    assert "代码" in cats and "配置" in cats and "监控" in cats and "流程" in cats


def test_the_panel_that_only_looks_at_5xx_shows_up_as_a_finding() -> None:
    row = [r for r in D.redis_findings() if r[1] == "监控" and "面板" in r[0]][0]
    assert "SLI 表" in row[3]


def test_the_severity_is_not_the_same_as_the_owner() -> None:
    """「值班不知道该找谁」是流程问题而严重度是「高」——**分类与严重度是两栏**。"""
    row = [r for r in D.redis_findings() if r[0].startswith("值班")][0]
    assert (row[1], row[2]) == ("流程", "高")


def test_a_finding_that_was_already_written_down_exists() -> None:
    """清单里要有一条「写了」——**否则「87.5% 没写」这个数就不是量出来的**。"""
    assert any("写了（" in r[3] for r in D.redis_findings())


def test_the_drill_table_percentages_are_ratios_not_counts() -> None:
    rows = D.drill_table()
    assert [r[4] for r in rows] == ["67%", "60%", "75%", "82%"]
    assert rows[3][3] == "9 条" and rows[3][4] == "82%"
