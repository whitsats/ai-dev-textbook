"""`app/image.py` 的用例：层是只加的、四招各自的账、密钥三档留在哪里。"""
from __future__ import annotations

from app import image as I


# ------------------------------------------------------------ 一、层的模型

def test_every_step_becomes_a_layer() -> None:
    build = I.run(I.NAIVE)
    assert len(build.layers) == len(I.NAIVE.steps) == 6


def test_layer_size_is_added_bytes_plus_whiteouts() -> None:
    build = I.run(I.NAIVE)
    rm = build.layers[3]
    assert rm.whiteouts == 3 and rm.size_kb == 3 * I.WHITEOUT_KB


def test_deleting_does_not_shrink_the_image() -> None:
    build = I.run(I.NAIVE)
    assert build.image_kb - build.squashed_kb == build.wasted_kb == 107_003


def test_the_rm_layer_is_tiny_while_what_it_hides_is_not() -> None:
    build = I.run(I.NAIVE)
    assert build.layers[3].size_kb < build.wasted_kb / 1000


def test_visible_view_loses_what_a_later_layer_removed() -> None:
    build = I.run(I.NAIVE)
    assert "/app/.venv" not in build.live and "/root/.cache/pip" not in build.live


def test_metadata_layers_have_no_size() -> None:
    build = I.run(I.NAIVE)
    assert all(layer.size_kb == 0 for layer in build.layers_of("USER"))
    assert all(layer.size_kb == 0 for layer in build.layers_of("CMD"))


def test_squashed_equals_base_plus_visible() -> None:
    build = I.run(I.NAIVE)
    assert build.squashed_kb == build.script.base_kb + build.visible_kb


def test_image_is_always_heavier_than_the_squashed_view() -> None:
    for script in I.SCRIPTS:
        build = I.run(script)
        assert build.image_kb >= build.squashed_kb


def test_unknown_script_name_raises() -> None:
    try:
        I.build_of("nope")
        assert False, "未知剧本应当报错"
    except KeyError:
        pass


# ------------------------------------------------------------ 二、四招

def test_slimming_table_has_one_row_per_move_plus_the_combination() -> None:
    assert len(I.slimming_table()) == 5


def test_swapping_the_base_changes_no_layer() -> None:
    naive, slim = I.run(I.NAIVE), I.run(I.SLIM_BASE)
    assert naive.layers == slim.layers and naive.script.base_kb > slim.script.base_kb


def test_merging_runs_removes_the_waste_entirely() -> None:
    assert I.build_of("merged").wasted_kb == 0


def test_multistage_also_removes_the_waste() -> None:
    assert I.build_of("multistage").wasted_kb == 0


def test_dockerignore_does_not_touch_the_waste_account() -> None:
    """它减的是「根本没进来的东西」，而浪费账说的是「进来了却用不上」。"""
    assert I.build_of("ignored").wasted_kb == I.build_of("naive").wasted_kb - 15_000


def test_the_four_moves_do_not_add_up() -> None:
    base = I.run(I.NAIVE).image_kb
    saved = sum(r["saved_kb"] for r in I.slimming_table() if r["name"] != "final")
    assert I.build_of("final").image_kb != base - saved


def test_the_stacking_moves_beat_every_single_move() -> None:
    final = I.build_of("final").image_kb
    assert all(r["image_kb"] > final for r in I.slimming_table() if r["name"] != "final")


# ------------------------------------------------------------ 三、传输

def test_a_restamp_changes_only_the_layer_it_touches() -> None:
    a = I.run(I.FINAL)
    b = I.run(I.restamped(I.FINAL, path="/app/app", kb=1_300))
    tr = I.transfer_report(a, b)
    assert tr["changed"] == 1 and tr["same"] == 4


def test_the_layer_digest_carries_the_size() -> None:
    """只写路径不写体积的话，「改了一行源码」会被判成「没变」。"""
    a = I.run(I.FINAL)
    b = I.run(I.restamped(I.FINAL, path="/app/app", kb=1_300))
    assert a.layers[1].digest != b.layers[1].digest


def test_the_same_build_against_itself_transfers_nothing() -> None:
    a = I.run(I.FINAL)
    assert I.transfer_report(a, a)["changed"] == 0


def test_restamp_keeps_the_base_and_the_other_layers() -> None:
    b = I.restamped(I.FINAL, path="/app/app", kb=1_300)
    assert b.base_kb == I.FINAL.base_kb and len(b.steps) == len(I.FINAL.steps)


def test_pull_seconds_follow_the_link_speed() -> None:
    assert I.pull_seconds(25_000) == 1.0
    assert I.pull_seconds(25_000, mbps=50) == 0.5


# ------------------------------------------------------------ 四、密钥三档

def test_env_leaks_into_all_three_places() -> None:
    row = next(r for r in I.secret_ladder() if r["rung"] == "env")
    assert (row["config"], row["layer"], row["cache"]) == (True, True, True)
    assert row["leaks"] == 3


def test_arg_leaves_the_config_out_but_not_the_layer() -> None:
    row = next(r for r in I.secret_ladder() if r["rung"] == "arg")
    assert row["config"] is False and row["layer"] is True and row["leaks"] == 2


def test_secret_mount_leaves_nothing() -> None:
    row = next(r for r in I.secret_ladder() if r["rung"] == "secret")
    assert row["leaks"] == 0 and I.secret_visible_to("secret") == ()


def test_the_ladder_has_three_rungs() -> None:
    assert [r["rung"] for r in I.SECRET_RUNGS] == ["env", "arg", "secret"]


def test_only_the_first_rung_is_readable_by_anyone_who_pulls() -> None:
    assert len(I.secret_visible_to("env")) == 3
    assert len(I.secret_visible_to("arg")) == 2
