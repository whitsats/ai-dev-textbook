"""向量索引：**三种，用同一份向量、同一批查询摆在一起比**。

为什么要在正文里手写它们，而不是装一个 `faiss`／连一个 Milvus 就完事？
因为本章要讲的那句结论不是「有哪几种索引」，而是**「索引是拿召回换速度，而换率是可量的」**。
拿现成的库跑，得到的是一串读数；自己写一遍，才知道那串读数里哪一项是结构决定的、
哪一项是实现决定的（例如：桶数是配置，**桶内的打分口径**才是结构）。

三种：

- `ExactIndex`：暴力精确。它不是拿来做产品的，它是**召回率的标尺**——
  没有它，就没法说「IVF 丢了多少」。
- `IVFIndex`：倒排文件。k-means 分桶 ＋ 只扫 `nprobe` 个最近桶。
  这是 Milvus 的 `IVF_FLAT`／`IVF_SQ8` 那一族的结构。
- `PQIndex`：乘积量化。把 d 维切成 m 段、每段只存一个质心编号——
  **内存从 `4 × d` 字节降到 `m` 字节**，代价是每段只能近似。这是 `IVF_PQ` 里 PQ 那一半。

三者的向量都假定**已经归一化**：归一化之后内积就等于余弦（`embed.py` 里可测），
所以打分那一步统一用点积。这个前提很重要——忘了它，`COSINE` 与 `IP` 就会被混着用。
"""
from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.embed import DimensionMismatch, dot, normalize


@dataclass
class Hit:
    """一条命中。`score` 的含义随度量不同而不同，所以它旁边永远带着 `metric`。"""

    row: int
    score: float


def _as_matrix(vectors: Sequence[Sequence[float]]) -> list[list[float]]:
    if not vectors:
        return []
    dim = len(vectors[0])
    for v in vectors:
        if len(v) != dim:
            raise DimensionMismatch(f"这一批向量自己就不齐：{len(v)} vs {dim}")
    return [list(v) for v in vectors]


def _kmeans(vectors: list[list[float]], k: int, *, iters: int = 12,
            seed: int = 0) -> list[list[float]]:
    """极简 k-means。**`seed` 固定**——索引的读数必须可复现，否则「另一天跑出来不一样」。
    它不追求收敛到全局最优：分桶只要「邻近的向量更可能落在同一个桶」，不需要最优划分。
    """
    rng = random.Random(seed)
    k = min(k, len(vectors))
    centers = [list(v) for v in rng.sample(vectors, k)]
    for _ in range(iters):
        buckets: list[list[list[float]]] = [[] for _ in range(k)]
        for v in vectors:
            best = max(range(k), key=lambda c: dot(v, centers[c]))
            buckets[best].append(v)
        moved = False
        for i, b in enumerate(buckets):
            if not b:
                continue                      # 空桶保持原样：**不重播种子**，免得读数飘
            mean = [sum(col) / len(b) for col in zip(*b)]
            new = normalize(mean)
            if any(abs(x - y) > 1e-12 for x, y in zip(new, centers[i])):
                moved = True
            centers[i] = new
        if not moved:
            break
    return [normalize(c) for c in centers]


class BaseIndex:
    """索引的公共部分：存向量、查维度、算召回。**这三个类共享它，是为了让差异只剩结构。**"""

    kind = "base"
    metric = "ip"

    def __init__(self, vectors: Sequence[Sequence[float]]) -> None:
        self.vectors = _as_matrix(vectors)
        self.dim = len(self.vectors[0]) if self.vectors else 0

    def __len__(self) -> int:
        return len(self.vectors)

    def _check(self, query: Sequence[float]) -> list[float]:
        q = list(query)
        if self.dim and len(q) != self.dim:
            # 素材里的头号排障条目就是它：**Collection 的 dimension 必须与嵌入模型一致**。
            # 所以这里不静默补齐、也不截断，直接报错——静默补齐会让「搜不到」变成一次无痕事故。
            raise DimensionMismatch(
                f"查询向量 {len(q)} 维，索引是 {self.dim} 维——"
                f"换嵌入模型之后必须重建索引，不能只改配置")
        return normalize(q)

    def search(self, query: Sequence[float], k: int = 3) -> list[Hit]:  # pragma: no cover
        raise NotImplementedError

    def footprint(self) -> dict:
        """内存账。**PQ 的价值全在这一个数上**，所以每个索引都必须能报出它。"""
        n = len(self.vectors)
        return {"kind": self.kind, "n": n, "dim": self.dim,
                "bytes": n * self.dim * 4, "bytes_per_vector": self.dim * 4}


class ExactIndex(BaseIndex):
    """暴力精确检索。`O(n·d)`，但**它是唯一能给出「正确答案」的那一个**。"""

    kind = "exact"

    def search(self, query: Sequence[float], k: int = 3) -> list[Hit]:
        q = self._check(query)
        scored = [(i, dot(q, v)) for i, v in enumerate(self.vectors)]
        scored.sort(key=lambda t: (-t[1], t[0]))     # 同分按序号，保证结果稳定
        return [Hit(i, round(s, 6)) for i, s in scored[:k]]


