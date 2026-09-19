# tests/test_registry.py —— 不需要密钥、不联网：内容戳、标签、回滚、三条线的 diff
"""这一份测的是 7.3 前半段的契约。六组：

1. **内容戳**：只由内容定——改一个字就变、换行/行尾空格/配置键序不变；
   **同内容连续保存不长版本**，而「把旧内容拿回来」要长版本（戳回到从前、号往前走）；
2. **版本是冻结的**：版本一旦存在，它的文本、配置、戳都不再改；
3. **标签**：一个标签只指一版，挪标签就是一次发布、必须留审计；
   原地不动不写流水；受保护的标签只有 admin／owner 挪得动；
4. **回滚**：把标签挪回去，**一版都不删**；到第一版之前要报错，不悄悄停下；
5. **diff 三条线**：文本行、变量、配置——只比文本的 diff 会漏掉后两条；
6. **静默漂移与失效线**：现场与标签那一版对不上要报，并说清那个戳是哪一版或不在表里；
   过了 `ends_by` 的实验要被点出来。
"""
from dataclasses import FrozenInstanceError

from app import registry as R


def _raises(exc, fn) -> bool:
    """`fn` 是不是抛了 `exc`。**本树不依赖 pytest**（`check_runnable` 直接调这些函数），
    所以「该不该报错」这一类断言也要自已写——但写出来就更清楚了：报错也是契约。"""
    try:
        fn()
    except Exception as err:               # noqa: BLE001 —— 夹具就是要在意异常类型
        return isinstance(err, exc)
    return False


def test_stamp_ignores_formatting_and_key_order():
    """换行符、行尾空格、配置键序都不是内容——**否则在 Windows 上编辑一次就多一个版本**。"""
    base = R.stamp(R.V3_TEXT, {"temperature": 0.2, "max_tokens": 512})
    assert base == R.stamp(R.V3_TEXT.replace("\n", "\r\n"), {"temperature": 0.2, "max_tokens": 512})
    assert base == R.stamp("\n".join(x + "   " for x in R.V3_TEXT.split("\n")),
                           {"max_tokens": 512, "temperature": 0.2})
    assert base == R.stamp(R.V3_TEXT, {"temperature": 0.2, "max_tokens": 512})


def test_one_character_moves_the_stamp_both_ways():
    """改一个字就变，改回来又一样——「按内容」的两个方向。"""
    base = R.stamp(R.V3_TEXT)
    assert R.stamp(R.V3_TEXT.replace("只", "仅")) != base
    assert R.stamp(R.V3_TEXT.replace("只", "仅").replace("仅", "只")) == base


def test_config_is_part_of_the_content():
    """文本一字未动、配置变了 → 内容变了。**只比文本的版本表会说「没变」。**"""
    assert R.stamp(R.V3_TEXT, {"temperature": 0.2}) != R.stamp(R.V3_TEXT, {"temperature": 0.9})


def test_identical_content_does_not_grow_a_version():
    reg = R.sample_registry()
    version, created = reg.save("zhizhou-support", R.V3_TEXT, dict(R.V4_CONFIG))
    assert created is False and version.number == 4
    assert len(reg.versions["zhizhou-support"]) == 4


def test_returning_to_earlier_content_grows_a_version_with_the_old_stamp():
    """回滚要留痕：号往前走、戳回到从前的那一份。"""
    reg = R.sample_registry()
    version, created = reg.save("zhizhou-support", R.V1_TEXT, {"temperature": 0.2, "max_tokens": 512})
    assert created is True and version.number == 5
    assert version.stamp == reg.by_number("zhizhou-support", 1).stamp
    assert reg.number_of("zhizhou-support", version.stamp) == 1


def test_versions_are_frozen():
    """版本一旦存在就不该再改：改内容要新开一版（否则内容戳会指向两份东西）。"""
    reg = R.sample_registry()
    version = reg.by_number("zhizhou-support", 2)
    assert _raises(FrozenInstanceError, lambda: setattr(version, "text", "改一下试试"))
    assert version.text == R.V2_TEXT


def test_labels_point_at_exactly_one_version_each():
    reg = R.sample_registry()
    reg.set_label("zhizhou-support", "production", 4, actor="admin")
    assert reg.label_number("zhizhou-support", "production") == 4
    assert reg.label_number("zhizhou-support", "latest") == 2      # 标签彼此独立
    assert reg.holders("production") == {"zhizhou-support": 4}


def test_moving_a_label_is_audited_and_in_place_moves_are_not():
    reg = R.sample_registry()
    before = len(reg.audit)
    reg.set_label("zhizhou-support", "production", 3, actor="admin")
    assert len(reg.audit) == before + 1
    assert "从第 2 版挪到第 3 版" in reg.audit[-1]
    reg.set_label("zhizhou-support", "production", 3, actor="admin")
    assert len(reg.audit) == before + 1                            # 原地不动不写流水


