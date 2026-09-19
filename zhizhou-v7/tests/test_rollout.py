# tests/test_rollout.py —— 不需要密钥、不联网：分桶、比例失衡、阶梯与偷看
"""这一份测的是 7.3 后半段的契约。六组：

1. **哈希**：同一个 `(实验, 单位)` 永远同一个桶、值落在 `[0, 1)`；两个哈希版本
   给出**不同的桶**（所以升级哈希版本＝重分桶）、未知版本要报错；
2. **区间**：左闭右开（相邻两段不会抢同一个桶）；覆盖度把每一段各自乘一次，
   于是**留缝**——缝里是 `-1`（不在实验里），不是第 0 组（对照组）；
   权重和不为 1 时退回等分，**不静默归一**；
3. **命名空间**：同一命名空间里两段不重叠 ＝ 互斥；不设命名空间时两个实验会盖住所有人；
4. **比例失衡**：它量的是「分桶坏没坏」——同样的偏差，样本越大越响；
   只支持 2／3 组（再多的 p 值没有闭式解，直接报错，不假装会算）；
5. **分辨率与可检测最小差异**：两个数一起看才知道这一档值不值得等；
6. **偷看**：只看一次回到名义值（锚）、看得越多假阳率越高、每行一条随机流所以
   与调用顺序无关、独立近似是个上界。
"""
from app import rollout as L


def _raises(exc, fn) -> bool:
    """`fn` 是不是抛了 `exc`（本树不依赖 pytest，报错也算契约的一部分）。"""
    try:
        fn()
    except Exception as err:               # noqa: BLE001
        return isinstance(err, exc)
    return False


def test_hash_is_stable_and_inside_the_unit_interval():
    units = L.sample_units()
    assert len({L.hash_bucket("e", "u007") for _ in range(10)}) == 1
    assert all(0.0 <= L.hash_bucket("e", u) < 1.0 for u in units)
    assert L.hash_bucket("a", "u007") != L.hash_bucket("b", "u007")   # 换个实验就换个桶


def test_hash_versions_disagree_and_the_unknown_one_raises():
    """换哈希版本 ＝ 全部重新分桶；这一步对正在跑的实验等于把它重开一次。"""
    units = L.sample_units()
    switched = sum(1 for u in units
                   if L.variant("e", u, (0.9, 0.1), hash_version=1)
                   != L.variant("e", u, (0.9, 0.1), hash_version=2))
    assert switched > 0
    assert L.HASH_BUCKETS == {1: 1000, 2: 10000}
    assert _raises(ValueError, lambda: L.hash_bucket("e", "u007", 3))


def test_ranges_are_half_open():
    assert L.in_range(0.5, (0.5, 1.0)) and not L.in_range(1.0, (0.5, 1.0))
    assert sum(1 for span in L.ranges((0.5, 0.5)) if L.in_range(0.5, span)) == 1


def test_coverage_leaves_gaps_and_a_gap_is_not_the_control_arm():
    assert L.ranges((0.4, 0.6), 0.5) == ((0.0, 0.2), (0.4, 0.7))
    units = L.sample_units()
    gaps = [u for u in units if L.variant("g", u, (0.4, 0.6), coverage=0.5) == -1]
    assert gaps and all(L.variant("g", u, (0.4, 0.6), coverage=0.5) == -1 for u in gaps)


def test_weights_that_do_not_sum_to_one_fall_back_to_equal_weights():
    """不静默归一：和不为 1 通常意味着配置写错了，而归一之后那张表仍然自洽、错误从此隐身。"""
    assert L.ranges((0.3, 0.3)) == L.ranges((0.5, 0.5))
    assert _raises(ValueError, lambda: L.ranges((0.5, 0.5), 1.5))


def test_renaming_the_experiment_reassigns_units():
    """名字是分桶输入的一部分：改名与换哈希版本是同一类动作。"""
    units = L.sample_units()
    before = [L.variant("support-v4-temp", u, (0.9, 0.1)) for u in units]
    after = [L.variant("support-v4-temp-v2", u, (0.9, 0.1)) for u in units]
    assert any(a != b for a, b in zip(before, after))


