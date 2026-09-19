"""向量从哪来：**一个 `(texts) -> list[list[float]]` 的出口**，形状与 `app/llm.py` 一样薄。

两条实现，与全书「离线当门、真机报数」同一条纪律：

- `HashedEmbedder`：离线、确定、零依赖。它把字符 n-gram 哈希进固定维度的桶，
  再做 L2 归一化。**它不是「假模型」，它是一把标尺**——刻度固定，所以
  「换一种索引／改一个参数，召回掉了多少」这件事才量得出来。
- `OpenAICompatEmbedder`：真机那一条，打服务商的 `/v1/embeddings`。
  它与 `app/llm.py` 的 `make_call()` 并列：一个是文本进、文本出，一个是文本进、向量出。

**为什么要专门写一个离线嵌入器，而不是随便给每个向量填随机数？**
随机向量没有语义——「感冒药」与「抗感冒药物」靠不出相似度，那么本章那条结论
（向量检索赢在「问法不同、说法不同」）就无从演示。哈希 n-gram 有一条真性质：
**字面重合越多的两段文本，向量越接近**。所以它既能跑，也真的能上榜。

它量不出来的那件事也写在正文里：**同义改写的匹配**。那要靠真嵌入模型，
而本章那条读数只能在有嵌入端点时才有——本机没有，所以那一行标注为「待有端点时再做」。
"""
from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

#: 只有汉字、字母、数字算「内容」，标点与空白一律当**分隔符**。
#: 与 5.1 的 `corpus._TOKEN_KEEP` 同一个口径——但它在这里还多一件职责：
#: **只有标点的一段文本会得到零向量**，而那正是要能被报警的那种状态（见 `stats`）。
_RUN = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]+")


def _ngrams(text: str, n: int) -> list[str]:
    """滑动 n-gram。字符级，所以**不需要分词器**——这是中文场景下最省事的一种。

    两层处理都有理由，不是随手写的：

    1. **按内容段切开**（标点是分隔符）：不切的话「发布规范：一句话」会多出一个
       跨标点的 2-gram「范一」，它两边都不像，却会掺进相似度里；
    2. **段内滑窗**：跨段不建 gram——一个句号两侧的两个字本来就不构成一个词。
    """
    out: list[str] = []
    for run in _RUN.findall(text):
        if len(run) < n:
            out.append(run)
            continue
        out += [run[i:i + n] for i in range(len(run) - n + 1)]
    return out


def _bucket(gram: str, dim: int) -> tuple[int, float]:
    """gram →（桶号, 符号）。

    符号那一半是必要的：不带符号的话，不同 gram 的贡献会互相抵消不掉，
    长文本的桶值会挤成一片正数，相似度就分不开了。用哈希的高位取符号，
    **保证同一个 gram 在每一次运行里落到同一个桶、带同一个符号**（可复现）。
    """
    h = int.from_bytes(hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest(), "big")
    return h % dim, 1.0 if (h >> 63) & 1 else -1.0


@dataclass(frozen=True)
class HashedEmbedder:
    """离线确定性嵌入器。`dim` 与 `ngram` 是它的两个旋钮，默认 256 维、2-gram。

    维度取 256 而不是「模型那种 1024／1536」：本树要量的对比都在同一小块语料上，
    维度只影响**内存与延迟的绝对值**，不影响那些结论的形状。正文里给出的
    「维度决定内存」那个账，用的是公式而不是这 256 这个数。
    """

    dim: int = 256
    ngram: int = 2
    normalize: bool = True

    def embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for gram in _ngrams(text, self.ngram):
            idx, sign = _bucket(gram, self.dim)
            vec[idx] += sign
        if self.normalize:
            vec = normalize(vec)
        return vec

    def __call__(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed_one(t) for t in texts]

    def spec(self) -> dict:
        """能进日志与读数的形态：读者要能一眼看出这批向量是怎么来的。"""
        return {"kind": "hashed", "dim": self.dim, "ngram": self.ngram,
                "normalize": self.normalize}


def normalize(vec: Sequence[float]) -> list[float]:
    """L2 归一化。**零向量原样返回**——它不是「归一化失败」，是一种要单独报的状态。"""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return list(vec)
    return [x / norm for x in vec]


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise DimensionMismatch(f"维度不一致：{len(a)} vs {len(b)}")
    return sum(x * y for x, y in zip(a, b))


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """余弦相似度。零向量与任何向量都没有夹角，**返回 0.0 而不是 0/0 的 NaN**。"""
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot(a, b) / (na * nb)


def l2(a: Sequence[float], b: Sequence[float]) -> float:
    """欧氏距离。**归一化之后它与余弦是单调等价的**——这一条是可测的，见 5.3.6。"""
    if len(a) != len(b):
        raise DimensionMismatch(f"维度不一致：{len(a)} vs {len(b)}")
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class DimensionMismatch(ValueError):
    """向量维度对不上。**单独一个异常类型**，因为这是入库阶段最常见的一类错。"""


def stats(vectors: Sequence[Sequence[float]]) -> dict:
    """一批向量的体检报告。**空向量率**是第 5 篇里最该被监控的一个数（见 5.3.6）。"""
    if not vectors:
        return {"count": 0, "dim": 0, "empty_ratio": 0.0, "mean_norm": 0.0}
    norm0 = math.sqrt(sum(x * x for x in vectors[0]))
    empties = sum(1 for v in vectors if math.sqrt(sum(x * x for x in v)) == 0.0)
    norms = [math.sqrt(sum(x * x for x in v)) for v in vectors]
    return {"count": len(vectors), "dim": len(vectors[0]),
            "empty_ratio": round(empties / len(vectors), 4),
            "mean_norm": round(sum(norms) / len(norms), 4),
            "first_norm": round(norm0, 4)}


def make_embedder(*, dim: int = 256, ngram: int = 2, normalize_: bool = True):
    """入口函数。**`normalize_` 带下划线**，因为它与模块级那个 `normalize` 重名——
    这里刻意不改名，好让「关掉归一化」这个开关在调用处一眼看得出来。"""
    return HashedEmbedder(dim=dim, ngram=ngram, normalize=normalize_)
