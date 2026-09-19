# tests/test_why_rag.py —— 不需要密钥、不需要网络：知识层、两条路径、引用核对
"""这一份测的是第 5 篇「第一步」能不能被机械验收。

七组断言，每一组都对应正文里的一个结论，**都不需要模型**：

1. 语料能读、能切、切出来的片数与文档规模对得上；
2. 索引的**已知失手形态**真的是那样（零重合同义问一片都召不回）——
   这一条是「回归门」：哪天有人把 2-gram 换成别的，测试会先喊；
3. 「不检索」与「检索到空」是两条**不同**的路径（第一版把它们合并了，见 `app.rag`）；
4. 引用核对能抓三种坏答案，且直答那一路不核对；
5. 该拒答的拒了、不该拒的没拒；
6. 阈值实验的那两个数（噪声 6.03 与正确召回 8.07）与正文一致；
7. 离线脚本跑通且打印出正文引用的那几行读数。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.corpus import Chunk, build_index, load_corpus, split_paragraphs   # noqa: E402
from app.questions import QUESTIONS, by_id                                  # noqa: E402
from app.rag import (NO_ANSWER, NO_CONTEXT, answer, build_messages,         # noqa: E402
                     check_citations, render_context)
from app.scripted import FABRICATED, ScriptedModel                          # noqa: E402

TOP_K = 3


def _chunks_for(text: str, k: int = TOP_K):
    index, _ = build_index()
    return index, tuple(c for c, _ in index.search(text, k=k))


# ---------------------------------------------------------------- 一、语料

def test_语料能读能切() -> None:
    docs = load_corpus()
    assert len(docs) == 6, "语料是 6 份文档"
    assert all(d.title for d in docs), "每份文档都要有标题，引用时要拿它显示"
    pieces = [c for d in docs for c in split_paragraphs(d)]
    assert len(pieces) == 15, f"按空行切出 15 片，实际 {len(pieces)}"
    assert all(c.text.strip() for c in pieces), "不允许出现空片"
    assert not any(c.text.lstrip().startswith("#") for c in pieces), \
        "标题行必须被去掉——留着会被算成正文命中，召回率就虚高了"


def test_每份文档都按空行切成多片() -> None:
    """6 份文档切成 15 片：**每一份都不止一片**，否则「漏片」这个现象就不存在。"""
    per_doc = {d.doc_id: len(split_paragraphs(d)) for d in load_corpus()}
    assert all(n >= 2 for n in per_doc.values()), per_doc


# ---------------------------------------------------------------- 二、索引

def test_零重合同义问一片都召不回() -> None:
    """**这是 5.1 的一条硬结论，也是 5.3／5.4 存在的理由。**
    「用户连点两下会不会写两条记录？」与库里那句话一个字都对不上——
    它不是「排序靠后」，是**根本不在榜上**。"""
    index, _ = build_index()
    got = index.search(by_id("Q3").text, k=10)
    assert got == (), f"零重合的问题不该召回任何片，实际 {[c.cite() for c, _ in got]}"


def test_换词不等于零重合() -> None:
    """**第一版的一个错，钉在测试里。** 我原本以为「防重复的标识」也对不上资料，
    实测它拿了 6.24 分。原因是「写接」「接口」两边都有——
    所以「零重合」得一个字都对不上，不能靠感觉。"""
    index, _ = build_index()
    got = index.search("写接口要带什么防重复的标识？", k=TOP_K)
    assert got and got[0][0].doc_id == "接口约定", "这一句是能召回的（所以它不能当失败例）"


def test_该空的问题反而召回了噪声() -> None:
    """「库里根本没有」（Q4）实测**召回到了 3 片**、最高 6.03。
    检索的行为是「永远把前 k 片填满」——这是 5.5 要面对的处境。"""
    index, _ = build_index()
    got = index.search(by_id("Q4").text, k=TOP_K)
    assert len(got) == TOP_K, "实测就是填满了"
    assert got[0][1] > 6.0, f"最高分实测 6.03，实际 {got[0][1]}"


def test_阈值裕度不到两分() -> None:
    """τ 在 (6.03, 8.07) 之间四条全对——**裕度不到 2 分**，而且这两个数
    一个是噪声、一个是正确召回。所以本树不给召回设默认阈值。
    另：同一份资料、只把问法写短，最高分就从 19.79 掉到 8.07。"""
    index, _ = build_index()
    noise = index.search(by_id("Q4").text, k=TOP_K)[0][1]
    short = index.search("发布说明要写几段？", k=TOP_K)[0][1]
    long_ = index.search(by_id("Q1").text, k=TOP_K)[0][1]
    assert 6.0 < noise < 7.0 and 8.0 < short < 8.2, (noise, short)
    assert short < long_ < 20.0, "问法写短，分数掉下来"
    assert (index.search(by_id("Q4").text, k=TOP_K, min_score=7.0)) == (), \
        "τ=7 能把噪声卡掉"


# ---------------------------------------------------------------- 三、两条路径

def test_不检索与检索到空是两条不同路径() -> None:
    """**第一版的真错**：`if chunks:` 把「空」与「无」并在同一个分支里，
    于是「召回为空」走了**直答**的提示，模型照旧编。"""
    direct = build_messages("问", None)
    grounded = build_messages("问", ())
    assert direct != grounded, "两条路径的提示必须不同"
    assert "只允许依据" in grounded[0]["content"], "召回为空时最该走的是「只依据资料」那条"
    assert NO_CONTEXT in grounded[-1]["content"], "空资料要在提示里写明，不能留白"


def test_空资料时模型应当拒答() -> None:
    index, chunks = _chunks_for(by_id("Q3").text)
    assert chunks == ()
    got = answer(ScriptedModel(), by_id("Q3").text, chunks)
    assert got.grounded and got.refused and got.text.strip() == NO_ANSWER


def test_渲染契约是一行一片() -> None:
    """片内有换行时渲染**必须折成单空格**：回读那一侧是逐行解析的，
    不然第二行起会静默丢掉（真事故：`调用预算#0` 的「2,400 万词元」曾整段消失）。"""
    c = Chunk("x", 0, "第一行\n第二行")
    out = render_context((c,))
    assert "\n" not in out.strip(), "一份资料必须渲染成一行"
    assert "第一行 第二行" in out


def test_带资料能答对私有数字而直答答不出() -> None:
    index, chunks = _chunks_for(by_id("Q2").text)
    model = ScriptedModel()
    grounded = answer(model, by_id("Q2").text, chunks)
    direct = answer(model, by_id("Q2").text, None)
    assert "2,400" in grounded.text and "2,400" not in direct.text
    assert grounded.citations == (1, 2), "照抄了两片就要标两个编号"


def test_私有规范那一题漏的是片不是文档() -> None:
    """**Q1 的漏法**：文档召回了，但装着四个条目的那一片排第 5。
    「答不对」与「找不到文档」是两种病，改的地方完全不同——
    这一条对应 5.2 的切分。"""
    index, chunks = _chunks_for(by_id("Q1").text)
    assert any(c.doc_id == "发布规范" for c in chunks), "文档召回了"
    got = answer(ScriptedModel(), by_id("Q1").text, chunks)
    assert "回滚" not in got.text, "关键那一片没到，所以答案里没有它"
    ranked = index.search(by_id("Q1").text, k=len(index.chunks))
    rank = next(i for i, (c, _) in enumerate(ranked, start=1) if "回滚" in c.text)
    assert rank == 5, f"实测排第 5，实际第 {rank}"


# ---------------------------------------------------------------- 四、引用核对

def test_引用核对三种坏答案() -> None:
    two = (Chunk("x", 0, "y"), Chunk("x", 1, "y"))
    assert check_citations("四段。[1]", two) == ()
    assert any("越界" in i for i in check_citations("四段。[7]", two))
    assert any("一条引用都没标" in i for i in check_citations("四段。", two))
    assert check_citations(NO_ANSWER, two) == (), "拒答不要求引用"


def test_零片却标了引用必须拦下() -> None:
    """`chunks=()` 是「检索了但一片都没有」——在这条路径上标任何编号都是错的。"""
    assert any("越界" in i for i in check_citations("四段。[1]", ()))


def test_直答那一路不做引用核对() -> None:
    """`chunks=None` 才是「不做检索」：没有资料可引，就不核对。"""
    got = answer(lambda msgs: "四段。[1]", "问", None)
    assert got.issues == () and not got.grounded


# ---------------------------------------------------------------- 五、夹具本身

def test_夹具的四条问题各有分工() -> None:
    assert [q.qid for q in QUESTIONS] == ["Q1", "Q2", "Q3", "Q4"]
    assert [q.want_recall for q in QUESTIONS] == ["命中", "命中", "空", "空"]
    assert by_id("Q4").want_doc is None, "Q4 是「库里没有」，不该指向任何文档"
    assert by_id("Q3").want_doc == "接口约定", "Q3 是「库里有、够不着」"


def test_编造表覆盖了每条该有答案的问题() -> None:
    """直答那一路对每条「可答」的问题都要有一个像样的错答案，
    否则 ② 那组读数就不是「全编」，而是「两条有回复、两条没有」。"""
    askable = [q.text for q in QUESTIONS if q.expect]
    missing = [t for t in askable if t not in FABRICATED]
    assert not missing, f"少了：{missing}"


# ---------------------------------------------------------------- 六、端到端

def test_离线脚本跑通并打印读数() -> None:
    """把脚本当门跑一遍：正文引用的每一行读数都必须在里面。"""
    import subprocess
    proc = subprocess.run([sys.executable, "scripts/why_rag.py", "--offline"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert proc.returncode == 0, proc.stderr[-300:]
    out = proc.stdout
    assert "离线自检通过" in out
    assert "该召回的召回了 2/2" in out
    assert "该空的一片都没给 1/2" in out
    assert "引用可核对 ≠ 引用正确" in out
    assert "排在第 5，没进前 3 片" in out
    assert "四条问题不是证据" in out


def test_自检夹具全绿() -> None:
    import subprocess
    proc = subprocess.run([sys.executable, "scripts/why_rag.py", "--self-test"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert proc.returncode == 0, proc.stdout[-400:]
    assert "自检 7/7 通过" in proc.stdout


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_why_rag.py`。"""
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
