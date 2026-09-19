"""5.6 的判分层：**把前五章的读数压成几个能互相比较的数字。**

前五章各量了一件事，而那些读数之间不可比：5.1 说「答案片排第 5」，5.3 说「召回率 0.6」，
5.4 说「改写把 Q3 从零召回变第 2」，5.5 说「一句话是 Fully」。它们各自都对，
但**没有任何两个能放在一起看**——因为每一章的「命中」是在不同深度、对不同目标定义的。

这一层只做一件事：**把「命中」定义一次，然后所有指标都基于它。** 定义写在 `hit()` 里，
三条规则：目标片必须在候选里、必须在前 `k` 条里、而 `want_doc` 为空表示「这一条本来就不该有目标」。

## 四个指标与它们的分工

| 指标 | 它回答的问题 | 它的分母 | 谁该为它负责 |
| --- | --- | --- | --- |
| `recall_at` | 该找到的找到了吗 | 语料里真有依据的那些题 | 检索层（5.1–5.4） |
| `answer_hit_rate` | 答案里真的出现了那段话吗 | 同上 | 生成侧（5.5） |
| `refusal_confusion` | 该拒的拒了吗、该答的答了吗 | 全部用例 | 拒答判据（5.5） |
| `support_ratio` | 说出来的话有多少是有依据的 | 句数 | 绑定层（5.5） |

**前两个的差是本章最值钱的一条读数**：`recall_at` 高而 `answer_hit_rate` 低，
意思是「检索到了但没用上」——那是生成侧的问题，加检索深度救不回来。
反过来低而高是不可能的：答案里的片段只能来自被召回的片（**这一条由用例守住**）。

## 一条纪律：可检测的最小差异

`MIN_DETECTABLE` 不是调出来的取值，是**算出来的**：n 条用例里改一条，
比率就动 `1/n`。所以 24 条用例的分辨率是 4.2 个百分点——
**任何小于 4.2 个点的「提升」都不该被报出来**，它落在噪声里。
这一条比任何容差参数都重要：容差是防退步的，而它是防吹牛的。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

__all__ = ["Case", "MIN_DETECTABLE", "answer_hit_rate", "flatten", "gate", "hit",
           "load_cases", "lower_is_better", "min_detectable", "polarity", "rank_of",
           "recall_at", "recall_by_kind", "refusal_confusion", "span_cite",
           "support_ratio"]

#: 「这句（这支片）算不算命中」只有这一个定义，全章都从它出发。
#: `k` 是候选深度：**同一条读数在不同的 k 下是两个数**，所以每个数都要写上它的 k。
DEFAULT_K = 3


@dataclass(frozen=True)
class Case:
    """一条用例。**它是一句话 ＋ 一个可核对的断言**，不是一句期望。

    `want` 必须是语料里**逐字存在**的片段（评测集自己有一条用例守着这件事）。
    写成「大意对就行」的话，这一条就退化成人的印象，而印象无法回归。
    """

    case: str
    kind: str
    text: str
    want: str = ""
    want_doc: str = ""
    expect_refuse: bool = False
    expect_retrieve: bool = True
    notes: str = ""

    @property
    def wants_answer(self) -> bool:
        """这一条应当被回答（而不是拒答）。**「不检索」与「拒答」是两件事**：
        创意题既不检索也不拒答——它压根不走这套判据。"""
        return not self.expect_refuse and bool(self.want)

    @property
    def needs_recall(self) -> bool:
        """这一条要求「目标片进候选」。拒答题与创意题都不要求。"""
        return bool(self.want_doc)


def load_cases(path: Path) -> tuple[Case, ...]:
    """读 JSONL。**空行跳过、字段缺省用默认值**——这样新增字段不需要改所有人。"""
    out: list[Case] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(Case(**json.loads(line)))
        except TypeError as exc:
            raise ValueError(f"{path.name} 第 {i} 行有未知字段：{exc}") from exc
    return tuple(out)


def min_detectable(n: int) -> float:
    """n 条用例的可检测最小差异＝一条用例占的比率。**它随条数下降，不随容差下降。**"""
    return round(1 / n, 4) if n else 0.0


#: 24 条用例的分辨率。它写在模块级是为了让「别报小于 4.2 个点的提升」这句话有个出处。
MIN_DETECTABLE = min_detectable(24)


def rank_of(cites: tuple[str, ...], want_doc: str) -> int:
    """目标文档在候选里的名次（1 起）。**返回 0 表示「候选里没有它」**。

    判据是**文档级**而不是片级：同一份文档有好几片，命中哪一片都算找到了。
    这一条是被 5.2 的读数逼出来的——父子片之后，同一份文档会同时以多片出现，
    按片级判会让「命中」变成一个由切分策略决定的数，而它本该由检索决定。
    """
    for i, cite in enumerate(cites, start=1):
        if cite.split("#", 1)[0] == want_doc:
            return i
    return 0


def hit(rank: int, k: int = DEFAULT_K) -> bool:
    """名次算不算命中。**候选里没有（0）与排在 k 之后是两个不同的坏**，但都算没命中。"""
    return 1 <= rank <= k


def span_cite(chunks, want: str) -> str:
    """装着 `want` 那一段话的片（`文档#段`）；没有则返回空串。

    **它把「命中」分成两级**：文档级（这份文档进了前三）与片级（装着答案的那一片进了前三）。
    本章两份都要报，因为它们在 6 份文档 15 片的语料上差距很大：
    文档级几乎总是命中（只有 6 个选项），而片级才是「模型能不能看到那句话」的真判据。
    只报文档级会把这一章的命中率报成 1.0，那是一条**钝的读数**（与 5.2 那个「答案片排名」同族）。
    """
    for c in chunks:
        if want and want in c.text:
            return c.cite()
    return ""


def recall_by_kind(rows: list[tuple[str, int]], k: int = DEFAULT_K) -> dict:
    """按用例类型分组的命中率。`rows` 是 `(kind, 名次)`。

    **分组报不是为了好看**：本章的错全都集中在两类上（措辞漂移与拒绝式判断），
    一个总命中率会把它们写在平均数里。分组之后，退步会直接指到那一类上。
    """
    out: dict[str, dict] = {}
    for kind, rank in rows:
        cell = out.setdefault(kind, {"n": 0, "hit": 0})
        cell["n"] += 1
        cell["hit"] += bool(hit(rank, k))
    return {k2: {**v, "rate": round(v["hit"] / v["n"], 4)} for k2, v in out.items()}


def recall_at(ranks: list[int], k: int = DEFAULT_K) -> float:
    """命中率。分母是**要求召回的那些条**（`needs_recall`），不是全部用例。

    把拒答题也算进分母是这一层最常见的错：那些题**本来就该召回到噪声**，
    算进去等于给一个正确的行为扣分。
    """
    return round(sum(1 for r in ranks if hit(r, k)) / len(ranks), 4) if ranks else 0.0


def answer_hit_rate(answers: list[tuple[bool, bool]]) -> float:
    """答案命中率。`answers` 是 `(答案里出现了 want 吗, 这一条要求召回吗)`。

    **只对「要求召回」的那些条计分**：拒答题的正确答案是那句拒答本身（不含片段），
    把它算进分母等于在问「拒答里有没有出现 2,400 万」——那是个没有意义的问题。
    与 `recall_at` 同一个分母，两个数才可以直接相减。
    """
    pool = [ok for ok, wants_recall in answers if wants_recall]
    return round(sum(1 for ok in pool if ok) / len(pool), 4) if pool else 0.0


def support_ratio(counts: dict) -> float:
    """5.5 的三档支撑折算成一个比率：Fully 计 1、Partially 计 0.5、No support 计 0。

    **这就是 RAGAS 的 Faithfulness 在本树上的确定性替身**，而它有一个已知的偏差：
    Partially 那一档里既有「转述」（应当计 1）也有「半对」（应当计更低），
    本树把两者都算 0.5。所以这个数**只能与自己比**（回归门），不能与论文里的
    Faithfulness 比——口径不同，这与 5.3、5.4 那两处「不引数字」是同一条纪律。
    """
    total = counts.get("sentences", 0)
    if not total:
        return 1.0            # 一句话都没说（例如拒答）：不产生「无依据」的分母
    score = counts.get("Fully", 0) + 0.5 * counts.get("Partially", 0)
    return round(score / total, 4)


# ---------------- 回归门：把「读数」变成「门」的那一层 ----------------

#: 极性判据的两张名单。**它们不是「把所有键列全」**——新指标只要归类得进去就自动生效，
#: 归不进去的由下面的反向守报出来（而不是被默认当成「没变坏」）。
_LOWER_TAILS = ("missed", "over", "errors", "best_errors")
_HIGHER_TAILS = ("hit", "support", "answer_hit", "right_refuse", "right_answer",
                 "windows_with_zero")


def polarity(key: str) -> str:
    """这一项是 `lower`（越小越好）、`higher`，还是 `?`（**没定义**）。

    第一版只做了「越小越好」这一侧：按最后一段看 `missed` / `over` / `errors` / `cost.*`。
    而扁平表里有一项叫 `sweep.best_errors`——它的尾段是 `best_errors`，**不在那一串里**，
    于是被判成「越大越好」：「可达的最少错」从 1 个变 2 个是一件真退步，门却一声不响。
    这是本项目里第七次同一族错误（写死的枚举必漏），而这次它长在**门自己身上**——
    比前六次都安静，因为它不会报错，只会不报。

    所以新写法不只补那一项，而是加一条反向守：**判不出来的键要报出来**。
    新增指标的那一天，输出里会出现一行「方向未定义」，而不是一个默认值。
    """
    tail = key.rpartition(".")[2]
    if key.startswith("cost.") or tail in _LOWER_TAILS:
        return "lower"
    if key.startswith(("recall.", "span.")) or tail in _HIGHER_TAILS:
        return "higher"
    return "?"


def lower_is_better(key: str) -> bool:
    """这一项是不是「越小越好」。**只有明确判为 `lower` 的返回真。**"""
    return polarity(key) == "lower"


def flatten(run: dict) -> dict[str, float]:
    """把嵌套读数压成一张扁平表（门的比对单位）。**键就是指标的名字，值就是那个数。**"""
    out = {f"recall.{m}": v for m, v in run["recall"].items()}
    out.update({f"span.{m}": v for m, v in run.get("span", {}).items()})
    out["answer_hit"] = run["answer_hit"]
    out["support"] = run["support"]
    for name, conf in run["refusal"].items():
        for key in ("right_refuse", "missed", "over", "errors"):
            out[f"refusal.{name}.{key}"] = conf[key]
    if run.get("sweep"):
        out["sweep.best_errors"] = min(row["errors"] for row in run["sweep"])
        out["sweep.windows_with_zero"] = sum(1 for row in run["sweep"] if row["errors"] == 0)
    out["cost.prompt_chars"] = run["cost"]["prompt_chars"]
    return out


def gate(now: dict[str, float], base: dict[str, float], tol: float = 0.0) -> list[str]:
    """退步清单。**两个方向都查**：该高的不能掉，该低的不能涨。

    `tol` 默认 0：容差不是「允许退步一点」，而是「小于分辨率的差别不该报」——
    本章的分辨率是 1/24 ≈ 4.2%，所以任何一格变化都是真的。
    新增的指标不拦（第一次出现没有基线可比）；而「这一次没跑到」要拦——
    它与「没退步」在输出里长得一样，静默略过是这一族里最难发现的一种。
    """
    bad: list[str] = []
    for key in sorted(base):
        if key not in now:
            bad.append(f"{key} 在这一次读数里消失了（可能是这一项没跑到）")
            continue
        delta = now[key] - base[key]
        if abs(delta) <= tol:
            continue
        if polarity(key) == "?":
            # 方向没定义时**不能默认「没变坏」**：那正是 `sweep.best_errors` 当初漏掉的方式。
            # 但它只在这一项**真的变了**的时候才报——没变就没有方向可言。
            bad.append(f"{key} 变了但好坏方向没定义（重新命名，或把它归进 `polarity()`）")
            continue
        worse = delta > 0 if lower_is_better(key) else delta < 0
        if worse:
            arrow = "涨" if delta > 0 else "降"
            bad.append(f"{key} 退步：{base[key]} → {now[key]}（{arrow} {abs(delta):.4f}）")
    return bad


def refusal_confusion(rows: list[tuple[bool, bool]]) -> dict:
    """拒答四格。`rows` 是 `(期望拒答吗, 实际拒答了吗)`。

    四个数各有去处：`missed`（该拒不拒）是质量事故，`over`（不该拒却拒）是可用性事故，
    而它们**在同一个阈值上此消彼长**——本章的阈值扫描量的是这件事。
    """
    missed = sum(1 for want, got in rows if want and not got)
    over = sum(1 for want, got in rows if not want and got)
    right_refuse = sum(1 for want, got in rows if want and got)
    right_answer = sum(1 for want, got in rows if not want and not got)
    return {"right_refuse": right_refuse, "missed": missed,
            "over": over, "right_answer": right_answer,
            "total": len(rows), "errors": missed + over}
