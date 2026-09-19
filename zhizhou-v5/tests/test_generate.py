# tests/test_generate.py —— 不需要密钥、不需要网络：评估器三档、精炼、引用绑定、拒答
"""这一份测的是第 5 篇「第五步」（生成侧）能不能被机械验收。

八组断言，每一组都对应正文里的一个结论：

1. **置信度只吃有尺度的分**：字面分按 `SCALE` 归一（5.1 量到的 19.79 → 0.99、
   噪声档的 6.03 → 0.30）；**融合分是非法输入**（5.4：RRF 只吃名次不吃分数），
   传进去必须报错而不是算出一个看着像样的数；
2. **三档的汇总写法是论文那一条**：有一片高于上阈值 → Correct（哪怕其余全是 0）；
   全都低于下阈值 → Incorrect；一片都没有 → 也按 Incorrect（等价于「全都够低」）；
3. **精炼不改地址、只改字数**：留下的片的 `cite()` 与原来一片一字不差；
   `drop_ratio` 在 0–1；整批被过滤干净时返回空片并留下一条 note（调用方据此走兜底）；
4. **strips 的顺序不动**（重组那一步的硬要求）；
5. **绑定只增不改**：把句末的 `[i]` 去掉之后，正文与模型原文逐字相同；
6. **三档支撑能被构造出来**：语料原句 → Fully；把原句砍成片段 → Partially；
   编造的一句 → No support，并且**它会出现在 `issues` 里**（幻觉变成可打印的名单）；
7. **拒答判据**：空片与 Incorrect 档各有理由；有依据时不拦；
8. **控制位**：事实题 → `yes`、创意题 → `no`、`continue` 只在不检索时才用；
   从模型输出里抓令牌，抓不到按 `yes`（宁可多查一次，不可漏查）。

另有一条端到端：`scripts/generate_reader.py --offline` 跑通，并且正文引用的那几行读数还在。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.corpus import Chunk                                            # noqa: E402
from app.critic import (CONF_LOWER, CONF_UPPER, SCALE, Quality,         # noqa: E402
                        confidence, fallback, judge, refine, strips)
from app.generate import (Control, bind, decide_retrieval, must_refuse,  # noqa: E402
                          offline_control, parse_control, split_sentences)
from app.rag import NO_ANSWER                                           # noqa: E402
from app.retrieve import Hit                                            # noqa: E402

C1 = Chunk("发布规范", 1, "发布说明必须包含四段：变更摘要、影响面、验证步骤、回滚方案。")
C2 = Chunk("调用预算", 0, "2026 年第三季度的月调用预算是 2,400 万词元。")


def _hit(chunk: Chunk, score: float, source: str = "bm25", rank: int = 1) -> Hit:
    return Hit(chunk, score, source, rank)


# ---------------- 1. 置信度只吃有尺度的分 ----------------

def test_置信度把5_1量到的两档翻译进三档语言() -> None:
    """19.79（5.1 的最高命中分）→ 0.99 落上档；6.03（噪声档）→ 0.30 落在中间那档。"""
    assert confidence((_hit(C1, 19.79),))[0] == round(19.79 / SCALE, 4)
    assert confidence((_hit(C1, 19.79),))[0] > CONF_UPPER
    noise = confidence((_hit(C1, 6.03),))[0]
    assert CONF_LOWER < noise < CONF_UPPER, "噪声档必须落在 Ambiguous 区间里"


def test_向量分原样使用且会被截断到0到1() -> None:
    assert confidence((_hit(C1, 0.62, "vector"),)) == (0.62,)
    assert confidence((_hit(C1, 1.4, "vector"),)) == (1.0,)
    assert confidence((_hit(C1, -3.0, "vector"),)) == (0.0,)


def test_融合分是非法输入() -> None:
    """5.4 的结论在这一行生效：秩序量不能进阈值判定，宁可报错。"""
    try:
        confidence((_hit(C1, 0.016, "rrf"),))
    except ValueError as exc:
        assert "秩序量" in str(exc)
    else:
        raise AssertionError("融合分必须被拒绝")


# ---------------- 2. 三档的汇总写法 ----------------

def test_有一片够高就是Correct哪怕其余是零() -> None:
    assert judge((0.0, 0.0, 0.99)) is Quality.CORRECT


def test_全都够低才是Incorrect() -> None:
    assert judge((0.01, 0.02, CONF_LOWER)) is Quality.INCORRECT
    assert judge((0.01, 0.02, CONF_LOWER + 0.01)) is Quality.AMBIGUOUS


def test_一片都没有等价于全都够低() -> None:
    assert judge(()) is Quality.INCORRECT


def test_三档各有一个动作名() -> None:
    acts = {q.action for q in Quality}
    assert len(acts) == 3
    assert any("兜底" in a for a in acts)


# ---------------- 3. 精炼不改地址、只改字数 ----------------

def test_精炼留下的是原文的子串且地址不变() -> None:
    r = refine("发布说明必须包含哪几段？", (C1, C2))
    assert r.stats()["sources"] == ("发布规范#1",), "地址必须与原来一片一字不差"
    for c in r.chunks:
        assert c.text in C1.text, "重组出来的必须是原文的子串（顺序也不能动）"
    assert r.chars_after <= r.chars_before
    assert 0.0 <= r.drop_ratio <= 1.0


def test_整批被过滤干净要留一条note() -> None:
    r = refine("量子纠缠的退相干时间是多少？", (C1, C2))
    assert r.chunks == ()
    assert r.notes and "兜底" in r.notes[0]
    assert r.drop_ratio == 1.0


def test_兜底指出最接近的片而不是假装有搜索结果() -> None:
    f = fallback("知舟 2027 年的营收目标是多少？", (C1, C2))
    assert f["refuse"] is True
    assert len(f["closest"]) == 1
    assert "不联网" in f["note"]


# ---------------- 4. strips 的顺序 ----------------

def test_strips保持原序且丢弃空段() -> None:
    got = strips("第一句。第二句；\n\n第三句！")
    assert got == ("第一句。", "第二句；", "第三句！")


# ---------------- 5. 绑定只增不改 ----------------

def test_绑定只加编号不改正文一个字() -> None:
    raw = "发布说明必须包含四段。2026 年的营收目标是 3.5 亿元。"
    b = bind(raw, (C1, C2))
    stripped = re.sub(r"\s*\[\d+\]", "", b.text)
    assert stripped.replace(" ", "") == raw.replace(" ", "")


def test_引用的地址一定来自给它的片() -> None:
    b = bind("发布说明必须包含四段。", (C1, C2))
    assert set(b.citations) <= {C1.cite(), C2.cite()}
    assert b.counts()["cited"] == 1


# ---------------- 6. 三档支撑能被构造出来 ----------------

def test_语料原句是Fully带片段是Partially编造是No() -> None:
    b = bind("发布说明必须包含四段：变更摘要、影响面、验证步骤、回滚方案。"
             "季度预算上限是 2,400 万。"
             "知舟计划在 2027 年把月预算提高到 9,000 万。", (C1, C2))
    sup = [s.support for s in b.sentences]
    assert sup[0] == "Fully", "原句照抄必须是 Fully"
    assert sup[1] == "Partially", "砍成片段应当降到 Partially"
    assert sup[2] == "No support", "编造的那一句必须落空"
    assert b.counts()["No support"] == 1
    assert b.issues and "找不到依据" in b.issues[0]


def test_拒答句不挂引用也不算无依据() -> None:
    b = bind(NO_ANSWER, (C1, C2))
    assert b.citations == ()
    assert b.issues == ()


# ---------------- 7. 拒答判据 ----------------

def test_空片与Incorrect档各有一条理由而正常不拦() -> None:
    assert must_refuse((), "correct") == "检索一片都没召回"
    assert "Incorrect" in must_refuse((C1,), "incorrect")
    assert must_refuse((C1,), "correct") is None


def test_拆句把没有标点的尾巴也算一句() -> None:
    assert split_sentences("只答一句没有标点的话") == ("只答一句没有标点的话",)


# ---------------- 8. 控制位 ----------------

def test_按需检索的判据() -> None:
    assert offline_control("知舟的发布说明必须包含哪几段？").retrieve == "yes"
    assert offline_control("写一首关于春天的诗").retrieve == "no"
    assert offline_control("继续", continuing=True).retrieve == "continue"
    assert decide_retrieval(Control("yes")) is True
    assert decide_retrieval(Control("continue")) is False


def test_从模型输出里抓令牌抓不到按yes处理() -> None:
    assert parse_control("[Retrieve=No] 春风拂面暖如酥。").retrieve == "no"
    assert parse_control("[Retrieve=Continue] 接着上面说。").retrieve == "continue"
    assert parse_control("直接回答，没有令牌").retrieve == "yes"


# ---------------- 端到端 ----------------

def test_离线读数脚本跑通并留下正文引用的那几行() -> None:
    proc = subprocess.run([sys.executable, "scripts/generate_reader.py", "--offline"],
                          cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    assert proc.returncode == 0, proc.stderr[-2000:]
    out = proc.stdout
    assert "离线自检通过" in out
    for key in ("三档", "精炼", "绑定", "控制位"):
        assert key in out, f"读数里缺「{key}」那一节"


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_generate.py`。"""
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