def test_protected_label_needs_a_privileged_actor():
    reg = R.sample_registry()
    assert _raises(PermissionError,
                   lambda: reg.set_label("zhizhou-support", "production", 4, actor="member"))
    reg.set_label("zhizhou-support", "production", 4, actor="owner")     # 不抛就是通过
    reg.set_label("zhizhou-support", "canary", 3, actor="member")        # 非保护标签谁都动得了


def test_rollback_moves_the_label_back_and_deletes_nothing():
    reg = R.sample_registry()
    reg.set_label("zhizhou-support", "production", 4, actor="admin")
    assert reg.rollback("zhizhou-support", actor="admin") == 3
    assert len(reg.versions["zhizhou-support"]) == 4
    assert reg.get("zhizhou-support").number == 3


def test_rollback_and_lookup_errors_are_explicit():
    reg = R.sample_registry()
    assert reg.rollback("zhizhou-support") == 1          # 第 2 版回得到第 1 版
    assert _raises(LookupError, lambda: reg.rollback("zhizhou-support"))   # 第 1 版前面没有了
    assert _raises(LookupError, lambda: reg.label_number("zhizhou-support", "不存在"))
    assert _raises(LookupError,
                   lambda: reg.set_label("zhizhou-support", "canary", 99, actor="admin"))
    assert _raises(LookupError, lambda: reg.label_number("别的提示词"))


def test_rollback_at_the_first_version_raises_instead_of_stopping():
    reg = R.Registry(versions={"x": R.sample_registry().versions["zhizhou-support"]},
                     labels={"x": {"production": 1}})
    assert _raises(LookupError, lambda: reg.rollback("x"))


def test_diff_reports_three_lanes():
    """变量改名落在「变量」那条线上，换配置落在「配置」那条线上。"""
    reg = R.sample_registry()
    name = "zhizhou-support"
    rename = reg.diff(reg.by_number(name, 2), reg.by_number(name, 3))
    assert rename.vars_added == ("query",) and rename.vars_removed == ("question",)
    assert rename.config_changed == () and len(rename.silent_risk()) == 2
    config = reg.diff(reg.by_number(name, 3), reg.by_number(name, 4))
    assert not config.lines_added and not config.lines_removed
    assert config.config_changed == ("temperature",) and config.same_stamp is False


def test_diff_of_a_version_with_itself_is_silent():
    reg = R.sample_registry()
    same = reg.diff(reg.by_number("zhizhou-support", 3), reg.by_number("zhizhou-support", 3))
    assert same.same_stamp is True and same.silent_risk() == []


def test_placeholders_are_ordered_and_deduped():
    assert R.placeholders("{{b}} {{a}} {{b}}") == ("b", "a")
    assert R.placeholders("{{ a }}") == R.placeholders("{{a}}")
    assert R.placeholders("你好") == ()


def test_drift_is_silent_only_when_the_live_content_matches_the_label():
    reg = R.sample_registry()
    config = {"temperature": 0.2, "max_tokens": 512}
    assert reg.drift("zhizhou-support", R.V2_TEXT, config) is None
    assert reg.drift("zhizhou-support", R.V2_TEXT, {"temperature": 0.5, "max_tokens": 512}) is not None


def test_drift_says_where_the_live_content_came_from():
    """两种漂移要分得开：**表里有这个戳**（有人在用候选版）与**表里没有**（有人手改过）。"""
    reg = R.sample_registry()
    config = {"temperature": 0.2, "max_tokens": 512}
    assert "第 3 版" in reg.drift("zhizhou-support", R.V3_TEXT, config)
    assert "不在注册表里" in reg.drift("zhizhou-support", R.V3_TEXT.replace("只", "仅"), config)


def test_alias_conflicts_compare_stamps_not_numbers():
    """同名同号而内容不同：**版本号会骗人，内容戳不会**。"""
    bad = R.alias_conflicts(R.sample_registry(), R.sample_twin(), "zhizhou-support")
    assert len(bad) == 2 and all("第 " in note for note in bad)
    assert R.alias_conflicts(R.sample_registry(), R.sample_registry(), "zhizhou-support") == []
    assert R.alias_conflicts(R.sample_registry(), R.Registry(), "zhizhou-support") == []


def test_expired_experiments_are_reported():
    """没有失效线的实验会永远挂着，所以 `ends_by` 是必填字段、且要被点出来。"""
    records = R.sample_experiments()
    assert [e.key for e in R.expired_experiments(records, "2026-09-19")] == ["support-v3-rename"]
    assert R.expired_experiments(records, "2026-09-01") == []
    assert records[0].expired("2026-09-25") is False and records[0].expired("2026-09-26") is True
