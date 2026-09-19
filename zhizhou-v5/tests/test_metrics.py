# tests/test_metrics.py —— 不需要密钥、不需要网络：命中定义、分母纪律、四项指标与回归门
"""这一份测的是第 5 篇「判分层」（5.6）能不能被机械验收。

十二组断言，每一组都对应正文里的一个结论：

1. **「命中」只有一个定义**：文档级判据（同一份文档的第二片也算命中）、`k` 的边界
   （名次恰好等于 `k` 算中、`k+1` 不算、候选里没有返回 0）；
2. **分母纪律**：空分母返回 0.0 而不是 1.0（不假装满分）；`answer_hit_rate` 只对
   「要求召回」的那些条计分——拒答题与创意题不进分母；
3. **片级判据是另一件事**：`span_cite` 找的是「装着那段话的那一片」，找不到返回空串，
   `want` 为空时也不报错（创意题没有目标片）；
4. **分组读数**：`recall_by_kind` 的分母按类各算各的，不是同一个分母分四份；
5. **忠实度的折算**：Fully 计 1、Partially 计 0.5、No support 计 0；
   一句话都没说（拒答）时返回 1.0 而不是 0.0——**拒答不产生「无依据」的分母**；
6. **拒答四格**：漏拒与误拒分开数，`errors` 是两者之和；
7. **可检测的最小差异**：`min_detectable(n) ＝ 1/n`，空集返回 0.0；
8. **极性判据**：`lower` / `higher` 两类按名字判，`cost.*` 归 `lower`，
   而**判不出来的返回 `?`**——含 `sweep.best_errors` 这条回归（它的尾段不在第一版名单里）；
9. **回归门是双向的**：该高的掉了要报、该低的涨了要报、改进不许报；
10. **门的反向守**：基线里有而这一次没有的键要报（「没跑」与「没退步」必须分得开）；
    方向没定义而**真的变了**的键也要报（不许默认成「没变坏」）；
11. **评测集自己也要被评测**：`eval_cases.jsonl` 能读、条数与正文一致，
    而且**每一条的 `want` 都逐字存在于语料里**——断言写成「大意对就行」就退化成印象；
12. **端到端**：`experiments/eval_run.py --offline --check` 跑通并打印「回归门通过」，
    且正文引用的那几个读数（24 条、分辨率 1/24）仍在。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.metrics import (MIN_DETECTABLE, answer_hit_rate, flatten,        # noqa: E402
                         gate, hit, load_cases, lower_is_better,
                         min_detectable, polarity, rank_of, recall_at,
                         recall_by_kind, refusal_confusion, span_cite,
                         support_ratio)

CASES = ROOT / "tests" / "rag" / "eval_cases.jsonl"


def test_rank_of_is_document_level() -> None:
    """同一份文档的第二片也算命中：判据是文档级，不是片级。"""
    assert rank_of(("接入清单#0", "发布规范#1"), "发布规范") == 2
    assert rank_of(("接入清单#0",), "发布规范") == 0
    assert rank_of((), "发布规范") == 0


def test_hit_k_boundary() -> None:
    """`k` 的边界：名次恰好等于 k 算中，k+1 不算，0（没进去）不算。"""
    assert hit(1, 3) and hit(3, 3)
    assert not hit(4, 3)
    assert not hit(0, 3)


def test_recall_at_empty_denominator() -> None:
    """空分母返回 0.0——**不假装满分**。"""
    assert recall_at([]) == 0.0
    assert recall_at([1, 0, 4, 2], 3) == 0.5


def test_answer_hit_rate_ignores_non_recall_cases() -> None:
    """拒答题不进分母：它的正确答案是那句拒答，不含片段。"""
    rows = [(True, True), (False, True), (False, False), (True, False)]
    assert answer_hit_rate(rows) == 0.5
    assert answer_hit_rate([]) == 0.0


def test_span_cite_finds_the_chunk_holding_the_answer() -> None:
    """片级判据：装着那段话的那一片是哪一片。"""
    from app.corpus import Chunk                          # noqa: PLC0415
    c1 = Chunk("发布规范", 0, "发布说明必须包含四段：变更摘要、影响面、验证步骤、回滚方案。")
    c2 = Chunk("调用预算", 1, "2026 年第三季度的月调用预算是 2,400 万词元。")
    assert span_cite((c1, c2), "回滚方案") == "发布规范#0"
    assert span_cite((c1, c2), "2,400 万") == "调用预算#1"
    assert span_cite((c1, c2), "库里没有这句话") == ""
    assert span_cite((c1, c2), "") == ""                  # 创意题：没有目标片，不报错


def test_recall_by_kind_uses_its_own_denominator() -> None:
    """分组读数：每一类各算各的分母。"""
    got = recall_by_kind([("命中-数字", 1), ("命中-数字", 0), ("措辞-漂移", 2)], k=3)
    assert got["命中-数字"] == {"n": 2, "hit": 1, "rate": 0.5}
    assert got["措辞-漂移"]["rate"] == 1.0


def test_support_ratio_conversion() -> None:
    """Fully 计 1、Partially 计 0.5；一句话都没说时返回 1.0。"""
    assert support_ratio({"Fully": 4, "Partially": 0, "No support": 0, "sentences": 4}) == 1.0
    assert support_ratio({"Fully": 0, "Partially": 2, "No support": 2, "sentences": 4}) == 0.25
    assert support_ratio({"Fully": 0, "Partially": 0, "No support": 0, "sentences": 0}) == 1.0


def test_refusal_confusion_four_cells() -> None:
    """漏拒与误拒分开数，errors 是两者之和。"""
    rows = [(True, True), (True, False), (False, False), (False, True)]
    conf = refusal_confusion(rows)
    assert (conf["right_refuse"], conf["missed"], conf["over"], conf["right_answer"]) == (1, 1, 1, 1)
    assert conf["errors"] == 2 and conf["total"] == 4


def test_min_detectable() -> None:
    """分辨率是算出来的：n 条用例改一条就动 1/n。"""
    assert min_detectable(0) == 0.0
    assert min_detectable(24) == round(1 / 24, 4)
    assert MIN_DETECTABLE == min_detectable(24)


def test_polarity_by_name_including_best_errors() -> None:
    """极性按名字判，**含 `best_errors` 那条回归**：它的尾段不在第一版名单里。"""
    assert polarity("refusal.plain.missed") == "lower"
    assert polarity("refusal.plain.over") == "lower"
    assert polarity("sweep.best_errors") == "lower"       # ← 第一版在这里漏过
    assert polarity("cost.prompt_chars") == "lower"
    assert polarity("recall.bm25") == "higher"
    assert polarity("span.hybrid") == "higher"
    assert polarity("support") == "higher"
    assert polarity("sweep.windows_with_zero") == "higher"
    assert polarity("mystery_score") == "?"               # 判不出来要说出来，不许默认
    assert lower_is_better("sweep.best_errors") and not lower_is_better("recall.bm25")


def test_gate_is_two_directional() -> None:
    """门是双向的：该高的掉了、该低的涨了都要报；改进不许报。"""
    base = {"recall.bm25": 0.8, "refusal.plain.missed": 1, "sweep.best_errors": 1}
    assert gate(base, base) == []
    assert gate({**base, "recall.bm25": 0.7}, base)
    assert gate({**base, "refusal.plain.missed": 2}, base)
    assert gate({**base, "sweep.best_errors": 2}, base)   # ← 第一版这里一声不响
    assert gate({**base, "recall.bm25": 0.9}, base) == []
    assert gate({**base, "sweep.best_errors": 0}, base) == []


def test_gate_reverse_guards() -> None:
    """反向守：消失的键要报；方向没定义而真的变了的键也要报。"""
    base = {"recall.bm25": 0.8, "mystery_score": 3}
    assert any("消失了" in x for x in gate({"mystery_score": 3}, base))
    assert any("方向没定义" in x for x in gate({**base, "mystery_score": 4}, base))
    assert gate(base, base) == []


def test_flatten_covers_every_family() -> None:
    """扁平表把每个家族都压进来，且新家族不会被漏掉。"""
    run = {
        "recall": {"bm25": 1.0}, "span": {"bm25": 0.5}, "answer_hit": 0.9, "support": 0.8,
        "refusal": {"plain": {"right_refuse": 1, "missed": 0, "over": 0, "errors": 0}},
        "sweep": [{"errors": 2}, {"errors": 1}],
        "cost": {"prompt_chars": 4000},
    }
    flat = flatten(run)
    assert flat["sweep.best_errors"] == 1
    assert flat["sweep.windows_with_zero"] == 0
    assert flat["cost.prompt_chars"] == 4000
    assert all(polarity(k) != "?" for k in flat)          # 扁平表里不许有方向未定义的键


def test_eval_cases_are_checkable_assertions() -> None:
    """评测集自己也要被评测：**每一条的 `want` 都必须逐字存在于语料里**。

    这一条是本章最值钱的反向守。断言写成「大意对就行」的话，指标就退化成人的印象，
    而印象无法回归——所以 `want` 只能从语料里**复制**，不能「差不多地写」。
    """
    from app.retrieve import build_retriever                  # noqa: PLC0415
    cases = load_cases(CASES)
    assert len(cases) == 24
    chunks = build_retriever().chunks
    corpus = "\n".join(c.text for c in chunks)
    for c in cases:
        assert c.want == "" or c.want in corpus, f"{c.case} 的 want 不在语料里：{c.want}"
        # 三格里恰好落一格：拒答题、创意题、要召回的事实题
        assert sum((c.expect_refuse, not c.expect_retrieve, c.needs_recall)) == 1
        assert not (c.expect_refuse and c.needs_recall), f"{c.case} 既拒答又要求召回"


def test_eval_run_end_to_end() -> None:
    """端到端：回归门跑通，并且正文引用的读数还在。"""
    proc = subprocess.run([sys.executable, "experiments/eval_run.py", "--offline", "--check"],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert proc.returncode == 0, proc.stdout[-400:] + proc.stderr[-400:]
    assert "回归门通过" in proc.stdout
    assert "24 条用例" in proc.stdout
    assert "可检测最小差异 1/24 ＝ 0.0417" in proc.stdout


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_metrics.py`。"""
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
