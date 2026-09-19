"""混合检索：**把两条路的「排名」合起来，而不是把它们的「分数」加起来。**

5.1–5.3 量出三条缺口，本章要救前两条：

| 缺口 | 5.1 实测 | 修在哪 |
| --- | --- | --- |
| 同义改写（字面零重合） | Q3 一片都召不回 | 本章：查询改写 |
| 近义替换 | 正确文档进不了前三（最高分落在错文档上） | 5.3 的向量 ＋ 本章的融合与重排 |
| 库里根本没有 | Q4 反而召回高分噪声 | 5.5 的拒答与阈值 |

三条设计决定，都不是「业界通常这么做」，而是本章要量的东西逼出来的：

1. **融合用 RRF（倒数排名融合），不用加权分数和。**
   两条路的分数**不在同一个刻度上**：BM25 是未归一的词频分（本章实测 Q1 在 30 上下），
   余弦是固定落在 `[-1, 1]` 的相似度。把两者相加，等于让 BM25 的单方面尺度决定排序，
   而那个尺度还会随语料与 query 长度漂。RRF 只看**名次**：

       RRF(片) = Σ 1 / (k + 名次)     （k 默认 60，是原论文里的经验值）

   代价也说清楚：**名次丢掉了「差距有多大」这一信息**——第一名领先第二名 10 分与领先 0.01 分，
   在 RRF 里一样。

2. **融合不会创造新信息。** 它是两条路结果的并集再排序：两条路都看不见的片，
   融合之后还是看不见。所以本章最重要的那条读数与直觉相反——
   **混合检索救不了 Q3**，真正救它的是查询改写。

3. **改写是唯一「造出新字面」的一环，也是唯一要多花一次模型调用的一环。**
   离线那一条用一张固定的同义表（确定、可复现），真机那一条把同一件事交给模型。
   两条路都要能跑，且**读数分开报**：改写表是本章的标尺，不是产品方案。
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.corpus import Chunk, NgramIndex, build_index
from app.embed import make_embedder
from app.vector_index import BaseIndex, ExactIndex

#: RRF 的平滑常数。**它是原论文的经验值，本树没有语料去调**——
#: 本章只量它「变大变小时排序怎么变」，不声称 60 是最优。
RRF_K = 60


@dataclass(frozen=True)
class Hit:
    """一条命中。**分数旁边永远带着 `source`**：

    BM25 的 12.4 与余弦的 0.62 不是同一种东西，脱掉来源就没法读了。
    融合之后 `source` 写 `rrf`、`score` 是那个和式的值，
    `from_` 记下这条片是被哪几条路带上来的（读数里要用）。
    """

    chunk: Chunk
    score: float
    source: str
    rank: int          # 1 起的名次：RRF 用的就是它
    from_: tuple[str, ...] = ()

    def cite(self) -> str:
        return self.chunk.cite()


def bm25_hits(index: NgramIndex, query: str, k: int = 10) -> tuple[Hit, ...]:
    """字面那一路。**不得分的一律不返回**（5.1 的纪律：0 分片塞进提示只会换来编答案）。"""
    return tuple(Hit(c, s, "bm25", i + 1)
                 for i, (c, s) in enumerate(index.search(query, k=k)))


def vector_hits(embedder: Callable, store: BaseIndex, chunks: Sequence[Chunk],
                query: str, k: int = 10) -> tuple[Hit, ...]:
    """向量那一路。**排序一律由 `store` 决定**（它自带维度校验与归一化，见 5.3.6）。

    这里只做一件事：把行号翻译回片。**这一句是刻意的窄口径**——
    如果在这里再排一次序，索引层的读数（5.3 量的那些）就不再是这条路的读数了。
    """
    qv = embedder([query])[0]
    return tuple(Hit(chunks[h.row], h.score, "vector", i + 1)
                 for i, h in enumerate(store.search(qv, k=k)))


def rrf(*lists: Sequence[Hit], k: int = RRF_K, limit: int | None = None) -> tuple[Hit, ...]:
    """倒数排名融合。**只吃名次，不吃分数。**

    返回的每条片都带 `from_`：它被哪几条路带上来的。这一列在读数里是关键——
    「融合把一条只被向量召回的片顶到第一」与「两条路都同意它」是两件事，
    而只看融合后的分数看不出区别。

    `limit=None` 表示全部返回（本章要看完整候选集，不截断）。

    **一条路对同一片只计一次**（去看 `seen`）。这一行是补上的：原先 `from_` 会去重、
    而 `total` 会重复累加，两个字段对「同一路出现过两次」给出不一致的答案——
    而 `from_` 的语义就是「这条片由哪几条路带上来」，所以分数也得按「路」算。
    现实里两条路各自返回的片本来就不会重复（`bm25_hits`／`vector_hits` 都按片去重），
    所以这个情形正常跑不到；但**两个字段不一致本身就是缺陷**，不因为跑不到就不是。
    """
    total: dict[str, float] = {}
    keep: dict[str, Chunk] = {}
    sources: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for lst in lists:
        for h in lst:
            key = h.chunk.cite()
            keep[key] = h.chunk
            if (key, h.source) in seen:
                continue
            seen.add((key, h.source))
            total[key] = total.get(key, 0.0) + 1.0 / (k + h.rank)
            sources.setdefault(key, []).append(h.source)
    order = sorted(total.items(), key=lambda kv: (-kv[1], kv[0]))
    out = [Hit(keep[key], round(score, 6), "rrf", i + 1, tuple(sources[key]))
           for i, (key, score) in enumerate(order)]
    return tuple(out if limit is None else out[:limit])


#: 离线改写表：`问法 → 库里的说法`。**它是标尺，不是方案**——
#: 它的每一条都要能指到语料里真实出现的词，否则就是「把答案抄进 query」。
#: （`tests/test_retrieve.py` 里有一条用例专门守这件事：右边每个词都必须在
#: `corpus/*.md` 里真的出现过。第一版我写的是「幂等 重复请求」，实测 `幂等` 一词
#: **全库零次**——那条用例把它拦下了。这一类错在读数里看不出来：
#: 它只会让「改写有效」这个结论变得不可信，而不是让脚本报错。）
#: 真机那一侧的提示。**两句话都是约束，不是描述**：
#: 「只允许使用企业内部文档里可能出现的词」防编造，「不要回答问题」防它把答案直接写进
#: query（那就成了作弊：把答案抄进检索词，而不是在改写）。
REWRITE_PROMPT = ("把下面的问题改写成检索用的关键词，只允许使用企业内部文档里可能出现的词，"
                  "不许编造新词，也不要回答问题。原问题：")

SYNONYMS: tuple[tuple[str, str], ...] = (
    ("连点两下", "重复请求 去重"),
    ("重复提交", "重复请求"),
    ("多久必须有人接", "值班 首次响应"),
    ("出事了多久必须有人接", "值班 首次响应"),
    ("退回去", "回滚"),
)


def rewrite(query: str, table: Sequence[tuple[str, str]] = SYNONYMS) -> tuple[str, tuple[str, ...]]:
    """离线改写：命中就**把库里的说法追加上去**，不改写原句。

    为什么是「追加」而不是「替换」：替换会丢掉原句里那些本来就对上的字
    （Q1 的「发布说明」是能召回的），而追加只会**扩大**字面重合面。
    返回 `(改写后的 query, 命中的问法)`，命中的那几条要能打印出来看。

    这里原本还写了一句「代价是 query 变长、BM25 的 IDF 权重被摊薄一点」，
    并且打算「量这一增一减」——**那一句量不出来，已经被删掉了**：改写后目标片拿的
    仍是 8.55 分，与只噎那两三个关键词完全相同（因为 query 里没匹配上的词贡献 0 分，
    不参与分母）。真正的代价在另一个地方，而且是可量的：**改写会把别的片一起拉上来**
    （`调用预算#1` 从 0 分变成 1.81 分，并在融合里被顶到第 1）——见 5.4.5。
    """
    hits = tuple(needle for needle, _ in table if needle in query)
    if not hits:
        return query, ()
    add = " ".join(dict.fromkeys(rep for needle, rep in table if needle in query))
    return f"{query} {add}", hits


def make_rewriter(call: Callable | None = None):
    """真机那一条的入口：把同一件事交给模型，**并在提示里钉死「不许编词」**。

    与 5.2 的 `make_parser` 同一个形状：离线与真机是同一个出口的两种实现。
    返回值是 `(query) -> (改写后的 query, 命中的来源)`，来源写 `"model"`。

    **`call` 的契约是 `call(messages) -> str`，`messages` 是 `[{"role", "content"}, ...]`**
    （与 `app/llm.make_call` 和 `app/scripted.ScriptedModel` 完全一致）。
    第一版这里传的是一整个字符串，而 `app/llm.py` 里那一行是 `roles[m["role"]]`——
    于是真机路径一点就跑出 `TypeError: string indices must be integers`。
    **这个错离线路径永远过不了**（离线那一支根本不碰 `call`），所以它只能在
    `--real` 里露出来，而 `--real` 不进提交门——因此补了一条不联网的用例
    （`tests/test_retrieve.py::test_真机改写的调用契约是消息列表`）把形状钉住。
    """
    if call is None:
        def offline(query: str):
            return rewrite(query)
        return offline

    def via_model(query: str):
        text = call([{"role": "user", "content": REWRITE_PROMPT + query}])
        return f"{query} {' '.join(text.splitlines())}", ("model",)

    return via_model


class Retriever:
    """把两条路、融合与候选集包成一个对象。**对外只有三个入口**，对应本章三件事。"""

    def __init__(self, chunks: Sequence[Chunk], index: NgramIndex,
                 embedder: Callable, store: BaseIndex) -> None:
        self.chunks = tuple(chunks)
        self.index = index
        self.embedder = embedder
        self.store = store
        self.rows = {c.cite(): i for i, c in enumerate(self.chunks)}
        self.calls = 0        # 改写用掉的「模型调用」次数（离线表算 0）
        self.pairs = 0        # 成对打分次数（重排的花销）

    def search(self, query: str, *, k: int = 3,
               mode: str = "hybrid", depth: int = 10) -> tuple[Hit, ...]:
        """`mode`：`bm25` ｜ `vector` ｜ `hybrid`。`depth` 是每条路的候选深度。

        **`depth` 与 `k` 是两件事**：前者决定「谁进了候选池」，
        后者决定「给下游看前几条」。重排只动后者，动不了前者——这就是它的边界。
        """
        if mode == "bm25":
            return bm25_hits(self.index, query, depth)[:k]
        if mode == "vector":
            return vector_hits(self.embedder, self.store, self.chunks, query, depth)[:k]
        if mode == "hybrid":
            return rrf(bm25_hits(self.index, query, depth),
                       vector_hits(self.embedder, self.store, self.chunks, query, depth),
                       limit=k)
        raise ValueError(f"没有这种检索方式：{mode}")

    def candidates(self, query: str, *, depth: int = 10) -> tuple[Hit, ...]:
        """重排的输入：融合后的**完整候选集**（不截断）。"""
        return rrf(bm25_hits(self.index, query, depth),
                   vector_hits(self.embedder, self.store, self.chunks, query, depth))

    def search_with_rewrite(self, query: str, *, k: int = 3, depth: int = 10,
                            rewriter=None) -> tuple[tuple[Hit, ...], str, tuple[str, ...]]:
        """改写之后再检索。**返回 (结果, 改写后的 query, 命中来源)**——
        中间那个 query 必须能被打印出来核对，否则「改写」就成了一个看不见的魔法。
        """
        if rewriter is None:
            new_query, hits = rewrite(query)
        else:
            new_query, hits = rewriter(query)
            if hits:
                self.calls += 1
        return self.search(new_query, k=k, mode="hybrid", depth=depth), new_query, hits

    def stats(self) -> dict:
        """花销账。**改写与重排都不是免费的**，本章要把它们记在同一张表里。"""
        return {"chunks": len(self.chunks), "bm25_terms": len(self.index.postings),
                "dim": self.store.dim, "calls": self.calls, "pairs": self.pairs,
                "rows": len(self.rows)}


def build_retriever(root=None, *, dim: int = 256, ngram: int = 2) -> Retriever:
    """一条命令拿到「两条路 ＋ 融合」。**与 5.1 的 `build_index` 同一种形状**：
    调用方拿到的永远是一个装好的对象，而不是四个需要自己拼的零件。

    这里刻意把向量那一路建成 `ExactIndex`：本章量的是**融合与重排**，
    不让 5.3 的近似误差掺进这一章的读数里（那一条在 5.3 已经量清楚了）。

    另：片的来源只有一处——`index.chunks`。**这一行写错了，向量那一路的 `row`
    就会指到别的片上，而它不会报错**，所以不另建一份语料。
    """
    index, _docs = build_index(root)
    chunks = tuple(index.chunks)
    embedder = make_embedder(dim=dim, ngram=ngram)
    store = ExactIndex(embedder([c.text for c in chunks]))
    return Retriever(chunks, index, embedder, store)
