"""成本与容量：**一次提问到底花在哪里**，以及「按这个量算要多少机器」。

## 先定口径：这一章报的是「笔数」，不是钱

前六章里我们已经数过汉字（`lint` 的有效字口径）、数过词元（3.1 的词元账）、
数过调用次数（5.4／5.5 的「模型调用 24」）。这一章加一层：把一次提问拆成
**四笔可见的支出**——

    嵌入（把问题变成向量）｜检索（两条路 ＋ 重排）｜提示（送进去的上下文）｜生成（吐出来的字）

不折算成货币。理由是 5.6 那条纪律的搬家：**货币单价随时会变，而且带阶梯与缓存折扣**
（各家对「缓存命中的输入词元」与「新输入词元」不是一个价），一个写死在正文里的
「每次 0.003 元」三个月后就是错的。所以本章只报「笔数」与「字数」，
读者拿自己那份价目表去乘即可。素材第 9 章给的分阶段月成本表（¥500 起）
**一条都没引**：它连测试语料规模与单价都没说，乘不出来。

## 缓存省下的那一笔必须能指认

「缓存让延迟降了 90%」这种话没有信息量。有信息量的是：
**这次命中省掉的是一次嵌入、一次检索、还是一次模型调用**——三者的量级完全不同
（本树实测：一次检索 0.3 毫秒，一次模型调用 1.7 秒）。

所以 `QueryCost` 不只记「命中了」，还记**命中把哪一笔划掉了**。
`from_runs()` 拿两次真实的读数相减（一次关缓存、一次开缓存），
差额就是缓存的价值——**不估、不折算，而是同一条管线跑两遍**。

## 容量：能算的部分与不能算的部分

可以算的（纯算术，与厂商无关）：日查询量 → 峰值 QPS；文档量 × 片数 × 维度 × 4 字节 → 向量存储；
再乘索引膨胀系数（HNSW 约 1.3）→ 内存；日查询量 × 日志大小 × 保留天数 → 日志盘。
不可以算的：单价、折扣、运维人力。**把这两类分开写**，读者才不会把
「算出来的 5.3GB」当成「买一台 8G 机器就够了」（还有模型权重、操作系统与峰值余量）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["Capacity", "QueryCost", "capacity", "hanzi", "hanzi_ratio"]

_HANZI = re.compile(r"[\u4e00-\u9fff]")


def hanzi(text: str) -> int:
    """汉字数。**与 `tools/lint_book.py` 同一口径**——正文里的「汉字」只有一种数法。

    不以「词」或「词元」计数：本机的离线替身不经过任何分词器，
    报「词元」就得先发明一个换算比例，而那个比例是猜的。
    真机那边的词元数由服务商返回，属于读数，不属于账（见 5.5 的「花销账」）。
    """
    return len(_HANZI.findall(text))


def hanzi_ratio(*, with_context: str, without_context: str) -> float:
    """上下文把输入放大了几倍。**这是本章最便宜也最有用的一个数。**"""
    base = hanzi(without_context) or 1
    return round(hanzi(with_context) / base, 3)


@dataclass
class QueryCost:
    """一次提问的账。字段都是**计数**，没有一个是换算出来的钱。"""

    embed_calls: int = 0        # 问题变向量；命中嵌入缓存则为 0
    retrieve_calls: int = 0     # 两条路 ＋ 融合（一次算一笔）
    rerank_pairs: int = 0       # 成对打分次数（重排的花销与它成正比）
    model_calls: int = 0        # 真实模型调用（改写、判档、生成都算）
    prompt_hanzi: int = 0       # 送进提示的汉字
    output_hanzi: int = 0       # 吐出来的汉字
    cache_hits: tuple[str, ...] = ()   # 命中的层，按发生顺序
    saved: dict = field(default_factory=dict)   # 命中省掉的笔数

    def as_dict(self) -> dict:
        return {"嵌入": self.embed_calls, "检索": self.retrieve_calls,
                "重排对数": self.rerank_pairs, "模型调用": self.model_calls,
                "提示汉字": self.prompt_hanzi, "输出汉字": self.output_hanzi,
                "命中层": list(self.cache_hits), "省下": dict(self.saved)}

    @classmethod
    def from_runs(cls, cold: "QueryCost", warm: "QueryCost") -> "QueryCost":
        """两次跑（关缓存／开缓存）相减 → 缓存的价值。**差额即为省下的笔数。**"""
        saved = {}
        for name, hot_field in (("模型调用", "model_calls"), ("嵌入", "embed_calls"),
                                ("检索", "retrieve_calls")):
            diff = getattr(cold, hot_field) - getattr(warm, hot_field)
            if diff:
                saved[name] = diff
        out = QueryCost(**{k: getattr(cold, k) for k in
                           ("embed_calls", "retrieve_calls", "rerank_pairs", "model_calls",
                            "prompt_hanzi", "output_hanzi")})
        out.cache_hits = warm.cache_hits
        out.saved = saved
        return out


@dataclass(frozen=True)
class Capacity:
    """容量账。每一项都带单位；**单位写进字段名**，免得三个「GB」互相顶替。"""

    peak_qps: float
    vector_gb: float
    index_gb: float
    log_gb: float
    bandwidth_kb_s: float

    def as_dict(self) -> dict:
        return {"峰值 QPS": round(self.peak_qps, 2), "向量存储 GB": round(self.vector_gb, 3),
                "索引内存 GB": round(self.index_gb, 3), "日志 GB": round(self.log_gb, 3),
                "带宽 KB/s": round(self.bandwidth_kb_s, 1)}


def capacity(*, dau: int, per_user: int, peak_factor: float = 5.0,
             docs: int = 0, chunks_per_doc: int = 20, dim: int = 1024,
             index_inflation: float = 1.3, log_bytes: int = 2048,
             keep_days: int = 30, response_bytes: int = 50 * 1024) -> Capacity:
    """六个公式的直译（素材第 9 章那张表里的公式本身是可用的）。

    两处值得说明的选择：

    - **向量按 4 字节算**（`float32`）。半精度（`float16`）能砍一半，
      但它会改变相似度排序——那是 5.3 的边界之外，不能悄悄替读者做这个决定；
    - **峰值系数默认 5**。它不是「业界惯例」，是一个**要写进配置并说明理由的参数**：
      企业内部工具的实际峰谷比通常在 3–10 之间，把它写死成 5 而不标出处就是猜。
    """
    daily = dau * per_user
    qps = daily / 86400 * peak_factor
    vector_bytes = docs * chunks_per_doc * dim * 4
    vector_gb = vector_bytes / 1e9
    index_gb = vector_gb * index_inflation
    log_gb = daily * log_bytes * keep_days / 1e9
    bandwidth_kb_s = qps * response_bytes / 1024
    return Capacity(peak_qps=qps, vector_gb=vector_gb, index_gb=index_gb,
                    log_gb=log_gb, bandwidth_kb_s=bandwidth_kb_s)
