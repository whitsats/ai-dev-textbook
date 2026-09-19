#!/usr/bin/env python
"""5.6 的读数：**把前五章的读数压成一份能回归的账。**

    python experiments/eval_run.py --offline                 # 五组读数（不需要密钥，进提交门）
    python experiments/eval_run.py --offline --write-baseline # 把当前读数存成基线
    python experiments/eval_run.py --offline --check          # 与基线比，退步就非零退出
    python experiments/eval_run.py --self-test                # 反例夹具：改坏一档必须被拦下
    python experiments/eval_run.py --real                     # 真机：把判分器换成模型，报一致率

五组读数是：

① **四个配置的命中率**（字面／向量／融合／改写）：同 24 条题、同一个 `k`，只有一个变量不同；
② **端到端命中率**：带资料那条路跑出来的答案里，那段话真的出现了吗——
   与①的差额就是「检索到了但没用上」；
③ **拒答四格**：该拒的拒了吗、该答的答了吗。**两条判据各报一遍**（只看分档 ／ 先改写再判）；
④ **阈值扫描**：5.1 留下的那条「阈值不知道定在哪」，这里把它铺成一张两栏表；
⑤ **花销账**：检索次数、送进提示的汉字数、调用次数。

## 为什么回归门要写死在这个脚本里

第 3.9 章起这一层叫「门」，说的是**它要能拦住退步**，而不是「它能报数」。
所以 `--check` 比对的是扁平化之后的每一个数，而 `--self-test` 反过来验它拦得住——
**一个从不报错的检查，与没有检查是一回事**（这条纪律来自 `check_runnable` 里那次
「测试清单写死、18 条用例白写」的事故）。

## 真机那一组（`--real`）不属于提交门

它把同一批（句子，资料片）交给真实模型判档，再与离线替身比。它报的是**一致率**，
不是「谁更对」：离线那一路是确定性替身，它有已知偏差（Partially 一律计 0.5），
真机那一路有随机性。两者对不上时，**能确定的只有「口径不同」**，不是「某一方错了」。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.critic import CONF_LOWER, CONF_UPPER, evaluate, judge          # noqa: E402
from app.generate import (bind, decide_retrieval, must_refuse,          # noqa: E402
                          offline_control)
from app.metrics import (MIN_DETECTABLE, answer_hit_rate, flatten, gate,   # noqa: E402
                         load_cases, min_detectable, rank_of, recall_at,
                         recall_by_kind, refusal_confusion, span_cite,
                         support_ratio)
from app.rag import answer, render_context                             # noqa: E402
from app.scripted import ScriptedModel                                 # noqa: E402
from app.retrieve import build_retriever                               # noqa: E402

CASES = ROOT / "tests" / "rag" / "eval_cases.jsonl"
BASELINE = ROOT / "experiments" / "eval_baseline.json"

#: 候选深度。**每个读数都要写上它的 `k`**：同一条读数在不同 `k` 下是两个数。
K = 3

#: 回归门的容差。它不是「允许退步 2%」，而是「小于分辨率的差别不该报」。
#: 本章的分辨率是 1/24 ≈ 4.2%，所以任何一格变化都是真的，容差取 0。
TOL = 0.0

#: 阈值扫描的网格。**它扫的是 5.5 那两个自定的阈值，不是「最优阈值」**——
#: 本章要做的是把两个方向的错摆出来，不是宣称找到了哪个数最好。
UPPER_GRID = (0.50, 0.55, 0.60, 0.70)
LOWER_GRID = (0.15, 0.20, 0.25, 0.30, 0.35, 0.40)

def _hr(title: str) -> None:
    print("=" * 74)
    print(title)
    print("=" * 74)


def _cites(r, query: str, mode: str, **kw) -> tuple[str, ...]:
    """一路检索的候选（`文档#段` 的元组）。**改写那一路返回的是改写后的结果。**"""
    if mode == "rewrite":
        hits, _new_query, _src = r.search_with_rewrite(query, k=K, **kw)
    else:
        hits = r.search(query, k=K, mode=mode, **kw)
    return tuple(h.cite() for h in hits)


def _refuse_flags(r, text: str, chunks) -> tuple[bool, bool]:
    """两条拒答判据各算一次，返回 `(只看分档, 先改写再判)`。

    第一条是 5.5 写的那条：三档判为 `incorrect`（或一片都没召回）就拒。
    第二条是本章加的：**原始问法与改写后的问法都判不可用，才拒**——
    它要修的是一类具体的错：换个说法就能查到的那道题，被第一次判分拒掉了。
    """
    _hits, _scores, quality = evaluate(r, text, depth=K)
    plain = must_refuse(chunks, quality.value) is not None
    _hits_rw, new_query, _src = r.search_with_rewrite(text, k=K)
    chunks2 = tuple(h.chunk for h in r.search(new_query, k=K, mode="bm25"))
    _h2, _s2, quality2 = evaluate(r, new_query, depth=K)
    rewritten = plain and must_refuse(chunks2, quality2.value) is not None
    return plain, rewritten


def _sweep(r, cases) -> list[dict]:
    """阈值扫描：**同一条题在每一组阈值下过一遍，两个方向的错一起报。**"""
    rows = []
    scored = []
    for c in cases:
        if not c.expect_retrieve:          # 与四格表同一口径：创意题不进拒答统计
            continue
        _hits, scores, _q = evaluate(r, c.text, depth=K)
        chunks = tuple(h.chunk for h in r.search(c.text, k=K, mode="bm25"))
        scored.append((c, max(scores) if scores else 0.0, bool(chunks)))
    for upper in UPPER_GRID:
        for lower in LOWER_GRID:
            if lower >= upper:
                continue
            cells = []
            for c, top, has_chunks in scored:
                refused = (not has_chunks) or \
                    judge((top,), upper=upper, lower=lower).value == "incorrect"
                cells.append((c.expect_refuse, refused))
            conf = refusal_confusion(cells)
            rows.append({"upper": upper, "lower": lower, "missed": conf["missed"],
                         "over": conf["over"], "errors": conf["errors"]})
    return rows


def run_offline() -> dict:
    """一次完整评测。**确定性**：不读时钟、不联网、不用随机数。"""
    cases = load_cases(CASES)
    r = build_retriever()
    model = ScriptedModel(max_chunks=K)
    recall: dict[str, list[int]] = {m: [] for m in ("bm25", "vector", "hybrid", "rewrite")}
    span: dict[str, list[int]] = {m: [] for m in recall}
    by_kind: list[tuple[str, int]] = []
    answers: list[tuple[bool, bool]] = []
    refusals: dict[str, list[tuple[bool, bool]]] = {"plain": [], "rewrite": []}
    support = {"Fully": 0, "Partially": 0, "No support": 0, "sentences": 0}
    detail: dict[str, dict[str, list[str]]] = {"plain": {"missed": [], "over": []},
                                               "rewrite": {"missed": [], "over": []}}
    span_miss: list[str] = []
    answer_miss: list[str] = []
    control: list[tuple[str, bool]] = []
    prompt_chars = 0
    rewrite_changed = 0
    for c in cases:
        chunks = tuple(h.chunk for h in r.search(c.text, k=K, mode="bm25"))
        prompt_chars += len(render_context(chunks))
        holder = span_cite(r.chunks, c.want)      # 装着答案那一段的片
        for mode in recall:
            cites = _cites(r, c.text, mode)
            if c.needs_recall:
                recall[mode].append(rank_of(cites, c.want_doc))
                span[mode].append(cites.index(holder) + 1 if holder in cites else 0)
                if mode == "bm25":            # 分组只算一路：算四路会把分母变成 4 倍
                    by_kind.append((c.kind, recall[mode][-1]))
                    if not span[mode][-1]:
                        span_miss.append(c.case)
        a = answer(model, c.text, chunks)
        b = bind(a.text, chunks)
        # 只累加三档与句数：`counts()` 里还有 `cited`，它不是支撑档位，
        # 混进 `support_ratio` 的分母会让「忠实度」变成一个与引用数相关的数。
        for key in ("Fully", "Partially", "No support", "sentences"):
            support[key] += b.counts()[key]
        if c.needs_recall:
            ok = c.want in a.text
            answers.append((ok, True))
            if not ok:
                answer_miss.append(c.case)
        # 拒答四格**只收「应当检索」的那些题**：创意题的正确动作是「不检索、直答」，
        # 它压根不该走到拒答判据上——把它算进去会凭空造出一个假的「误拒」。
        if c.expect_retrieve:
            plain, rewritten = _refuse_flags(r, c.text, chunks)
            for name, flag in (("plain", plain), ("rewrite", rewritten)):
                refusals[name].append((c.expect_refuse, flag))
                if c.expect_refuse and not flag:
                    detail[name]["missed"].append(c.case)
                if not c.expect_refuse and flag:
                    detail[name]["over"].append(c.case)
        else:
            control.append((c.case, not decide_retrieval(offline_control(c.text))))
        if _cites(r, c.text, "rewrite") != _cites(r, c.text, "hybrid"):
            rewrite_changed += 1
    return {
        "cases": len(cases),
        "k": K,
        "recall": {m: recall_at(v, K) for m, v in recall.items()},
        "recall_n": {m: len(v) for m, v in recall.items()},
        "span": {m: recall_at(v, K) for m, v in span.items()},
        "by_kind": recall_by_kind(by_kind, K),
        "span_miss": span_miss,
        "answer_miss": answer_miss,
        "control": {"n": len(control), "right": sum(1 for _c, ok in control if ok),
                    "wrong": [c for c, ok in control if not ok]},
        "refusal_detail": detail,
        "answer_hit": answer_hit_rate(answers),
        "support": support_ratio(support),
        "support_counts": support,
        "refusal": {name: refusal_confusion(rows) for name, rows in refusals.items()},
        "sweep": _sweep(r, cases),
        "cost": {"searches": 2 * len(cases), "prompt_chars": prompt_chars,
                 "calls": model.calls, "grounded_calls": model.grounded_calls,
                 "rewrite_changed": rewrite_changed},
        "resolution": min_detectable(len(cases)),
    }


def write_baseline(run: dict) -> None:
    BASELINE.write_text(json.dumps({"flat": flatten(run), "raw": run},
                                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"基线已写入 {BASELINE.relative_to(ROOT)}（{len(flatten(run))} 项）")


def read_baseline() -> dict[str, float]:
    if not BASELINE.exists():
        raise SystemExit(f"没有基线文件 {BASELINE.name}——先跑一次 --write-baseline")
    return json.loads(BASELINE.read_text(encoding="utf-8"))["flat"]


def _compare(now: dict, base: dict) -> list[str]:
    """入口在 `app.metrics.gate`；这里只是把容差这个 CLI 侧的决定传进去。"""
    return gate(now, base, TOL)


def report(run: dict) -> None:
    """五组读数。**每一张表都写清它的分母与 k**——读数没有分母就不是读数。"""
    _hr("① 四个配置的命中率（同一批题、同一个 k，只换一个变量）")
    print(f"{'配置':10s}{'命中':>12s}{'命中率':>10s}   说明")
    note = {"bm25": "字面路（5.1）", "vector": "向量路（5.3）",
            "hybrid": "融合（5.4）", "rewrite": "改写 ＋ 融合（5.4）"}
    for m, rate in run["recall"].items():
        n = run["recall_n"][m]
        hit_count = round(rate * n)
        print(f"{m:10s}{f'{hit_count}/{n}':>12s}{rate:>10.4f}   {note[m]}")
    print(f"\n（分母是「语料里真有依据」的 {run['recall_n']['bm25']} 条；k={run['k']}）")
    print("\n换个判据再看同一批结果——**片级**（装着答案的那一片进没进前三）：")
    for m, rate in run["span"].items():
        print(f"    {m:10s}{rate:.4f}")
    print(f"\n片级没命中的用例：{'、'.join(run['span_miss']) or '无'}")
    print(f"答案里没出现那段话的用例：{'、'.join(run['answer_miss']) or '无'}")
    print("按用例类型分组（字面路、文档级判据）：")
    for kind, cell in run["by_kind"].items():
        print(f"    {kind:13s}{cell['hit']}/{cell['n']}  {cell['rate']:.4f}")

    _hr("② 端到端命中率：答案里真的出现了那段话吗")
    gap = run["recall"]["bm25"] - run["answer_hit"]
    print(f"检索命中率（字面路）  {run['recall']['bm25']:.4f}")
    print(f"答案命中率（同一条路）{run['answer_hit']:.4f}")
    print(f"差额                  {gap:+.4f}   ← 这一段是「检索到了但没用上」")

    _hr("③ 拒答四格：两条判据各报一遍")
    print(f"{'判据':10s}{'正确拒答':>10s}{'漏拒':>8s}{'误拒':>8s}{'正确回答':>10s}{'合计错':>10s}")
    for name, conf in run["refusal"].items():
        label = {"plain": "只看分档", "rewrite": "先改写再判"}[name]
        print(f"{label:10s}{conf['right_refuse']:>10d}{conf['missed']:>8d}"
              f"{conf['over']:>8d}{conf['right_answer']:>10d}{conf['errors']:>10d}")
    for name, cells in run["refusal_detail"].items():
        if name != "plain":
            continue
        print(f"\n漏拒：{'、'.join(cells['missed']) or '无'}；"
              f"误拒：{'、'.join(cells['over']) or '无'}")
    con = run["control"]
    print(f"\n另两组「不检索」的题（它们不走拒答判据）：{con['right']}/{con['n']} 判对；"
          f"判错的：{'、'.join(con['wrong']) or '无'}")
    print("（**「不检索」与「拒答」是两件事**：前者是路由，后者是质量判定。"
          "把它们算进同一张四格表，会凭空多出一个「误拒」）")

    _hr("④ 阈值扫描：5.1 留下的「阈值不知道定在哪」")
    print(f"{'上':>6s}{'下':>6s}{'漏拒':>8s}{'误拒':>8s}{'合计错':>10s}")
    for row in run["sweep"]:
        print(f"{row['upper']:>6.2f}{row['lower']:>6.2f}{row['missed']:>8d}"
              f"{row['over']:>8d}{row['errors']:>10d}")
    print(f"\n（本树当前用的是 上 {CONF_UPPER}／下 {CONF_LOWER}，两档都是自定值——"
          "扫描不是去找一个「最优阈值」，是把两个方向的错摆在同一张表上）")

    _hr("⑤ 花销账")
    cost = run["cost"]
    print(f"检索次数 {cost['searches']}｜送进提示 {cost['prompt_chars']} 汉字｜"
          f"模型调用 {cost['calls']}（其中带资料 {cost['grounded_calls']}）")
    print(f"支撑统计 {run['support_counts']}｜折算忠实度 {run['support']:.4f}")
    # 改写到底改了多少东西：它数的是「改写路与融合路的候选**不同**的题数」。
    # 这一项不进 `flatten()`（它是诊断量，不是好坏量），但**必须能被读者看到**——
    # 正文里那句「改写改变的是候选集」就是拿这个数说的。
    print(f"改写改变候选 {cost['rewrite_changed']}/{run['cases']} 条")
    print(f"可检测最小差异 1/{run['cases']} ＝ {run['resolution']:.4f}"
          f"（小于它的差别不该被报出来）")
    # 一行摘要。**它是给门读的，不是给人读的**：`tools/check_runnable.py` 按
    # 「条用例」这个标记把这一行抓出来打印，抓不到就报「这段输出没人核对」。
    # 所以改这行时两处要一起改——这是「跨作用域共用字符串」必须能在门里看得见的一个例子。
    plain = run["refusal"]["plain"]
    print(f"本次评测：{run['cases']} 条用例｜k={run['k']}"
          f"｜片级命中（融合）{run['span']['hybrid']:.4f}｜答案命中 {run['answer_hit']:.4f}"
          f"｜漏拒 {plain['missed']}／误拒 {plain['over']}｜忠实度 {run['support']:.4f}"
          f"｜提示 {run['cost']['prompt_chars']} 汉字")


def self_test() -> int:
    """夹具：**改坏一档必须被拦下，改好一档不许被拦。**"""
    base = {"recall.bm25": 0.8, "answer_hit": 0.6, "refusal.plain.missed": 1,
            "refusal.plain.over": 0, "support": 0.9, "cost.prompt_chars": 4000,
            "sweep.best_errors": 1, "mystery_score": 3}
    cases = [
        ("命中率掉一条：必须报出",
         {**base, "recall.bm25": 0.8 - MIN_DETECTABLE}, 1),
        ("命中率涨一条：不许报（改进不是退步）",
         {**base, "recall.bm25": 0.8 + MIN_DETECTABLE}, 0),
        ("漏拒多一条：必须报出",
         {**base, "refusal.plain.missed": 2}, 1),
        ("漏拒少一条：不许报",
         {**base, "refusal.plain.missed": 0}, 0),
        ("误拒涨一条：必须报出",
         {**base, "refusal.plain.over": 1}, 1),
        ("忠实度掉一条的分辨率：必须报出",
         {**base, "support": 0.9 - MIN_DETECTABLE}, 1),
        ("提示字数涨了：必须报出（它是花销）",
         {**base, "cost.prompt_chars": 4200}, 1),
        # 这一条是给 `polarity()` 那处缺陷守的：`sweep.best_errors` 的尾段不在第一版的名单里，
        # 于是「可达的最少错」从 1 涨到 2 被判成「越大越好」，门一声不响。
        ("可达最少错 1 → 2：必须报出",
         {**base, "sweep.best_errors": 2}, 1),
        ("可达最少错 1 → 0：不许报（能到 0 个错是改进）",
         {**base, "sweep.best_errors": 0}, 0),
        ("方向没定义的键变了：必须报出（不许当成没退步）",
         {**base, "mystery_score": 4}, 1),
        ("方向没定义的键没变：沉默",
         {**base, "mystery_score": 3}, 0),
    ]
    ok = 0
    for name, now, want in cases:
        got = len(gate(now, base))
        good = (got > 0) == (want > 0)
        ok += good
        print(("  ✔ " if good else "  ✖ ") + name
              + ("" if good else f"（期望 {want} 处报出，实得 {got}）"))
    extra = [
        ("rank_of：同一份文档的第二片也算命中",
         rank_of(("接入清单#0", "发布规范#1"), "发布规范") == 2, True),
        ("rank_of：候选里没有它返回 0",
         rank_of(("接入清单#0",), "发布规范") == 0, True),
        ("recall_at：空分母返回 0（不假装 1.0）", recall_at([]), 0.0),
        ("可检测最小差异：24 条 ＝ 1/24",
         min_detectable(24) == round(1 / 24, 4), True),
    ]
    for name, got, want in extra:
        good = got == want
        ok += good
        print(("  ✔ " if good else "  ✖ ") + name
              + ("" if good else f"（期望 {want!r}，实得 {got!r}）"))
    total = len(cases) + len(extra)
    print(f"自检 {ok}/{total} 通过")
    return 0 if ok == total else 1


def reading_real() -> dict:
    """真机：把判分器换成模型，报**一致率**（不是「谁更对」）。"""
    from app.config import Config                                # noqa: PLC0415
    from app.llm import make_call                                # noqa: PLC0415

    _hr("⑥ 真机：判分器换成模型，与离线替身的一致率")
    cfg = Config.from_env()
    call = make_call(cfg)
    print(f"服务商 {cfg.base_url}｜模型 {cfg.model}｜温度 {cfg.temperature}")
    cases = load_cases(CASES)
    r = build_retriever()
    agree = total = 0
    for c in cases[:6]:
        chunks = tuple(h.chunk for h in r.search(c.text, k=K, mode="bm25"))[:2]
        for ch in chunks:
            offline = "Fully" if c.want and c.want in ch.text else "No support"
            verdict = call([{"role": "system", "content":
                             "只回答 Fully 或 No support：给定的资料里能不能推出这句话。"},
                            {"role": "user", "content":
                             f"资料：{ch.text}\n\n这句话：{c.text}"}]).strip()
            got = "Fully" if "Fully" in verdict else "No support"
            total += 1
            agree += got == offline
            print(f"  [{c.case}] 离线 {offline:10s} 真机 {got:10s} {ch.cite()}")
    rate = agree / total if total else 0.0
    print(f"\n一致率 {agree}/{total} ＝ {rate:.2f}；**不一致不代表某一方错了**——"
          "离线判的是字面，模型判的是能不能推出，两者口径不同（见 5.6.7）")
    return {"agree": agree, "total": total}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="五组离线读数（不需要密钥）")
    ap.add_argument("--check", action="store_true", help="与基线比，退步则非零退出")
    ap.add_argument("--write-baseline", action="store_true", help="把当前读数存成基线")
    ap.add_argument("--self-test", action="store_true", help="反例夹具")
    ap.add_argument("--real", action="store_true", help="真机判分器（只报数）")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.real:
        reading_real()
        return 0
    if not args.offline:
        ap.print_help()
        return 0
    run = run_offline()
    if args.write_baseline:
        write_baseline(run)
        report(run)
        return 0
    if args.check:
        bad = _compare(flatten(run), read_baseline())
        report(run)
        if bad:
            print("\n✖ 评测集比基线差（可能是一次真退步）：")
            for line in bad:
                print("   " + line)
            return 1
        print("\n✔ 回归门通过（所有指标不低于基线）")
        return 0
    report(run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
