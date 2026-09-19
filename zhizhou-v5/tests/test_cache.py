# tests/test_cache.py —— 不需要密钥、不需要网络：失效矩阵、TTL、单飞与记账纪律
"""这一份测的是第 5 篇「在线侧」的第一层（5.7）。

十组断言，每一组都对应正文里的一个结论：

1. **失效矩阵**：改提示只作废 `answer`、改语料作废 `retrieval` ＋ `answer`、
   换模型只作废 `embedding`——**三层的依赖不一样**，所以「改一处就清空」是错的；
2. **戳要用内容算**：`Versions.from_content()` 在正文改了之后一定给出不一样的戳。
   同一条的另一面是那条真实事故：**只改正文、不改标签**时，键**必须**变；
3. **键的稳定性**：同一份载荷两次算出同一个键（`sort_keys` 那一行的作用），
   否则冷启动两次命中率凭空掉一半；
4. **载荷进键、版本进戳**：只有 `k` 变了（版本没变）时，键也要变——
   否则「换了用法却读到旧结果」；
5. **TTL**：过期计入 `expired` 而**不是** `misses`（两者混在一起就看不出来 TTL 设短了）；
   且重写一个键之后**它的过期时刻是新设的那个**（Redis `EXPIRE` 文档那条陷阱）；
6. **有界容量**：超过上限先淘汰最早过期的，且 `evictions` 记在账上；
7. **单飞**：8 个线程同时要同一个键，`compute` 只跑 1 次；
   没有单飞时（对照组）跑 8 次——**这一条是量的，不是信的**；
8. **降级结果不进缓存**：`store_if` 返回假时不写，下一次仍会重新算；
9. **`normalize` 只折字面**：首尾空白与句末标点被折掉，
   而**同义改写不折**（缓存层一旦开始猜「这两句是不是一个意思」，
   它就会在猜错时静默返回别人的答案）；
10. **账目自洽**：三层各自的 `lookups == hits + misses`，命中率与两个数一致。
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cache import (DEPENDS, LAYERS, LayeredCache, MemoryTier,     # noqa: E402
                       SingleFlight, Versions, cache_key, content_stamp,
                       normalize)


class FakeClock:
    """可推进的单调钟。**过期行为必须能被确定地测出来**，不能靠 `sleep`。"""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def tick(self, seconds: float) -> None:
        self.now += seconds


def test_失效矩阵只清该清的层() -> None:
    cache = LayeredCache(Versions())
    for layer in LAYERS:
        cache.tiers[layer].set(f"{layer}:x", 1, ttl=60)
    cleared = cache.set_versions(Versions(prompt="p1"))
    assert cleared == {"embedding": 0, "retrieval": 0, "answer": 1}, cleared
    for layer in LAYERS:
        cache.tiers[layer].set(f"{layer}:x", 1, ttl=60)
    cleared = cache.set_versions(Versions(prompt="p1", corpus="c1"))
    assert cleared == {"embedding": 0, "retrieval": 1, "answer": 1}, cleared
    for layer in LAYERS:
        cache.tiers[layer].set(f"{layer}:x", 1, ttl=60)
    cleared = cache.set_versions(Versions(prompt="p1", corpus="c1", model="m2"))
    assert cleared == {"embedding": 1, "retrieval": 0, "answer": 0}, cleared
    assert DEPENDS["embedding"] == ("model",)


def test_戳必须用内容算而不是用标签() -> None:
    a = Versions.from_content(prompt="只允许依据资料回答", corpus="片一", index="dim=256",
                              model="hashed")
    b = Versions.from_content(prompt="只允许依据资料回答，并给出出处", corpus="片一",
                              index="dim=256", model="hashed")
    assert a.prompt != b.prompt
    # 反例：只维护标签的写法（真事故）——标签一样，键就一样，旧答案被复用
    same_label = Versions(prompt="v3")
    assert cache_key("answer", {"q": "x"}, same_label) == cache_key("answer", {"q": "x"},
                                                                   Versions(prompt="v3"))
    assert cache_key("answer", {"q": "x"}, a) != cache_key("answer", {"q": "x"}, b)
    assert content_stamp("短") != content_stamp("长")


def test_键要稳定且与载荷有关() -> None:
    v = Versions()
    k1 = cache_key("retrieval", {"q": "x", "k": 3, "mode": "hybrid"}, v)
    k2 = cache_key("retrieval", {"mode": "hybrid", "k": 3, "q": "x"}, v)
    assert k1 == k2, "同一份载荷必须算出同一个键（字典序不固定会掉一半命中率）"
    k3 = cache_key("retrieval", {"q": "x", "k": 5, "mode": "hybrid"}, v)
    assert k1 != k3, "参数变了、版本没变——键必须变"
    assert k1.startswith("retrieval:")
    assert cache_key("answer", {"q": "x", "k": 3, "mode": "hybrid"}, v) != k1, "层不同键必不同"


def test_ttl过期记在expired而不是misses() -> None:
    clock = FakeClock()
    tier = MemoryTier("answer", clock=clock)
    tier.set("a", 1, ttl=10)
    assert tier.get("a") == 1
    clock.tick(11)
    assert tier.get("a") is None
    assert (tier.stats.hits, tier.stats.misses, tier.stats.expired) == (1, 1, 1)
    assert len(tier) == 0


def test_重写键之后过期时刻是新的() -> None:
    """Redis `EXPIRE` 文档那条：TTL 会被「覆盖键内容」的命令清掉。

    本树把它写成「写入与设期不可分」，这一条就是它的断言：
    第二次 `set` 之后，**按第一次的 TTL 算已经过期，但键还在**（因为新 TTL 更长）。
    """
    clock = FakeClock()
    tier = MemoryTier("retrieval", clock=clock)
    tier.set("k", "old", ttl=5)
    clock.tick(3)
    tier.set("k", "new", ttl=60)          # 重写：不能把过期时刻留在 2 秒后
    clock.tick(5)
    assert tier.get("k") == "new"
    assert tier.stats.expired == 0


def test_容量有界且淘汰记账() -> None:
    clock = FakeClock()
    tier = MemoryTier("answer", max_items=2, clock=clock)
    tier.set("a", 1, ttl=10)
    clock.tick(1)
    tier.set("b", 2, ttl=10)
    clock.tick(1)
    tier.set("c", 3, ttl=10)                    # 满了：淘汰最早过期的 a
    assert tier.stats.evictions == 1
    assert tier.get("a") is None
    assert tier.get("b") == 2 and tier.get("c") == 3
    assert len(tier) == 2


def test_单飞让并发只算一次() -> None:
    runs = {"without": 0, "locked": 0, "peek": 0}

    def hammer(bucket: str, flight: SingleFlight | None, *, with_peek: bool) -> None:
        """三组对照：没单飞 ｜ 有锁但没复查 ｜ 有锁且复查。"""
        barrier = threading.Barrier(8)
        hold: dict = {}

        def compute():
            runs[bucket] += 1
            time.sleep(0.05)
            value = f"值{runs[bucket]}"
            hold["v"] = value
            return value

        def one():
            barrier.wait()
            if flight is None:
                compute()
            elif with_peek:
                flight.run("k", compute, peek=lambda: hold.get("v"))
            else:
                flight.run("k", compute)

        threads = [threading.Thread(target=one) for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]

    hammer("without", None, with_peek=False)
    assert runs["without"] == 8, "对照组：没有单飞就是 8 次计算"
    hammer("locked", SingleFlight(), with_peek=False)
    assert runs["locked"] == 8, (
        "**只加锁不够**：8 个线程会被串行化，但每一个拿到锁之后照样算一遍——"
        "这就是「单飞必须配复查」那条（第一版就是这个错）")
    hammer("peek", SingleFlight(), with_peek=True)
    assert runs["peek"] == 1, "有锁 + 等锁期间复查：只算 1 次"


def test_降级结果不进缓存() -> None:
    cache = LayeredCache(Versions())
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"degraded": ("检索失败",)}

    value, hit = cache.get_or_compute("answer", {"q": "x"}, compute,
                                      store_if=lambda p: not p["degraded"])
    assert not hit and calls["n"] == 1
    _again, hit2 = cache.get_or_compute("answer", {"q": "x"}, compute,
                                        store_if=lambda p: not p["degraded"])
    assert not hit2 and calls["n"] == 2, "坏的（降级的）结果不许被缓存"
    assert cache.tiers["answer"].stats.stores == 0


def test_normalize只折字面() -> None:
    assert normalize("  知舟  的发布说明 必须包含哪几段？ ") == "知舟 的发布说明 必须包含哪几段"
    assert normalize("发布规范？") == normalize("发布规范。")
    assert normalize("库存预警阈值是多少") != normalize("库存告警的门槛是多少"), \
        "同义改写不归并——那是 5.4 的活，缓存层猜错了会静默返回别人的答案"


def test_账目自洽() -> None:
    cache = LayeredCache(Versions())
    cache.get_or_compute("answer", {"q": "a"}, lambda: "v1")
    cache.get_or_compute("answer", {"q": "a"}, lambda: "v1")
    cache.get_or_compute("answer", {"q": "b"}, lambda: "v2")
    stats = cache.stats()
    for layer in LAYERS:
        s = stats[layer]
        assert s["lookups"] == s["hits"] + s["misses"], s
    assert stats["answer"]["hits"] == 1 and stats["answer"]["misses"] == 2
    assert stats["answer"]["hit_rate"] == round(1 / 3, 4)
    assert cache.computed == 2, "算了两次（b 一次、a 一次）"


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_cache.py`。"""
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
