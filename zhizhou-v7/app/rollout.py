"""分桶与放量：谁看哪一版，是**算出来的**，不是抽出来的。

「随机分流」这句话里藏着一个必须说清的区分：**随机 ≠ 每次都抽**。同一个用户第一次
落在候选组、第二次落在对照组，他看到的提示词会来回跳，而两组指标都会被他污染。
所以分桶的第一条性质不是「均匀」，是**稳定**：同一个 `(实验, 用户)` 永远算出同一个桶
——靠的是**哈希**，不是 `random()`。

三件事只有把哈希写出来才看得见：

1. **换哈希版本 ＝ 全部重新分桶**。官方 SDK 的哈希有 v1／v2 两版（v1 在并行实验下会偏，
   v2 用 32 位 FNV-1a 的两次哈希、取模 10,000），而**两版给出的桶不同**——
   所以「升级哈希版本」这件事对每一个正在跑的实验都等于**把它重开一次**；
   桶的粒度也跟着变：v1 是 1,000 个桶、v2 是 10,000 个——**粒度就是分辨率的下限**；
2. **桶是半开区间**（官方规范的 `inRange` 是 `n >= start && n < end`），
   而覆盖度是把**每一段各自乘一次**（于是权重 0.4／0.6、覆盖度 0.5 得到
   `[0, 0.2)` 与 `[0.4, 0.7)`——两段之间**留缝**）。缝隙里的用户**不在实验里**，
   而「不在实验里」与「进了对照组」在下游报表上长得一样；
3. **两个实验会互相污染**：同一批用户被两个「各自看不出问题」的分桶同时抽中，
   比如「改了提示词」与「换了模型」一起上——两组指标的差异就分不清是谁造成的。
   官方给两种隔离手段：**命名空间**（同一命名空间里两段不重叠 ＝ 互斥）
   与**过滤器**（按另一个哈希把用户排除在某些实验之外）。

`peeking()` 放在这一块，因为它回答的是「**什么时候敢下结论**」：固定视界的检验
多看一次就多一次假阳机会。官方文档的说法是「α 是 5%，但你偷看之后假阳率会远高于 5%」。
这里不引用它的数字，而是**把这件事算出来**：造几千次「其实没有效果」的实验，
看「每 n 条看一次」的假阳率是多少、连续看又是多少——两者与名义上的 5% 差多远，
是这一章唯一用模拟得出的读数，所以它必须带一个**蒙特卡洛误差**。
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import NormalDist

#: 两个哈希版本各自有多少个桶。**桶数就是分辨率的下限**：v1 是 1/1000、v2 是 1/10000。
HASH_BUCKETS = {1: 1000, 2: 10000}

#: 分桶的默认哈希版本（官方 SDK 的默认是 2；1 留着是为了说清「换版本＝重分桶」）。
DEFAULT_HASH = 2

#: 放量阶梯。最后一档是 100%——**那一档没有对照了**，这件事本身要写进口径。
STEPS = (0.01, 0.05, 0.25, 0.50, 1.00)


def fnv32a(text: str) -> int:
    """32 位 FNV-1a。官方的哈希函数就是它，**必须逐字节一致**（跨 SDK 的约定）。"""
    h = 0x811C9DC5
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def hash_bucket(seed: str, unit: str, version: int = DEFAULT_HASH) -> float:
    """把 `(实验, 单位)` 哈希成 `[0, 1)` 里的一个数。**同一个输入永远同一个数。**

    v2（官方现行）：`fnv32a(str(fnv32a(seed + unit))) % 10000 / 10000`；两次哈希是为了
    打散「前缀相同」的输入。v1（旧版）：`fnv32a(unit + seed) % 1000 / 1000`——
    它把 seed 拼在**后面**，于是并行跑的实验之间会相关，这正是它被换掉的原因。
    """
    if version == 2:
        return (fnv32a(str(fnv32a(seed + unit))) % HASH_BUCKETS[2]) / HASH_BUCKETS[2]
    if version == 1:
        return (fnv32a(unit + seed) % HASH_BUCKETS[1]) / HASH_BUCKETS[1]
    raise ValueError(f"未知的哈希版本：{version}（可选 {tuple(HASH_BUCKETS)}）")


def ranges(weights: tuple[float, ...], coverage: float = 1.0) -> tuple[tuple[float, float], ...]:
    """把权重与覆盖度翻成区间。**每一段各自乘一次覆盖度**（官方规范的 `getBucketRanges`）。

    权重和不为 1（或与分段数不符）时**退回等分**——不静默归一，因为「和不为 1」
    通常意味着配置写错了，而归一化之后那张表仍然自洽、错误从此隐身。
    """
    if not 0.0 <= coverage <= 1.0:
        raise ValueError(f"覆盖度要在 [0, 1]：{coverage}")
    n = len(weights)
    if n == 0:
        return ()
    if abs(sum(weights) - 1.0) > 1e-9:
        weights = tuple(1.0 / n for _ in range(n))
    out: list[tuple[float, float]] = []
    cumulative = 0.0
    for w in weights:
        out.append((round(cumulative, 10), round(cumulative + coverage * w, 10)))
        cumulative += w
    return tuple(out)


def in_range(x: float, interval: tuple[float, float]) -> bool:
    """**左闭右开**：`n >= start && n < end`。取闭区间会让相邻两段抢一个桶。"""
    return interval[0] <= x < interval[1]


def variant(exp_key: str, unit: str, weights: tuple[float, ...] = (0.5, 0.5), *,
            coverage: float = 1.0, hash_version: int = DEFAULT_HASH,
            seed: str | None = None) -> int:
    """这个单位在这次实验里进第几组。**落在缝里返回 `-1`**（＝不在实验里，不是对照组）。"""
    x = hash_bucket(seed or exp_key, unit, hash_version)
    for index, interval in enumerate(ranges(weights, coverage)):
        if in_range(x, interval):
            return index
    return -1


def namespace_position(unit: str, namespace: str) -> float:
    """命名空间里的位置。官方用 `"__"` 前缀 ＋ 哈希版本 1（**与实验自己的哈希无关**）。"""
    return hash_bucket("__" + namespace, unit, 1)


def in_namespace(unit: str, namespace: str, span: tuple[float, float]) -> bool:
    return in_range(namespace_position(unit, namespace), span)


def overlaps(x: float, span: tuple[float, float]) -> bool:
    """这一段是否与 `span` 相撞（同一命名空间里相撞 ＝ 两个人被同一个实验抽中）。"""
    return not (x < span[0] or x >= span[1])


@dataclass(frozen=True)
class Spec:
    """一次分流的规格：实验名、权重、覆盖度、哈希版本，外加可选的命名空间段。"""

    key: str
    weights: tuple[float, ...] = (0.5, 0.5)
    coverage: float = 1.0
    hash_version: int = DEFAULT_HASH
    seed: str | None = None
    namespace: tuple[str, float, float] | None = None

    def variant_of(self, unit: str) -> int:
        if self.namespace is not None:
            ns, lo, hi = self.namespace
            if not in_namespace(unit, ns, (lo, hi)):
                return -1
        return variant(self.key, unit, self.weights, coverage=self.coverage,
                       hash_version=self.hash_version, seed=self.seed)


def overlap(units: tuple[str, ...], a: Spec, b: Spec) -> dict:
    """两个实验在同一批单位上的实际交叠。**「看不出问题的两次分桶」是怎么互相污染的。**"""
    both = same = 0
    for unit in units:
        va, vb = a.variant_of(unit), b.variant_of(unit)
        if va >= 0 and vb >= 0:
            both += 1
            same += 1 if va == vb else 0
    return {"units": len(units), "both": both, "same_arm": same,
            "rate": (both / len(units)) if units else None,
            "same_rate": (same / both) if both else None}


@dataclass(frozen=True)
class SrmReport:
    """比例失衡（SRM）读数。**它量的不是效果，是「分桶有没有坏」。**"""

    counts: tuple[int, ...]
    expected: tuple[float, ...]
    chi2: float
    df: int
    p: float
    worst: float          # 偏差最大的那一组：(实际 − 期望) / 期望
    flag: bool            # 是否越过 0.001 这条线

    def lines(self) -> list[str]:
        return [f"各臂 {self.counts}（期望 {tuple(round(e, 1) for e in self.expected)}）",
                f"卡方 {self.chi2:.4f}（自由度 {self.df}）、p ＝ {self.p:.6g}；"
                f"最大相对偏差 {self.worst:+.4%}",
                f"判定：{'越线——先别读效果，先修分桶' if self.flag else '没越线'}"
                f"（这条线是本层声明的 0.001，不是官方给的数）"]


def srm(counts: tuple[int, ...], weights: tuple[float, ...] = (0.5, 0.5),
        alpha: float = 0.001) -> SrmReport:
    """比例失衡：**实际各臂的人数与声明的权重对不上**。

    这不是「效果不显著」，这是**分桶坏了**——读者必须先看这一栏再看效果。
    只支持 2 或 3 组（自由度 1 或 2），因为这两种的 p 值有闭式解
    （`erfc` 与 `exp(-x/2)`）；再多要上不完全伽马函数，本层不假装会算，
    直接**报错**——「算不出来」与「算出来是 0」必须分开，这是本书从 7.1 起的纪律。
    """
    if len(counts) != len(weights):
        raise ValueError("各臂人数与权重个数必须一样")
    if not 2 <= len(counts) <= 3:
        raise ValueError(f"本层只支持 2 或 3 组，收到 {len(counts)} 组"
                         "（再多需要不完全伽马函数——那是另一个模块的事）")
    total = sum(counts)
    expected = tuple(total * w for w in weights)
    chi2 = sum((c - e) ** 2 / e for c, e in zip(counts, expected) if e) if total else 0.0
    df = len(counts) - 1
    if df == 1:
        p = math.erfc(math.sqrt(chi2 / 2.0))          # 卡方 df=1 的闭式解
    else:
        p = math.exp(-chi2 / 2.0)                     # 卡方 df=2 的闭式解
    worst = max(((c - e) / e for c, e in zip(counts, expected) if e), default=0.0)
    return SrmReport(tuple(counts), expected, chi2, df, p, worst, bool(total) and p < alpha)


def resolution(n: int) -> float:
    """一格的粒度：`n` 次里数出 `k` 次，比例的最小非零变化是 `1/n`。"""
    if n <= 0:
        raise ValueError("样本量要是正数")
    return 1.0 / n


def min_detectable(n: int, p0: float = 0.2, se_multiple: float = 2.0) -> float:
    """两组各 `n` 次时能看出的**最小差距**（口径：两倍标准误，两组都按基线比例算）。"""
    if n <= 0:
        raise ValueError("样本量要是正数")
    return se_multiple * math.sqrt(2 * p0 * (1 - p0) / n)


def ladder(requests_per_day: int, *, steps: tuple[float, ...] = STEPS,
           p0: float = 0.2, target: int = 1000) -> list[dict]:
    """放量阶梯：每一档**能看见什么、看不清什么**。

    候选组的样本量 ＝ 一天流量 × 这一档的比例；而「能看见的最小差距」由它决定。
    于是前几档的用途就清楚了：它们**不是小步快跑**，是「发现崩溃」
    （错误率、格式坏掉、超时），因为质量上的差异在那点样本量下根本算不出来。
    最后一档（100%）**没有对照组**——那时只能与「发布前的历史」比，而那不是同一个对照。

    `days` 是「按这一档的比例，攒到 `target` 次候选样本要几天」——它把「等」这件事
    变成一个数：阶梯前几档等得起，第五档等不起（因为它已经不是实验了）。
    """
    rows: list[dict] = []
    for share in steps:
        n = int(requests_per_day * share)
        rows.append({
            "share": share, "candidate_n": n,
            "resolution": resolution(n) if n else None,
            "delta": min_detectable(n, p0) if n else None,
            "days": (target / n) if n else None,
            "has_control": share < 1.0,
        })
    return rows


def peeking(*, trials: int = 2000, n: int = 400, looks: tuple[int, ...] = (1, 5, 10, 20, 0),
            alpha: float = 0.05, seed: int = 20260919) -> dict:
    """偷看的代价：**名义 5%，实际是多少**。

    造 `trials` 次「两组其实一样」的实验（每一步都掷一个标准正态的增量，
    于是第 `n_j` 步的 z 统计量是 `S / √n_j`），记录「有几次**看过**的 z 越过临界值」。
    返回每一档的假阳率、蒙特卡洛误差，以及两参照：

    · `fixed`——只看一次（`k=1`），**它必须回到名义的 5%**，否则模拟本身写错了；
    · `independent` ——按「每次偷看都是一次独立检验」算的 `1 − (1−α)^k`。
      这个模型**是错的**（相邻两次看的 z 高度相关），但它给的是一个**上界**，
      而它比真值更常被人当成真值。

    **每一行用自己的一条随机流**（种子由 `seed` 与该行的观察点个数拼成），
    所以**把哪几行放在一起问，不影响任何一行的数**。这不是洁癖：第一版让所有行
    共用一条流，于是同一行在两次不同的调用里给出 0.4645 与 0.4860 两个值
    ——而正文只能引一个。**「可复算」这句话里含「与调用形状无关」。**
    """
    crit = NormalDist().inv_cdf(1 - alpha / 2)
    rows: list[dict] = []
    for k in looks:
        checkpoints = tuple(range(1, n + 1)) if k == 0 else \
            tuple(max(1, round(n * i / k)) for i in range(1, k + 1))
        rng = random.Random(f"{seed}:{n}:{len(checkpoints)}")
        hits = 0
        for _ in range(trials):
            total, idx = 0.0, 0
            for i in range(1, checkpoints[-1] + 1):
                total += rng.gauss(0.0, 1.0)
                if i == checkpoints[idx]:
                    if abs(total / math.sqrt(i)) >= crit:
                        hits += 1
                        break
                    idx += 1
                    if idx == len(checkpoints):
                        break
        rate = hits / trials
        rows.append({
            "looks": k, "checkpoints": len(checkpoints), "rate": rate,
            "mc_error": 1.96 * math.sqrt(max(rate * (1 - rate), 1e-12) / trials),
            "independent": 1 - (1 - alpha) ** len(checkpoints),
        })
    return {"alpha": alpha, "crit": crit, "trials": trials, "n": n, "rows": rows}


# ---------------------------------------------------------------- 样本

def sample_units(n: int = 200) -> tuple[str, ...]:
    """样本单位。**写死的**（`u001`…）——分桶必须可复算，所以单位也不能是随机生成的。"""
    return tuple(f"u{i:03d}" for i in range(1, n + 1))
