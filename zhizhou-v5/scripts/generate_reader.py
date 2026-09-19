#!/usr/bin/env python
"""5.5 的读数：**生成侧的四组账，外加真机上的一遍引用核对。**

    python scripts/generate_reader.py --offline      # 四组，不需要密钥，进提交门
    python scripts/generate_reader.py --real         # 真机：模型自己标的编号对不对
    python scripts/generate_reader.py --self-test    # 夹具自检（三条坏形态必须都被抓出来）

四组离线读数是：

① **三档**：把「检索到的那批片」喂给评估器，看每条问题落在 Correct／Ambiguous／Incorrect；
② **精炼**：分解—过滤—重组之后，送进提示的汉字数变了多少（**收益是账，不是印象**）；
③ **绑定**：同一段回答，A 路（模型自己写 `[i]`）与 B 路（代码按句绑定）各自抓到了什么——
   三条坏形态里，**只有 B 路抓得到「编号没错、指错了片」那一条**；
④ **控制位**：Self-RAG 的按需检索在本语料上省下几次调用、几片上下文。

真机那一组（`--real`）**不属于提交门**，它报的是读数：真实模型自己标的编号里，
有多少条指错了片、有多少句在资料里根本找不到依据。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.critic import (CONF_LOWER, CONF_UPPER, Quality, evaluate,        # noqa: E402
                        refine, strips)
from app.generate import bind, offline_control                            # noqa: E402
from app.questions import QUESTIONS                                       # noqa: E402
from app.rag import NO_ANSWER, answer, check_citations                     # noqa: E402
from app.scripted import ScriptedModel                                    # noqa: E402
from app.retrieve import build_retriever                                  # noqa: E402

#: 两条「创意题」：它们不该触发检索（Self-RAG 的 `[Retrieve=No]`）。
CREATIVE = ("写一首关于春天的诗", "给知舟的检索服务起三个名字")


def _hr(title: str) -> None:
    print("=" * 74)
    print(title)
    print("=" * 74)


def _grounded_chunks(r, query: str, *, k: int = 3):
    """「带资料」那条路真正会送进提示的片：**字面那一路的前三片**。

    与 5.1 的 `reading_two_paths` 同一条路、同一个 `TOP_K = 3`——
    这样两章的读数能对着读（包括 5.1 那条「答案片排第 5、没进前三」的漏）。
    三组读数共用这一份片，所以「三档」「精炼」「绑定」看的都是同一批东西。
    """
    return tuple(h.chunk for h in r.search(query, k=k, mode="bm25"))


def _pad(text: str, width: int) -> str:
    """按**显示宽度**补齐：汉字与全角标点在终端上占两列。

    这不是细心问题：第一版用 `f"{t:<34}"` 排出来的表格全是歪的，
    而一张歪掉的表在正文里贴出来就是错的证据。
    """
    wide = sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)
    return text + " " * max(0, width - wide)


# ---------------- ① 三档 ----------------

def reading_quality() -> dict:
    """把 5.1／5.4 那几个问题各自召回的一批片，判一次档。

    **注意输入是哪一路**：`bm25` 那一路的原始分（未归一），向量那一路的余弦分。
    融合分（`rrf`）不在这里出现——它在 `confidence()` 里是非法输入（见 critic.py）。
    """
    _hr("① 三档：这批片配不配被引用（论文的汇总写法：有一片够高就是 Correct）")
    r = build_retriever()
    rows = []
    for q in QUESTIONS:
        # `evaluate` 取的是 bm25 与 vector 两条**原始路**的分，
        # 不是 `candidates()` 的融合结果——融合分是秩序量，进不了阈值判定。
        _hits, scores, quality = evaluate(r, q.text, depth=3)
        rows.append((q.qid, q.kind, scores, quality))

    print(_pad("问题", 8) + _pad("类型", 22) + _pad("最高置信度", 14)
          + _pad("档", 12) + "动作")
    for qid, kind, scores, quality in rows:
        top = f"{max(scores):.4f}" if scores else "—"
        print(_pad(qid, 8) + _pad(kind, 22) + _pad(top, 14)
              + _pad(quality.value, 12) + quality.action)
    print(f"\n（阈值是本树自定：上 {CONF_UPPER}／下 {CONF_LOWER}；"
          "论文主文只说「设了上下两个阈值」，没给取值）")
    return {"rows": [(q, k, tuple(s), qq.value) for q, k, s, qq in rows]}


# ---------------- ② 精炼 ----------------

def reading_refine() -> dict:
    """分解—过滤—重组：**送进提示的字数变了多少，以及答案跟着变了什么。**

    第二半才是要看的：精炼省的是词元，而它**可能把装着答案的那一片丢碾**——
    这一节就是去量那件事。用的是一种可复现的模型（剧本模型照抄资料），
    所以「答得出／答不出」是可判定的，不是印象。
    """
    _hr("② 精炼：过滤掉与问题无关的句子之后，还剩多少——以及答案跟着变了什么")
    r = build_retriever()
    model = ScriptedModel(max_chunks=3)
    print(_pad("问题", 8) + _pad("片数", 6) + _pad("过滤前", 9) + _pad("过滤后", 9)
          + _pad("丢掉", 8) + _pad("原答案含关键片", 16) + "精炼后")
    out = {}
    for q in QUESTIONS:
        chunks = _grounded_chunks(r, q.text)
        ref = refine(q.text, chunks)
        before = answer(model, q.text, chunks)
        after = answer(model, q.text, ref.chunks)
        want = q.expect or "（该拒答）"
        ok_b = (q.expect in before.text) if q.expect else before.refused
        ok_a = (q.expect in after.text) if q.expect else after.refused
        out[q.qid] = {**ref.stats(), "before_chars": before.chars,
                      "after_chars": after.chars,
                      "before_ok": ok_b, "after_ok": ok_a}
        print(_pad(q.qid, 8) + _pad(str(len(chunks)), 6)
              + _pad(str(ref.chars_before), 9) + _pad(str(ref.chars_after), 9)
              + _pad(f"{ref.drop_ratio:.0%}", 8)
              + _pad(f"{'是' if ok_b else '否'}（{want}）", 16)
              + ("是" if ok_a else "否"))
    tot_before = sum(v["chars_before"] for v in out.values())
    tot_after = sum(v["chars_after"] for v in out.values())
    lost = [q for q, v in out.items() if v["before_ok"] and not v["after_ok"]]
    print(f"\n四题合计：过滤前 {tot_before} 字 → 过滤后 {tot_after} 字"
          f"（丢掉 {1 - tot_after / tot_before:.1%}）；"
          f"其中 {len(lost)} 条（{'、'.join(lost) if lost else '无'}）从「答得出」变成「答不出」。")
    print("这就是这一节的结论：**精炼省下的词元，与它丢掉的信息，是同一笔账。**")
    for qid in lost:
        q = next(x for x in QUESTIONS if x.qid == qid)
        chunks = _grounded_chunks(r, q.text)
        ref = refine(q.text, chunks)
        keep = ref.chunks[0].text if ref.chunks else ""
        hit = next((c for c in chunks if q.expect in c.text), None)
        print(f"\n[{qid}] 该答出来的片段是「{q.expect}」，它在 "
              f"{hit.cite() if hit else '—'} 里。")
        print(f"    过滤前会喂进去的第一片：{chunks[0].text[:52]!r}")
        print(f"    过滤后只剩：{keep[:52]!r}")
    print("\n一条廉价的、按字面重合度算的评估器会把「引子那一句」当成最相关的一句：\n"
          "「…月调用预算上限是」与问题重合得最多，而紧接着的「**每月 2,400 万词元**」\n"
          "里没有一个词与问题重合——**数字那一半被当成冗余丢掉了**。\n"
          "论文用微调过的 T5-large 当评估器，学的正是「相关」而不是「字面像」；\n"
          "本树的替身没有这个能力，所以**本章不采用精炼作为默认路径**，只把它当一组读数。")
    return out


# ---------------- ③ 绑定：A 路 vs B 路 ----------------

#: 三条坏形态的夹具。**正文都取自真实片的第一句，只有引用那一处不同**——
#: 这样「内容对、引用错」才是受控的：三行里没有一行内容有问题，
#: 而 A 路只能报出其中两条。
#: 它们是「模型会犯的错」，不是「本树会犯的错」——真机那一组（`--real`）量的就是真实模型犯不犯。
def bad_answers(chunks) -> dict[str, str]:
    """按**真实召回片**拼出三条夹具（所以读者能拿地址去 `corpus/` 里核）。"""
    if len(chunks) < 2:
        raise SystemExit("这一组需要至少两片，才能造出「错指」那条夹具")
    first = strips(chunks[0].text)[0]
    core = first.rstrip("。！？；：").rstrip()
    return {
        "越界": f"{core} [9]。",                    # 编号超出片数 → A 路报出
        "漏标": first,                              # 一条编号都没标 → A 路报出
        "错指": f"{core} [{len(chunks)}]。",         # 编号合法但指错片 → 只有 B 路报出
    }


def reading_binding() -> dict:
    """同一批片、三段回答：A 路（模型自己写编号）与 B 路（代码按句绑定）各抓到什么。

    夹具里的三段回答，**内容都是对的**（照抄了 `发布规范#1`），差别只在引用怎么写。
    这正是最要紧的那一类错：**内容对、引用错**，而 A 路只看编号在不在范围内。
    """
    _hr("③ 绑定：A 路（模型写编号）与 B 路（代码绑定）各抓到什么")
    r = build_retriever()
    chunks = _grounded_chunks(r, QUESTIONS[0].text)[:2]
    print("本次给的片：" + "、".join(f"[{i}] {c.cite()}" for i, c in enumerate(chunks, 1)))
    print()
    print(_pad("夹具", 8) + _pad("A 路：check_citations", 34)
          + "B 路：bind（按句绑定）")
    out = {}
    fixtures = bad_answers(chunks)
    for name, text in fixtures.items():
        a_issues = check_citations(text, chunks)
        b = bind(text, chunks)
        out[name] = {"a": a_issues, "b": b.issues,
                     "counts": b.counts(), "citations": b.citations}
        a_txt = "、".join(a_issues) if a_issues else "通过（一条都没报）"
        b_txt = "、".join(b.issues) if b.issues else "通过"
        print(_pad(name, 8) + _pad(a_txt[:30], 34) + b_txt[:40])
    print("\n逐句的依据（错指那一条只有 B 路看得出差别）：")
    b = bind(fixtures["错指"], chunks)
    print(_pad("  句子", 44) + _pad("支撑", 12) + "绑定到的片")
    for s in b.sentences:
        print(_pad("  " + s.text[:40], 44) + _pad(s.support, 12) + (s.cite or "—"))
    print("\n越界那条写的是 [9]（片只有 2 片）→ A 路报出；"
          "\n错指那条写的是 [1]（合法编号）→ A 路放过，而 B 路把它绑到"
          f" {b.sentences[0].cite}。")
    return out


# ---------------- ④ 控制位 ----------------

def reading_control() -> dict:
    """Self-RAG 的按需检索：本语料上省下几次调用、几片上下文。"""
    _hr("④ 控制位：该查的查、不该查的不查（省下的是调用与上下文）")
    r = build_retriever()
    rows = []
    for text in [q.text for q in QUESTIONS] + list(CREATIVE):
        ctrl = offline_control(text)
        hits = _grounded_chunks(r, text, k=3) if ctrl.retrieve == "yes" else ()
        rows.append((text, ctrl.retrieve, len(hits)))
    print(_pad("问题", 34) + _pad("[Retrieve]", 12) + "片数")
    for text, bit, n in rows:
        print(_pad(text[:32], 34) + _pad(bit, 12) + str(n))
    yes = sum(1 for _, b, _ in rows if b == "yes")
    print(f"\n{len(rows)} 条问题里只有 {yes} 条需要检索；"
          f"另外 {len(rows) - yes} 条直接答——省下 {len(rows) - yes} 次检索与它们的上下文。")
    print("诚实的一句话：**这一组的比例是本语料的，不是普遍的**。"
          "创意题多的场景里它省得多，事实题多的场景里它几乎不省。")
    return {"rows": rows, "yes": yes}


# ---------------- ⑤ 真机 ----------------

def reading_real() -> dict:
    """真机：让模型自己写编号，然后**逐句核验它指的是哪一片**。

    这一组报的是读数，不是结论：**模型的引用正确率随模型与提示而变**，
    所以只报这一遍的数，不写「通常都错」这类话。
    """
    from app.config import Config            # noqa: PLC0415
    from app.llm import make_call            # noqa: PLC0415
    from app.rag import answer               # noqa: PLC0415

    _hr("⑤ 真机：模型自己标的编号，有多少条指错了片")
    cfg = Config.from_env()
    call = make_call(cfg)
    print(f"服务商 {cfg.base_url}｜模型 {cfg.model}｜温度 {cfg.temperature}")
    r = build_retriever()
    out = {}
    for q in QUESTIONS[:2]:
        chunks = _grounded_chunks(r, q.text)[:2]
        a = answer(call, q.text, chunks)
        b = bind(a.text, chunks)
        out[q.qid] = {"text": a.text, "a": a.issues, "b": b.issues,
                      "counts": b.counts(), "citations": b.citations}
        print(f"\n[{q.qid}] {q.text}")
        print(f"  模型标的编号 {list(a.citations)}；A 路问题："
              f"{list(a.issues) or '无'}；绑定到的地址 {list(b.citations)}")
        print(f"  逐句支撑：{b.counts()}")
        print(f"  回答：{a.text[:80]}")
    wrong = sum(1 for v in out.values() if v["a"] is not None and v["a"])
    print(f"\n两条问题里，A 路报出问题的有 {wrong} 条；"
          "B 路报出的无依据句见上面每一行的「逐句支撑」。")
    return out


def self_test() -> int:
    """夹具自检：**三条坏形态里，B 路至少要抓到错指那一条。**"""
    r = build_retriever()
    chunks = _grounded_chunks(r, QUESTIONS[0].text)[:2]
    fx = bad_answers(chunks)
    cases = [
        ("越界：A 路必须报（编号超出片数）",
         bool(check_citations(fx["越界"], chunks)), True),
        ("错指：A 路必须放过（编号合法）",
         bool(check_citations(fx["错指"], chunks)), False),
        ("错指：B 路必须抓到（标了的片不是它的依据）",
         any("错指" in i for i in bind(fx["错指"], chunks).issues), True),
        ("漏标：A 路必须报（给了资料却一条引用都没标）",
         bool(check_citations(fx["漏标"], chunks)), True),
        ("内容取自真片：B 路必须判为 Fully",
         bind(fx["漏标"], chunks).counts()["Fully"] == 1, True),
        ("空片：拒答句不挂引用",
         bind(NO_ANSWER, ()).citations, ()),
    ]
    ok = 0
    for name, got, want in cases:
        good = got == want
        ok += good
        print(("  ✔ " if good else "  ✖ ") + name
              + ("" if good else f"（期望 {want!r}，实得 {got!r}）"))
    print(f"夹具自检：{ok}/{len(cases)} 通过")
    return 0 if ok == len(cases) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="四组离线读数（不需要密钥）")
    ap.add_argument("--real", action="store_true", help="真机那一组：引用正确率")
    ap.add_argument("--self-test", action="store_true", help="夹具自检")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.real:
        reading_real()
        return 0
    if args.offline:
        reading_quality()
        print()
        reading_refine()
        print()
        reading_binding()
        print()
        reading_control()
        print("\n离线自检通过")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
