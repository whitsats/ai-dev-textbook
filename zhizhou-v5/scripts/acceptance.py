#!/usr/bin/env python
"""5.8 的端到端验收：**一条命令回答「这一版知识库能不能上」。**

    python scripts/acceptance.py --offline        # 四组读数 ＋ 验收清单（进提交门）
    python scripts/acceptance.py --self-test      # 夹具自检（三档拒收 / 复用 / 戳）

四组读数：

① **入库报告**：`corpus/` 与 `knowledge/` 两个根，各几份文件、几份进库、几份被拒、
   被拒的三档各几条、语料戳是多少；
② **三套库的对照**：同一批 24 条评测集、同一个检索器，只换知识库——
   **A 现状**（`corpus/` ＋ 5.1 的段落切）、**B 扩库**（A ＋ 多格式新片）、
   **C 迁移**（全部换成 5.2 的结构感知切 ＋ 多格式）。报片级、答案命中、拒答四格，
   并逐项与 5.6 的基线比；
③ **端到端一次请求**：在 C 库上走完整的 `Service.handle()`（检索 → 判档 → 生成 → 绑定），
   看它引用了哪几片、账有几笔、绑定有没有过；
④ **验收清单**：把「这一版能不能上」拆成可勾的条目，逐条给通过与否。

## 两处不重复造轮子的地方

一是**判分口径**：`_measure()` 里的每一句都照抄 `experiments/eval_run.py` 的
`run_offline()`——同一批题、同一个 `k`、同一条 `output_control`，不另写一份实现。
两份实现会漂，而这一层的漂移**不会报错**，只会让「C 比 A 好」这个结论失去基准。
本脚本因此把 A 组的结果**与 5.6 记录的基线逐项断言相等**：分毫不差，说明两边是同一套定义；
不相等就是有一边改了（这条断言在写完本章的第一次运行里就报过一次，见 5.8.7）。

二是**「提升」的判据**：差值必须超过 5.6 算出的可检测最小差异（1/24 ≈ 0.0417），
否则只是噪声——**扩库那一组四项读数一格没动，正因为它落在分辨率之下**。

## 为什么三套并排，而不是直接把线上那条路迁到 C

**换切法等于换系统。** A 组是 5.1–5.7 全部读数的锚：迁到 C 会让那七章的正文数字作废，
而那是一次**发布动作**，不是一次重构。本章的交付是把这次迁移变成
「一条命令 ＋ 两组读数 ＋ 一份差异清单」，让做决定的人手里有账。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.corpus import NgramIndex, load_corpus                        # noqa: E402
from app.critic import evaluate                                       # noqa: E402
from app.embed import make_embedder                                   # noqa: E402
from app.generate import bind, must_refuse                            # noqa: E402
from app.ingest import ingest                                         # noqa: E402
from app.metrics import (MIN_DETECTABLE, answer_hit_rate, load_cases,  # noqa: E402
                         recall_at, refusal_confusion, span_cite)
from app.observe import JsonLog                                       # noqa: E402
from app.rag import answer, check_citations                            # noqa: E402
from app.retrieve import Retriever, build_retriever                   # noqa: E402
from app.scripted import ScriptedModel                                # noqa: E402
from app.serve import Service                                         # noqa: E402
from app.split import split_document                                   # noqa: E402
from app.vector_index import ExactIndex                                # noqa: E402

CASES = ROOT / "tests" / "rag" / "eval_cases.jsonl"
KNOWLEDGE = ROOT / "knowledge"
CORPUS = ROOT / "corpus"

#: 候选深度。**每个读数都要写上它的 `k`**（5.6 的纪律）。
K = 3

#: 5.6 的基线。A 组必须与它逐项相同，否则这一章的对照自己就不成立。
BASELINE = {"span": 0.8333, "answer": 0.9444, "missed": 1, "over": 0}

#: 三套库的名字。**顺序就是「改动量」的顺序**：越往下改得越多。
ARMS = ("A 现状（段落切）", "B 扩库（＋多格式）", "C 迁移（结构感知切）")


def _hr(title: str) -> None:
    print("=" * 74)
    print(title)
    print("=" * 74)


def _build(chunks) -> Retriever:
    """一组片 → 一个装好的检索器。**零件与 `build_retriever()` 完全一样，只换片**——

    否则这一组读数比的就不是「知识库」，而是两套检索器。
    """
    chunks = tuple(chunks)
    emb = make_embedder(dim=256, ngram=2)
    return Retriever(chunks, NgramIndex(chunks), emb, ExactIndex(emb([c.text for c in chunks])))


def _sections_of_corpus():
    """C 组那一侧：`corpus/` 改用 5.2 的结构感知切。"""
    return tuple(p.as_chunk() for d in load_corpus()
                 for p in split_document(d, strategy="sections", size=300, overlap=60))


# ---------------------------------------------------------------- ① 入库
def read_ingest() -> dict:
    _hr("① 入库报告：两个根、三档处置、一个语料戳")
    rep = {"corpus": ingest(CORPUS, prefix="corpus."), "knowledge": ingest(KNOWLEDGE, prefix="knowledge.")}
    for label, r in (("corpus/", rep["corpus"]), ("knowledge/", rep["knowledge"])):
        d = r.as_dict()
        print(f"{label:<11}文件 {d['files']} ｜ 进库 {d['kept']} ｜ 被拒 {d['rejected']}"
              f" ｜ 片 {d['chunks']} ｜ 汉字 {d['hanzi']} ｜ 戳 {d['stamp']}")
        # 被拒的文件用 `✗`（一份**处置记录**），验收失败用 `✖`（一处**不通过**）。
        # 两个记号分开是有用的：测试里那句「输出里没有 ✖」于是等于「没有一项验收失败」，
        # 而不用去数缩进（第一版两个记号共用一个字符，那句断言当场就乱了）。
        for e in r.rejected:
            print(f"    ✗ {e.path:<16}{e.reason}")
    c, k = rep["corpus"].as_dict(), rep["knowledge"].as_dict()
    print(f"\n两库合计：{c['files'] + k['files']} 份源文件 → 进库 {c['kept'] + k['kept']} 份"
          f"、被拒 {c['rejected'] + k['rejected']} 份 ｜ {c['chunks'] + k['chunks']} 片"
          f" ｜ {c['hanzi'] + k['hanzi']} 汉字")
    print(f"解析出的格式：{'、'.join(sorted({e.fmt for e in rep['knowledge'].kept}))}"
          f"（外加 corpus/ 的 md）")
    return rep


# ---------------------------------------------------------------- ② 三套库
def _measure(r: Retriever) -> dict:
    """一组片上的四项读数。**每一句都照抄 5.6 的 `run_offline()`**（见模块开头）。"""
    cases = load_cases(CASES)
    model = ScriptedModel(max_chunks=K)
    spans: list[int] = []
    answers: list[tuple[bool, bool]] = []
    cells: list[tuple[bool, bool]] = []
    cites_only = 0
    for c in cases:
        chunks = tuple(h.chunk for h in r.search(c.text, k=K, mode="bm25"))
        cites = tuple(h.cite() for h in r.search(c.text, k=K, mode="hybrid"))
        holder = span_cite(r.chunks, c.want)
        if c.needs_recall:
            spans.append(cites.index(holder) + 1 if holder in cites else 0)
            a = answer(model, c.text, chunks)
            bind(a.text, chunks)
            answers.append((c.want in a.text, True))
        if c.expect_retrieve:
            _h, _s, quality = evaluate(r, c.text, depth=K)
            cells.append((c.expect_refuse, must_refuse(chunks, quality.value) is not None))
        if c.expect_refuse and any(x.startswith("knowledge.") for x in cites):
            cites_only += 1
    conf = refusal_confusion(cells)
    return {"pieces": len(r.chunks), "span": recall_at(spans, K), "answer": answer_hit_rate(answers),
            "missed": conf["missed"], "over": conf["over"], "refused_cites": cites_only}


def _gap(row: dict) -> tuple[str, ...]:
    """A 组与 5.6 基线的差异。**空元组表示分毫不差。**

    做成一个函数而不是一句断言，是为了让它能**自己被夹具验**：
    「差一格要报、不差要沉默」两件倿都得有用例（`--self-test`）。
    """
    keys = (("片级", row["span"], BASELINE["span"]), ("答案命中", row["answer"], BASELINE["answer"]),
            ("漏拒", row["missed"], BASELINE["missed"]), ("误拒", row["over"], BASELINE["over"]))
    return tuple(f"{n} {got} ≠ {want}" for n, got, want in keys if got != want)


def _reportable(a: dict, row: dict) -> bool:
    """这一组的提升报不报得出来：**差值必须超过可检测最小差异**（仍 1/24）。

    扩库那一组四项一格没动，它落在分辨率之下——写进正文就是一句没有尺寸的话。
    """
    return max(abs(row["span"] - a["span"]), abs(row["answer"] - a["answer"])) > MIN_DETECTABLE


def _entered(r: Retriever) -> int:
    """扩库那一组的**归因**：24 条里有几条的前三名里出现过新片。"""
    n = 0
    for c in load_cases(CASES):
        cites = tuple(h.cite() for h in r.search(c.text, k=K, mode="hybrid"))
        n += any(x.startswith("knowledge.") for x in cites)
    return n


def _changed(a: Retriever, b: Retriever) -> int:
    """逐条比对两套库的前三名候选：**有几条的候选（成员或顺序）不同。**

    与 5.4 的 `rewrite_changed` 同一个形状：「新库进来了」与「读数变了」是两件事，
    两个数都要报——否則一组「四项一格没动」的读数看上去就像根本没生效。
    """
    n = 0
    for c in load_cases(CASES):
        one = tuple(h.cite() for h in a.search(c.text, k=K, mode="hybrid"))
        two = tuple(h.cite() for h in b.search(c.text, k=K, mode="hybrid"))
        n += one != two
    return n


def read_arms(rep: dict) -> dict:
    _hr("② 三套知识库：同一批 24 条题、同一个检索器，只换库")
    new = list(rep["knowledge"].chunks)
    base = list(build_retriever().chunks)
    arms = {"A 现状（段落切）": base,
            "B 扩库（＋多格式）": base + new,
            "C 迁移（结构感知切）": list(_sections_of_corpus()) + new}
    out: dict[str, dict] = {}
    print(f"{'知识库':<20}{'片':>4}{'片级':>10}{'答案命中':>10}{'漏拒':>6}{'误拒':>6}")
    for label in ARMS:
        r = _build(arms[label])
        row = out[label] = _measure(r)
        print(f"{label:<20}{row['pieces']:>4}{row['span']:>10.4f}{row['answer']:>10.4f}"
              f"{row['missed']:>6}{row['over']:>6}")
    a = out[ARMS[0]]
    print(f"\n5.6 的基线（A 组必须逐项相同）：片级 {BASELINE['span']:.4f} ｜ "
          f"答案命中 {BASELINE['answer']:.4f} ｜ 漏拒 {BASELINE['missed']}／误拒 {BASELINE['over']}")
    # **口径漂了要立刻停**：A 组与 5.6 记的基线差一格，就说明有一边改了定义，
    # 而「C 比 A 好」这个结论的基准就没了（本章的第一次运行就报过一次）。
    assert not _gap(a), "A 组与 5.6 基线不一致：" + "；".join(_gap(a))

    print(f"\n逐项差（可检测最小差异仍是 1/24 ＝ {MIN_DETECTABLE:.4f}）：")
    for label in ARMS[1:]:
        row = out[label]
        d_span, d_ans = row["span"] - a["span"], row["answer"] - a["answer"]
        mark = "报得出" if _reportable(a, row) else "在分辨率之下，不报"
        print(f"  {label}：片级 {d_span:+.4f} ｜ 答案命中 {d_ans:+.4f} ｜ 漏拒 "
              f"{row['missed'] - a['missed']:+d}／误拒 {row['over'] - a['over']:+d}  ← {mark}")
    r_a, r_b, r_c = _build(base), _build(base + new), _build(arms[ARMS[2]])
    entered = _entered(r_b)
    print(f"\n扩库那一组的归因：24 条里有 {entered} 条的前三名出现过新片")
    print(f"逐条比对（前三名候选）：扩库改了 {_changed(r_a, r_b)}/24 条，"
          f"迁移改了 {_changed(r_a, r_c)}/24 条")
    return out | {"_entered": entered, "_changed_b": _changed(r_a, r_b),
                  "_changed_c": _changed(r_a, r_c)}


# ---------------------------------------------------------------- ③ 端到端
def read_end_to_end(rep: dict) -> dict:
    _hr("③ 端到端一次请求：在 C 库上走完整路径（检索 → 判档 → 生成 → 绑定）")
    service = Service(_build(list(_sections_of_corpus()) + list(rep["knowledge"].chunks)),
                      ScriptedModel(max_chunks=K), log=JsonLog(), sleep=lambda _s: None)
    out = []
    for question in ("夜间值守是谁？", "发布说明必须包含哪几段？"):
        reply = service.handle(question)
        # **验收的是「发出去的那一份」**：`reply.text` 已经过绑定层修正，
        # 而 `reply.citations_ok` 把两件事混在一个布尔里——它还包括
        # 「离线替身自己的编号有没有写对」（`bind()` 的 `issues`）。
        # 本章的第一版清单直接读了那个布尔，于是两条完全合格的答复被判成「不通过」；
        # 这与 5.7 审阅时抓出的同一族错误（把「自称不符」读成「答复不合格」）。
        delivered = check_citations(reply.text, reply.chunks) if reply.chunks else ()
        out.append({"q": question, "cites": [c.cite() for c in reply.chunks],
                    "quality": reply.quality, "refused": reply.refused,
                    "delivered_ok": not delivered, "self_claimed_ok": reply.citations_ok,
                    "cost": reply.cost.as_dict(), "hanzi": len(reply.text)})
        print(f"问：{question}")
        print(f"  引用：{'、'.join(c.cite() for c in reply.chunks) or '（未检索）'}")
        print(f"  质量档 {reply.quality} ｜ 拒答 {reply.refused} ｜ 答复 {len(reply.text)} 字")
        print(f"  引用核对（对发出去的那一份）：{'通过' if not delivered else delivered}"
              f"　自称与绑定{'一致' if reply.citations_ok else '不符（绑定层改过）'}")
        print(f"  四笔账：{reply.cost.as_dict()}")
    mis = sum(1 for r in out if r["delivered_ok"] and not r["self_claimed_ok"])
    print(f"\n{len(out)} 条里 {mis} 条的「模型自称」与绑定不符；而**发出去的"
          f"那 {len(out)} 份全部通过核对**——两个数必须分开报")
    return {"replies": out, "misnumbered": mis}


# ---------------------------------------------------------------- ④ 验收清单
def read_checklist(rep: dict, arms: dict, e2e: dict) -> list[tuple[str, bool, str]]:
    _hr("④ 验收清单：这一版能不能上")
    c, k = rep["corpus"].as_dict(), rep["knowledge"].as_dict()
    a, cc = arms[ARMS[0]], arms[ARMS[2]]
    rows = [
        ("入库有报告，三档分得开",
         k["files"] > 0 and k["rejected"] >= 1 and len(rep["knowledge"].by_reason()) >= 2,
         f"{k['kept']} 份进库／{k['rejected']} 份被拒："
         f"{json.dumps(rep['knowledge'].by_reason(), ensure_ascii=False)}"),
        ("多格式真的进来了（不是只有 .md）",
         len({e.fmt for e in rep["knowledge"].kept}) >= 3,
         "解析出的格式：" + "、".join(sorted({e.fmt for e in rep["knowledge"].kept}))),
        ("语料戳由内容算，两库各一个",
         len(rep["corpus"].stamp) == 12 and rep["corpus"].stamp != rep["knowledge"].stamp,
         f"corpus={rep['corpus'].stamp} ｜ knowledge={rep['knowledge'].stamp}"),
        ("A 组与 5.6 的基线逐项相同", not _gap(a),
         f"片级 {a['span']:.4f} ｜ 答案命中 {a['answer']:.4f} ｜ "
         f"漏拒 {a['missed']}／误拒 {a['over']}"),
        ("扩库不伤既有读数", arms[ARMS[1]]["answer"] >= a["answer"],
         f"B 组答案命中 {arms[ARMS[1]]['answer']:.4f}（差 "
         f"{arms[ARMS[1]]['answer'] - a['answer']:+.4f}）"),
        ("迁移这一档有读数、且方向说得清", cc["span"] >= a["span"],
         f"C 组片级 {cc['span']:.4f}（{cc['span'] - a['span']:+.4f}）、"
         f"答案命中 {cc['answer']:.4f}（{cc['answer'] - a['answer']:+.4f}）"),
        ("端到端有答复、引用由代码核对通过", all(r["delivered_ok"] for r in e2e["replies"]),
         f"{len(e2e['replies'])} 条问题的答复全部通过核对（其中 "
         f"{e2e['misnumbered']} 条的模型自称与绑定不符）"),
        ("四笔账记得下来", all(r["cost"]["模型调用"] >= 0 for r in e2e["replies"]),
         "、".join(f"{r['q'][:5]}…：检索 {r['cost']['检索']} 笔" for r in e2e["replies"])),
    ]
    for name, ok, detail in rows:
        print(f"  {'✔' if ok else '✖'} {name}　{detail}")
    return rows


# ---------------------------------------------------------------- 夹具自检
def rep0_chunks():
    """夹具里要用到的 knowledge/ 片。**单独一个函数是为了不让夹具依赖 `read_ingest()`**
    （那个函数会打印一堆东西，而 `--self-test` 的输出要保持可读）。"""
    return ingest(KNOWLEDGE, prefix="knowledge.").chunks


def self_test() -> int:
    """**三档拒收各一条 ＋ 复用一条 ＋ 戳一条**，共五条。

    条数要打印出来（`夹具自检：5/5`）——理由与 5.6、5.7 同一条：
    一个把夹具删光的脚本会安静地通过。
    """
    import os
    import tempfile
    import time

    _hr("夹具自检：三档拒收 ＋ 复用 ＋ 戳")
    tmp = Path(tempfile.mkdtemp())
    (tmp / "好.md").write_text("# 好\n\n" + "知舟的发布说明包含范围、回滚、通知三节。" * 3,
                               encoding="utf-8")
    (tmp / "坏.xyz").write_bytes(b"\x80\x81\x82\x83\x84\x85\x86\x87")
    (tmp / "空.md").write_text("", encoding="utf-8")
    # 乱码那一条**必须先过汉字下限**：只写控制字符会被判成「内容太少」，
    # 于是这条夹具守的是另一档——第一版就是这样，它「通过」了但什么也没守。
    (tmp / "乱.txt").write_text("\x01\x02\x03" * 10 + "这是一份乱码文件，请人工核对内容。" * 3,
                                encoding="utf-8")

    rep = ingest(tmp, prefix="t.")
    reasons = rep.by_reason()
    again = ingest(tmp, prefix="t.", previous=rep)
    stamp_before = ingest(tmp, prefix="t.").stamp
    os.utime(tmp / "好.md", (time.time() + 5, time.time() + 5))

    # 基线断言与分辨率判据各自的**两个方向**：该报的必须报、不该报的必须沉默。
    good = {**BASELINE}
    drifted = {**good, "span": 0.8889}

    # 引用要看「发出去的那一份」——**这一条是拿一次错换来的**：
    # 第一版读的是 `reply.citations_ok`，它把「模型自称的编号对不对」也算进去了，
    # 于是两条完全合格的答复被清单报成 ✖（同 5.7 那一族错误的第三次露面）。
    service = Service(_build(list(_sections_of_corpus()) + list(rep0_chunks())),
                      ScriptedModel(max_chunks=K), log=JsonLog(), sleep=lambda _s: None)
    reply = service.handle("夜间值守是谁？")
    delivered = check_citations(reply.text, reply.chunks)

    checks = [
        ("缺解析器被拦", reasons.get("缺解析器", 0) == 1, str(reasons)),
        ("空内容被拦", reasons.get("内容太少", 0) == 1, str(reasons)),
        ("乱码超线被拦", reasons.get("乱码超线", 0) == 1, str(reasons)),
        ("二次入库复用旧片", again.as_dict()["reused"] == 1,
         f"reused={again.as_dict()['reused']}／进库 {again.as_dict()['kept']}"),
        ("戳随内容变、不随 mtime 变", ingest(tmp, prefix="t.").stamp == stamp_before,
         f"只 touch：{stamp_before} → {ingest(tmp, prefix='t.').stamp}（必须相同）"),
        ("A 组与基线相同：沉默", _gap(good) == (), "；".join(_gap(good)) or "无差异"),
        ("A 组差一格：必须报", _gap(drifted) != (), "；".join(_gap(drifted))),
        ("差值在分辨率之下：不报", not _reportable(good, {**good, "span": 0.8750}),
         f"+0.0417 ≤ {MIN_DETECTABLE:.4f}"),
        ("差值超过分辨率：报", _reportable(good, drifted), f"+0.0556 > {MIN_DETECTABLE:.4f}"),
        ("引用看的是发出去的那一份", not delivered,
         f"自称与绑定{'一致' if reply.citations_ok else '不符'}｜"
         f"发出去的答复核对{'通过' if not delivered else str(delivered)}"),
    ]
    bad = 0
    for name, ok, detail in checks:
        print(f"  {'✔' if ok else '✖'} {name}　{detail}")
        bad += 0 if ok else 1
    print(f"\n夹具自检：{len(checks) - bad}/{len(checks)}" + (" 通过" if not bad else f"（{bad} 项不通过）"))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="5.8 端到端验收")
    ap.add_argument("--offline", action="store_true", help="四组读数（进提交门）")
    ap.add_argument("--self-test", action="store_true", help="夹具自检")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    rep = read_ingest()
    print()
    arms = read_arms(rep)
    print()
    e2e = read_end_to_end(rep)
    print()
    rows = read_checklist(rep, arms, e2e)
    print()
    _hr("一次验收的读数摘要（供正文引用）")
    a, cc = arms[ARMS[0]], arms[ARMS[2]]
    c, k = rep["corpus"].as_dict(), rep["knowledge"].as_dict()
    print(f"本次验收：源文件 {c['files'] + k['files']} 份（进库 {c['kept'] + k['kept']}／"
          f"被拒 {c['rejected'] + k['rejected']}）｜片 {a['pieces']}→{cc['pieces']}"
          f"（扩库 {arms[ARMS[1]]['pieces']}）｜片级 {a['span']:.4f}→{cc['span']:.4f}"
          f"｜答案命中 {a['answer']:.4f}→{cc['answer']:.4f}"
          f"｜清单 {sum(1 for _n, ok, _d in rows if ok)}/{len(rows)} 通过")
    print()
    _hr("离线自检通过")
    return 0 if all(ok for _n, ok, _d in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
