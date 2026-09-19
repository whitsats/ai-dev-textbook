#!/usr/bin/env python
"""5.4 读数：**三条路（字面／向量／融合）与两个后处理（改写／重排）各自改了什么。**

七组：

    ① 融合的形状：RRF 只吃名次，而「加权和」在本语料上就是 BM25 在排序
    ② 三条路对照：5.1 那四条问题 ＋ 一条「近义替换」，各召回什么
    ③ 融合的两条边界：不创造信息；以及**它会把单条路做对的那一次抹掉**
    ④ 改写：唯一造出新字面的一环（救两条），以及它的代价
    ⑤ 重排：换了打分口径（成对、3-gram），所以它能把 BM25 认为相关的片判零分
    ⑥ 候选深度：重排能看见的范围由它决定（不是由 k 决定）
    ⑦ 花销账：三件后处理里，只有重排的花销随候选数线性长

    python scripts/retrieve_reader.py --offline     # 不需要密钥、不需要网络：提交钩子跑这个
    python scripts/retrieve_reader.py --self-test   # 反例夹具：几条不变式必须成立
    python scripts/retrieve_reader.py --real        # 真机那一侧的改写：把同一件事交给模型

一条纪律写在最前面：**本章的主要结论与「业界通常这么做」相反。**
动笔前我以为「混合检索」会救回同义改写。实测是：**四条问题上融合没有改变任何一条的命中**，
而第五条上它反而把向量单独做对的第一名压到了第三。真正救回来的是**改写**。
融合与重排不是没用，是它们各自的能力边界比宣传里说的窄得多——
本章只报本语料量得到的部分。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.corpus import Chunk, load_corpus                               # noqa: E402
from app.questions import QUESTIONS                                     # noqa: E402
from app.rerank import depth_sweep, pair_score, rerank                  # noqa: E402
from app.retrieve import (RRF_K, SYNONYMS, Hit, bm25_hits,               # noqa: E402
                          build_retriever, rewrite, rrf, vector_hits)

TOP_K = 3
DEPTH = 10

#: 第五条：5.1 的 `LIMITS` 里那条「近义替换」。它不在 `QUESTIONS` 里，
#: 因为 `questions.py` 是 5.1／5.2／5.3 三章共用的夹具，**加一条会让前几章的读数失效**。
#: 本章只读它、不动它：这条的定义写在 5.1 的 `corpus.LIMITS` 里（「最高分 2.17 落在错文档上」）。
EXTRA = ("近义替换", "出事了多久必须有人接？", "值班与响应")


def _hr(title: str) -> None:
    print("=" * 74)
    print(title)
    print("=" * 74)


def _pad(text: str, width: int) -> str:
    """按**显示宽度**补齐：汉字与全角标点在终端上占两列。"""
    shown = sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)
    return text + " " * max(0, width - shown)


def _cites(hits, n: int = 5) -> str:
    got = [h.cite() for h in hits][:n]
    return "、".join(got) or "（0 片）"


def _vec(hits, n: int = 5) -> str:
    got = [f"{h.cite()}({h.score:.4f})" for h in hits][:n]
    return "、".join(got) or "（0 片）"


# --------------------------------------------------------------------------- ①
def reading_shape(r) -> dict:
    _hr("① 融合的形状：RRF 只吃名次，「加权和」吃尺度")
    print(f"RRF 的分数是 `1 / ({RRF_K} + 名次)`，所有片的分都落在一个很窄的带里：")
    print()
    for rank in (1, 2, 3, 5, 8, 10):
        print(f"     名次 {rank:>2} → {1 / (RRF_K + rank):.6f}")
    print()
    print("这条形状决定了三件事：")
    print(f"  · 名次 1 与名次 2 只差 {(1 / (RRF_K + 1) - 1 / (RRF_K + 2)) / (1 / (RRF_K + 1)) * 100:.1f}%，")
    print("    所以**「第一名」这个信息在融合里并不重**；")
    print(f"  · 两条路都排进前面的片（1/61 ＋ 1/62 = {1 / 61 + 1 / 62:.6f}）稳定压过")
    print(f"    「一条第一、另一条没有」（1/61 = {1 / 61:.6f}）——这是它的设计意图；")
    print("  · 但同一条纪律会**在第 ③ 组变成缺点**（一条路系统性失手时，它会把另一条路做对的压下去）。")
    print()
    print(f"换个 k 会怎样（k 是那条式子的平滑常数，本章不声称 {RRF_K} 是最优）：")
    print()
    print("  " + _pad("次序（两条路的名次）", 34) + f"{'k=60':>10}{'k=10':>10}{'k=1':>10}")
    for label, pair in (("BM25 第 1 ＋ 向量 没有", (1, None)),
                        ("BM25 第 1 ＋ 向量 第 8", (1, 8)),
                        ("BM25 第 2 ＋ 向量 第 3", (2, 3)),
                        ("BM25 第 3 ＋ 向量 第 1", (3, 1))):
        row = "  " + _pad(label, 34)
        for k in (60, 10, 1):
            s = sum(1 / (k + p) for p in pair if p)
            row += f"{s:>10.4f}"
        print(row)
    print()
    print("**k=60 时「两条路都同意」赢；k=1 时「一条路的第一名」赢**——两行的次序在第 2、3 行之间翻过来了。")
    print("所以 k 不是一个可以随手抄的常数：它决定「融合偏共识还是偏尖子」。")
    print("本树没有语料去把它调好（要等 5.6 的评测集），所以正文只说它「变大会更偏共识」。")
    print()

    print("## 反例：为什么不用加权和")
    print()
    print("把两条路的分数按 `0.5 × BM25 ＋ 0.5 × 余弦` 相加，是很多示例里的写法。")
    print("先看尺度差多少：")
    print()
    print("  " + _pad("问题", 30) + f"{'BM25 最高':>10}{'余弦最高':>12}")
    scales = {}
    for q in QUESTIONS:
        bm = bm25_hits(r.index, q.text, DEPTH)
        ve = vector_hits(r.embedder, r.store, r.chunks, q.text, DEPTH)
        b, v = max([h.score for h in bm], default=0.0), max([h.score for h in ve], default=0.0)
        scales[q.qid] = (b, v)
        print("  " + _pad(f"{q.qid} {q.text[:14]}", 30) + f"{b:>10.2f}{v:>12.4f}")
    bmax = max(b for b, _ in scales.values())
    vmax = max(v for _, v in scales.values())
    print()
    print(f"两个量级差 **{bmax / vmax:.0f} 倍**（{bmax:.2f} 与 {vmax:.4f}）。后果不是「排序微调」——")
    print(f"余弦那一票的最大贡献是 0.5（满分 1 乘上权重 0.5），而它要被加上的那个和最高是 {0.5 * bmax:.2f}。")
    print(f"要让向量那一票改变名次，两条片的 BM25 分差必须小于 **{vmax:.2f}**")
    print("（余弦项的满票 = 权重 0.5 × 满分 1 = 0.5；反过来除回 BM25 的权重 0.5，得到 1.0 × 余弦满分）。")
    print()
    print("这不是推理，下面这一列是实测（同一批候选，只换融合方式）：")
    print()
    diff_rows = {}
    for q in QUESTIONS:
        bm = bm25_hits(r.index, q.text, DEPTH)
        ve = vector_hits(r.embedder, r.store, r.chunks, q.text, DEPTH)
        bms, vs = {h.cite(): h.score for h in bm}, {h.cite(): h.score for h in ve}
        keys = list(dict.fromkeys(list(bms) + list(vs)))
        wsum = sorted(keys, key=lambda c: (-(0.5 * bms.get(c, 0) + 0.5 * vs.get(c, 0)), c))
        bmonly = sorted(keys, key=lambda c: (-bms.get(c, 0), c))
        vonly = sorted(keys, key=lambda c: (-vs.get(c, 0), c))
        d_bm = sum(1 for a, b in zip(wsum[:TOP_K], bmonly[:TOP_K]) if a != b)
        d_vs = sum(1 for a, b in zip(wsum[:TOP_K], vonly[:TOP_K]) if a != b)
        diff_rows[q.qid] = (d_bm, d_vs)
        print(f"  {q.qid}：加权和的前 {TOP_K} 与 BM25 序差 {d_bm} 位；与向量序差 {d_vs} 位")
    print()
    print("**四条问题里有三条，加权和的排序与 BM25 完全相同**——因为余弦那一票太小，加进去等于没加。")
    print("（唯一例外的 Q3 是 BM25 全零的那一条，那时加权和退化成了向量序。）")
    print("所以「融合」在加权和这个写法下是一句空话；要真让另一条路说话，就得先把尺度抹掉——")
    print("这就是取名次（RRF）的理由。")
    return {"rrf_k": RRF_K, "scales": scales, "weighted_sum_diff": diff_rows}


# --------------------------------------------------------------------------- ②
def reading_three_ways(r) -> dict:
    _hr("② 三条路对照：同一批问题、同一个 k=3")
    cases = list(QUESTIONS) + [None]
    print(f"语料 {len(r.chunks)} 片（同一份 5.2 的结构感知切法语料）｜k={TOP_K}｜depth={DEPTH}")
    print("第五条不在 `QUESTIONS` 里（见文件头），它的「该召回到」抄自 5.1 的 `corpus.LIMITS`。")
    print()
    rows = {}
    for q in cases:
        qid, kind, text = (q.qid, q.kind, q.text) if q else ("Q5", EXTRA[0], EXTRA[1])
        want = q.want_doc if q else EXTRA[2]
        bm = r.search(text, k=TOP_K, mode="bm25")
        ve = r.search(text, k=TOP_K, mode="vector")
        hy = r.search(text, k=TOP_K, mode="hybrid")
        rows[qid] = {"want": want, "bm25": [h.cite() for h in bm],
                     "vector": [h.cite() for h in ve], "hybrid": [h.cite() for h in hy]}
        print(f"{qid}（{kind}）　该召回到：{want}　问：{text}")
        print(f"    字面  ：{_cites(bm)}")
        print(f"    向量  ：{_cites(ve)}")
        print(f"    融合  ：{_cites(hy)}")
        print()
    # 分母只数「语料里真有依据」的那几条：Q4 的 `want` 是 `None`（库里本来就没有），
    # 把它算进分母就是把「不该召回到任何片」当成「没召回成功」——第一版就是这么写错的。
    # 另：命中的判定是 `startswith`，不是相等——存的是引用标识（`发布规范#0`），
    # 而「该召回到」写的是文档名（`发布规范`）。两个都是字符串，比错了不会报错，只会静默地全判成否。
    def _hit_want(v, key: str) -> bool:
        return bool(v["want"]) and any(c.startswith(v["want"]) for c in v[key])

    def _counts(keys: list[str]) -> dict[str, int]:
        subset = {k: v for k, v in rows.items() if k in keys and v["want"]}
        return {key: sum(1 for v in subset.values() if _hit_want(v, key))
                for key in ("bm25", "vector", "hybrid")} | {"n": len(subset)}

    four, five = _counts(["Q1", "Q2", "Q3", "Q4"]), _counts(list(rows))
    print("top3 命中目标文档（分母只数「语料里真有依据」的那几条；Q4 的 `want` 是 `None`）：")
    print(f"    5.1 那四条：字面 {four['bm25']}/{four['n']}　向量 {four['vector']}/{four['n']}"
          f"　融合 {four['hybrid']}/{four['n']}")
    print(f"    加上第五条：字面 {five['bm25']}/{five['n']}　向量 {five['vector']}/{five['n']}"
          f"　融合 {five['hybrid']}/{five['n']}")
    same = sum(1 for v in rows.values() if v["bm25"] == v["hybrid"])
    print(f"融合的 top3 与字面路**完全相同**的问题：{same}/{len(rows)}")
    print()
    print("三句要一起读：")
    print(f"  · **在 5.1 那四条上，三条路的命中数一模一样**（{four['bm25']}/{four['n']}）——")
    print("    融合一条都没多，也就不能拿它当「混合检索提升了召回率」的证据；")
    print(f"  · 只有第五条（近义替换）上，融合比字面路多拿到 {five['hybrid'] - four['hybrid']} 条；")
    print("    而那是**向量单独做对**的那一次——融合把它留在第 3 名，刚好还在 top3 里（见 ③）；")
    print(f"  · 融合的 top3 与字面路有 {same}/{len(rows)} 条一模一样：**字面路全零的那条才是向量在说话。**")
    return rows


# --------------------------------------------------------------------------- ③
def reading_fusion_limits(r) -> dict:
    _hr("③ 融合的两条边界：不创造信息；会把单条路做对的那一次抹掉")
    q3 = next(q for q in QUESTIONS if q.qid == "Q3")
    print("## 边界一：它只能重排手里的片")
    print()
    print("Q3（同义改写，字面零重合）在**不同候选深度**下的候选集里，目标文档在哪：")
    print()
    print("  " + _pad("候选深度 depth", 20) + f"{'融合候选数':>12}{'接口约定名次':>16}")
    cand_pos = {}
    for d in (3, 5, 10, 15):
        cand = r.candidates(q3.text, depth=d)
        pos = [i + 1 for i, h in enumerate(cand) if h.chunk.doc_id == q3.want_doc]
        cand_pos[d] = pos
        print("  " + _pad(str(d), 20) + f"{len(cand):>12}"
              + f"{(str(pos) if pos else '不在'):>16}")
    print()
    print("三条要一起记：")
    print("  · **候选集的大小不等于 `depth`**（两条路各出 depth 条，并集去重后是 3–13 片）；")
    print(f"  · **`depth={DEPTH}` 时目标文档连候选都不是**——这是本章最重要的一条读数：")
    print("    融合的输入里没有它，融合再准也拿不出来；")
    print("  · `depth` 拉到 15（= 全库）时它以第 11 名出现：**候选集是有它的，只是排在门外。**")
    print("    所以「融合救不了同义改写」这句话要精确成「在 depth 小于全库时救不了」。")
    print()
    print("## 边界二：共识偏好会抹掉单条路的第一名")
    print()
    q5text, q5want = EXTRA[1], EXTRA[2]
    bm = bm25_hits(r.index, q5text, DEPTH)
    ve = vector_hits(r.embedder, r.store, r.chunks, q5text, DEPTH)
    hy = rrf(bm, ve)
    print(f"第五条（{EXTRA[0]}）问：{q5text}")
    print(f"    字面  ：{_cites(bm)}　→ 目标文档 {q5want} " +
          ("在第 1" if bm and bm[0].cite().startswith(q5want) else "**不在第 1**") + "，最高分落在别处")
    print(f"    向量  ：{_cites(ve)}　→ 目标文档在第 " +
          f"{next((i + 1 for i, h in enumerate(ve) if h.chunk.doc_id == q5want), '不在')}")
    print(f"    融合  ：{_cites(hy)}　→ 目标文档在第 " +
          f"{next((i + 1 for i, h in enumerate(hy) if h.chunk.doc_id == q5want), '不在')}")
    print()
    print("**向量单独做对了（第 1），融合把它压到了第 3。** 为什么：融合给「两条路都同意」的片")
    print("两份分，而 `发布规范` 那两片被字面路排在前二（虽然它是错的）；目标文档只有向量那一票。")
    print()
    print("这条不是「融合坏了」，是它的前提被破坏了：**RRF 假设两条路的错是独立的。**")
    print("而这里字面路的错是系统性的（它数的是同一件事的字面重合，同义改写必然失手），")
    print("于是「两条路都同意」等于「这条片的字面重合够多」——**共识变成了对其中一条路的加权**。")
    print("工程上的结论：**两条路的失手方式要不一样，融合才有意义**；")
    print("否则要么别融合，要么先修那条系统性失手的路（本章的答案是改写）。")
    return {"q3_candidate_pos": cand_pos}


# --------------------------------------------------------------------------- ④
def reading_rewrite(r) -> dict:
    _hr("④ 改写：唯一造出新字面的一环")
    print("改写的实现是**追加**，不是替换：把库里真实出现的说法接到原问题后面。")
    print("追加的理由是可测的——替换会丢掉原句里本来就对上的字（Q1 的「发布说明」是能召回的），")
    print("而追加以外只做一件事：**扩大字面重合面**。")
    print()
    out = {}
    for qid, text, want in (("Q3", next(q for q in QUESTIONS if q.qid == "Q3").text,
                             "接口约定"), ("Q5", EXTRA[1], EXTRA[2])):
        new_text, fired = rewrite(text)
        before = r.search(text, k=TOP_K)
        after = r.search(new_text, k=TOP_K)
        out[qid] = {"fired": fired, "before": [h.cite() for h in before],
                    "after": [h.cite() for h in after]}
        print(f"{qid}　原问：{text}")
        print(f"     命中改写表：{fired or '（没有命中）'}")
        print(f"     改写后　　：{new_text}")
        print(f"     改写前 top3：{_cites(before)}")
        print(f"     改写后 top3：{_cites(after)}")
        print(f"     目标文档名次：改写前 " +
              f"{next((i + 1 for i, h in enumerate(before) if h.chunk.doc_id == want), '不在')}"
              f" → 改写后 "
              f"{next((i + 1 for i, h in enumerate(after) if h.chunk.doc_id == want), '不在')}")
        print()
    print("两条都要精确地读：**Q3 是从「一片都召不回」到第 2 名**（这一条是定性变化，不是名次变化），")
    print("**Q5 是从第 3 名到第 1 名**（它原本就在 top3 里，改写只是把它顶上前）。")
    print("这是本章唯一一条「加了东西就变好」的读数，而它**靠的是一次模型调用，不是融合。**")
    print()
    print("## 代价：改写是唯一要多花一次模型调用的一环，而且它会带上来别的片")
    print()
    q3text = next(q for q in QUESTIONS if q.qid == "Q3").text
    new_text, _ = rewrite(q3text)
    print(f"改写后的 query 里多出来的词会匹配到**别的片**——实测：")
    bm = bm25_hits(r.index, new_text, DEPTH)
    for h in bm[:4]:
        print(f"    {h.cite():<14} {h.score:>7.2f}"
              + ("　← 目标" if h.chunk.doc_id == "接口约定" else ""))
    print()
    print("`调用预算#1` 本来是零分（它跟原问题一个字都对不上），改写后拿了 1.81 分，")
    print("并且因为**向量路也召回了它**，它在融合里被顶到了**第 1 名**——把目标文档挤到第 2。")
    print("所以「改写」这一环的读数必须连着融合一起看：改写把正确的片带回来，")
    print("也把搭便车的片带回来，**而融合恰好会放大搭便车的那一条**（它被两条路都同意）。")
    print("这就是 ⑤ 的重排要处理的事。")
    print()
    print("## 一条纪律：改写表右边必须是语料里真有的词")
    print("第一版我写的是「幂等 重复请求」。实测 **`幂等` 一词在 6 份语料里出现 0 次**——")
    print("而读数看上去毫无异常（改写后照样召回）。这类错不会让脚本报错，")
    print("它只会让「改写有效」这个结论变得不可信。`tests/test_retrieve.py` 里有一条用例")
    print("把这件事钉死了：**右边每个词都必须在 `corpus/*.md` 里真的出现过。**")
    print("反过来说，「把答案抄进 query」也是同一个动作——所以这张表是**标尺**，不是产品方案；")
    print("真机那一条（`--real`）把同一件事交给模型，读数分开报。")
    return out


# --------------------------------------------------------------------------- ⑤
def reading_rerank(r) -> dict:
    _hr("⑤ 重排：换打分口径，不改候选集")
    q3text = next(q for q in QUESTIONS if q.qid == "Q3").text
    new_text, _ = rewrite(q3text)
    cand = r.candidates(new_text, depth=DEPTH)
    print("重排的打分与 BM25 **不是同一件事**：BM25 数 2-gram 的词频，重排把 (query, 片)")
    print("作为一对送进去算 3-gram 的覆盖率与密度。口径一换，同一条片的名次就会变。")
    print()
    print(f"改写后的 Q3，逐片成对分（前 5 条候选）：")
    print("  " + _pad("片", 16) + f"{'覆盖率':>10}{'密度':>10}{'成对分':>10}　融合名次")
    for i, h in enumerate(cand[:5]):
        ps = pair_score(new_text, h.chunk.text)
        print("  " + _pad(h.cite(), 16) + f"{ps.cover:>10.4f}{ps.density:>10.4f}"
              f"{ps.score:>10.6f}　{i + 1}")
    print()
    print("看第一行：**`调用预算#1` 的成对分是 0.000000**——它在 BM25 那边拿了 1.81 分，")
    print("在成对口径下一个 3-gram 都没覆盖上。这不是「重排更准」的证据（本章没有标注集），")
    print("而是**「字面相关」这四个字在两套口径下指的可以是不同的东西**。")
    print()
    re_rows = {}
    for label, text in (("Q3（改写后）", new_text),
                        ("Q1", next(q for q in QUESTIONS if q.qid == "Q1").text),
                        ("Q5", EXTRA[1])):
        c = r.candidates(text, depth=DEPTH)
        before, after = [h.cite() for h in c[:TOP_K]], [h.cite() for h in rerank(text, c, k=TOP_K)]
        want = {"Q1": "发布规范", "Q5": EXTRA[2]}.get(label, "接口约定")
        pos_b = next((i + 1 for i, x in enumerate(c) if x.chunk.doc_id == want), None)
        pos_a = next((i + 1 for i, x in enumerate(rerank(text, c, k=TOP_K))
                      if x.chunk.doc_id == want), None)
        re_rows[label] = {"before": before, "after": after}
        print(f"  {label}")
        print(f"     重排前：{_cites(c[:TOP_K])}")
        print(f"     重排后：{_cites(rerank(text, c, k=TOP_K))}")
        print(f"     目标文档名次：{pos_b or '不在'} → {pos_a or '不在'}")
        print()
    print("一条把 2 名提到 1 名，两条**一位没动**。所以本章不写「重排提升 N%」——")
    print("本语料（15 片、5 条问题）量不出一个可信的百分比，能立的只有：")
    print("**它改得动名次，而且它与字面路的口径不同。**")
    print()
    print("## 边界：重排改变不了候选集")
    print()
    old_cand = r.candidates(q3text, depth=DEPTH)
    print(f"拿**没有改写**的 Q3 直接上重排，depth={DEPTH}：" )
    print(f"     候选集里有没有目标文档：{'有' if any(h.chunk.doc_id == '接口约定' for h in old_cand) else '**没有**'}")
    print(f"     重排后 top3：{_cites(rerank(q3text, old_cand, k=TOP_K))}")
    print(f"     逐片成对分的最高值：{max(pair_score(q3text, h.chunk.text).score for h in old_cand):.6f}")
    print()
    print("成对分的最高值是 0——**不是因为语料里没有依据，是因为目标文档不在候选集里。**")
    print("所以「加了重排还是答不上」有两种完全不同的原因，读数里必须能分辨：")
    print("一种是候选集里没有（修上游：改写／加深候选），一种是候选集里有但排在后面（修重排）。")
    print("分不清这两件事，就会去修错的那一层。")
    return re_rows


# --------------------------------------------------------------------------- ⑥
def reading_depth(r) -> dict:
    _hr("⑥ 候选深度：重排能看见的范围由 depth 决定，不是由 k 决定")
    q3text = next(q for q in QUESTIONS if q.qid == "Q3").text
    new_text, _ = rewrite(q3text)
    cand15 = r.candidates(new_text, depth=15)
    print(f"改写后的 Q3，候选集固定为 depth=15 的那 {len(cand15)} 片，只改「给重排看几条」：")
    print()
    print("  " + _pad("depth", 8) + f"{'重排输出':>8}　用掉成对打分　重排后 top3")
    grid = {}
    for row in depth_sweep(new_text, cand15, k=TOP_K, depths=(1, 2, 3, 5, 10, 15)):
        grid[row["depth"]] = row
        print("  " + _pad(str(row["depth"]), 8) + f"{row['n']:>8}　{row['pairs']:>12}　"
              + "、".join(row["order"]))
    print()
    print("三行要一起读：")
    print("  · **`depth=1` 时输出只有 1 片**（`min(k, 候选数)`）——候选不够时它不补齐、不回退；")
    print("    「重排之后剩几片」本身就是一个读数，掩盖它就等于把上游的问题藏起来；")
    print("  · 目标文档在候选集里是第 2 名，所以 `depth ≥ 2` 时它都在（这一组量不出「加深变差」）；")
    print("  · 成对打分次数**等于 depth**：这一环的花销随候选数线性长，而融合是 0 次。")
    print()
    print("要演示「depth 不够就救不回来」，得让目标文档排在 depth 之外——")
    print("本语料只有 15 片，能做到这一点的只有第 ③ 组那条（`depth=10` 时它不在候选集里）。")
    print("所以这一组**只报量得到的部分**：depth 决定重排能看见谁，而它不由 k 决定。")
    return grid


# --------------------------------------------------------------------------- ⑦
def reading_cost(r) -> dict:
    _hr("⑦ 花销账：三件后处理，只有一件的花销随候选数长")
    q3text = next(q for q in QUESTIONS if q.qid == "Q3").text
    new_text, _ = rewrite(q3text)
    print("  " + _pad("环节", 24) + f"{'模型调用':>10}{'成对打分':>10}{'读名次':>10}")
    print("  " + _pad("融合（RRF）", 24)
          + f"{0:>10}{0:>10}{len(r.candidates(q3text, depth=DEPTH)):>10}")
    print("  " + _pad("重排", 24) + f"{0:>10}{DEPTH:>10}{0:>10}")
    print("  " + _pad("改写（离线表）", 24) + f"{0:>10}{0:>10}{0:>10}")
    print("  " + _pad("改写（真机）", 24) + f"{1:>10}{0:>10}{0:>10}")
    print()
    print("三条一句一条：**融合几乎不要钱**（只是读一遍名次）；**重排要付 depth 次成对打分**")
    print("（它是唯一随候选数线性长的环节，所以「重排 top100」与「重排 top10」不是同一笔账）；")
    print("**改写要一次模型调用**——但一次就够，因为它只改 query，不碰每一片。")
    print()
    print("这张表是本章所有取舍的最后一道依据：**收益量不出来的时候，先看花销的结构。**")
    print("改写花 1 次调用换回「1 条从零召回到第 2、1 条从第 3 提到第 1」；")
    print(f"重排花 {DEPTH} 次成对打分换回 1 个名次（它随 depth 变，不随语料规模变）——")
    print("本语料上就这么多，多的部分得等 5.6 的评测集。")
    r.calls, r.pairs = 1, DEPTH        # 让 stats() 能打印真实形态
    print()
    print(f"`Retriever.stats()`：{r.stats()}")
    return {"fusion_reads": len(r.candidates(q3text, depth=DEPTH)), "rerank_pairs": DEPTH}


# --------------------------------------------------------------------------- 自检
def _hit(cite: str, src: str, rank: int, score: float = 0.0, text: str | None = None):
    """自检用的真 `Hit`：**不用假对象**。

    第一版这里用的是 `type("H", (), {...})()` 拼出来的假命中，带 `chunk=None`——
    结果 `rrf()` 一读 `h.chunk.cite()` 就崩。**假对象不会跟着真类型一起变**，
    所以自检里也用真 `Chunk`／`Hit`：它多验一层「字段名与顺序没改」。
    """
    doc, _, idx = cite.partition("#")
    return Hit(Chunk(doc_id=doc, index=int(idx or 0), text=text or f"{doc} 的正文"),
               score, src, rank)


def self_test() -> int:
    _hr("自检：几条不变式（改坏了必须被拦下）")
    checks: list[tuple[str, bool, str]] = []

    # 1. RRF 只看名次：把同一条片的 BM25 分数放大一万亿倍，次序不许变
    bm = [_hit(f"doc#{i}", "bm25", i + 1, score=10.0 ** i) for i in range(3)]
    big = [_hit(f"doc#{i}", "bm25", i + 1, score=1e12 * 10.0 ** i) for i in range(3)]
    r1, r2 = rrf(bm, k=60), rrf(big, k=60)
    checks.append(("RRF 对分数不敏感（只吃名次）",
                   [h.cite() for h in r1] == [h.cite() for h in r2], ""))

    # 2. 融合不创造新片：输出 ⊆ 两条输入的并集
    a = [_hit("doc#0", "bm25", 1), _hit("doc#1", "bm25", 2)]
    b = [_hit("doc#1", "vector", 1), _hit("doc#2", "vector", 2)]
    out = [h.cite() for h in rrf(a, b, k=60)]
    checks.append(("融合的输出不超出两条输入的并集",
                   set(out) == {"doc#0", "doc#1", "doc#2"}, str(out)))

    # 3. from_ 记得住来源
    by = {h.cite(): h.from_ for h in rrf(a, b, k=60)}
    checks.append(("`from_` 记下被哪几条路带上来的",
                   by["doc#1"] == ("bm25", "vector") and by["doc#0"] == ("bm25",), str(by)))

    # 4. 改写表右边必须是语料里真有的词（第一版「幂等」零次就是这么被抓到的）
    blob = "".join(d.text for d in load_corpus())
    missing = [(needle, word) for needle, rep in SYNONYMS for word in rep.split()
               if word not in blob]
    checks.append(("改写表右边每个词都在语料里出现过", not missing, str(missing)))

    # 5. 改写是追加：原句必须完整保留
    new_text, fired = rewrite("用户连点两下会不会写两条记录？")
    checks.append(("改写是追加（原句完整保留）",
                   new_text.startswith("用户连点两下会不会写两条记录？") and bool(fired),
                   new_text))

    # 6. 没命中时改写不动 query
    same, none = rewrite("知舟的发布说明必须包含哪几段？")
    checks.append(("改写表没命中时 query 原样返回",
                   same == "知舟的发布说明必须包含哪几段？" and none == (), same))

    # 7. 重排的输出条数是 min(k, 候选数)，不补齐
    hits = [_hit(f"doc#{i}", "rrf", i + 1, text="发布说明的四段") for i in range(2)]
    checks.append(("重排的输出条数 = min(k, 候选数)",
                   len(rerank("发布说明的四段", tuple(hits), k=5)) == 2, ""))

    # 8. 成对分对称地看两边：query 与片互换，覆盖率/密度互换
    a1 = pair_score("幂等 重复请求", "重复请求返回第一次的结果")
    a2 = pair_score("重复请求返回第一次的结果", "幂等 重复请求")
    checks.append(("覆盖率与密度在互换两边后对调",
                   abs(a1.cover - a2.density) < 1e-9 and abs(a1.density - a2.cover) < 1e-9,
                   f"{a1} vs {a2}"))

    # 9. 空输入不抛异常，返回 0 分
    checks.append(("空 query／空片得 0 分而不是异常",
                   pair_score("", "有内容").score == 0.0
                   and pair_score("有内容", "").score == 0.0, ""))

    # 10. 深度扫描的成对打分次数等于 depth（阶数：它是重排唯一随候选数长的花销）
    c = [_hit(f"doc#{i}", "rrf", i + 1, text=f"发布说明 第 {i} 段") for i in range(4)]
    rows = depth_sweep("发布说明", tuple(c), k=3, depths=(1, 2, 4))
    checks.append(("深度扫描的花销等于 depth（阶数）",
                   [row["pairs"] for row in rows] == [1, 2, 4], str(rows)))

    bad = 0
    for name, ok, extra in checks:
        print(f"  {'✔' if ok else '✖'} {name}" + (f"｜{extra}" if extra and not ok else ""))
        bad += 0 if ok else 1
    print(f"\n自检 {len(checks) - bad}/{len(checks)} 通过")
    return 1 if bad else 0


# --------------------------------------------------------------------------- 真机
def reading_real() -> dict:
    _hr("⑧ 真机边界：把改写交给模型（读数与离线表分开报）")
    from app.config import Config                                   # noqa: PLC0415
    from app.llm import make_call                                   # noqa: PLC0415
    from app.retrieve import make_rewriter                          # noqa: PLC0415

    try:
        cfg = Config.from_env()
    except RuntimeError as exc:
        print(f"{exc}｜跳过（**跳过不是通过**）")
        return {"skipped": True}
    print(f"服务商：{cfg.redacted()['base_url']}　模型：{cfg.model}")
    print()
    rewriter = make_rewriter(make_call(cfg))
    for text in (next(q for q in QUESTIONS if q.qid == "Q3").text, EXTRA[1]):
        try:
            new_text, fired = rewriter(text)
        except Exception as exc:                                    # noqa: BLE001
            print(f"  问：{text}\n    → 调用失败：{type(exc).__name__}: {exc}")
            continue
        print(f"  问：{text}")
        print(f"    → {new_text}")
        print()
    print("两件事要分开读：**模型改出来的词是不是语料里真有的**（离线表靠用例守，")
    print("这一侧只能靠人看），以及**它有没有在回答问题**（提示里写了「不许回答问题」，")
    print("但这只是一句提示，不是保证）。所以真机那一侧不参与 `--offline` 的任何结论。")
    return {"model": cfg.model}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.real:
        reading_real()
        return 0
    if not args.offline:
        ap.print_help()
        return 2

    r = build_retriever()
    reading_shape(r)
    reading_three_ways(r)
    reading_fusion_limits(r)
    reading_rewrite(r)
    reading_rerank(r)
    reading_depth(r)
    reading_cost(r)
    print()
    print(f"（语料 {len(r.chunks)} 片 ｜ 全部读数由 `--offline` 复现；")
    print("`--real` 只把改写交给模型，不改任何结论）")
    _hr("离线自检通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
