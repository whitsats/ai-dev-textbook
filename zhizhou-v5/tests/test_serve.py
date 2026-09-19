# tests/test_serve.py —— 不需要密钥、不需要网络：一次请求的四件事
"""这一份测的是 5.7 的组装层（`app/serve.py`）。十一组断言：

1. **冷热两跑**：热跑命中答案缓存——模型调用 1 → 0，**而正文一字不差**；
2. **省下的是哪一笔**：`QueryCost.from_runs()` 的差额与两跑的成本对得上；
3. **降级**：模型抛异常时有界重试到上限、返回兜底文案、`degraded` 写明原因，
   **且这次结果不进缓存**（恢复之后不能继续吃旧兜底）；
4. **重试也是钱**：`model_calls` 记的是尝试次数而不是成功次数；
5. **时间预算**：退避会把预算耗光时，**不许再睡**（否则一次请求卡到连接都断了）；
6. **限流**：并发上层与排队上限都生效，被拒的请求带 `outcome="rejected"`；
7. **观测**：结构化日志里事件名是 `rag_query_done`；指标名带 `_total`／单位后缀；
   **高基数标签会抛错**（这是 Prometheus 文档那条被写成了代码）；
8. **版本失效**：改提示版本之后答案重建（旧文本不再返回），而**嵌入层仍命中**；
9. **判档不是免费的**：一次请求里 `retrieve_calls` 除了融合那一次，还要算判档的两条原始路；
10. **引用绑定**：绑定之后 `citations_ok` 由代码判定（不是由模型自报）；
11. **性能改动必须过门**：同一批 24 条评测集，开关缓存两跑，
    答案集合**逐条相同**——缓存不许换掉系统的答案。
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cache import LayeredCache, Versions, cache_key                    # noqa: E402
from app.cost import QueryCost, capacity                                   # noqa: E402
from app.metrics import load_cases                                         # noqa: E402
from app.observe import JsonLog, MetricError, Registry, Trace              # noqa: E402
from app.retrieve import build_retriever                                   # noqa: E402
from app.scripted import ScriptedModel                                     # noqa: E402
from app.serve import FALLBACK_TEXT, Limiter, RetryPolicy, Service         # noqa: E402

CASES = ROOT / "tests" / "rag" / "eval_cases.jsonl"
QUESTION = "知舟的发布说明必须包含哪几段？"


def make_service(**kw) -> tuple[Service, ScriptedModel]:
    model = ScriptedModel()
    service = Service(build_retriever(), model, sleep=lambda _s: None, **kw)
    return service, model


def test_冷热两跑命中答案缓存且正文相同() -> None:
    service, model = make_service()
    cold = service.handle(QUESTION)
    warm = service.handle(QUESTION)
    assert not cold.cached and warm.cached
    assert cold.text == warm.text, "缓存不许改一个字"
    assert (cold.cost.model_calls, warm.cost.model_calls) == (1, 0)
    assert model.calls == 1, "热跑一次模型都没调"
    assert warm.cache_hits == ("answer",)
    assert service.cache.stats()["answer"]["hit_rate"] == 0.5


def test_省下的是哪一笔() -> None:
    service, _ = make_service()
    cold = service.handle(QUESTION)
    warm = service.handle(QUESTION)
    diff = QueryCost.from_runs(cold.cost, warm.cost)
    assert diff.saved["模型调用"] == 1
    assert diff.saved["检索"] == cold.cost.retrieve_calls, "整段检索都被跳过了"


def test_降级不进缓存且提示原因() -> None:
    class Broken:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, messages):
            self.calls += 1
            raise ConnectionError("连接被重置")

    broken = Broken()
    service = Service(build_retriever(), broken, sleep=lambda _s: None,
                      retry=RetryPolicy(attempts=3, backoff=0.01))
    first = service.handle(QUESTION)
    assert first.text == FALLBACK_TEXT
    assert first.outcome == "degraded"
    assert broken.calls == 3, "有界重试：正好三次"
    assert any("ConnectionError" in d for d in first.degraded)
    assert first.cost.model_calls == 3, "重试也是钱：记的是尝试次数"
    assert not first.cached
    assert service.cache.tiers["answer"].stats.stores == 0, "降级结果不许进缓存"
    second = service.handle(QUESTION)
    assert not second.cached and broken.calls == 6, "第二次照样要走完整路径"
    # 恢复之后立刻拿到真答案（坏值没有被缓存住）
    service.call = ScriptedModel()
    third = service.handle(QUESTION)
    assert third.text != FALLBACK_TEXT and third.outcome == "ok"


def test_时间预算不够就不再睡() -> None:
    slept: list[float] = []

    class Broken:
        def __call__(self, messages):
            raise TimeoutError("上游超时")

    clock = {"now": 0.0}

    def fake_clock() -> float:
        return clock["now"]

    def fake_sleep(seconds: float) -> None:
        slept.append(seconds)
        clock["now"] += seconds

    service = Service(build_retriever(), Broken(), sleep=fake_sleep, clock=fake_clock,
                      budget=0.2, retry=RetryPolicy(attempts=5, backoff=0.5))
    reply = service.handle(QUESTION)
    assert "时间预算用尽，停止重试" in reply.degraded
    assert len(slept) <= 1, "预算只有 0.2 秒，不该睡第二轮（0.5 秒的退避）"
    assert reply.cost.model_calls < 5


def test_限流会拒掉超出上界的请求() -> None:
    limiter = Limiter(limit=1, queue=0)
    release = threading.Event()

    class Slow:
        def __call__(self, messages):
            release.wait(5.0)           # 占住闸门，直到测试放行
            return "慢回答"

    service = Service(build_retriever(), Slow(), limiter=limiter, sleep=lambda _s: None)
    results: list = []

    def one() -> None:
        results.append(service.handle(QUESTION))

    threads = [threading.Thread(target=one) for _ in range(3)]
    threads[0].start()
    time.sleep(0.2)                     # 让第一个线程确实进了闸门
    threads[1].start()
    threads[2].start()
    time.sleep(0.2)                     # 后两个撞上限流
    release.set()
    assert all(t.join(10.0) is None for t in threads), "线程没在 10 秒内结束"
    rejected = [r for r in results if r.outcome == "rejected"]
    assert len(rejected) == 2, [r.outcome for r in results]
    assert limiter.rejected == len(rejected)
    assert service.limiter.max_active == 1, "闸门上限必须真的生效"


def test_观测的命名与基数护栏() -> None:
    registry = Registry()
    service, _ = make_service(registry=registry, log=JsonLog())
    service.handle(QUESTION)
    text = registry.render()
    assert "# TYPE zhizhou_rag_queries_total counter" in text
    assert "zhizhou_rag_cache_lookups_total{" in text
    assert "zhizhou_rag_request_duration_seconds_bucket{" in text
    assert "le=" in text
    assert service.log.find("query_done"), service.log.lines()
    assert set(service.log.find("query_start")[0]) >= {"trace_id", "event", "ts"}
    for line in service.log.lines():
        json.loads(line)                # 一行一个合法 JSON
    try:
        registry.counter("bad_total", "不该能注册", ("user_id",))
    except MetricError as exc:
        assert "高基数" in str(exc)
    else:                                                           # pragma: no cover
        raise AssertionError("高基数标签必须抛错而不是被静默丢掉")
    trace = Trace()
    with trace.measure("retrieve", chunks=3):
        time.sleep(0.001)
    assert trace.total > 0 and trace.as_dict()["spans"][0]["chunks"] == 3


def test_版本失效只影响该失效的层() -> None:
    service, model = make_service()
    first = service.handle(QUESTION)
    assert not first.cached
    service.cache.set_versions(Versions(prompt="p-新提示"))
    after = service.handle(QUESTION)
    assert not after.cached, "提示版本变了，答案必须重建"
    assert after.text == first.text, "本树的剧本模型与提示无关，所以正文相同"
    assert service.cache.tiers["embedding"].stats.hits >= 1, "嵌入层不该被清掉"
    assert model.calls == 2


def test_判档不是免费的且账目分得开() -> None:
    service, _ = make_service()
    reply = service.handle(QUESTION)
    assert reply.cost.retrieve_calls == 3, "融合 1 次 ＋ 判档的两条原始路 2 次"
    assert reply.cost.embed_calls == 1, "在线路径上的嵌入只有问题那一次"
    assert reply.cost.prompt_hanzi > 0 and reply.cost.output_hanzi > 0
    assert reply.quality == "correct"


def test_引用由代码绑定判定() -> None:
    service, _ = make_service()
    reply = service.handle(QUESTION)
    assert reply.chunks, "这一条应当召回到片"
    assert reply.citations_ok is False, (
        "剧本模型把两片照抄下来却按 1,2 编号，绑定层必须报出「编号合法但指错了片」")
    assert reply.text.count("[") >= 2


def test_缓存不许换掉系统的答案() -> None:
    """**性能改动必须过 5.6 的门**：同一批 24 条，开关缓存两跑，答案逐条相同。"""
    cases = list(load_cases(CASES))
    plain_service, plain_model = make_service()
    cached_service, cached_model = make_service()
    for case in cases:
        cold = plain_service.handle(case.text, use_cache=False)
        cached_service.handle(case.text)                 # 冷跑：填缓存
        calls = cached_model.calls
        warm = cached_service.handle(case.text)          # 热跑：命中缓存
        assert warm.cached, f"{case.case} 第二次应当命中答案缓存"
        assert warm.text == cold.text, f"{case.case} 的答案被缓存改掉了"
        assert cached_model.calls == calls, f"{case.case} 的热跑又调了一次模型"
    assert cached_service.cache.stats()["answer"]["hits"] == len(cases)
    assert cached_model.calls == plain_model.calls, (
        "两跑各自只生成一次：缓存不改答案，只改「算了几遍」")


def test_容量公式与单位() -> None:
    cap = capacity(dau=10_000, per_user=20, docs=50_000, chunks_per_doc=20, dim=1024)
    assert round(cap.peak_qps, 2) == round(200_000 / 86400 * 5, 2)
    assert round(cap.vector_gb, 3) == round(50_000 * 20 * 1024 * 4 / 1e9, 3)
    assert round(cap.index_gb, 3) == round(cap.vector_gb * 1.3, 3)
    assert cap.log_gb > 0 and cap.bandwidth_kb_s > 0
    assert set(cap.as_dict()) == {"峰值 QPS", "向量存储 GB", "索引内存 GB", "日志 GB", "带宽 KB/s"}


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_serve.py`。"""
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