class IVFIndex(BaseIndex):
    """倒排文件索引：`nlist` 个桶，查询只扫 `nprobe` 个最近的桶。

    **`nprobe` 就是本章那个「召回换延迟」的旋钮**：它一变大，召回趋近精确、
    延迟线性上升。`nprobe == nlist` 时它就是精确检索——这一条也是可测的，
    而且它顺带证明了 IVF 没有「丢信息的结构缺陷」，丢的是**没扫到的那部分**。
    """

    kind = "ivf"

    def __init__(self, vectors: Sequence[Sequence[float]], *, nlist: int = 8,
                 nprobe: int = 1, seed: int = 0) -> None:
        super().__init__(vectors)
        self.nlist = max(1, min(nlist, max(1, len(self.vectors))))
        self.nprobe = max(1, min(nprobe, self.nlist))
        self.centers = _kmeans(self.vectors, self.nlist, seed=seed) if self.vectors else []
        self.buckets: list[list[int]] = [[] for _ in self.centers]
        for i, v in enumerate(self.vectors):
            self.buckets[self._nearest_center(v)].append(i)

    def _nearest_center(self, v: Sequence[float]) -> int:
        return max(range(len(self.centers)), key=lambda c: dot(v, self.centers[c]))

    def search(self, query: Sequence[float], k: int = 3) -> list[Hit]:
        q = self._check(query)
        order = sorted(range(len(self.centers)), key=lambda c: -dot(q, self.centers[c]))
        probed = order[:self.nprobe]
        scored = [(i, dot(q, self.vectors[i]))
                  for b in probed for i in self.buckets[b]]
        scored.sort(key=lambda t: (-t[1], t[0]))
        return [Hit(i, round(s, 6)) for i, s in scored[:k]]

    def footprint(self) -> dict:
        base = super().footprint()
        base.update({"nlist": self.nlist, "nprobe": self.nprobe,
                     "bucket_sizes": [len(b) for b in self.buckets],
                     "centroids_bytes": len(self.centers) * self.dim * 4})
        return base


class PQIndex(BaseIndex):
    """乘积量化：d 维切成 `m` 段，每段用它最近的质心编号代替。

    内存从 `4 × d` 字节降到 `m` 字节——**这就是「压缩率」的全部来源**，
    而代价是**每段一次近似**：`m` 越小压得越狠、也糊得越厉害。
    查询时把查询向量本身按段替换成质心（ADC，非对称距离计算）后做点积。
    """

    kind = "pq"

    def __init__(self, vectors: Sequence[Sequence[float]], *, m: int = 4,
                 ksub: int = 16, seed: int = 0) -> None:
        super().__init__(vectors)
        if self.dim and self.dim % m:
            raise ValueError(f"维度 {self.dim} 不能被 m={m} 整除——PQ 要按段切，不能切出半段")
        self.m = m
        self.ksub = min(ksub, max(1, len(self.vectors)))
        self.codebooks: list[list[list[float]]] = []
        self.codes: list[list[int]] = []
        seg = self.dim // m if m else 0
        for s in range(m):
            block = [v[s * seg:(s + 1) * seg] for v in self.vectors]
            book = _kmeans(block, self.ksub, seed=seed + s)
            self.codebooks.append(book)
        for v in self.vectors:
            code = []
            for s in range(m):
                seg_v = v[s * seg:(s + 1) * seg]
                code.append(max(range(len(self.codebooks[s])),
                                key=lambda c: dot(seg_v, self.codebooks[s][c])))
            self.codes.append(code)

    def _approx(self, vec: Sequence[float]) -> list[float]:
        seg = self.dim // self.m
        out: list[float] = []
        for s in range(self.m):
            out += list(self.codebooks[s][max(
                range(len(self.codebooks[s])),
                key=lambda c: dot(list(vec[s * seg:(s + 1) * seg]), self.codebooks[s][c]))])
        return out

    def search(self, query: Sequence[float], k: int = 3) -> list[Hit]:
        q = self._approx(self._check(query))
        scored = [(i, dot(q, self._approx(v))) for i, v in enumerate(self.vectors)]
        scored.sort(key=lambda t: (-t[1], t[0]))
        return [Hit(i, round(s, 6)) for i, s in scored[:k]]

    def footprint(self) -> dict:
        base = super().footprint()
        base.update({"m": self.m, "ksub": self.ksub,
                     "bytes": len(self.vectors) * self.m,
                     "bytes_per_vector": self.m})
        return base


def recall_at_k(index: BaseIndex, truth: Sequence[Sequence[int]], queries,
                k: int = 3) -> float:
    """**召回率的分母是「精确检索给出的前 k 条」**，不是「人工标注的正确答案」。

    两者不是一回事：这里量的是「索引丢了多少」，所以标尺必须是同一份向量上的暴力检索。
    章节里凡是提到「召回率」，口径都是这一个。
    """
    if not queries:
        return 1.0
    hit = 0
    for q, want in zip(queries, truth):
        got = [h.row for h in index.search(q, k)]
        hit += len(set(got) & set(want[:k]))
    return round(hit / (len(queries) * k), 4)


@dataclass
class Bench:
    """一次对照的读数。`metric` 与 `footprint` 一路带着走，防止两个索引的读数被混着念。"""

    kind: str
    n: int
    dim: int
    recall: float
    scanned: int
    footprint: dict = field(default_factory=dict)

    def line(self) -> str:
        return (f"{self.kind:<10} 召回@{'{k}'} {self.recall:>6.2f}  "
                f"扫描 {self.scanned:>3} 条  单条 {self.footprint.get('bytes_per_vector', 0):>5} 字节")
