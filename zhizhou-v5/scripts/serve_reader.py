#!/usr/bin/env python
"""5.7 的读数：**在线侧的六组账，外加一遍夹具自检。**

    python scripts/serve_reader.py --offline      # 六组，不需要密钥，进提交门
    python scripts/serve_reader.py --self-test    # 夹具自检（三条坏形态必须都被抓出来）

六组离线读数是：

① **三层缓存**：拿 5.6 那 24 条评测集，冷跑一遍、热跑两遍，报每层的命中／未命中／
   命中率，以及「省下的笔数」——**细到嵌入／检索／模型调用各几笔**；
② **版本戳矩阵**：改提示／改语料／改索引／换模型，各清掉几层几条；
   并给出两处反例（**只改正文不改标签**的旧写法，与**内容哈希**的写法）；
③ **并发**：单飞开关的对照（8 个并发同一问题，嵌入与检索各算几次），
   以及异步下的阻塞点（同一批同步函数，「直接 await」与「丢进线程」的墙钟）；
④ **流式**：一条回答的事件序列是否满足三条不变量；断线续传补几帧、拼接后是否逐字相等；
   三条坏形态各自被哪一条规则抓到；
⑤ **成本与容量**：一次提问的四笔账（冷跑／热跑），以及四个容量数字；
⑥ **门的对照**：把同 24 条走一遍**组装后的服务**，与 5.6 的读数逐项比——
   片级命中、答案命中、拒答四格，**必须相同**（不同的那一栏要能解释）。

> ⚠️ 全部读数在本机跑，**不带任何「业界通用百分比」**：素材第 9 章那张调优清单里的
> 「缓存命中率 ＋20–40%」「延迟 −90%」一条都没有引——它连测试语料都没说。
> 本章报的数，每一个都能用这里的命令复算。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cache import LayeredCache, Versions, cache_key                   # noqa: E402
from app.cost import QueryCost, capacity                                  # noqa: E402
from app.critic import evaluate                                        # noqa: E402
from app.generate import must_refuse                                   # noqa: E402
from app.metrics import (MIN_DETECTABLE, hit, load_cases, rank_of,        # noqa: E402
                         span_cite)
from app.observe import JsonLog, Registry                                 # noqa: E402
from app.rag import check_citations                                   # noqa: E402
from app.retrieve import build_retriever                                  # noqa: E402
from app.scripted import ScriptedModel                                 # noqa: E402
from app.serve import RetryPolicy, Service                                # noqa: E402
from app.stream import (StreamWriter, check, encode, parse, publish,      # noqa: E402
                        sse_frame)

CASES = ROOT / "tests" / "rag" / "eval_cases.jsonl"
K = 3


def _hr(title: str) -> None:
    print("=" * 74)
    print(title)
    print("=" * 74)


def _fresh(**kw) -> tuple[Service, ScriptedModel]:
    model = ScriptedModel(max_chunks=K)
    service = Service(build_retriever(), model, k=K, sleep=lambda _s: None, **kw)
    return service, model


# ---------------------------------------------------------------- ① 三层缓存
def read_cache() -> dict:
    cases = list(load_cases(CASES))
    service, model = _fresh(registry=Registry(), log=JsonLog())

    def one_pass(*, use_cache: bool) -> tuple[QueryCost, int]:
        total = QueryCost()
        models = 0
        for case in cases:
            reply = service.handle(case.text, use_cache=use_cache)
            total.model_calls += reply.cost.model_calls
            total.retrieve_calls += reply.cost.retrieve_calls
            total.embed_calls += reply.cost.embed_calls
            models += reply.cost.model_calls
        return total, models

    # 三遍的含义必须写清，否则读数会自相矛盾：
    #   ① 关缓存：一笔都不存，所以它量的是「完全不缓存」的代价；
    #   ② 开缓存的第一遍：**填缓存**（这一遍每层的第一次查询都是未命中）；
    #   ③ 开缓存的第二遍：**真热跑**（三层全命中）——省下的账用①与③相减。
    # 第一版只跑了 ②，于是「热跑」里满是未命中，差一点把结论写成「缓存没用」。
    _hr("① 三层缓存：24 条评测集（冷跑一遍 ＋ 开缓存跑两遍：第一遍填、第二遍热）")
    cold_cost, cold_models = one_pass(use_cache=False)
    fill_cost, _ = one_pass(use_cache=True)
    warm_cost, _ = one_pass(use_cache=True)
    stats = service.cache.stats()
    print(f"{'层':<10}{'命中':>6}{'未命中':>8}{'过期':>6}{'命中率':>9}   说明")
    notes = {"embedding": "只有「问题 → 向量」这一笔进请求路径",
             "retrieval": "融合后的候选（片段 ＋ 改写后的 query）",
             "answer": "整段答复（含质量档与降级标记）"}
    for layer in ("embedding", "retrieval", "answer"):
        s = stats[layer]
        print(f"{layer:<10}{s['hits']:>6}{s['misses']:>8}{s['expired']:>6}"
              f"{s['hit_rate']:>9.4f}   {notes[layer]}")
    diff = QueryCost.from_runs(cold_cost, warm_cost)
    print(f"\n① 冷跑（关缓存）    ：模型调用 {cold_cost.model_calls} ｜ 嵌入 {cold_cost.embed_calls}"
          f" ｜ 检索 {cold_cost.retrieve_calls}")
    print(f"② 开缓存的第一遍    ：模型调用 {fill_cost.model_calls} ｜ 嵌入 {fill_cost.embed_calls}"
          f" ｜ 检索 {fill_cost.retrieve_calls}（这一遍在填缓存）")
    print(f"③ 热跑（同一批再来）：模型调用 {warm_cost.model_calls} ｜ 嵌入 {warm_cost.embed_calls}"
          f" ｜ 检索 {warm_cost.retrieve_calls}")
    print(f"→ 缓存省下（①与③ 之差）：{diff.saved}")
    assert warm_cost.model_calls == 0 and warm_cost.embed_calls == 0, "热跑不该再算任何一笔"
    assert cold_models > 0, "冷跑必须真的调过模型，否则这一组读数是空的"
    assert fill_cost.model_calls == cold_cost.model_calls, "填缓存那一遍与冷跑一样费"
    print(f"\n可检测最小差异仍是 1/{len(cases)} ＝ {MIN_DETECTABLE * len(cases):.4f}"
          f"（{MIN_DETECTABLE:.4f}）——命中率的变化小于它就不该被报成「提升」")
    return {"stats": stats, "diff": diff.saved, "cases": len(cases)}


# ---------------------------------------------------------------- ② 版本戳
def read_versions() -> dict:
    _hr("② 版本戳矩阵：改一处要作废哪几层")
    base = Versions.from_content(prompt="提示甲", corpus="语料甲", index="dim=256",
                                 model="hashed-embedder-v1")
    changes = {
        "换提示正文": Versions.from_content(prompt="提示乙", corpus="语料甲", index="dim=256",
                                            model="hashed-embedder-v1"),
        "换语料": Versions.from_content(prompt="提示甲", corpus="语料乙", index="dim=256",
                                        model="hashed-embedder-v1"),
        "换索引参数": Versions.from_content(prompt="提示甲", corpus="语料甲", index="dim=512",
                                            model="hashed-embedder-v1"),
        "换嵌入模型": Versions.from_content(prompt="提示甲", corpus="语料甲", index="dim=256",
                                            model="bge-large-zh-v1.5"),
    }
    print(f"{'改动':<12}{'嵌入':>6}{'检索':>6}{'答案':>6}   说明")
    why = {"换提示正文": "只有答案层的值依赖提示",
           "换语料": "片换了，检索与答案都得重算；**嵌入是「文字→向量」，与语料清单无关**",
           "换索引参数": "索引换了，同一句话召回的就不同",
           "换嵌入模型": "向量换了，前面所有缓存都失去意义"}
    out = {}
    for name, new in changes.items():
        cache = LayeredCache(base)
        for layer in ("embedding", "retrieval", "answer"):
            cache.tiers[layer].set(f"{layer}:x", 1, ttl=60)
        cleared = cache.set_versions(new)
        out[name] = cleared
        print(f"{name:<12}{cleared['embedding']:>6}{cleared['retrieval']:>6}"
              f"{cleared['answer']:>6}   {why[name]}")
    # 反例：只改正文不改标签（真事故）
    label_only = Versions(prompt="v3")
    same = cache_key("answer", {"q": "问题"}, label_only) == \
        cache_key("answer", {"q": "问题"}, Versions(prompt="v3"))
    by_content = cache_key("answer", {"q": "问题"}, base) != \
        cache_key("answer", {"q": "问题"}, changes["换提示正文"])
    print(f"\n只改正文不改标签 → 键一样吗？**{'一样（旧答案被复用）' if same else '不一样'}**")
    print(f"用内容算戳        → 键一样吗？**{'一样（失效了）' if not by_content else '不一样（正确失效）'}**")
    assert same is True, "标签式版本控制的那个洞必须被读出来"
    assert by_content is True, "内容哈希必须真的改键"
    return out


# ---------------------------------------------------------------- ③ 并发
def read_concurrency() -> dict:
    _hr("③ 并发：单飞对照 ＋ 异步下的阻塞点")
    # 单飞对照：8 个线程同时问同一个**冷**问题。
    #
    # 两组都数「嵌入真算了几次」，而两组走的**不是同一条路**：
    #   对照组：不走缓存，8 个线程各自跑一遍检索（每次都嵌入）；
    #   本树组：走缓存 ＋ 单飞，先到的算一次，后面的拿它算好的。
    # 两组的问题与语料完全相同，**只差「有没有并发去重」这一个变量**。
    def hammer(label: str, *, cache: bool) -> int:
        service, _ = _fresh() if cache else (None, None)
        counts = {"embed": 0}
        question = "知舟的发布说明必须包含哪几段？"

        if cache:
            raw = service._raw_embedder

            def counted(texts, raw=raw):
                counts["embed"] += 1
                time.sleep(0.02)          # 把窗口拉开：不然单飞没机会重合
                return raw(texts)

            service._raw_embedder = counted

            def one() -> None:
                service.handle(question)
        else:
            retriever = build_retriever()
            plain = retriever.embedder

            def counted(texts, raw=plain):
                counts["embed"] += 1
                time.sleep(0.02)
                return raw(texts)

            retriever.embedder = counted

            def one() -> None:
                retriever.search(question, k=K)

        barrier = threading.Barrier(8)
        threads = [threading.Thread(target=lambda: (barrier.wait(), one()))
                   for _ in range(8)]
        [t.start() for t in threads]
        [t.join(30.0) for t in threads]
        print(f"  {label}：嵌入实际算了 {counts['embed']} 次")
        return counts["embed"]

    without = hammer("没有单飞（对照组）", cache=False)
    with_flight = hammer("有单飞（本树）", cache=True)
    assert without == 8, without
    assert with_flight == 1, (
        f"有单飞时应当只算 1 次，实测 {with_flight} 次——"
        "8 个线程里可能有几个先撞上「还没有值」再排队，那是另一档（见 test_cache）")

    # 异步下的阻塞点：同一批同步函数，直接 await 与丢进线程
    def blocking(seconds: float = 0.05) -> float:
        time.sleep(seconds)
        return seconds

    async def serial(n: int) -> float:
        t0 = time.perf_counter()
        for _ in range(n):
            blocking()                      # **同步调用**：事件循环被它摁住
        return time.perf_counter() - t0

    async def threaded(n: int) -> float:
        t0 = time.perf_counter()
        await asyncio.gather(*(asyncio.to_thread(blocking) for _ in range(n)))
        return time.perf_counter() - t0

    n = 8
    t_serial = asyncio.run(serial(n))
    t_thread = asyncio.run(threaded(n))
    print(f"\n{n} 个同步任务（各 50ms）：")
    print(f"  直接 await（阻塞事件循环）：{t_serial * 1000:8.1f} ms")
    print(f"  丢进线程（to_thread）      ：{t_thread * 1000:8.1f} ms"
          f"（快 {t_serial / t_thread:.2f} 倍）")
    print("  （这是**结构量**：用 CPU 睡眠制造的等待，不是真实网络延迟；"
          "要看的比值与重叠数，不是毫秒）")
    assert t_thread < t_serial * 0.5, "并发必须真的重叠起来"

    # 默认线程池的上限（官方文档给的是 min(32, CPU+4)）
    import concurrent.futures
    import os
    pool = concurrent.futures.ThreadPoolExecutor()
    print(f"\n默认线程池上限：min(32, CPU+4) ＝ {min(32, os.cpu_count() + 4)}"
          f"（本机 CPU {os.cpu_count()}；实测 max_workers ＝ {pool._max_workers}）")
    print("→ 丢进线程不是「无限并发」：**超过这个数的请求会排队**，"
          "而它的失败模式不是报错，是变慢。")
    pool.shutdown()
    return {"without": without, "with": with_flight,
            "serial_ms": round(t_serial * 1000, 1), "thread_ms": round(t_thread * 1000, 1)}


# ---------------------------------------------------------------- ④ 流式
def read_stream() -> dict:
    _hr("④ 流式：一条回答的序列、断线续传与三条坏形态")
    service, _ = _fresh()
    reply = service.handle("知舟的发布说明必须包含哪几段？")
    segments = [s for s in reply.text.split("。") if s.strip()]
    writer = StreamWriter()
    text = publish(writer, sources=[c.cite() for c in reply.chunks], segments=segments,
                   beats=2)
    issues = check(text)
    print(f"发布：来源 {len(reply.chunks)} 片 ｜ 正文 {len(segments)} 段 ｜ "
          f"心跳若干 ｜ 事件帧 {writer.sent} 个")
    print(f"三条不变量（编号严格递增 / 以 done 结尾 / 心跳不带编号）："
          f"{'全部通过' if not issues else '有 ' + str(len(issues)) + ' 条不满足'}")
    assert not issues, issues

    # 断线续传：客户端在收到前 2 帧之后断线（它手上是 open ＋ 那两帧）
    received = writer.open() + "".join(encode(f) for f in writer.log.frames[:2])
    last_id = parse(received)[-1].id
    tail = "".join(writer.resume(last_id))
    whole = received + tail
    tokens_before = [f.data for f in parse(received) if f.event == "token"]
    tokens_after = [f.data for f in parse(whole) if f.event == "token"]
    print(f"\n断在第 {last_id} 帧：补发 {len(parse(tail))} 帧；"
          f"拼接后正文段数 {len(tokens_after)}（应等于 {len(segments)}）")
    print(f"不重不漏：{tokens_after == [json.dumps({'content': s}, ensure_ascii=False) for s in segments]}"
          f" ｜ 补发前已有 {len(tokens_before)} 段")
    assert check(whole) == ()
    assert len(tokens_after) == len(segments)
    assert tokens_before == tokens_after[:len(tokens_before)], "补发不许改动已收内容"

    # 三条坏形态
    bad = {
        "乱序（编号倒退）": sse_frame("sources", [], id=1) + sse_frame("token", {"c": "甲"}, id=3)
        + sse_frame("token", {"c": "乙"}, id=2) + sse_frame("done", {}, id=4),
        "重复（同一编号两次）": sse_frame("sources", [], id=1) + sse_frame("token", {"c": "甲"}, id=2)
        + sse_frame("token", {"c": "甲"}, id=2) + sse_frame("done", {}, id=3),
        "缺 done": sse_frame("sources", [], id=1) + sse_frame("token", {"c": "甲"}, id=2),
    }
    print()
    for name, stream_text in bad.items():
        got = check(stream_text)
        print(f"  {name:<18}→ {'；'.join(got) if got else '没抓到（错）'}")
        assert got, f"{name} 必须被 check 抓到"
    return {"frames": writer.sent, "segments": len(segments)}


# ---------------------------------------------------------------- ⑤ 成本与容量
def read_cost() -> dict:
    _hr("⑤ 成本与容量：一次提问的四笔账")
    service, _ = _fresh()
    q = "知舟的发布说明必须包含哪几段？"
    cold = service.handle(q)        # 缓存是空的 → 这一次就是冷的那一次
    warm = service.handle(q)        # 同一句话再问一次 → 命中答复缓存
    print("冷跑（首次提问）：")
    for k, v in cold.cost.as_dict().items():
        print(f"    {k}：{v}")
    print("热跑（同一句再问一次）：")
    for k, v in warm.cost.as_dict().items():
        print(f"    {k}：{v}")
    print(f"\n省下：{QueryCost.from_runs(cold.cost, warm.cost).saved}")
    cap = capacity(dau=10_000, per_user=20, docs=50_000, chunks_per_doc=20, dim=1024)
    print(f"\n容量（DAU 1 万、人均 20 次、5 万文档 × 20 片 × 1024 维）：")
    for k, v in cap.as_dict().items():
        print(f"    {k}：{v}")
    print("    （单价与折扣**不在这里**：单价随时会变，乘一下就是钱，"
          "但写进正文的「每次多少钱」三个月后就是错的）")
    assert cold.cost.model_calls == 1 and warm.cost.model_calls == 0
    return {"cold": cold.cost.as_dict(), "capacity": cap.as_dict()}


# ---------------------------------------------------------------- ⑥ 门
def read_gate() -> dict:
    """与 5.6 的对照。**关键在口径**：两边必须逐条比同一件事。

    5.6 的读数是直接调检索器算的（不进服务、不算控制位）；本章的服务会先按
    5.5 的四个控制位决定「这条题目到底要不要检索」。于是同一批 24 条里，
    只有一部分真的走检索——硬把两边的总分放一起比，比的是**两份不同的分母**，
    那正是 5.6 自己骂过的那种算法。所以这一组做两件事：

    1. **逐条对照**：对「真的检索了」的题，把服务的候选与直接调检索器的候选
       一条一条比——它们必须完全相同（缓存不该换掉候选）；
    2. **同一分母上比读数**：片级命中与服务路径、直接路径各算一份，
       分母是同一批题；而 5.6 的总分（24 条）只作参考列出，并注明分母不同。
    """
    _hr("⑥ 门的对照：组装之后读数变了吗（与 5.6 逐条比）")
    cases = list(load_cases(CASES))
    service, _ = _fresh(judge_depth=K)   # 默认 control="always"；判档跟 k 走（与 5.6 同口径）
    direct = build_retriever()
    same = 0
    compared = 0
    doc_svc: list[int] = []
    doc_direct: list[int] = []
    span_svc: list[int] = []
    span_direct: list[int] = []
    span_miss: list[str] = []
    skipped: list[str] = []
    matched = 0
    needs = 0
    # 四格的口径（写成两个名字就不容易搞反了）：
    #   `missed` 漏拒 ＝ 该拒没拒（质量事故）；`over` 误拒 ＝ 不该拒却拒（可用性事故）。
    missed = over = 0
    missed_ids: list[str] = []
    over_ids: list[str] = []
    cites_bad = 0
    degraded = 0
    delivered = 0
    for case in cases:
        reply = service.handle(case.text)
        cites_svc = service.cached_cites(case.text)
        if cites_svc is None:
            skipped.append(case.case)          # 控制位判「不需要检索」
        else:
            hits_direct, _q, _s = direct.search_with_rewrite(case.text, k=K)
            cites_direct = tuple(h.chunk.cite() for h in hits_direct)
            compared += 1
            same += 1 if cites_svc == cites_direct else 0
            if case.needs_recall:
                # 两个判据都要报（5.6 就是靠它们的差别才发现「文档级是钧读数」的）：
                #   文档级：目标文档的**任意一片**进了前三就算中；
                #   片级：**装着那段话的那一片**进了前三才算中（严得多）。
                holder = span_cite(direct.chunks, case.want)
                doc_svc.append(rank_of(cites_svc, case.want_doc))
                doc_direct.append(rank_of(cites_direct, case.want_doc))
                span_svc.append(cites_svc.index(holder) + 1 if holder in cites_svc else 0)
                span_direct.append(cites_direct.index(holder) + 1 if holder in cites_direct
                                   else 0)
                if not span_svc[-1]:
                    span_miss.append(case.case)
        if case.needs_recall:
            needs += 1
            matched += 1 if case.want in reply.text else 0
        if case.expect_retrieve:
            if reply.refused and not case.expect_refuse:
                over += 1
                over_ids.append(case.case)
            if not reply.refused and case.expect_refuse:
                missed += 1
                missed_ids.append(case.case)
        if reply.chunks and not reply.citations_ok:
            cites_bad += 1
        if reply.degraded:
            degraded += 1
        # 发出去的那一份必须干净：同一批答复，**自称**可以不符（上面那 19 条），
        # 但**绑定后的正文**再查一遍必须一条问题都没有。
        # 少了这条断言，「绑定层已经改对了」在正文里就只是一句话。
        if reply.chunks and not reply.refused:
            delivered += 1
            assert not check_citations(reply.text, reply.chunks), \
                f"{case.case}：对外答复的引用没通过核对"

    def rate(ranks: list[int]) -> float:
        return round(sum(1 for r in ranks if hit(r, K)) / len(ranks), 4) if ranks else 0.0

    answer_rate = round(matched / needs, 4) if needs else 0.0
    print(f"24 条里真的走了检索的：{compared} 条（其余 {len(skipped)} 条由控制位判为不需检索"
          f"：{', '.join(skipped)}）")
    print(f"两条路径的候选逐条相同：{same}/{compared}"
          f"{'（缓存没有换掉候选）' if same == compared else '（**有差异**）'}")
    print(f"\n同一分母（{len(doc_svc)} 条需要召回的题）上的命中率：")
    print(f"  文档级（任意一片）：服务 {rate(doc_svc):.4f} ｜ 直接调 {rate(doc_direct):.4f}")
    print(f"  片级（那一片）    ：服务 {rate(span_svc):.4f} ｜ 直接调 {rate(span_direct):.4f}"
          f"（未命中：{', '.join(span_miss) or '无'}）")
    print(f"\n答案命中：{answer_rate:.4f}（{matched}/{needs}，分母是全部要求召回的题）")
    print(f"拒答四格（漏拒／误拒）：{missed}／{over}"
          f"（{'、'.join(missed_ids + over_ids) or '无'}）")
    # 这一行的名字改过一次，值得记：「引用未通过绑定核对」会被读成「发出去的答复引用不合格」，
    # 而它数的是**替身自己标的编号与代码算出的依据不符**（5.5 的 `claimed` 那一路）。
    # 对外答复用的是绑定后的正文：重查一遍 `check_citations`，19 条全部通过。
    # 所以真正的读数是「自证的路有多不可靠」，而不是「这一章的引用质量 19/24」。
    print(f"引用自称与绑定不符：{cites_bad} 条（对外答复已按绑定改写）｜降级过的请求：{degraded} 条")
    print(f"对外答复（绑定后）再查一遍：{delivered} 条，引用全部通过")
    print("\n5.6 的基线（24 条全算）：文档级 1.0000 ｜ 片级 0.8333 ｜"
          "答案命中 0.9444 ｜ 漏拒 1／误拒 0")
    assert same == compared, "服务的候选必须与直接检索逐条相同"
    assert rate(doc_svc) == rate(doc_direct) == 1.0, rate(doc_svc)
    assert rate(span_svc) == rate(span_direct) == 0.8333, rate(span_svc)
    assert answer_rate == 0.9444, f"答案命中应当与 5.6 相同，实测 {answer_rate}"
    assert compared == len(cases), "默认总是检索，所以 24 条都该走检索"
    # 5.6 那一格是怎么算出来的：**它判的是原问法**，而服务判的是改写后的问法。
    # 两边的错误**总数相同**、方向正好相反——这是一个只有把两条路都跑一遍
    # 才看得见的差别，也直接决定「接下来该修哪一端」。
    ref_missed = ref_over = 0
    ref_ids: list[str] = []
    for case in cases:
        if not case.expect_retrieve:
            continue
        hits = tuple(h.chunk for h in direct.search(case.text, k=K, mode="bm25"))
        _h, _s, q = evaluate(direct, case.text, depth=K)
        flag = must_refuse(hits, q.value) is not None
        if flag and not case.expect_refuse:
            ref_over += 1
            ref_ids.append(case.case)
        if not flag and case.expect_refuse:
            ref_missed += 1
            ref_ids.append(case.case)
    print(f"5.6 原路径（判原问法）：漏拒 {ref_missed}／误拒 {ref_over}"
          f"（{'、'.join(ref_ids) or '无'}）")
    print("  → 两边逐项相同：把判档挪到**改写后的问法**上，四格一格都没动。")
    print("    这与 5.6 那条「先改写再判一次都没触发」是同一件事的第二次出现：")
    print("    **本案的置信度是两极的**（要么高到过上限、要么低到在下阈值之下），")
    print("    所以「换个同义问法就能救回来」的假设在本语料上找不到落脚点。")
    assert (missed, over) == (1, 0), (missed, over)
    assert (ref_missed, ref_over) == (1, 0), (ref_missed, ref_over)

    # ---- 判档取几条候选：同一个词、两个值，四格会翻 ----
    print("\n判档时多看两片会怎样（`judge_depth` 5 对 3）：")
    depth_rows: dict[int, tuple[int, int]] = {}
    for jd in (K, 5):
        svc, _ = _fresh(judge_depth=jd)
        m = o = 0
        for case in cases:
            reply = svc.handle(case.text)
            if not case.expect_retrieve:
                continue
            if reply.refused and not case.expect_refuse:
                o += 1
            if not reply.refused and case.expect_refuse:
                m += 1
        depth_rows[jd] = (m, o)
        print(f"  judge_depth={jd} → 漏拒 {m}／误拒 {o}")
    print("  → **不动读数**（与 5.6 的两组「改一个数、什么都不变」同一现象：")
    print("    这批题的置信度是两极的，中间那一档几乎没有落脚点）。")
    print("    但「不动的参数」也要写进配置（本树默认跟 k 走）：")
    print("    它不动，是因为这批题；换一批题它就会动，而到那时没人记得它默认是几。")
    assert depth_rows[K] == depth_rows[5] == (1, 0), depth_rows

    # ---- 另一半：把 5.5 那个实验开关接到默认路径上会怎样 ----
    print("\n把 5.5 的「按需检索」接成默认值会怎样（`control=\"offline\"`）：")
    offline_service, _ = _fresh(control="offline")
    off_ranks: list[int] = []
    off_matched = 0
    off_fn = off_fp = 0
    off_retrieved = 0
    for case in cases:
        reply = offline_service.handle(case.text)
        cites = offline_service.cached_cites(case.text)
        if cites is not None:
            off_retrieved += 1
            if case.needs_recall:
                off_ranks.append(rank_of(cites, case.want_doc))
        if case.needs_recall:
            off_matched += 1 if case.want in reply.text else 0
        if case.expect_retrieve and reply.refused and not case.expect_refuse:
            off_fn += 1
        if case.expect_retrieve and not reply.refused and case.expect_refuse:
            off_fp += 1
    off_rate = round(off_matched / needs, 4) if needs else 0.0
    print(f"  真的走了检索：{off_retrieved}/{len(cases)} 条")
    print(f"  答案命中：{off_rate:.4f}（{off_matched}/{needs}）—— 对照总是检索的 {answer_rate:.4f}")
    print(f"  拒答四格（漏拒／误拒）：{off_fn}／{off_fp}")
    print("  → 省下的调用是真的，丢掉的质量也是真的：**这一对数字必须一起看**。")
    assert off_rate < answer_rate, "按需检索不应该比总是检索更好，否则这一组读数得重写"
    return {"doc": rate(doc_svc), "span": rate(span_svc), "answer": answer_rate,
            "compared": compared, "refused": (missed, over), "citations_bad": cites_bad,
            "skipped": len(skipped), "offline_answer": off_rate,
            "offline_retrieved": off_retrieved}


# ---------------------------------------------------------------- 夹具自检
def self_test() -> int:
    """三处最容易被写错的不变量，每一处都配一条能报错的夹具。

    **条数要打印出来**（`夹具自检：3/3 通过`），理由与 3.9／5.6 那两次同一条：
    一个把夹具删光的脚本会安静地通过——只判「全过」是判不出这件事的。
    初版这句写的是「三条坏形态 ＋ 两处账会被记错」，列了五项却只跑了三项，
    正文引的是句子而不是输出，于是两边的数字悄悄对不上。
    """
    _hr("夹具自检：三处最关键的不变量")
    bad = 0
    total = 3
    # 1) 流：三条坏形态
    from app.stream import StreamLog
    log = StreamLog(max_items=1)
    writer = StreamWriter(log=log)
    writer.open()
    writer.event("token", {"content": "甲"})
    writer.event("token", {"content": "乙"})
    window_ok = log.replay(0) == () or len(log.replay(0)) == 1
    print(f"  窗口上限生效（只留 1 帧）：{'✔' if window_ok else '✖'} "
          f"→ replay(0) 给出 {len(log.replay(0))} 帧")
    bad += 0 if window_ok else 1
    # 2) 缓存：没有复查的单飞等于没省
    assert callable(LayeredCache.__init__)
    clock = {"t": 0.0}
    tier_cache = LayeredCache(Versions(), clock=lambda: clock["t"])
    looks = tier_cache.tiers["answer"]
    looks.set("answer:x", 1, ttl=10)
    clock["t"] = 11.0
    got = tier_cache.tiers["answer"].get("answer:x")
    expired_counted = got is None and tier_cache.tiers["answer"].stats.expired == 1
    print(f"  TTL 过期记在 expired 而不是 misses：{'✔' if expired_counted else '✖'}")
    bad += 0 if expired_counted else 1
    # 3) 服务：降级结果不许进缓存
    class Broken:
        def __call__(self, messages):
            raise RuntimeError("上游挂了")

    service = Service(build_retriever(), Broken(), sleep=lambda _s: None,
                      retry=RetryPolicy(attempts=1))
    service.handle("知舟的发布说明必须包含哪几段？")
    no_store = service.cache.tiers["answer"].stats.stores == 0
    print(f"  降级结果不进缓存：{'✔' if no_store else '✖'}"
          f"（stores ＝ {service.cache.tiers['answer'].stats.stores}）")
    bad += 0 if no_store else 1
    print(f"\n夹具自检：{total - bad}/{total}" + (" 通过" if not bad else f"（{bad} 项不通过）"))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="5.7 在线侧读数")
    ap.add_argument("--offline", action="store_true", help="六组离线读数（进提交门）")
    ap.add_argument("--self-test", action="store_true", help="夹具自检")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    read_cache()
    print()
    read_versions()
    print()
    read_concurrency()
    print()
    read_stream()
    print()
    read_cost()
    print()
    gate = read_gate()
    print()
    _hr("一次请求的读数摘要（供正文引用）")
    print(f"{_summary_line(gate)}")
    print()
    _hr("离线自检通过")
    return 0


def _summary_line(gate: dict) -> str:
    return (f"本次评测：{gate['compared']} 条走了检索｜文档级 {gate['doc']:.4f}｜"
            f"片级 {gate['span']:.4f}｜答案命中 {gate['answer']:.4f}｜"
            f"漏拒 {gate['refused'][0]}／误拒 {gate['refused'][1]}｜"
            f"引用自称与绑定不符 {gate['citations_bad']} 条｜"
            f"按需检索（对照）答案命中 {gate['offline_answer']:.4f}")


if __name__ == "__main__":
    raise SystemExit(main())
