"""重排：**在候选集之上再算一次分，这次让问题和片「见面」。**

为什么需要它：前一步（向量）把 query 与片分别压成向量，再比两个向量的夹角——
信息在压缩那一步就丢了一次。重排的做法相反：**把 `(query, 片)` 作为一对送进模型**，
让它逐字看着两边打分。素材里那一段说的是同一件事（`Cohere Rerank 3` 用的是交叉编码器），
本章的离线替身是「字符 3-gram 的覆盖率 ＋ 密度」——它同样是成对计算的，
而且**确定、可复现、零依赖**，所以它的读数能当成一条标尺。

两条边界必须写在模块开头，因为它们比「重排涨了多少」更要紧：

1. **重排改变不了候选集**。它只能给手里这些片重新排序——候选集里没有的正确答案，
   重排多少个都救不回来。所以它的收益上限是「候选集里的最好名次」，
   而那个上限由前一步的 `depth` 决定。本章会量这条：把 `depth` 从 10 降到 3，
   重排后的名次就跟着变差。
2. **它是唯一花销随候选数线性长的一环**：`depth=10` 就是 10 次成对打分，
   而融合那一步是零次（只读名次）。花销账要记在同一个表里。
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.corpus import Chunk
from app.retrieve import Hit

#: 只有汉字、字母、数字算内容（与 5.1 的 `corpus._TOKEN_KEEP`、5.3 的 `embed._RUN` 同一个口径）。
_RUN = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]+")


def _ngrams(text: str, n: int = 3) -> set[str]:
    """**3-gram** 而不是 2-gram：重排要区分「有这几个字」与「这几个字连在一起」。

    2-gram 太松——「接口约定」与「接口违约」在 2-gram 上几乎一样。
    3-gram 会把这些差别留住，代价是**零重合的概率更高**（长 n 更容易对不上），
    所以覆盖率那一项是主要信号，密度那一项只是修边。
    """
    out: set[str] = set()
    for run in _RUN.findall(text):
        if len(run) < n:
            out.add(run)
            continue
        out |= {run[i:i + n] for i in range(len(run) - n + 1)}
    return out


@dataclass(frozen=True)
class PairScore:
    """一次成对打分的两个分量。**分开报**，因为它们会各自失手：
    覆盖率抓「query 的词在不在片里」，密度抓「片是不是通篇都在讲这件事」。
    """

    cover: float     # query 的 gram 里有多少出现在片里
    density: float   # 片的 gram 里有多少被 query 碰到
    score: float


def pair_score(query: str, text: str) -> PairScore:
    """成对打分：`0.7 × 覆盖率 ＋ 0.3 × 密度`。

    两个权重是**本章定的口径**，不是从哪抄的：覆盖率的权重高，是因为读者问什么，
    片上就得有什么；密度只是防「一整篇长文档刚好提了一次关键词」被顶到前面。
    真机那一半要用交叉编码器，就把这个函数换掉——**接口形状不变**。
    """
    q = _ngrams(query)
    d = _ngrams(text)
    if not q or not d:
        return PairScore(0.0, 0.0, 0.0)
    inter = len(q & d)
    cover = inter / len(q)
    density = inter / len(d)
    return PairScore(round(cover, 4), round(density, 4),
                     round(0.7 * cover + 0.3 * density, 6))


def rerank(query: str, hits: Sequence[Hit], *, k: int = 3) -> tuple[Hit, ...]:
    """对候选集逐条成对打分，按新分重排，取前 `k`。

    **返回条数是 `min(k, len(hits))`**：候选集不够时不许补齐、不许回退到原顺序——
    「重排之后剩几片」本身就是一个读数。融合分（`from_`）保留下来，
    因为「重排把哪条路带上来的片顶上去」是能读出来的信息。
    """
    scored = [(pair_score(query, h.chunk.text).score, h) for h in hits]
    scored.sort(key=lambda t: (-t[0], t[1].rank))
    return tuple(Hit(h.chunk, s, "rerank", i + 1, h.from_)
                 for i, (s, h) in enumerate(scored[:k]))


def depth_sweep(query: str, candidates: Sequence[Hit], *, k: int = 3,
                depths: Sequence[int] = (3, 5, 10)) -> tuple[dict, ...]:
    """候选深度扫描：**同一批候选，只改「给重排看几条」。**

    这是本章量「重排的边界」的那把尺子：如果正确答案本来就在第 1 名，
    加深候选只会把它推后（因为分母里多了一条更匹配的长片）；
    如果正确答案本来在第 7 名，`depth=3` 时它连参赛资格都没有。
    两种情形都会在这张表里露出来。
    """
    out = []
    for d in depths:
        got = rerank(query, tuple(candidates)[:d], k=k)
        out.append({"depth": d, "n": len(got),
                    "order": tuple(h.cite() for h in got),
                    "pairs": d})
    return tuple(out)
