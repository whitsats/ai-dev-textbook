# tests/test_vector.py —— 不需要密钥、不需要网络：嵌入、三种索引、两类硬错
"""这一份测的是第 5 篇「第三步」能不能被机械验收。

七组断言，每一组都对应正文里的一个结论，**都不需要模型与网络**：

1. **嵌入是确定的**：同一段文本在任何一次运行里得到同一个向量（否则读数不可复现）；
2. **标点不参与、只有标点的文本得零向量**：零向量是**一种要被报警的状态**，
   不是「嵌入失败」，所以它不许抛异常、也不许变 NaN；
3. **归一化之后内积 == 余弦**，且**不归一化时两种排序会分歧**（这是「必须先归一化」的证据）；
4. **维度不匹配。** 两个方向都要拦：查询比索引小、比索引大——这一族错在别处会静默；
5. **IVF 的性质**：`nprobe == nlist` 时它与精确检索逐条一致；`nprobe` 变小时召回不升；
6. **PQ 的性质**：内存是 `m` 字节/条，且**它的分数与精确分数不同量纲**（不许跨索引比分数）；
7. 端到端：离线脚本跑通，并打印出正文引用的那几行读数。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.embed import (DimensionMismatch, HashedEmbedder, cosine, dot,   # noqa: E402
                       l2, normalize, stats)
from app.vector_index import ExactIndex, IVFIndex, PQIndex, recall_at_k  # noqa: E402

TEXTS = ["发布说明必须包含回滚、灰度、验证与通知", "回滚是发布说明里的一段",
         "月调用预算上限是 2,400 万", "汽车发动机需要定期保养",
         "接口约定要求写入请求带一个幂等键", "值班与响应的第一联系人是谁"]


def _emb() -> HashedEmbedder:
    return HashedEmbedder(dim=64, ngram=2)


# ------------------------------------------------------------------ 1 确定性
def test_嵌入是确定的() -> None:
    emb = _emb()
    assert emb.embed_one("同一段文本") == emb.embed_one("同一段文本")
    # 换一个实例也必须是同一个向量（哈希带随机盐的话，读数就没法复现了）
    assert _emb().embed_one("同一段文本") == emb.embed_one("同一段文本")


def test_向量已经归一化() -> None:
    v = _emb().embed_one(TEXTS[0])
    assert abs(dot(v, v) - 1.0) < 1e-9


# ------------------------------------------------------------------ 2 零向量
def test_只有标点的文本得到零向量而不是异常() -> None:
    emb = _emb()
    zero = emb.embed_one("！！？……——")
    assert all(x == 0.0 for x in zero)
    assert cosine(zero, emb.embed_one(TEXTS[0])) == 0.0     # 不是 NaN


def test_空向量率抓得住零向量() -> None:
    emb = _emb()
    vectors = emb(["！！？", TEXTS[0], TEXTS[1], "……"])
    st = stats(vectors)
    assert st["empty_ratio"] == 0.5, st
    assert st["dim"] == 64 and st["count"] == 4


def test_标点是分隔符不跟着建词() -> None:
    """「发布规范：一句话」不许出现跨标点的 2-gram「范一」。"""
    emb = _emb()
    assert emb.embed_one("发布规范：一句话") != emb.embed_one("发布规范一句话")


# ------------------------------------------------------------------ 3 归一化
def test_归一化后内积等于余弦() -> None:
    emb = _emb()
    a, b = emb.embed_one(TEXTS[0]), emb.embed_one(TEXTS[1])
    assert abs(dot(a, b) - cosine(a, b)) < 1e-9


def test_未归一化时内积会把不同长度的文本判成同分() -> None:
    """这是「先归一化」那条结论的**可测证据**，而不是一句「余弦更稳」。

    两条长度为 1:4 的文本都只含一次「回滚」，未归一化时内积把它们判成同分；
    余弦分得开（0.2582 vs 0.1961）。**夹具特意选成「长度差得开、内容也不同」**，
    因为这正是真实语料里的常态：一句问话与一整节正文。
    """
    raw = HashedEmbedder(dim=64, ngram=2, normalize=False)
    texts = ["回滚", "回滚：发布说明必须包含的四段之一",
             "发布说明必须包含回滚、灰度、验证、通知这四段，缺一段就不许发布"]
    vecs = raw(texts)
    q = raw.embed_one("回滚")
    assert abs(dot(q, vecs[1]) - dot(q, vecs[2])) < 1e-9, "内积不再同分，夹具要重选"
    assert cosine(q, vecs[1]) > cosine(q, vecs[2]), "余弦应当分得开这两条"


def test_零向量的归一化是原样返回() -> None:
    assert normalize([0.0] * 4) == [0.0] * 4


# ------------------------------------------------------------------ 4 维度
def test_维度不匹配两个方向都要拦() -> None:
    index = ExactIndex(_emb()(TEXTS))
    for bad in ([0.0] * 8, [0.0] * 128):
        try:
            index.search(bad, k=1)
            raise AssertionError(f"维度 {len(bad)} 没有被拦下")
        except DimensionMismatch:
            pass


def test_一批向量自己不齐也要拦() -> None:
    try:
        ExactIndex([[1.0, 0.0], [1.0, 0.0, 0.0]])
        raise AssertionError("参差不齐的一批向量没有被拦下")
    except DimensionMismatch:
        pass


# ------------------------------------------------------------------ 5 IVF
def test_IVF_在扫全部桶时与精确一致() -> None:
    emb = _emb()
    vectors = emb(TEXTS)
    exact, ivf = ExactIndex(vectors), IVFIndex(vectors, nlist=3, nprobe=3)
    for t in TEXTS[:3]:
        q = emb.embed_one(t)
        assert [h.row for h in ivf.search(q, 3)] == [h.row for h in exact.search(q, 3)]


def test_IVF_扫的桶越多召回不降() -> None:
    emb = _emb()
    vectors = emb(TEXTS)
    exact = ExactIndex(vectors)
    queries = [emb.embed_one(t) for t in TEXTS]
    truth = [[h.row for h in exact.search(q, 3)] for q in queries]
    recalls = [recall_at_k(IVFIndex(vectors, nlist=3, nprobe=n), truth, queries, 3)
               for n in (1, 2, 3)]
    assert recalls == sorted(recalls), recalls
    assert recalls[-1] == 1.0
    assert recalls[0] < 1.0, "nprobe=1 时召回就已经满分，说明这批查询分不开桶"


def test_IVF_的桶覆盖每一片() -> None:
    vectors = _emb()(TEXTS)
    ivf = IVFIndex(vectors, nlist=3, nprobe=1)
    flat = sorted(i for b in ivf.buckets for i in b)
    assert flat == list(range(len(TEXTS)))


# ------------------------------------------------------------------ 6 PQ
def test_PQ_的内存是每片_m_字节() -> None:
    """64 维的 float32 是 256 字节/条，PQ m=4 是 4 字节/条——**压缩 64 倍**。

    注意 m 字节这个数成立的前提是 `ksub <= 256`（一个编号一个字节）；
    这是 PQ 的常见用法，也是素材里 `IVF_PQ` 那一族的默认口径。
    """
    vectors = _emb()(TEXTS)
    pq = PQIndex(vectors, m=4, ksub=8)
    assert pq.footprint()["bytes_per_vector"] == 4
    assert ExactIndex(vectors).footprint()["bytes_per_vector"] == 64 * 4
    assert (pq.footprint()["bytes_per_vector"]
            == pq.footprint()["bytes"] // len(vectors))


def test_PQ_的分数与精确不同量纲() -> None:
    emb = _emb()
    vectors = emb(TEXTS)
    q = emb.embed_one(TEXTS[0])
    exact_score = ExactIndex(vectors).search(q, 1)[0].score
    pq_score = PQIndex(vectors, m=2, ksub=8).search(q, 1)[0].score
    assert exact_score <= 1.0 + 1e-9, "精确检索的余弦不该超过 1"
    assert pq_score != exact_score, "两者分数相同，就说明这一条读数的演示不成立"


def test_PQ_的_m_必须整除维度() -> None:
    vectors = _emb()(TEXTS)          # 64 维
    for bad_m in (5, 48):
        try:
            PQIndex(vectors, m=bad_m, ksub=4)
            raise AssertionError(f"m={bad_m} 没有被拦下")
        except ValueError:
            pass
    PQIndex(vectors, m=8, ksub=4)     # 合法的那一个要能建起来


# ------------------------------------------------------------------ 7 端到端
def test_离线脚本跑通并打印正文引用的读数() -> None:
    proc = subprocess.run([sys.executable, "scripts/vector_reader.py", "--offline"],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", timeout=180)
    assert proc.returncode == 0, proc.stdout[-600:]
    out = proc.stdout
    for line in ("① 嵌入的形状", "② 两类硬错", "③ 三种索引", "④ 向量 vs BM25"):
        assert line in out, f"缺这一组：{line}"
    assert "IVF nprobe=4" in out and "PQ m=8" in out
    assert "两边都召回到目标文档的问题：2/4" in out
    # 第二个旋钮那一组（nlist × nprobe）：只调 nprobe 是看不出桶数影响的
    assert "第二个旋钮" in out and "0.33" in out


def test_自检夹具全绿() -> None:
    proc = subprocess.run([sys.executable, "scripts/vector_reader.py", "--self-test"],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", timeout=120)
    assert proc.returncode == 0, proc.stdout[-400:]
    assert "自检 9/9 通过" in proc.stdout


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_vector.py`。"""
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
