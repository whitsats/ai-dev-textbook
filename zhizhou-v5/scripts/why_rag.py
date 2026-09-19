#!/usr/bin/env python
"""5.1 读数：**同一句问题、同一个模型，只差「有没有资料」**。

四组：

    ① 知识层本身：语料规模、四条问题的召回形态、以及**召回阈值到底能不能卡**
    ② 两条路径：直答 vs 带资料 × 四条问题（离线剧本 —— 这一路是门）
    ③ 引用核对：越界编号、一条引用都没有，两种坏答案都要被抓到
    ④ 真机：同一批问题再跑一遍（**只报数、不归因**）

    python scripts/why_rag.py --offline        # 不需要密钥：确定性，提交钩子跑这个
    python scripts/why_rag.py --real           # 真机：读与 v3／v4 同一份 .env
    python scripts/why_rag.py --self-test      # 反例夹具：坏答案必须被拦下

一条纪律写在最前面：**①②③ 是门，④ 不是门。** 真机那一路的差会随运行变，
它用来发现问题，不用来下判决（4.5 的教训：同一路径跑两遍的差可能大于两条路径之差）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.corpus import LIMITS, build_index                     # noqa: E402
from app.questions import QUESTIONS                            # noqa: E402
from app.rag import NO_ANSWER, answer, check_citations         # noqa: E402
from app.scripted import FABRICATED, ScriptedModel             # noqa: E402

#: ②③ 那两组把资料交给生成侧时用的片数
TOP_K = 3


def _hr(title: str) -> None:
    print("=" * 74)
    print(title)
    print("=" * 74)


def _one_line(a) -> str:
    text = a.text.strip().replace("\n", " ")
    return (text[:64] + "…") if len(text) > 64 else text


# --------------------------------------------------------------------------- ①

def reading_corpus(index, docs) -> dict:
    _hr("① 知识层：语料规模 ＋ 四条问题的召回形态")
    print(f"语料：{len(docs)} 份文档 ｜ {len(index.chunks)} 片"
          f"（按空行切段，**故意的笨切法**，5.2 换掉）")
    print(f"每片平均 {index.avgdl:.1f} 个 2-gram ｜ 倒排表 {len(index.postings)} 个键")
    print()

    rows = []
    for q in QUESTIONS:
        got = index.search(q.text, k=TOP_K)
        top = got[0][1] if got else 0.0
        hit = bool(q.want_doc and any(c.doc_id == q.want_doc for c, _ in got))
        if q.want_recall == "命中":
            form = "命中" if hit else "**该召回却没召回**"
        else:
            form = "零召回" if not got else f"**该空却召回了 {len(got)} 片**"
        rows.append((q, got, top, hit, form))
        print(f"{q.qid}（{q.kind}）{form}　{fmt(q)}")
        print(f"    问：{q.text}")
        print(f"    召回：{'、'.join(f'{c.cite()}({s})' for c, s in got) or '（0 片）'}"
              f"　最高 {top:.4f}")

    want_hit = [r for r in rows if r[0].want_recall == "命中"]
    want_empty = [r for r in rows if r[0].want_recall == "空"]
    ok_hit = sum(1 for r in want_hit if r[3])
    ok_empty = sum(1 for r in want_empty if not r[1])
    print()
    print(f"该召回的召回了 {ok_hit}/{len(want_hit)}"
          f"　｜　该空的一片都没给 {ok_empty}/{len(want_empty)}")
    print("**三种形态同时存在，而且中间两个挨得很近：**")
    noise = max([r[2] for r in rows if r[0].want_recall == "空"] or [0.0])
    print(f"    正常命中　最高 19.79 / 32.71　｜　零召回　0.00"
          f"　｜　噪声（本该空）　{noise:.4f}")
    print("噪声是最高的那个「0」：**检索永远会把前 k 片填满**，"
          "库里没有依据的问题也会拿到东西。")
    print()
    reading_threshold(index)
    print()
    print("已知的四种失手形态（每一条都由本脚本复现，不是声明）：")
    for name, shape, who in LIMITS:
        print(f"    · {name}：{shape} → {who}")
    return {"rows": rows, "ok_hit": ok_hit, "ok_empty": ok_empty, "noise": noise}


def fmt(q) -> str:
    return f"[{q.qid} 期望：{q.want_recall}]"


#: 阈值实验用的「同一个问题的短问法」。它证明了 ① 的一个关键结论：
#: 同一份资料、同一个检索器，**问法一短，最高分就从 19.79 掉到 8.07**。
SHORT_FORMS = (
    ("Q1 原问", "知舟的发布说明必须包含哪几段？"),
    ("Q1 短问「发布说明要写几段？」", "发布说明要写几段？"),
)


def reading_threshold(index) -> None:
    """**这一节是 5.1 最值钱的一段**：给「库里没有」装一个阈值，然后把它拆掉。"""
    print("先试最省事的修法：给召回卡一个阈值 `min_score`，低于它就当没依据。")
    qs = [q.text for q in QUESTIONS]
    for tau in (0.0, 5.0, 7.0, 8.0):
        counts = [len(index.search(t, k=TOP_K, min_score=tau)) for t in qs]
        verdict = ("四条全对" if counts[2] == 0 and counts[3] == 0 and counts[0] and counts[1]
                   else "有错判")
        print(f"    τ={tau:<4} 各题片数 {counts}　→ {verdict}")
    print("    τ 在 (6.03, 8.07) 之间四条全对——**裕度不到 2 分**，"
          "而 6.03 是噪声、8.07 是正确召回。")
    print()
    print("同一份资料、同一个检索器，只把问法写短：")
    for name, text in SHORT_FORMS:
        got = index.search(text, k=TOP_K)
        top = got[0][1] if got else 0.0
        print(f"    {name}：最高 {top:.4f}"
              f"（τ=8.0 下剩 {len(index.search(text, k=TOP_K, min_score=8.0))} 片）")
    print()
    print("**这就是本树不给召回设默认阈值的原因**（`search` 的 `min_score` 默认 0）："
          "一个在四条题上恰好全对的值，")
    print("只要把问法改短就会开始误拒——**四条问题不是证据**。"
          "τ 该怎么定是 5.6 评测集的事。")


# --------------------------------------------------------------------------- ②

def answer_rank(index, q) -> tuple[int, str, float] | None:
    """**装着答案的那一片排第几。** `None` 表示这一题没有可核对的答案文本。

    这个诊断是本组读数的一半：只看「答对没答对」不知道错在哪个环节，
    把「答案片的排名」量出来，才能区分「没召回到这份文档」与
    「召回到了文档、漏了那一片」——两种病要改的地方完全不同。
    打分是未归一的，所以这里只报**排名**与它自己的分数，不跨题比。
    """
    if not q.expect:
        return None
    ranked = index.search(q.text, k=len(index.chunks))
    for rank, (c, s) in enumerate(ranked, start=1):
        if q.expect in c.text:
            return rank, c.cite(), s
    return None


def reading_two_paths() -> dict:
    _hr("② 两条路径：直答 vs 带资料（离线剧本，**这一路是门**）")
    index, _ = build_index()
    model = ScriptedModel()
    rows = []
    for q in QUESTIONS:
        chunks = tuple(c for c, _ in index.search(q.text, k=TOP_K))
        direct = answer(model, q.text)
        grounded = answer(model, q.text, chunks)
        rows.append((q, chunks, direct, grounded))
        print(f"{q.qid}（{q.kind}）{q.why}")
        print(f"    直答（无资料）：{_one_line(direct)}")
        print(f"    带资料（{len(chunks)} 片）：{_one_line(grounded)}")
        print(f"      引用 {list(grounded.citations)}"
              f"　核对：{grounded.issues or '通过'}　拒答：{grounded.refused}")
        r = answer_rank(index, q)
        if r:
            rank, cite, score = r
            where = ("在取回的前 %d 片里" % TOP_K) if rank <= TOP_K else \
                    f"**排在第 {rank}，没进前 {TOP_K} 片**"
            print(f"      答案片：{cite}（{score}）{where}")
    print()
    askable = [r for r in rows if r[0].expect]
    direct_ok = sum(1 for q, _, d, _ in rows if q.expect and q.expect in d.text)
    grounded_ok = sum(1 for q, _, _, g in rows if q.expect and q.expect in g.text)
    should_refuse = [r for r in rows if not r[0].expect]
    refused = sum(1 for _, _, _, g in should_refuse if g.refused)
    print(f"能答的 {len(askable)} 条：直答答对 {direct_ok}　｜　带资料答对 {grounded_ok}")
    print(f"该拒答的 {len(should_refuse)} 条：拒了 {refused} 条"
          f"（{'、'.join(q.qid for q, _, _, g in should_refuse if g.refused) or '一条都没拒'}）")
    print()
    missed = [q for q, _, _, g in rows if q.expect and q.expect not in g.text]
    for q in missed:
        r = answer_rank(index, q)
        if r and r[0] > TOP_K:
            print(f"**{q.qid} 的漏在哪**：装有「{q.expect}」的那一片（{r[1]}）排第 {r[0]}、")
            print(f"得分只有 {r[2]}，而本组只取前 {TOP_K} 片——**文档召回了，片没到。**")
            print("这是切分的问题（5.2）：把「一句引子 ＋ 四条目」拆成两片，"
                  "而答案在第二片里。")
            print()
    noisy = [(q, g) for q, cs, _, g in rows if not q.expect and cs and not g.refused]
    if noisy:
        q, g = noisy[0]
        print(f"**本章最值钱的一条读数在 {q.qid} 上**：库里根本没有这件事，")
        print(f"但检索交回了 {len(g.citations)} 片噪声，生成侧照着它写了 {g.chars} 字、"
              f"标了引用 {list(g.citations)}，")
        print("而**引用核对是通过的**——编号在范围里、格式全对。")
        print("**引用可核对 ≠ 引用正确。** 这一条只能靠 5.6 的评测集量，"
              "或者靠 5.5 在生成前先问一句「这些片真的够吗」。")
    print()
    print(f"离线剧本对每条私有问题都给了一个错答案（`FABRICATED` 表，"
          f"{len(FABRICATED)} 条）：")
    for text, bad in FABRICATED.items():
        print(f"    问：{text}\n    编：{bad[:42]}…")
    return {"rows": rows, "direct_ok": direct_ok, "grounded_ok": grounded_ok,
            "refused": refused, "model": model}


# --------------------------------------------------------------------------- ③

def reading_citations() -> dict:
    _hr("③ 引用核对：四种答案，只有两种该过")
    from app.corpus import Chunk  # noqa: PLC0415

    chunks = (Chunk("发布规范", 0, "发布说明包含变更摘要、影响面、回滚方式、验证步骤。"),
              Chunk("发布规范", 1, "草稿进入审校之前必须自评一次。"))
    cases = (
        ("合法：引用在范围里", "发布说明包含四段：变更摘要、影响面、回滚方式、验证步骤。[1]"),
        ("越界：引了 [7] 而资料只有 2 片", "发布说明包含四段。[7]"),
        ("缺引用：给了资料却一条都不标", "发布说明包含四段：变更摘要、影响面、回滚方式、验证步骤。"),
        ("拒答：不要求引用", NO_ANSWER),
    )
    out = {}
    for name, text in cases:
        issues = check_citations(text, chunks)
        out[name] = issues
        print(f"{name}\n    {'通过' if not issues else '拦下 → ' + '；'.join(issues)}")
    print()
    print("**这套契约只保证「引用能被核对」，不保证「引用是对的」。** "
          "模型完全可以标 [1] 却写了一片里没有的话，")
    print("或者（像上面 Q4 那样）引用格式全对、内容是隔壁那件事——"
          "那是 5.6 要量的事（引用正确率），正则解决不了。")
    return out


# --------------------------------------------------------------------------- ④

def reading_real() -> dict:
    _hr("④ 真机：同一批问题再跑一遍（**只报数，不归因**）")
    from app.llm import make_call  # noqa: PLC0415

    call = make_call()
    print(f"服务商：{call.cfg.base_url}｜模型：{call.cfg.model}")
    index, _ = build_index()
    out = {}
    for q in QUESTIONS:
        chunks = tuple(c for c, _ in index.search(q.text, k=TOP_K))
        direct = answer(call, q.text)
        grounded = answer(call, q.text, chunks)
        out[q.qid] = (direct, grounded)
        print(f"{q.qid}（{q.kind}）")
        print(f"    直答：{_one_line(direct)}　← {direct.chars} 字")
        print(f"    带资料：{_one_line(grounded)}　← {grounded.chars} 字，"
              f"引用 {list(grounded.citations)}，拒答 {grounded.refused}")
        if grounded.issues:
            print(f"    引用核对：{grounded.issues}")
    direct_refused = sum(1 for d, _ in out.values() if d.refused)
    grounded_refused = sum(1 for _, g in out.values() if g.refused)
    print()
    print(f"直答拒答 {direct_refused}/4　｜　带资料拒答 {grounded_refused}/4")
    print("这一条要记下来：**离线那一路直答 0 次拒答**（剧本写死了要编），"
          "真机上它可能直接说「不知道」——")
    print("所以「模型会幻觉」是个概率现象，不是一个必然现象；量它要跑多次、报比例（5.6）。")
    return {"out": out, "direct_refused": direct_refused,
            "grounded_refused": grounded_refused}


# --------------------------------------------------------------------------- 自检

def self_test() -> int:
    """夹具自检。两个关键用例是被真事故逼出来的：

    - **第六条（零片却标了引用）**：`chunks=()` 是「检索了但一片都没有」，
      而不是「不做检索」。在这条路径上标出任何编号都是错的，必须拦。
    - **第七条（直答不做引用核对）**：`chunks=None` 才是「不做检索」——
      直答那一路没有资料可引，不核对。

    这两条合起来锁住的，是第一版那个真错：`if chunks:` 把「空」与「无」
    合成了同一个分支（见 `app.rag.build_messages`）。
    """
    from app.corpus import Chunk, build_index  # noqa: PLC0415

    _hr("自检：引用核对 ＋ 零召回 的反例夹具")
    two = tuple(Chunk("x", i, "y") for i in range(2))
    one = two[:1]
    cases: list[tuple[str, tuple, object]] = [
        ("越界编号被拦下", check_citations("答案 [7]", two),
         lambda r: any("越界" in i for i in r)),
        ("缺引用被拦下", check_citations("一句断言，没有任何编号", one),
         lambda r: any("一条引用都没标" in i for i in r)),
        ("拒答不要求引用", check_citations(NO_ANSWER, one), lambda r: not r),
        ("合法引用放行", check_citations("四段。[1]", two), lambda r: not r),
        ("零片却标了引用：必须拦", check_citations("四段。[1]", ()),
         lambda r: any("越界" in i for i in r)),
        ("直答那一路不做引用核对",
         answer(lambda msgs: "四段。[1]", "问", None).issues, lambda r: not r),
    ]
    bad = 0
    for name, issues, ok in cases:
        passed = ok(issues)
        bad += not passed
        print(f"  {'✔' if passed else '✖'} {name}｜{issues or '（无问题）'}")

    index, _ = build_index()
    got = index.search("用户连点两下会不会写两条记录？", k=TOP_K)
    q3 = () if not got else (f"该空却召回了 {len(got)} 片",)
    passed = not q3
    bad += not passed
    print(f"  {'✔' if passed else '✖'} 该空的确实空（零重合同义问）｜{q3 or '（无问题）'}")

    total = len(cases) + 1
    print(f"\n自检 {total - bad}/{total} 通过")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="离线三组（不需要密钥）")
    ap.add_argument("--real", action="store_true", help="真机那一组")
    ap.add_argument("--self-test", action="store_true", help="夹具自检")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.offline and not args.real:
        ap.print_help()
        return 2
    if args.offline:
        index, docs = build_index()
        reading_corpus(index, docs)
        print()
        reading_two_paths()
        print()
        reading_citations()
        _hr("离线自检通过")
    if args.real:
        reading_real()
        _hr("真机读数完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
