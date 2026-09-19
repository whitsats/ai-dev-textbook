"""5.5 的第一件东西：**在把资料交给模型之前，先判断这批资料配不配被引用。**

CRAG（arXiv 2401.15884）的机制是三步：

    评估   一个**轻量检索评估器**逐对打出「问题—文档」的相关分，汇总成一个置信度；
    分档   按上、下两个阈值判成 Correct / Incorrect / Ambiguous 三档；
    动作   Correct → 知识精炼（分解 → 过滤 → 重组）；
           Incorrect → 丢掉本地结果，改走网络搜索；
           Ambiguous → 两边都要（精炼后的本地片 ＋ 网络结果）。

论文对分档的**汇总写法**与直觉不同，正文里要按原话讲：**只要有一片的置信度高于上阈值就是
Correct；所有片都低于下阈值才是 Incorrect；其余一律 Ambiguous**（§4.3）。所以它判的是
「这批检索结果里有没有可用之物」，而不是「平均分高不高」。

## 本树照搬的是形状，不是那些数

三处必须说清，否则这一章就会变成「抄了一篇论文的结论」：

1. **评估器是替身。** 论文用的是微调过的 **T5-large（0.77B）**，本机与服务商都没有它
   （5.3 已经把「没有嵌入端点」量过一次）。这里用**可复算的确定性替身**：
   字面那一路上归一化后的 BM25 分、向量那一路的余弦分，取两者里更高的那个。
2. **阈值是自己定的。** 论文只写了「设了上下两个阈值」，**主文里没有给出取值**，
   所以本树的 `CONF_UPPER` / `CONF_LOWER` 是自定的口径，并由测试钉住行为。
   凡是「换上真评估器会不会更好」的问题，本章一律不作答。
3. **网络搜索这一支没有。** 不联网是这一整棵树的纪律（离线当门），
   对应的动作改成**明确拒答 ＋ 指出库里最接近的片**——这是「兜底」的诚实形态，
   而不是把「该上网」这件事假装没发生。

## 一条被 5.4 的结论逼出来的约束

**融合分不能当置信度。** 5.4 量到的是「RRF 只吃名次、不吃分数」——它输出的 `1/(60+rank)` 是
一个**秩序量**，第 1 名与第 2 名的差(0.0163 与 0.0161)里没有「有多相关」这个信息。
把一个秩序量塞进阈值判定，三档会几乎全落在 Ambiguous 上，而那是**伪装的确定**。
所以 `confidence()` 只吃 `bm25` 与 `vector` 两路的分，遇到 `rrf` 直接报错——宁可报错。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from app.corpus import Chunk
from app.rerank import pair_score
from app.retrieve import Hit

__all__ = ["CONF_LOWER", "CONF_UPPER", "SCALE", "Quality", "Refinement", "Strip",
           "confidence", "evaluate", "fallback", "judge", "refine", "strips"]

#: 字面分的归一化尺度：`score / SCALE`，截断到 1。
#: 20 这个数不是拍出来的——5.1 量到的最高命中分是 **19.79**（`发布规范#1`），
#: 而噪声那一档的 6.03 落进来正好是 0.30：**在 AMBIGUOUS 区间里**。
#: 也就是说，这条映射把「5.1 量出来的那条裕度」翻译成了三档语言，而不是另立一把尺子。
SCALE = 20.0

#: 上、下阈值。**本树自定**（论文主文未给取值），由 `tests/test_critic.py` 钉住。
CONF_UPPER = 0.55
CONF_LOWER = 0.25

#: 句级精炼的过滤线：一条 strip 的覆盖率低于它就被丢掉。
STRIP_MIN_COVER = 0.25


class Quality(Enum):
    """检索质量的三个取值。名字与论文一致，便于读者去对照原文。"""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    AMBIGUOUS = "ambiguous"

    @property
    def action(self) -> str:
        """这一档对应的动作。**字符串要能直接读进正文的读数表。**"""
        return {
            Quality.CORRECT: "精炼（只用本地片）",
            Quality.INCORRECT: "兜底（本地一片都不用）",
            Quality.AMBIGUOUS: "精炼 ＋ 兜底（本地片 ＋ 最接近的片）",
        }[self]


def confidence(hits: tuple[Hit, ...]) -> tuple[float, ...]:
    """把命中分归一到 0–1。**秩序量（`rrf`）在这里是非法的输入**，见模块开头。

    归一化只做一件事：`min(1, score / SCALE)`（字面）或原样（向量，余弦本来就在 0–1）。
    不做 min-max、不做 softmax——**两者都会让分数依赖「这批里还有什么」**，
    于是同一片在不同的候选集里得到不同的置信度，三档判定就跟着漂。
    """
    out: list[float] = []
    for h in hits:
        if h.source == "rrf":
            raise ValueError(
                "融合分是秩序量，不能当置信度（5.4：RRF 只吃名次不吃分数）。"
                "评估器要吃 bm25／vector 两路里**有尺度**的那一份。"
            )
        if h.source == "bm25":
            out.append(min(1.0, h.score / SCALE))
        else:                     # vector：余弦，已在 0–1
            out.append(max(0.0, min(1.0, h.score)))
    return tuple(round(x, 4) for x in out)


def judge(scores: tuple[float, ...], *, upper: float = CONF_UPPER,
          lower: float = CONF_LOWER) -> Quality:
    """论文的汇总写法：**有一片够高就是 Correct，全都够低才是 Incorrect，其余 Ambiguous。**"""
    if not scores:
        return Quality.INCORRECT        # 一片都没有，等价于「全都低于下阈值」
    if max(scores) > upper:
        return Quality.CORRECT
    if all(s <= lower for s in scores):
        return Quality.INCORRECT
    return Quality.AMBIGUOUS


def evaluate(retriever, query: str, *, depth: int = 5):
    """一次完整的「评估」：取两条原始路的分 → 归一 → 判档。

    **这里刻意不用 `Retriever.candidates()`。** 那一个返回的是**融合后**的片
    （`source="rrf"`），而融合分是秩序量——要判档就得回到 `bm25` 与 `vector`
    两条原始路上去取分。这是本章与 5.4 最直接的一处接口约定，
    也是 `confidence()` 会对 `rrf` 直接报错的原因。
    """
    hits = (retriever.search(query, k=depth, mode="bm25")
            + retriever.search(query, k=depth, mode="vector"))
    scores = confidence(hits)
    return hits, scores, judge(scores)


#: 句级切分。**只用标点与换行**，不引分词器——strip 的边界要能被读者一眼复核。
_SENT = re.compile(r"(?<=[。！？；])|\n+")


def strips(text: str) -> tuple[str, ...]:
    """把一片切成分解—重组算法要用的最小单位（论文里的 knowledge strip）。

    论文的口径是「一两句就当一个 strip，否则按长度切成几句」；本树的片本来就只有一两句
    （5.1 的语料是段级），所以这里按句切、剥空白、丢空串，**顺序不动**——
    「按原序拼回」是重组那一步的硬要求（换序会让引用对不上原文）。
    """
    return tuple(s for s in (p.strip() for p in _SENT.split(text)) if s)


@dataclass(frozen=True)
class Strip:
    """一句（或一段）strip 与它的覆盖率。**留出 `cite` 是为了让精炼不改地址。**"""

    cite: str
    text: str
    cover: float

    @property
    def kept(self) -> bool:
        return self.cover >= STRIP_MIN_COVER


@dataclass(frozen=True)
class Refinement:
    """一次精炼的结果：新的片 ＋ 账。

    新的片的 `cite()` **与原来那一片一字不差**（段号不变，变的是「这一片里留下哪些句子」）。
    这样 `rag.render_context` 与引用核对这两处一个字都不用改——**精炼不该改变地址，
    只该改变送进提示的字数**。
    """

    quality: Quality
    chunks: tuple[Chunk, ...]
    strips: tuple[Strip, ...] = ()
    chars_before: int = 0
    chars_after: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def drop_ratio(self) -> float:
        """丢掉的比例。**它是这一节的读数**：精炼到底省下了多少。"""
        if not self.chars_before:
            return 0.0
        return round(1 - self.chars_after / self.chars_before, 4)

    def stats(self) -> dict:
        return {
            "quality": self.quality.value,
            "action": self.quality.action,
            "strips": len(self.strips),
            "kept_strips": sum(1 for s in self.strips if s.kept),
            "chars_before": self.chars_before,
            "chars_after": self.chars_after,
            "drop_ratio": self.drop_ratio,
            "sources": tuple(c.cite() for c in self.chunks),
        }


def refine(question: str, chunks: tuple[Chunk, ...]) -> Refinement:
    """分解 → 过滤 → 重组。**不改地址，只改字数。**

    覆盖率复用 5.4 的 `pair_score`（3-gram 覆盖率）：同一把尺子量「问题与片有多重合」，
    与 5.4 的成对重排**同一个函数**——两章读数因此可以对照着读。
    """
    chars_before = sum(len(c.text) for c in chunks)
    kept_text: dict[str, list[str]] = {}
    all_strips: list[Strip] = []
    for c in chunks:
        kept_text[c.cite()] = []
        for s in strips(c.text):
            cover = pair_score(question, s).cover
            st = Strip(cite=c.cite(), text=s, cover=cover)
            all_strips.append(st)
            if st.kept:
                kept_text[c.cite()].append(s)
    new_chunks = tuple(
        Chunk(doc_id=c.doc_id, index=c.index, text="".join(kept_text[c.cite()]))
        for c in chunks if kept_text[c.cite()]
    )
    chars_after = sum(len(c.text) for c in new_chunks)
    notes = () if new_chunks else ("整批片都被过滤干净了——这一档只能走兜底",)
    return Refinement(Quality.CORRECT, new_chunks, tuple(all_strips),
                      chars_before, chars_after, notes)


def fallback(question: str, chunks: tuple[Chunk, ...], *,
             closest: int = 1) -> dict:
    """Incorrect 那一档的**本树版兜底**：不上网，改成「明确拒答 ＋ 指出库里最接近的片」。

    为什么不做成「假装有网络结果」：那会让这一档的读数变成假的——
    「兜底救回了多少条」是本章最想知道的一件事，而它的上限由语料决定，
    不由脚本决定。论文的网页结果可以补上语料里没有的知识；**语料里没有的就是没有**，
    这正是 5.1 那句「检索到空也要走带资料那条提示」在生成侧的延续。

    返回的 `note` 是给读者的：**别把「拒答」当成失败**——它是这一档唯一正确的动作。
    """
    scored = sorted(((pair_score(question, c.text).cover, c) for c in chunks),
                    key=lambda t: (-t[0], t[1].cite()))[:closest]
    return {
        "refuse": True,
        "closest": tuple(c.cite() for _, c in scored),
        "note": "本地语料判为不可用；本树不联网，所以这一档的动作是拒答而不是补充搜索",
    }
