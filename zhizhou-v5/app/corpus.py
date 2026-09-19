"""v5 的知识层第一步：**把资料读进来，并且找得到**。

这一层是**故意朴素**的：只用标准库，字符 2-gram 倒排 ＋ BM25 打分，没有向量、没有重排。
理由有两条：

1. **5.1 要回答的是「为什么需要检索增强」，不是「怎么把检索做好」。**
   用最笨的办法先把「有资料 vs 没资料」的差量出来，这个差才有说服力——
   如果一上来就用向量检索，读者没法判断答案是资料带来的还是模型本来就会。
2. **朴素检索器的失败形态本身就是后面几章的教材。** 同义改写查不到 → 5.4 的查询改写与
   混合检索；切分把一段话腰斩 → 5.2 的切分策略；「词不一样就找不到」 → 5.3 的向量与
   嵌入模型。`LIMITS` 里那几条不是猜的，是 `scripts/why_rag.py` 在本机量出来的。

一个必须讲清的取舍：**这里「片」的单位是自然段，不是固定长度**。按空行切最笨，
但它恰好让 5.1 的引用可以指到「哪一份文档的第几段」——读者能自己去核对。
5.2 会把这一行换掉，换的时候要重新量一遍召回。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

#: 语料目录（相对本文件往上两级）：`zhizhou-v5/corpus/`
CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"

#: 切分与打分只要这几个字符类：汉字、字母、数字。标点与空白一律丢掉。
_TOKEN_KEEP = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]+")


@dataclass(frozen=True)
class Doc:
    """一份文档。`doc_id` 就是文件名去掉后缀——引用时读者要能拿它去 `corpus/` 里对。"""

    doc_id: str
    title: str
    text: str
    path: Path


@dataclass(frozen=True)
class Chunk:
    """检索的最小单位。`cite()` 是**引用标识**：文档名 ＋ 第几段。

    引用标识长得像个地址，这是**故意**的：它要能被读者拿去核对，
    也要能被程序回查（`rag.check_citations`）。不可核对的引用等于没有引用。
    """

    doc_id: str
    index: int
    text: str

    def cite(self) -> str:
        return f"{self.doc_id}#{self.index}"


def load_corpus(root: Path | None = None) -> tuple[Doc, ...]:
    """读 `corpus/*.md`。按文件名排序，保证**每一次拿到的顺序都一样**。"""
    root = root or CORPUS_DIR
    docs = []
    for p in sorted(root.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        title = ""
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        docs.append(Doc(doc_id=p.stem, title=title or p.stem, text=text, path=p))
    return tuple(docs)


def split_paragraphs(doc: Doc) -> tuple[Chunk, ...]:
    """按空行切段。**这是全书最笨的切法，故意留在这里当对照的起点**（5.2 换掉它）。

    切之前先把标题行去掉——标题会跟着它下面那一段一起被召回，
    于是「标题命中」会被算成「正文命中」，召回率就虚高了。这一步不做的话，
    5.1 量出的召回率是假的。
    """
    body = "\n".join(
        line for line in doc.text.splitlines() if not line.lstrip().startswith("#")
    )
    parts = [p.strip() for p in re.split(r"\n\s*\n", body)]
    return tuple(
        Chunk(doc_id=doc.doc_id, index=i, text=p)
        for i, p in enumerate(p for p in parts if p)
    )


def _grams(text: str, n: int = 2) -> tuple[str, ...]:
    """字符 n-gram。对中文不用分词器也能跑，代价是**它只会认字面的字**。"""
    joined = "".join(_TOKEN_KEEP.findall(text)).lower()
    if len(joined) < n:
        return (joined,) if joined else ()
    return tuple(joined[i : i + n] for i in range(len(joined) - n + 1))


class NgramIndex:
    """字符 2-gram 倒排索引 ＋ BM25 打分。

    三个实现细节决定了它的行为，也是它会在哪里失手的原因：

    1. **只认字面的字**：query 里的「防重复的标识」与文档里的「Idempotency-Key」
       一个 2-gram 都不重合，得分 0——不是排序错，是根本召不回；
    2. **IDF 压常见字**：「的」「是」这类 gram 权重接近 0，所以长 query 里
       真正有信息量的那两三个字决定排序；
    3. **BM25 的 `k1`／`b` 是照抄经验的**（1.5／0.75），本树没有语料去调它——
       调参数要等 5.6 有了评测集才谈得上。
    """

    def __init__(self, chunks: tuple[Chunk, ...], *, k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self._grams: list[tuple[str, ...]] = [_grams(c.text) for c in chunks]
        self.avgdl = (
            sum(len(g) for g in self._grams) / len(self._grams) if self._grams else 0.0
        )
        df: dict[str, int] = {}
        self.postings: dict[str, list[int]] = {}
        for i, gs in enumerate(self._grams):
            for g in set(gs):
                df[g] = df.get(g, 0) + 1
                self.postings.setdefault(g, []).append(i)
        n = len(chunks)
        self.idf = {
            g: math.log(1 + (n - d + 0.5) / (d + 0.5)) for g, d in df.items()
        }

    def search(self, query: str, *, k: int = 3,
               min_score: float = 0.0) -> tuple[tuple[Chunk, float], ...]:
        """返回 `[(片, 分), ...]`，按分降序；**得分为 0 的一律不返回**。

        不返回 0 分片是本节的一条纪律：0 分意味着「一个字都对不上」，
        把它塞进提示里只会让模型拿一段无关的话去编答案。
        「干脆一条都不给」才是诚实的——5.5 要教模型在这种时候**说不清就说不清**。

        `min_score` 是**召回阈值**，默认 0 就是不卡。它存在的理由要讲清楚：
        检索的行为是「永远返回前 k 片」——库里没有依据的问题也会拿到几片噪声
        （`LIMITS` 最后一条）。看上去阈值能救，本节的读数也会给出一个
        「在四条问题上恰好全对」的值；**但那是四条问题，不是证据**，
        一个改短了的问法就能把它推翻（5.6 的评测集就是为这件事存在的）。

        另：打分是**未归一的**，跨 query 之间不能比绝对值（Q1 的 19.8 与 Q4 的 4.2
        不是「相关 4.7 倍」）。要比分数，得先有 5.6 那套带标注的集。
        """
        q_grams = _grams(query)
        if not q_grams:
            return ()
        hits: dict[int, float] = {}
        for g in q_grams:
            if g not in self.postings:
                continue
            idf = self.idf[g]
            for i in self.postings[g]:
                gs = self._grams[i]
                tf = gs.count(g)
                dl = len(gs)
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                hits[i] = hits.get(i, 0.0) + idf * tf * (self.k1 + 1) / denom
        ranked = [(i, s) for i, s in sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))
                  if s >= min_score]
        return tuple((self.chunks[i], round(s, 4)) for i, s in ranked[:k])


def build_index(root: Path | None = None) -> tuple[NgramIndex, tuple[Doc, ...]]:
    """一条命令拿到「索引 ＋ 文档」。返回文档是为了旁边能打印语料规模（可复核）。"""
    docs = load_corpus(root)
    chunks = tuple(c for d in docs for c in split_paragraphs(d))
    return NgramIndex(chunks), docs


#: 这个朴素检索器的**已知失手形态**。每一条都由 `scripts/why_rag.py --offline` 实测复现，
#: 不是声明。后面几章逐条来救：同义 → 5.4 的查询改写；近义 → 5.3 的嵌入；
#: 切分 → 5.2；「库里根本没有」→ 5.5 的拒答与阈值。
#:
#: **头两条重要**：一是第一版里有一条是错的，二是这四条里有一条**实测没失手**。
#:
#: 错的：原本写「问『防重复的标识』、文档写『Idempotency-Key』，所以召不回」。
#: 实测它拿了 6.24 分、**召回到了**——因为「写接」「接口」这些 2-gram 两边都有。
#: 换词不等于零重合，真正的零重合要一个字都对不上（现在的 Q3 就是量出来的那一条）。
#:
#: 没失手的：「词原上限是多少？」——「词原」对不上，但「上限」「是多少」撑着，
#: 它照样把 `调用预算` 召回回来（5.30 / 3.90）。**同一类错，有的致命、有的被别的字救回来**，
#: 所以「哪种失手会发生」不能靠推理，只能靠量。
LIMITS = (
    ("同义改写（零重合）", "问「用户连点两下会不会写两条记录？」——实测**一片都召不回**（0 片）",
     "5.4 查询改写与混合检索"),
    ("近义替换", "问「出事了多久必须有人接？」——正确文档进不了前三，最高分 2.17 落在错文档上",
     "5.3 向量与嵌入模型"),
    ("库里根本没有", "问 2027 年的营收目标——实测反而召回到**高分噪声**（最高 6.03）",
     "5.5 拒答与召回阈值"),
    ("错别字（实测**没**失手）", "问「词原上限是多少？」——仍召回 `调用预算`：别的字把它救回来了",
     "不修；但要记住它是被别的字撑住的，不是错别字无害"),
)