def test_namespace_makes_two_experiments_mutually_exclusive():
    units = L.sample_units()
    exclusive = L.overlap(units, L.Spec("a", namespace=("ns", 0.0, 0.5)),
                          L.Spec("b", namespace=("ns", 0.5, 1.0)))
    assert exclusive["both"] == 0
    assert L.overlap(units, L.Spec("a"), L.Spec("b"))["both"] == len(units)
    assert L.namespace_position("u007", "ns") == L.hash_bucket("__ns", "u007", 1)


def test_overlap_reports_both_the_rate_and_the_same_arm_rate():
    units = L.sample_units()
    report = L.overlap(units, L.Spec("a", (0.9, 0.1)), L.Spec("b", (0.9, 0.1)))
    assert report["rate"] == 1.0 and 0.6 < report["same_rate"] < 1.0


def test_srm_needs_a_big_sample_to_flag_a_small_deviation():
    """1% 的偏差：一万样本判不出来、百万样本一眼就红——**这条线的灵敏度随 n 长**。"""
    assert not L.srm((5050, 4950)).flag
    assert not L.srm((5100, 4900)).flag
    assert L.srm((505000, 495000)).flag
    assert L.srm((5050, 4950)).p > L.srm((50500, 49500)).p > L.srm((505000, 495000)).p


def test_srm_refuses_more_arms_than_it_can_compute():
    """算不出来与算出来是 0 必须分开——这一层不假装会算不完全伽马函数。"""
    assert _raises(ValueError, lambda: L.srm((1, 2, 3, 4)))
    assert _raises(ValueError, lambda: L.srm((1, 2), (0.5, 0.3, 0.2)))
    assert L.srm((4000, 3000, 3000), (1 / 3, 1 / 3, 1 / 3)).df == 2
    assert L.srm((0, 0)).flag is False


def test_resolution_and_min_detectable_move_in_opposite_directions():
    assert L.resolution(1000) == 0.001
    assert L.min_detectable(1000) > L.min_detectable(4000)
    assert _raises(ValueError, lambda: L.resolution(0))


def test_ladder_shows_what_each_step_can_see():
    rows = L.ladder(8000)
    assert tuple(r["share"] for r in rows) == (0.01, 0.05, 0.25, 0.50, 1.00)
    assert [r["has_control"] for r in rows] == [True, True, True, True, False]
    assert rows[0]["delta"] > 2 * rows[2]["delta"]
    assert all(abs(r["resolution"] - 1 / r["candidate_n"]) < 1e-12 for r in rows)


def test_peeking_anchor_returns_to_the_nominal_rate():
    """只看一次必须回到名义的 5%——**锚对了，别的行才可信**。"""
    row = L.peeking(trials=2000, n=400, looks=(1,))["rows"][0]
    assert abs(row["rate"] - 0.05) < 0.03
    assert row["checkpoints"] == 1


def test_peeking_grows_with_the_number_of_looks():
    rows = L.peeking(trials=2000, n=400, looks=(1, 5, 0))["rows"]
    one, five, continuous = rows
    assert one["rate"] < five["rate"] < continuous["rate"]
    assert continuous["rate"] > 3 * 0.05


def test_peeking_rows_do_not_depend_on_the_call_shape():
    """每行一条独立随机流：**「可复算」这句话里含「与调用形状无关」**。"""
    forward = {(r["looks"], r["checkpoints"]): r["rate"]
               for r in L.peeking(trials=300, n=400, looks=(0, 1))["rows"]}
    backward = {(r["looks"], r["checkpoints"]): r["rate"]
                for r in L.peeking(trials=300, n=400, looks=(1, 0))["rows"]}
    assert forward == backward


def test_independent_approximation_is_an_upper_bound():
    rows = L.peeking(trials=2000, n=400, looks=(1, 5, 20, 0))["rows"]
    assert all(r["independent"] >= r["rate"] for r in rows if r["checkpoints"] > 1)
    assert rows[-1]["independent"] > 0.99          # 连续看时它趋近 1：所以不能当结论用
    assert all(r["mc_error"] > 0 for r in rows)
