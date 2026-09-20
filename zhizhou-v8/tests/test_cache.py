"""`app/cache.py` 的用例：失效的判据是「这一层之前的输入」，mtime 不算，`RUN` 不会自己过期。"""
from __future__ import annotations

from app import cache as K


def test_the_two_orderings_hold_the_same_three_steps() -> None:
    assert len(K.UNSORTED) == len(K.SORTED) == 3


def test_changing_the_source_invalidates_everything_when_it_sits_first() -> None:
    run = K.cache_run(K.UNSORTED, changed=(K.SRC_FILE,))
    assert run.rebuilt == 3 and run.first_miss == 0


def test_changing_the_source_invalidates_only_the_last_layer_when_it_sits_last() -> None:
    run = K.cache_run(K.SORTED, changed=(K.SRC_FILE,))
    assert run.rebuilt == 1 and run.first_miss == 2


def test_the_saving_comes_from_overlap_not_from_speed() -> None:
    fast = K.cache_run(K.SORTED, changed=(K.SRC_FILE,)).seconds(K.SORTED)
    slow = K.cache_run(K.UNSORTED, changed=(K.SRC_FILE,)).seconds(K.UNSORTED)
    assert slow > 30 * fast


def test_changing_the_dependency_file_is_expensive_in_both_orderings() -> None:
    for instrs in (K.UNSORTED, K.SORTED):
        assert K.cache_run(instrs, changed=(K.DEP_FILE,)).rebuilt == 3


def test_a_touched_file_does_not_invalidate_anything() -> None:
    """官方：修改时间（mtime）不参与缓存校验和。"""
    for instrs in (K.UNSORTED, K.SORTED):
        assert K.cache_run(instrs, touched=(K.SRC_FILE,)).rebuilt == 0


def test_touching_is_a_different_argument_from_changing() -> None:
    touched = K.cache_run(K.SORTED, touched=(K.SRC_FILE,)).rebuilt
    changed = K.cache_run(K.SORTED, changed=(K.SRC_FILE,)).rebuilt
    assert (touched, changed) == (0, 1)


def test_nothing_changed_means_everything_is_reused() -> None:
    """没有「这一层过期了」这种东西——`RUN apt-get update` 也不会自己重跑。"""
    run = K.cache_run(K.UNSORTED)
    assert run.reused == 3 and run.first_miss is None


def test_editing_an_instruction_rebuilds_from_that_point() -> None:
    run = K.cache_run(K.UNSORTED, edited=(1,))
    assert run.hits == (True, False, False) and run.first_miss == 1


def test_a_miss_never_turns_back_into_a_hit() -> None:
    for kwargs in ({"changed": ("app/main.py",)}, {"edited": (0,)}, {"changed": ("README.md",)}):
        run = K.cache_run(K.UNSORTED, **kwargs)
        first = run.first_miss
        if first is not None:
            assert all(not h for h in run.hits[first:])


def test_a_copy_without_files_never_invalidates() -> None:
    """只跑命令的那一层（`RUN`）不按文件算校验和——官方原话就是这么分工的。"""
    assert K.UNSORTED[1].files == () and K.UNSORTED[2].files == ()


def test_only_the_copy_layers_carry_files() -> None:
    assert all(not ins.files for ins in K.SORTED if not ins.text.startswith("COPY"))


def test_variants_cover_five_cases() -> None:
    rows = K.variants()
    assert len(rows) == 5 and rows[2]["case"].startswith("只碰一下")


def test_reused_plus_rebuilt_is_the_whole_file() -> None:
    run = K.cache_run(K.SORTED, changed=(K.SRC_FILE,))
    assert run.reused + run.rebuilt == len(K.SORTED)


def test_seconds_only_count_the_rebuilt_layers() -> None:
    assert K.cache_run(K.UNSORTED).seconds(K.UNSORTED) == 0
