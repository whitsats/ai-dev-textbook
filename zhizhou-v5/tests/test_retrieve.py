# tests/test_retrieve.py —— 不需要密钥、不需要网络：融合、改写、重排、候选深度
"""这一份测的是第 5 篇「第四步」能不能被机械验收。

七组断言，每一组都对应正文里的一个结论，**都不需要模型与网络**：

1. **融合只吃名次**：把输入的分数放大一万亿倍，输出次序不许变（否则「融合」是句空话）；
   并且输出**不许超出两条输入的并集**（它不创造信息），`from_` 要记得住来源；
2. **尺度不可比**：BM25 是未归一的分（可以远超 1），余弦固定在 `[-1, 1]`——
   所以「加权和」在本语料上会退化成尺度大的那一条路的排序（正文那一列读数有这一条）；
3. **改写是追加**：原句完整保留；没命中就不动 query；**表右边每个词都必须在语料里出现过**
   （第一版写了「幂等」，全库 0 次——这条用例就是为它写的）；
4. **重排的口径变了**：3-gram 而不是 2-gram（「接口约定」与「接口违约」在 3-gram 上零重合）；
   空输入得 0 分不抛异常；覆盖率与密度在互换两边后对调；
5. **重排的边界**：输出条数是 `min(k, 候选数)`（不补齐）；**候选集里没有的，重排救不回来**
   （实测：未改写的 Q3 上，成对分的最高值是 0，而那不是「语料里没有依据」）；
6. **候选深度**：候选集大小不等于 `depth`（两条路的并集去重）；成对打分次数等于 `depth`；
7. 端到端：离线脚本跑通，并逐条确认正文引用的那几行读数还在。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.corpus import Chunk, load_corpus                            # noqa: E402
from app.questions import QUESTIONS                                  # noqa: E402
from app.rerank import _ngrams, depth_sweep, pair_score, rerank      # noqa: E402
from app.retrieve import (RRF_K, SYNONYMS, Hit, bm25_hits,           # noqa: E402
                          build_retriever, make_rewriter, rewrite, rrf,
                          vector_hits)

TOP_K = 3
DEPTH = 10
Q3 = next(q for q in QUESTIONS if q.qid == "Q3")
Q5_TEXT, Q5_WANT = "出事了多久必须有人接？", "值班与响应"


def _hit(cite: str, src: str, rank: int, score: float = 0.0, text: str = "") -> Hit:
    doc, _, idx = cite.partition("#")
    return Hit(Chunk(doc_id=doc, index=int(idx or 0), text=text or f"{doc} 的正文"),
               score, src, rank)


def _retriever():
    return build_retriever()


# ------------------------------------------------------------------ 1 融合
def test_RRF_对分数不敏感() -> None:
    """把分数放大一万亿倍，次序一字不许变——它读的只有 `rank`。"""
    a = [_hit(f"doc#{i}", "bm25", i + 1, score=10.0 ** i) for i in range(4)]
    b = [_hit(f"doc#{i}", "bm25", i + 1, score=1e12 * 10.0 ** i) for i in range(4)]
    assert [h.cite() for h in rrf(a)] == [h.cite() for h in rrf(b)]


def test_RRF_输出不超出两条输入的并集() -> None:
    a = [_hit("doc#0", "bm25", 1), _hit("doc#1", "bm25", 2)]
    b = [_hit("doc#1", "vector", 1), _hit("doc#2", "vector", 2)]
    out = {h.cite() for h in rrf(a, b)}
    assert out == {"doc#0", "doc#1", "doc#2"}


def test_RRF_按路去重而不是按条累加() -> None:
    """`from_` 与分数两个字段必须一致地说「一条路只算一次」。

    第一版里 `from_` 去重了、`total` 却在累加——两个字段会对同一情形给出不同答案。
    现实里跑不到（两条路各自返回的片本来就不重复），**但两个字段不一致本身就是缺陷**。
    这条用例反向验过：把 `seen` 那两行删掉，它当场变红（分数变成 2/(k+1)）。
    """
    a = [_hit("doc#0", "bm25", 1), _hit("doc#0", "bm25", 2)]
    got = rrf(a)
    assert len(got) == 1
    assert got[0].from_ == ("bm25",)
    # 只计**第一次**那一条（= 第 1 名的分），不是两条相加。
    # 注意这里比的是 `round(...)`：`rrf` 把分四舍到 6 位，拿 1e-9 去比会红在舍入上
    # （第一版就是这么红的，而它看起来像「去重没生效」）。
    assert got[0].score == round(1 / (RRF_K + 1), 6), got[0].score
    # 两条**不同的路**报同一条片：这时才该拿两份分
    two = rrf([_hit("doc#0", "bm25", 1)], [_hit("doc#0", "vector", 1)])
    assert two[0].score == round(2 / (RRF_K + 1), 6), two[0].score
    assert two[0].from_ == ("bm25", "vector")


def test_k_变小时更偏尖子而不是共识() -> None:
    """k 是一个会改变结论的常数：60 时「两条路都同意」赢，1 时「有一条路的第一名」赢。

    能翻过来的那一对是**（第 1 ＋ 第 8）对（第 2 ＋ 第 3）**——
    第一版这里写的是「（第 1 ＋ 没有）对（第 2 ＋ 第 3）」，那一对在两个 k 下都是一个次序，
    用例当场红。这也是一句提醒：**「k 变小时偏尖子」不是一句可以随口说的话，
    它只在一段区间里成立**（要拿三个以上的 k 去扫才知道区间在哪）。
    """
    def _score(pair, k):
        return sum(1 / (k + p) for p in pair if p)
    assert _score((2, 3), 60) > _score((1, 8), 60)
    assert _score((1, 8), 1) > _score((2, 3), 1)


def test_融合的实际形状_与字面路逐条相同() -> None:
    """正文说「5.1 那四条上融合一条都没多」——这里是它的机械形态。"""
    r = _retriever()
    same = 0
    for q in QUESTIONS:
        bm = [h.cite() for h in r.search(q.text, k=TOP_K, mode="bm25")]
        hy = [h.cite() for h in r.search(q.text, k=TOP_K, mode="hybrid")]
        same += 1 if bm == hy else 0
    assert same >= 3, f"只有 {same}/4 条与字面路相同，融合的读数要重测"


# ------------------------------------------------------------------ 2 尺度
def test_BM25_未归一而余弦有界() -> None:
    r = _retriever()
    bm = bm25_hits(r.index, QUESTIONS[0].text, DEPTH)
    ve = vector_hits(r.embedder, r.store, r.chunks, QUESTIONS[0].text, DEPTH)
    assert bm and ve
    assert max(h.score for h in bm) > 1.0, "BM25 是未归一的分，应当能超过 1"
    assert all(-1.0 - 1e-9 <= h.score <= 1.0 + 1e-9 for h in ve), "余弦必须在 [-1, 1]"


def test_加权和会退化成尺度大的那一条路() -> None:
    """四条问题里至少三条：`0.5·BM25 + 0.5·余弦` 的前 3 与 BM25 序完全相同。

    这是「为什么用 RRF 而不是加权和」的可测证据。**把 BM25 的分数乘上任何常数，
    这条断言都不该变**——所以它测的是「尺度差」而不是某个具体数值。
    """
    r = _retriever()
    same = 0
    for q in QUESTIONS:
        bm = {h.cite(): h.score for h in bm25_hits(r.index, q.text, DEPTH)}
        ve = {h.cite(): h.score for h in vector_hits(r.embedder, r.store, r.chunks, q.text, DEPTH)}
        keys = list(dict.fromkeys(list(bm) + list(ve)))
        w = sorted(keys, key=lambda c: (-(0.5 * bm.get(c, 0) + 0.5 * ve.get(c, 0)), c))
        only = sorted(keys, key=lambda c: (-bm.get(c, 0), c))
        same += 1 if w[:TOP_K] == only[:TOP_K] else 0
    assert same >= 3, f"只有 {same}/4 条退化，尺度差的读数要重测"


# ------------------------------------------------------------------ 3 改写
def test_改写是追加而不是替换() -> None:
    text = Q3.text
    new_text, fired = rewrite(text)
    assert new_text.startswith(text)
    assert fired == ("连点两下",)
    assert new_text != text


def test_没命中时_query_原样返回() -> None:
    text = QUESTIONS[0].text
    same, fired = rewrite(text)
    assert same == text and fired == ()


def test_改写表右边必须是语料里真有的词() -> None:
    """第一版写的是「幂等 重复请求」，而 `幂等` 在 6 份语料里出现 0 次。

    这类错**不会让任何脚本报错**：改写照样命中、读数照样变化，
    只是「改写有效」这个结论变得不可信。所以它需要一条用例，而不是一句注释。
    """
    blob = "".join(d.text for d in load_corpus())
    missing = [(needle, w) for needle, rep in SYNONYMS for w in rep.split() if w not in blob]
    assert not missing, f"这些词在语料里不存在：{missing}"


def test_改写把两条问题都带回前排() -> None:
    """Q3 从「一片都召不回」到第 2；Q5 从第 3 到第 1。--- 文案里的两个数字都在这条里守。"""
    r = _retriever()
    for text, want, expect_before, expect_after in ((Q3.text, "接口约定", None, 2),
                                                    (Q5_TEXT, Q5_WANT, 3, 1)):
        new_text, _ = rewrite(text)
        assert new_text != text, f"{text} 没有命中改写表"
        before = r.search(text, k=TOP_K)
        after = r.search(new_text, k=TOP_K)
        got_before = next((i + 1 for i, h in enumerate(before) if h.chunk.doc_id == want), None)
        got_after = next((i + 1 for i, h in enumerate(after) if h.chunk.doc_id == want), None)
        assert got_before == expect_before, (text, got_before)
        assert got_after == expect_after, (text, got_after)


def test_真机改写的调用契约是消息列表() -> None:
    """`make_rewriter(call)` 里那个 `call` 必须收到 `[{"role", "content"}, ...]`。

    这是**不联网的真机夹具**：用一个记录参数、直接返回固定文本的假 `call`，
    就能把「消息的**形状**」钉住。它值一条用例的理由很具体：

    - 第一版传的是一整个字符串，而 `app/llm.py` 里那一行是 `roles[m["role"]]`，
      于是 `--real` 一点就跑出 `TypeError: string indices must be integers`；
    - **离线路径永远碰不到这个错**（`call is None` 时走另一支），
      而 `--real` 不进提交门——所以没有这条用例时，
      这个缺陷会一直活到有人真的去真机跑那一天。
    """
    seen: list[object] = []

    def fake_call(messages):
        seen.append(messages)
        return "重复请求 去重\n（顺带一句多余的话）"

    rewriter = make_rewriter(fake_call)
    out, source = rewriter(Q3.text)

    assert seen, "改写没有调用模型"
    assert isinstance(seen[0], list), f"`call` 收到的是 {type(seen[0]).__name__}，不是消息列表"
    assert all(isinstance(m, dict) and {"role", "content"} <= set(m) for m in seen[0]), seen[0]
    assert source == ("model",)
    # 多行输出压成一行（换行会把 query 断成两半，BM25 那边会当成两个词）
    assert "\n" not in out and out.startswith(Q3.text)


def test_改写的代价_会带上来别的片() -> None:
    """改写后的 query 会让「搭便车的片」得分——正文里那条 `调用预算#1` 的读数。"""
    r = _retriever()
    new_text, _ = rewrite(Q3.text)
    bm = bm25_hits(r.index, new_text, DEPTH)
    assert bm and bm[0].chunk.doc_id == "接口约定"
    riders = [h for h in bm[1:] if h.score > 0]
    assert riders, "没有搭便车的片，说明这一条读数的演示不成立"


# ------------------------------------------------------------------ 4 重排口径
def test_重排用_3gram_分得开接口约定与接口违约() -> None:
    """这是「为什么是 3-gram」的可测证据：2-gram 上两者几乎一样，3-gram 上零重合。"""
    a, b = "接口约定", "接口违约"
    assert _ngrams(a, 3).isdisjoint(_ngrams(b, 3))
    assert not _ngrams(a, 2).isdisjoint(_ngrams(b, 2))


def test_成对分对称地看两边() -> None:
    a = pair_score("幂等 重复请求", "重复请求返回第一次的结果")
    b = pair_score("重复请求返回第一次的结果", "幂等 重复请求")
    assert abs(a.cover - b.density) < 1e-9 and abs(a.density - b.cover) < 1e-9


def test_空输入得零分而不是异常() -> None:
    for query, text in (("", "有内容"), ("有内容", ""), ("", "")):
        ps = pair_score(query, text)
        assert ps.score == 0.0 and ps.cover == 0.0 and ps.density == 0.0


def test_重排的输出条数是不补齐的() -> None:
    hits = [_hit(f"doc#{i}", "rrf", i + 1, text="发布说明的四段") for i in range(2)]
    assert len(rerank("发布说明的四段", tuple(hits), k=5)) == 2
    assert len(rerank("发布说明的四段", (), k=5)) == 0


def test_重排能把_BM25_认为相关的片判零分() -> None:
    """改写后的 Q3：`调用预算#1` 在 BM25 那边有分、在成对口径上是 0.000000。

    两套口径对「相关」的定义不同——这是正文那一张逐片成对分表的机械形态。
    """
    r = _retriever()
    new_text, _ = rewrite(Q3.text)
    rider = next(h for h in bm25_hits(r.index, new_text, DEPTH)
                 if h.chunk.doc_id == "调用预算")
    assert rider.score > 0, "夹具失效：这条片在 BM25 那边没有分"
    assert pair_score(new_text, rider.chunk.text).score == 0.0


# ------------------------------------------------------------------ 5 重排边界
def test_重排改变不了候选集() -> None:
    """未改写的 Q3：目标文档不在候选集里，所以成对分的最高值是 0。"""
    r = _retriever()
    cand = r.candidates(Q3.text, depth=DEPTH)
    assert not any(h.chunk.doc_id == Q3.want_doc for h in cand)
    assert max(pair_score(Q3.text, h.chunk.text).score for h in cand) == 0.0
    assert not any(h.chunk.doc_id == Q3.want_doc
                   for h in rerank(Q3.text, cand, k=TOP_K)), "重排不该凭空造出候选集外的片"


def test_重排把第_2_名提到第_1_名() -> None:
    r = _retriever()
    new_text, _ = rewrite(Q3.text)
    cand = r.candidates(new_text, depth=DEPTH)
    assert cand[0].chunk.doc_id == "调用预算"
    assert rerank(new_text, cand, k=TOP_K)[0].chunk.doc_id == "接口约定"


# ------------------------------------------------------------------ 6 候选深度
def test_候选集大小不等于_depth() -> None:
    """两条路各出 depth 条，并集去重后是 3–13 片。

    这里用的是 Q2 而不是 Q3：**Q3 在 depth=10 时恰好也是 10 片**（字面路全空，
    向量路独自填满 depth），拿它做夹具就分不出「并集」与「单条路」——
    第一版就是这么写错的，用例红在了夹具上而不是结论上。
    """
    r = _retriever()
    q2 = next(q for q in QUESTIONS if q.qid == "Q2")
    assert len(r.candidates(q2.text, depth=DEPTH)) == 13
    assert 0 < len(r.candidates(Q3.text, depth=DEPTH)) <= 2 * DEPTH


def test_加深候选会把目标文档带进候选集() -> None:
    """depth=10 时它不在，depth=15（全库）时它以第 11 名出现。"""
    r = _retriever()
    assert not any(h.chunk.doc_id == Q3.want_doc
                   for h in r.candidates(Q3.text, depth=DEPTH))
    deep = r.candidates(Q3.text, depth=len(r.chunks))
    pos = [i + 1 for i, h in enumerate(deep) if h.chunk.doc_id == Q3.want_doc]
    assert pos and pos[0] == 11, pos


def test_深度扫描的花销等于_depth() -> None:
    hits = [_hit(f"doc#{i}", "rrf", i + 1, text=f"发布说明 第 {i} 段") for i in range(6)]
    rows = depth_sweep("发布说明", tuple(hits), k=TOP_K, depths=(1, 2, 4, 6))
    assert [row["pairs"] for row in rows] == [1, 2, 4, 6]
    assert [row["n"] for row in rows] == [1, 2, 3, 3]


# ------------------------------------------------------------------ 7 端到端
def test_离线脚本跑通并打印正文引用的读数() -> None:
    proc = subprocess.run([sys.executable, "scripts/retrieve_reader.py", "--offline"],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", timeout=180)
    assert proc.returncode == 0, proc.stdout[-600:]
    out = proc.stdout
    for line in ("① 融合的形状", "② 三条路对照", "③ 融合的两条边界",
                 "④ 改写", "⑤ 重排", "⑥ 候选深度", "⑦ 花销账"):
        assert line in out, f"缺这一组：{line}"
    # 正文直接引用的那几条读数，一条也不许漂
    for line in ("5.1 那四条：字面 2/3　向量 2/3　融合 2/3",
                 "向量单独做对了（第 1），融合把它压到了第 3",
                 "目标文档名次：改写前 不在 → 改写后 2",
                 "0.000000",
                 "目标文档名次：2 → 1"):
        assert line in out, f"读数漂了：{line}"


def test_自检夹具全绿() -> None:
    proc = subprocess.run([sys.executable, "scripts/retrieve_reader.py", "--self-test"],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", timeout=120)
    assert proc.returncode == 0, proc.stdout[-400:]
    assert "自检 10/10 通过" in proc.stdout


def test_语料里没有幂等这个词() -> None:
    """这条用例是**反向守**：`SYNONYMS` 里曾经写过「幂等」，而全库没有这个词。

    留着它有两个作用：一是证明上面那条用例真的能拦下人（把「幂等」加回表里它就红），
    二是给读者一个可核对的锚——**这条读数是量出来的，不是推理出来的。**
    """
    blob = "".join(d.text for d in load_corpus())
    assert re.search(r"幂等", blob) is None


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_retrieve.py`。"""
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    bad = 0
    for fn in fns:
        try:
            fn()
            print(f"  ✔ {fn.__name__}")
        except Exception as exc:                                   # noqa: BLE001
            bad += 1
            print(f"  ✖ {fn.__name__}｜{type(exc).__name__}: {exc}")
    print(f"\n{len(fns) - bad}/{len(fns)} 通过")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(run())
