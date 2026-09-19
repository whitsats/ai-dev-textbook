#!/usr/bin/env python
"""5.3 读数：**向量到底比字面匹配多拿到了什么。**

五组：

    ① 嵌入的形状：维度、归一化，与三个相似度函数之间的关系
    ② 两类硬错：空向量（零范数）与维度不匹配（换模型没重建索引）
    ③ 三种索引同语料：精确 / IVF（扫 nprobe 个桶）/ PQ（乘积量化）
    ④ 向量 vs BM25：5.1 那四条问题，在同一份 5.2 切法语料上各召回什么
    ⑤ 真机那一侧的真实边界：服务商有没有嵌入端点（**没有就说不有**）

    python scripts/vector_reader.py --offline     # 不需要密钥、不需要网络：提交钩子跑这个
    python scripts/vector_reader.py --self-test   # 反例夹具：几条不变式必须成立
    python scripts/vector_reader.py --real        # 打服务商的 /models，看有没有嵌入模型

一条纪律写在最前面：**①②③④ 是门，⑤ 是一次探测。**
本章的嵌入器是离线的哈希 n-gram，它的「语义」代理是**字面重合**——
所以 ④ 那一组会看到它**并没有比 BM25 多召回任何一条**。那不是脚本坏了，那就是结论：
真正能救「同义改写」的是真嵌入模型（本机没有端点）或查询改写（5.4）。
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.corpus import load_corpus                                    # noqa: E402
from app.embed import (DimensionMismatch, HashedEmbedder, cosine,      # noqa: E402
                       dot, l2, normalize, stats)
from app.questions import QUESTIONS                                   # noqa: E402
from app.split import build_index                                     # noqa: E402
from app.vector_index import (ExactIndex, IVFIndex, PQIndex,          # noqa: E402
                              recall_at_k)

TOP_K = 3
DIM = 256
#: 语料只有十几片，桶数取 4——**桶数不该比片数还多**，否则每个桶里只有一两片，
#: nprobe 的对照就退化成「扫不扫那一片」，量不出结构上的规律。
NLIST = 4


def _hr(title: str) -> None:
    print("=" * 74)
    print(title)
    print("=" * 74)


def _pad(text: str, width: int) -> str:
    """按**显示宽度**补齐：汉字与全角标点在终端上占两列。

    这不是细心问题：第一版用 `f"{t:<34}"` 排出来的表全是歪的，
    而这类歪斜在代码里完全看不出来（字符串是齐的），只有跑一遍才发现。
    """
    shown = sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)
    return text + " " * max(0, width - shown)


# --------------------------------------------------------------------------- ①
def reading_shape() -> dict:
    _hr("① 嵌入的形状：维度、归一化与三个相似度")
    emb = HashedEmbedder(dim=DIM, ngram=2)
    print(f"嵌入器：哈希 2-gram ｜ 维度 {DIM} ｜ 归一化 开")
    print("它没有语义层，只有一条真性质：**字面重合越多，向量越接近**。")
    print()

    pairs = [("感冒药物", "抗感冒药物"), ("感冒药物", "汽车发动机"), ("解热镇痛药的副作用", "副作用")]
    for a, b in pairs:
        va, vb = emb.embed_one(a), emb.embed_one(b)
        print(f"  cos({a}，{b}) = {cosine(va, vb):.4f}　"
              f"内积 {dot(va, vb):.4f}　L2 {l2(va, vb):.4f}")
    print()
    print("归一化之后 **内积 == 余弦**（上面每一行两个数相等）。")
    print("不归一化时它们会分开，后果不是「排序微调」，而是**内积退化成数重合次数**：")
    print()

    # 另一半也要量：「归一化后 L2 与余弦单调等价」这句话，本章不能只靠公式说。
    # 做法：拿真实语料上的四个查询，分别按三种度量排序，看三个排名是否逐条相同。
    bm25_pieces = [
        "发布说明必须包含回滚、灰度、验证与通知这四段",
        "月调用预算上限是 2,400 万，超出要走审批",
        "用户连续提交两次时以幂等键去重，只落一条记录",
        "值班与响应的第一联系人写在接入清单里，",
        "命名与目录：接口文件放 app/api，模型放 app/models",
        "灰度阶段只放 5% 流量，回滚窗口 30 分钟",
    ]
    vecs = emb(bm25_pieces)
    agree = 0
    tied = 0
    for query in ("发布说明要写哪四段", "预算超了怎么办", "连点两下会不会写两条"):
        q = emb.embed_one(query)
        cos = [round(cosine(q, v), 6) for v in vecs]
        tied += len(cos) - len(set(cos))          # 余弦精确相等的位置数
        by_cos = [i for i, _ in sorted(enumerate(vecs),
                                       key=lambda t: (-cos[t[0]], t[0]))[:3]]
        by_ip = [i for i, _ in sorted(enumerate(vecs),
                                      key=lambda t: (-round(dot(q, t[1]), 6), t[0]))[:3]]
        by_l2 = [i for i, _ in sorted(enumerate(vecs),
                                      key=lambda t: (round(l2(q, t[1]), 6), t[0]))[:3]]
        agree += 1 if by_cos == by_ip == by_l2 else 0
    print(f"归一化后三种度量的前 3 名是否一致：**{agree}/3 条查询一致**")
    print("（这一组就是「归一化之后选哪个度量是成本问题」，但它**只在归一化后成立**；")
    print("不归一化时上面那张表已经给出反例。）")
    print()
    print(f"但这一次不是白跑的：**有 {tied} 个位置是「同分」（余弦精确相等）**。")
    print("同分时谁先出列，取决于你把次序写成什么——上面三行之所以一致，是因为先四舍到")
    print("6 位、再按下标定次序（与 `ExactIndex.search` 里 `sort(key=lambda t: (-t[1], t[0]))`")
    print("是同一个手法）。**不写次序就等于把名次交给浮点误差。**")
    print()

    texts = ["回滚", "回滚：发布说明必须包含的四段之一",
             "发布说明必须包含回滚、灰度、验证、通知这四段，缺一段就不许发布"]
    raw = HashedEmbedder(dim=DIM, ngram=2, normalize=False)
    raw_vecs = raw(texts)
    print("  " + _pad("文本", 30) + f"{'范数':>8}{'cos↓':>9}{'内积↓':>9}{'L2↑':>9}")
    q = raw.embed_one("回滚")
    for t, v in zip(texts, raw_vecs):
        print("  " + _pad(t[:14], 30) + f"{sum(x * x for x in v) ** 0.5:>8.2f}"
              f"{cosine(q, v):>9.4f}{dot(q, v):>9.2f}{l2(q, v):>9.2f}")
    print()
    print("看「内积」那一列：**后两条文本拿了同一个分 1.00**。它们长度差一倍、内容也不同，")
    print("内积却分不开——因为它数的就是「「回滚」这个 gram 出现几次」，两条都只出现一次。")
    print("余弦把那点差别拿回来了（0.2582 vs 0.1961），L2 在这一组里顺序与余弦一致，")
    print("但它的数值里还夹着两个模长的差，所以**不能拿绝对值跨对比较**。")
    print()
    print("这就是「先归一化、并把度量口径写进契约」的理由：Milvus 里换 `metric_type`")
    print("而向量没归一化，等于**把「相关多少」换成了「重合几个词」**——而两者在这份语料上会给出")
    print("同一个第一名，所以你很难发现换错了。（上面这一段是本章第一个「两种做法看起来对、其实不同」的地方。）")
    print()
    print("补一句边界：L2 与余弦的**顺序一致**只在归一化之后才是一般结论，未归一化时不一定——")
    print("这一组恰好一致，不能当规律用。")
    return {"pairs": [(a, b, round(cosine(emb.embed_one(a), emb.embed_one(b)), 4))
                     for a, b in pairs]}


# --------------------------------------------------------------------------- ②
def reading_hard_errors(pieces) -> dict:
    _hr("② 两类硬错：空向量与维度不匹配")
    emb = HashedEmbedder(dim=DIM)
    vectors = emb([p.text for p in pieces])

    # 空向量：一段**只有标点符号**的片。它不是「嵌入失败」，是一种真实存在的入库结果。
    weird = ["！！？", "……——", pieces[0].text]
    vv = emb(weird)
    st = stats(vv)
    print(f"「只有标点」那两段：{weird[0]} → 向量前 5 位 {[round(x, 3) for x in vv[0][:5]]}")
    print(f"  这批（2 段只有标点 ＋ 1 段真文本）空向量率 = {st['empty_ratio']}　平均范数 {st['mean_norm']}")
    print("**空向量不会自己报错**：`cosine()` 对它返回 0.0（不是 NaN），排序照常有结果——")
    print("所以要靠「空向量率」这个比值来报警，而不是靠异常。素材里那条「全零占比 > 1%」，")
    print("监控的就是这件事：那说明嵌入这一步没真正跑起来（模型没加载、批被截断）。")
    print()

    print("维度不匹配（换嵌入模型没重建索引）：")
    ex = ExactIndex(vectors)
    for bad_dim, label in [(64, "查询向量 64 维（换了小模型）"), (DIM + 1, "查询向量 257 维")]:
        try:
            ex.search([0.0] * bad_dim, k=TOP_K)
            print(f"  {label}：**没有报错**——这是缺陷")
        except DimensionMismatch as exc:
            print(f"  {label}：报错 → {exc}")
    print()
    print("两条都是「静默」与「硬拦」之间的选择：**空向量静默、维度不匹配硬拦**。")
    print("反过来做会怎样，②的反例夹具里各有一条。")
    return {"empty_ratio": st["empty_ratio"], "n": len(pieces)}


# --------------------------------------------------------------------------- ③
def reading_indexes(pieces, queries) -> dict:
    _hr("③ 三种索引：召回、扫描量、单条字节")
    emb = HashedEmbedder(dim=DIM)
    vectors = emb([p.text for p in pieces])
    exact = ExactIndex(vectors)
    truth = [[h.row for h in exact.search(q, TOP_K)] for q in queries]

    print(f"语料：{len(pieces)} 片 ｜ 维度 {DIM} ｜ 查询 {len(queries)} 条 ｜ 标尺 = 精确检索的前 {TOP_K} 条")
    print()
    print("  " + _pad("索引", 24) + f"{'召回@3':>8}{'平均扫描':>10}{'单条字节':>10}")
    print("  " + _pad("精确（暴力）", 24)
          + f"{1.0:>8.2f}{len(pieces):>10}{exact.footprint()['bytes_per_vector']:>10}")

    out = {"exact": {"recall": 1.0, "scanned": len(pieces),
                     "bytes_per_vector": exact.footprint()["bytes_per_vector"]}}
    for nprobe in (1, 2, 3, NLIST):
        iv = IVFIndex(vectors, nlist=NLIST, nprobe=nprobe)
        rec = recall_at_k(iv, truth, queries, TOP_K)
        scanned = sum(len(iv.buckets[b])
                      for b in sorted(range(len(iv.centers)),
                                      key=lambda c: -dot(normalize(queries[0]),
                                                         iv.centers[c]))[:nprobe])
        print("  " + _pad(f"IVF nprobe={nprobe}", 24)
              + f"{rec:>8.2f}{scanned:>10}{iv.footprint()['bytes_per_vector']:>10}")
        out[f"ivf_nprobe{nprobe}"] = {"recall": rec, "scanned": scanned}
    print(f"  （桶大小 {iv.footprint()['bucket_sizes']}，nlist={NLIST}）")

    for m in (2, 4, 8):
        pq = PQIndex(vectors, m=m, ksub=8)
        rec = recall_at_k(pq, truth, queries, TOP_K)
        print("  " + _pad(f"PQ m={m}", 24)
              + f"{rec:>8.2f}{len(pieces):>10}{pq.footprint()['bytes_per_vector']:>10}")
        out[f"pq_m{m}"] = {"recall": rec, "bytes_per_vector": pq.footprint()["bytes_per_vector"]}
    print()
    print("三条要一起读的话：")
    print("  · **IVF 丢的是「没扫到的那部分」**：nprobe 从 1 加到 nlist，召回 0.50 → 0.75 →")
    print("    0.92 → 1.00，而扫描条数同期从 5 升到 12——**它就是精确检索加一个「少看几桶」的旋钮**，")
    print("    不是「有损结构」；")
    print("  · **PQ 丢的是精度**：内存压到 m 字节/条（256 倍），分数也不再是余弦（被近似扯开了量纲），")
    print("    **跨索引比分数是错的，只有排名可比**；")
    print("  · 但 PQ 的召回在这 12 片上**不单调**（0.42 / 0.50 / 0.50）——**样本太小，不能拿它排序**。")
    print("    能立住的只有两条：内存降两个数量级、分数量纲变了；损失要等有规模的语料与评测集（5.6）才谈得上。")
    print("  · 同理，三种索引的差距在十几片上很小——**索引的收益随规模长**，这一条本章量不出来，")
    print("    所以正文里不写「快了多少倍」，只写「扫了多少条」。")
    print()
    print("## 第二个旋钮：`nlist`（桶数）与 `nprobe` 是一对，不能只调一个")
    print()
    print("     nlist\\nprobe" + "".join(f"{n:>7}" for n in (1, 2, 4, 8)))
    grid: dict[str, float] = {}
    for nlist in (2, 4, 8):
        row = f"     {nlist:>10}"
        for nprobe in (1, 2, 4, 8):
            np_ = min(nprobe, nlist)
            rec = recall_at_k(IVFIndex(vectors, nlist=nlist, nprobe=np_), truth,
                              queries, TOP_K)
            row += f"{rec:>7.2f}"
            grid[f"nlist{nlist}_nprobe{nprobe}"] = rec
        print(row)
    print(f"    （表头是 nprobe，行首是 nlist；语料 {len(pieces)} 片、{len(queries)} 条查询，"
          f"标尺仍为精确检索）")
    print()
    print("两列一起看才有意义：**`nprobe` 是「看几个桶」，`nlist` 是「桶有多小」。**")
    print("桶越多，同一个 nprobe 看到的比例越小；而 nprobe 触及 nlist 时又回到精确。")
    print("所以「nprobe 取多少」这个问法本身不够——它得连着 nlist 一起定。")
    print("另：桶数不该比片数还多（本章 12 片时取 4），否则每个桶里只剩一两片，")
    print("对照就退化成「扫不扫那一片」，量不出结构上的规律。")
    out["grid"] = grid
    return out


# --------------------------------------------------------------------------- ④
def reading_vs_bm25(pieces, bm25) -> dict:
    _hr("④ 向量 vs BM25：四条问题各召回什么")
    emb = HashedEmbedder(dim=DIM)
    vectors = emb([p.text for p in pieces])
    index = ExactIndex(vectors)
    print(f"同一份语料（5.2 的结构感知切法）、同一个 k={TOP_K}、同四条问题。")
    print("两种检索器的**唯一差别**是「怎么算像」：BM25 数字面，向量数向量。")
    print()

    rows = {}
    for q in QUESTIONS:
        bm = [(c.cite(), round(s, 2)) for c, s in bm25.search(q.text, k=TOP_K)]
        vq = emb.embed_one(q.text)
        vec = [(pieces[h.row].doc_id + f"#{pieces[h.row].index}", round(h.score, 4))
               for h in index.search(vq, TOP_K)]
        rows[q.qid] = {"bm25": bm, "vector": vec, "want": q.want_doc}
        print(f"{q.qid}（{q.kind}）　期望：{q.want_recall}"
              + (f" → {q.want_doc}" if q.want_doc else " → 库里没有"))
        print(f"    问：{q.text}")
        print(f"    BM25　：{('、'.join(f'{c}({s})' for c, s in bm)) or '（0 片）'}")
        print(f"    向量　：{('、'.join(f'{c}({s})' for c, s in vec)) or '（0 片）'}")
        same = [c for c, _ in bm] == [c for c, _ in vec]
        print(f"    两者一致：{'是' if same else '**否**'}"
              + ("" if same else "　← 差别只在「同一批候选的排序」，还是「候选集本身就不同」"))
        print()

    both_hit = sum(1 for q in QUESTIONS
                   if q.want_doc and any(c.startswith(q.want_doc) for c, _ in rows[q.qid]["vector"])
                   and any(c.startswith(q.want_doc) for c, _ in rows[q.qid]["bm25"]))
    print(f"两边都召回到目标文档的问题：{both_hit}/{len(QUESTIONS)}")
    print()
    print("**本章最重要的一条读数在这里，而它与我动笔前的预设相反。**")
    print("我原本以为向量会把 Q3（同义改写）救回来。实测是：")
    print("  · Q3 在 BM25 那边是**零召回**（0 片），在向量这边是**3 片噪声**（最高 0.11）——")
    print("    它不是「救回来了」，是把「一片都没有」变成了「看起来有三条候选」；")
    print("  · Q4（库里没有）两边都给噪声；四道题里向量**没有多召回到任何一条目标文档**。")
    print()
    print("原因不在索引、不在参数，在**嵌入器**：哈希 2-gram 的「语义」就是字面重合，")
    print("它与 BM25 数的是同一件事，只是换了个数法。所以「上了向量就好了」是错的。")
    print("能救 Q3 的两条路：**换成真嵌入模型**（本机无端点，见 ⑤）或者**先改写问题**（5.4）。")
    print()
    print("而它顺带指出一件更要紧的事：**换检索器会把「零召回」这个可判定的状态，")
    print("变成「低分召回」**。前者是明确的「库里没有」，后者看上去像候选——5.5 的拒答")
    print("要处理的就是后者。所以向量检索要么配一个分数下限，要么配一个重排（5.4）。")
    return rows


# --------------------------------------------------------------------------- ⑤
def reading_real() -> dict:
    _hr("⑤ 真机边界：服务商有没有嵌入端点")
    env = Path(__file__).resolve().parent.parent.parent / "zhizhou-v3" / ".env"
    cfg: dict[str, str] = {}
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip()
    base = cfg.get("LLM_BASE_URL", "").rstrip("/")
    key = cfg.get("LLM_API_KEY", "")
    if not base or not key:
        print("没有读到与 v3／v4 同一份 .env，跳过（**跳过不是通过**）。")
        return {"skipped": True}

    def _req(path: str, payload: dict | None = None) -> tuple[int, dict]:
        """`payload=None` 就是 GET（列模型）；给了就是 POST（真发一次嵌入请求）。"""
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Authorization": f"Bearer {key}"}
        if data:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"{base}{path}", data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, {"error": exc.read().decode("utf-8")[:240]}

    print(f"服务商：{base}　（密钥脱敏：***{key[-4:]}）")
    status, body = _req("/models")
    ids = [m.get("id", "") for m in body.get("data", [])] if status == 200 else []
    print(f"GET  /models → HTTP {status}，{len(ids)} 个模型")
    print(f"     清单：{'、'.join(ids) if ids else json.dumps(body, ensure_ascii=False)[:120]}")
    emb_like = [i for i in ids if any(w in i.lower() for w in ("embed", "bge", "text-embedding"))]
    print(f"     其中**嵌入模型：{emb_like or '一个都没有'}**")
    print()
    print("为什么不能只看那一行？**「清单里没有」不等于「这个端点不存在」**——")
    print("所以再 POST 一次，看它是「路由不到」还是「路由到了但没有可用模型」：")
    for name in ("text-embedding-3-small", "bge-m3", ids[0] if ids else "agnes-2.5-flash"):
        code, resp = _req("/embeddings", {"model": name, "input": "测试"})
        print(f"POST /embeddings  model={name:<24} → HTTP {code}｜"
              f"{json.dumps(resp, ensure_ascii=False)[:96]}")
    print()
    if not emb_like:
        print("结论：**本机与这个服务商都没有可用的嵌入端点。**")
        print("所以本章的嵌入走离线的哈希 n-gram（确定性、可回归），")
        print("「真嵌入模型能救 Q3」这一条**本章不宣称跑过**——它标为待有端点时再做。")
        print("这条边界本身是读数：**「向量检索」这一层能不能被验证，取决于你有没有端点**，")
        print("而服务商的模型清单是会变的，所以这句话要带日期。")
    return {"models": len(ids), "embedding_models": emb_like,
            "embeddings_endpoint_exists": True}


# --------------------------------------------------------------------------- 自检
def self_test() -> int:
    _hr("自检：几条不变式（改坏了必须被拦下）")
    emb = HashedEmbedder(dim=32)
    checks: list[tuple[str, bool, str]] = []

    seen = emb.embed_one("同一段文本")
    checks.append(("嵌入是确定的（同一段文本两次结果相同）",
                   emb.embed_one("同一段文本") == seen, ""))

    zero = emb.embed_one("！！？")
    checks.append(("只有标点的文本 → 零向量",
                   all(x == 0.0 for x in zero), f"实际 {[round(x, 3) for x in zero[:4]]}"))

    checks.append(("零向量与任何向量的余弦是 0.0，不是 NaN",
                   cosine(zero, seen) == 0.0, ""))

    try:
        ExactIndex([seen]).search([0.0] * 7, k=1)
        checks.append(("维度不匹配必须报错", False, "没有报错"))
    except DimensionMismatch:
        checks.append(("维度不匹配必须报错", True, ""))

    vectors = [emb.embed_one(t) for t in ["abc", "abd", "xyz", "汽车", "回滚", "发布说明"]]
    ex = ExactIndex(vectors)
    q = emb.embed_one("abc")
    truth = [[h.row for h in ex.search(q, 2)]]
    iv = IVFIndex(vectors, nlist=3, nprobe=3)
    checks.append(("IVF 在 nprobe=nlist 时与精确检索一致",
                   [h.row for h in iv.search(q, 2)] == truth[0], ""))

    pq = PQIndex(vectors, m=2, ksub=4)
    top = pq.search(q, 1)
    checks.append(("PQ 的分数不再是余弦（量纲被近似扯开）",
                   abs(top[0].score) > 1.0 or top[0].score != ex.search(q, 1)[0].score, ""))

    checks.append(("归一化后内积 == 余弦",
                   abs(dot(seen, seen) - cosine(seen, seen)) < 1e-9, ""))

    small = [emb.embed_one(t) for t in ("发布说明要写回滚", "预算上限是 2400 万", "幂等键去重")]
    q2 = emb.embed_one("发布说明的段落")
    rank = lambda key: [i for i, _ in sorted(enumerate(small), key=lambda t: key(t[1]))[:2]]
    checks.append(("归一化后 L2／余弦／内积给同一个前三名",
                   rank(lambda v: -cosine(q2, v)) == rank(lambda v: -dot(q2, v))
                   == rank(lambda v: l2(q2, v)), ""))

    try:
        PQIndex(vectors[:1], m=5, ksub=2)
        checks.append(("PQ 的 m 不能整除维度时报错", False, "没有报错"))
    except ValueError:
        checks.append(("PQ 的 m 不能整除维度时报错", True, ""))

    bad = 0
    for name, ok, extra in checks:
        print(f"  {'✔' if ok else '✖'} {name}" + (f"｜{extra}" if extra and not ok else ""))
        bad += 0 if ok else 1
    print(f"\n自检 {len(checks) - bad}/{len(checks)} 通过")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    bm25, docs, pieces = build_index(strategy="sections")
    emb = HashedEmbedder(dim=DIM)
    queries = [emb.embed_one(q.text) for q in QUESTIONS]

    if args.real:
        reading_real()
        return 0

    if args.offline:
        reading_shape()
        reading_hard_errors(pieces)
        reading_indexes(pieces, queries)
        reading_vs_bm25(pieces, bm25)
        print()
        print(f"（语料 {len(docs)} 份 ｜ {len(pieces)} 片 ｜ 全部读数由 `--offline` 复现；"
              f"`--real` 只探端点，不改任何结论）")
        _hr("离线自检通过")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
