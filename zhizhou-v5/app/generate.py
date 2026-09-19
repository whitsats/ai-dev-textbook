"""5.5 的第二件东西：**引用不再由模型写，而由代码按句绑定。**

5.1 的 `app/rag.py` 走的是「让模型在句末写 `[1]`」。那条路能机检，但只能抓三种毛病：
编号越界、一条都不标、以及（靠人看）标错了片。第三种恰恰是最要紧的那种——
**句子指着一个编号，内容却不是那一片说的**，而它在文本上与正确引用长得一模一样。

本章把这件事翻过来：**模型只写正文，引用由代码挂。**

    回答 → 按句切开 → 每句与每一片算 3-gram 覆盖率 → 取最高的那片当依据
         → 覆盖率分三档：Fully（≥0.6）／Partially（0.25–0.6）／No support（<0.25）

三档就是 Self-RAG 的 **ISSUP**（`[ISSUP=FullySupported/PartiallySupported/NoSupport]`，
arXiv 2310.11511 表 1）在本树上的确定性版本。它能被离线复现，因为**覆盖率是可复算的**：
同一句话、同一批片，任何人跑一遍都得到同一个档位。

于是「幻觉」从一个形容词变成一个**可打印的名单**：凡是 No support 的句子，
就是模型自己写的、资料里没有的东西。这是本章最实用的一条输出，
也是 5.6 评测集里「忠实度」那一项的雏形。

## 三条设计决定与它们的理由

1. **覆盖率复用 5.4 的 `pair_score`**，不另写一个相似度。两章的读数因此可以叠在一起看：
   5.4 用它给「片与问题」排序，5.5 用它给「句与片」定档。
2. **绑定只增不改。** 绑定不会去动模型的正文（不改一个字），只在句末追加 `[i]`。
   一旦允许「顺手把没依据的句子润掉」，这份名单就不再是原始的模型输出，
   「模型编了多少」这个读数也就没了。
3. **拒答是一等公民。** `must_refuse()` 把「什么情况下根本不该调模型」写成可判定的条件
   （一片都没召回、三档判为 Incorrect、精炼后为空）。5.1 的实测里 Q4（库里没有）
   反而召回了噪声、模型照编——那一条正是在这里被拦下的。

## Self-RAG 的另外三个令牌

`[Retrieve=yes/no/continue]`（要不要检索）、`[ISREL]`（这片相关吗）、`[ISUSE]`（这答案有用吗）
在本树上的对应物很轻：`Control` 一个结构 ＋ `decide_retrieval()` 一个判据。
**本树不训练模型**，所以这四个令牌不是「模型学会了输出」，而是「把控制位显式化成可打印的契约」：
离线由剧本模型给、真机由提示要求它给。差别在读数里说明，不在正文里含糊过去。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.corpus import Chunk
from app.rag import NO_ANSWER
from app.rerank import pair_score

#: ISSUP 的两条档位线。**和 `critic.STRIP_MIN_COVER` 同源**（都是「字面覆盖率」这一把尺子），
#: 但取值不同：那边过滤的是「片里的句子要不要留」，这边判的是「这一句有没有依据」。
SUPPORT_FULL = 0.6
SUPPORT_PARTIAL = 0.25

#: 句级切分：与 `critic.strips` 同一套标点，**但不吞换行**——
#: 这里要保留原文的分行，因为渲染回正文时它要一字不差。
_SENT = re.compile(r"(?<=[。！？；])")
#: 引用标记 `[3]`。**它只在这里被解析，正文里出现的地方都要能被摘掉。**
_CITE = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class Sentence:
    """一句话与它的依据。`cite` 为空表示**没有任何片支撑它**。

    `index` 是**代码绑给它的编号**，`claimed` 是**模型自己标的编号**（0 表示没标）。
    两个都在，才能判出「错指」：编号合法、句子也写得对，但它指的片不是它的依据。
    """

    text: str
    support: str                 # Fully ｜ Partially ｜ No support
    cite: str = ""
    cover: float = 0.0
    index: int = 0               # 代码绑上去的编号（1 起）；0 表示没挂
    claimed: int = 0             # 模型自己标的编号；0 表示没标

    @property
    def unsupported(self) -> bool:
        return self.support == "No support"

    @property
    def misbound(self) -> bool:
        return bool(self.claimed and self.claimed != self.index)


@dataclass(frozen=True)
class Bound:
    """一次「按句绑定」的结果。**`text` 是可直接给读者看的正文**（句末带 `[i]`）。"""

    sentences: tuple[Sentence, ...]
    text: str
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def citations(self) -> tuple[str, ...]:
        """引用到的**地址**（`文档#段`），按首次出现的顺序去重。"""
        out: list[str] = []
        for s in self.sentences:
            if s.cite and s.cite not in out:
                out.append(s.cite)
        return tuple(out)

    def counts(self) -> dict:
        c = {"Fully": 0, "Partially": 0, "No support": 0}
        for s in self.sentences:
            c[s.support] += 1
        c["sentences"] = len(self.sentences)
        c["cited"] = len(self.citations)
        return c


def split_sentences(text: str) -> tuple[str, ...]:
    """按标点切句。**尾部没有标点的那一段也算一句**——它常常正是那句「顺手补上去的话」。"""
    return tuple(s for s in (p.strip() for p in _SENT.split(text)) if s)


def bind(answer_text: str, chunks: tuple[Chunk, ...], *,
         full: float = SUPPORT_FULL, partial: float = SUPPORT_PARTIAL) -> Bound:
    """按句绑定依据。**只改编号那一处，正文一个字不动。**

    三件事在同一趟里做完：

    1. 每句取覆盖率最高的那片当依据，定 ISSUP 那一档；
    2. 句末**重新挂上代码绑到的编号**（模型自己写的那个被换掉）；
    3. 顺手比一次两者：**模型标的编号与依据不符**的句子一条条报出来。

    第 3 条是 A 路做不到的事：`rag.check_citations` 只能查编号在不在范围内，
    而「编号合法、指错了片」要在这一层才看得见——这也是本章把引用从模型手里
    拿过来的全部理由。

    `NO_ANSWER` 那一句（拒答）不挂引用，也不计入「无依据」——拒答不是断言。
    """
    sentences: list[Sentence] = []
    number = {c.cite(): i for i, c in enumerate(chunks, start=1)}
    issues: list[str] = []
    for raw in split_sentences(answer_text):
        m = _CITE.search(raw)
        claimed = int(m.group(1)) if m else 0
        body = _CITE.sub("", raw).strip()      # 算覆盖率时把标记摘掉
        if NO_ANSWER in body:
            sentences.append(Sentence(body, "Fully", "", 0.0, 0, claimed))
            continue
        best_cover, best_cite = 0.0, ""
        for c in chunks:
            cover = pair_score(body, c.text).cover
            if cover > best_cover:
                best_cover, best_cite = cover, c.cite()
        support = ("Fully" if best_cover >= full
                   else "Partially" if best_cover >= partial else "No support")
        sentences.append(Sentence(body, support, best_cite if best_cite else "",
                                  round(best_cover, 4),
                                  number.get(best_cite, 0) if best_cite else 0,
                                  claimed))
    text = " ".join(f"{s.text} [{s.index}]" if s.index else s.text for s in sentences)
    bad = [s.text for s in sentences if s.unsupported]
    if bad:
        head = bad[0][:24] + "…" if len(bad[0]) > 24 else bad[0]
        issues.append(f"{len(bad)} 句在给的资料里找不到依据（第一句：{head}）")
    for i, s in enumerate(sentences, start=1):
        if s.misbound:
            issues.append(f"引用错指：第 {i} 句标了 [{s.claimed}]，"
                          f"而它的依据是 [{s.index}]（{s.cite}）")
    return Bound(tuple(sentences), text, tuple(issues))


def must_refuse(chunks: tuple[Chunk, ...], quality: str) -> str | None:
    """**什么情况下根本不该调模型。** 返回理由；`None` 表示可以调。

    三条各自对应一个实测过的事故：
    - 一片都没召回 → 5.1 的 `if chunks:` 把「空」与「无」并成了一条分支，模型照编；
    - 三档判为 `incorrect` → 这批资料里没有一个够格被引用；
    - （精炼后为空由 `critic.refine` 的 `notes` 报出，调用方把它并进来。）
    """
    if not chunks:
        return "检索一片都没召回"
    if quality == "incorrect":
        return "整批片的置信度都低于下阈值（CRAG 的 Incorrect 档）"
    return None


# ---------------- Self-RAG 侧的四个控制位（本树版） ----------------

#: 该检索的问法：事实、数字、规范。「创意题」不在此列——检索救不了它，只会占上下文。
_FACTUAL = re.compile(r"多少|哪几|是否|会不会|什么时候|几天|几段|上限|规范|约定|必须|应该")


@dataclass(frozen=True)
class Control:
    """Self-RAG 的四个令牌在本树上的显式形态。取值与论文表 1 一致，**大小写按论文写**。"""

    retrieve: str = "yes"        # yes ｜ no ｜ continue
    isrel: str = ""              # relevant ｜ irrelevant
    issup: str = ""              # fully supported ｜ partially supported ｜ no support
    isuse: int = 0               # 1–5


def offline_control(question: str, *, continuing: bool = False) -> Control:
    """离线控制位：**由问法判定，不调模型**。

    这不是「模型学会了输出令牌」，而是把判据写死成可复算的一版——
    它的价值是让「按需检索能省几次调用」这个读数**在提交门里也能跑**。
    真机那一侧由提示要求模型先给 `[Retrieve=...]`，读数里会写明两者不是一回事。
    """
    if continuing:
        return Control("continue")
    return Control("yes" if _FACTUAL.search(question) else "no")


def decide_retrieval(control: Control) -> bool:
    """只有 `yes` 才去检索；`no` 直接答，`continue` 沿用上一次的片。"""
    return control.retrieve == "yes"


#: 真机那一侧的控制位提示。**要求它把令牌写在最前面一行**，好被下面的正则抓下来。
CONTROL_PROMPT = (
    "先用一行给出检索判断：需要查企业内部资料就写 [Retrieve=Yes]，"
    "不需要（例如纯创作、闲聊、常识）就写 [Retrieve=No]。然后正常回答。"
)
_CTRL = re.compile(r"\[Retrieve=(Yes|No|Continue)\]", re.I)


def parse_control(text: str) -> Control:
    """从模型输出里抓控制位。**抓不到就按 yes 处理**（宁可多查一次，不可漏查）。"""
    m = _CTRL.search(text)
    if not m:
        return Control("yes")
    return Control(m.group(1).lower().replace("continue", "continue")
                   .replace("yes", "yes").replace("no", "no"))
