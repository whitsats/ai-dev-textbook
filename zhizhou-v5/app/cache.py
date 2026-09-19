"""三层缓存：**嵌入、检索、答案**。这一章的第一件事是「缓存不是什么都能存」。

## 三层不是「一个缓存分三份」

它们的**失效面不一样**，这才是分层的理由：

| 层 | 键的载荷 | 依赖的版本 | 为什么 |
| --- | --- | --- | --- |
| `embedding` | 片或问题的**文本** | 只依赖**嵌入模型** | 换语料、重切分都不影响「这段文字的向量」——它只跟文字与模型有关 |
| `retrieval` | 问题 ＋ 检索参数（`k`／`mode`／`depth`） | 语料 ＋ 索引 | 片换了、索引换了，同一句话的召回就不同 |
| `answer` | 问题 ＋ 控制位（要不要检索、走哪条提示） | 提示 ＋ 语料 ＋ 索引 | 提示换了，答案必须重算 |

**「改一处就把所有缓存清掉」是常见做法，也是最浪费的一种**：它顺手丢掉了嵌入缓存里
真正可复用的那一层（重切分之后，大多数片的文字一字未变）。所以本章把「失效」写成
一张**依赖矩阵**，而不是一条 `flush_all()`。

## 键里放参数，戳里放版本

两件事必须分开，否则一定会错：

- **同一进程内会变的调参**（`k`、`mode`、`depth`、要不要检索）→ 进**键的载荷**。
  它们是「这次查询的参数」，不是「这一版系统的身份」；
- **发布一次才变的东西**（提示正文、语料清单、索引参数、嵌入模型）→ 进**版本戳**。
  它们变了，旧值就**不能再算数**——这与 TTL 走的是两条不同的路（见下）。

## TTL 管新鲜度，版本戳管正确性

- **TTL** 回答的是「这东西还能用多久」：语料每月更新、答案里的口径会漂，
  过期就重算。它是**概率性的**；
- **版本戳**回答的是「这东西还算不算数」：提示改了、语料换了，旧值**一定**不对。
  它是**确定的**。

只用 TTL 会有一个说不通的窗口：改了提示之后的头一个小时里，缓存照样命中旧答案。
只用版本戳则永远不清：一片文档下架了，没人去动版本戳，旧答案就一直在。
两件一起做才对。

## 戳要用**内容**算，不能用标签算

`Versions.prompt` 在本树里是**提示正文的哈希**，不是 `"v3"` 这样的标签。原因是一条
真实事故（见 5.7.5 的读数）：改了提示正文、忘了改标签，于是「标签没变 → 戳没变 →
旧答案被复用」——而 revisit 时两边都「看着对」。**能给内容算哈希的地方，就不要用人工
维护的编号。** 与 5.6 那条「这份数字是算出来的还是抄过来的」是同一个问题。

## TTL 的一个真实陷阱（Redis 官方文档写明）

`EXPIRE` 的文档里写着：**「timeout 只会被删除或覆盖键内容的命令清掉，包括 DEL、SET、
GETSET」**。也就是说 `SET key value`（不带 `EX`）会把刚设好的 TTL 一起抹掉——
内存实现里如果没有对应的语义，读代码时根本看不出来。本模块把这条写进了
`MemoryTier.set()` 的注释，并在测试里钉住：**重写一个键之后，它必须还带 TTL**。
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

__all__ = ["DEPENDS", "LAYERS", "Entry", "LayeredCache", "MemoryTier", "SingleFlight",
           "Stats", "Versions", "cache_key", "content_stamp", "normalize"]

#: 三层的名字。顺序是数据流的方向：先嵌入、再检索、最后生成。
LAYERS = ("embedding", "retrieval", "answer")

#: 每一层依赖哪些版本。**这张表就是本章的失效矩阵**，改它等于改行为。
DEPENDS: dict[str, tuple[str, ...]] = {
    "embedding": ("model",),
    "retrieval": ("corpus", "index"),
    "answer": ("prompt", "corpus", "index"),
}


def content_stamp(text: str, *, size: int = 12) -> str:
    """给**内容**算戳（默认取哈希前 12 位）。

    `size=12` 是「够短到能进日志、够长到撞不上」的折中：12 位十六进制是 48 比特，
    本书规模的手工改稿不可能撞。**它不是安全边界**，别拿它当签名用。
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:size]


@dataclass(frozen=True)
class Versions:
    """四个版本戳。**它们是「这一版系统」的身份**，不是某次查询的参数。

    默认值只是为了让示例能直接跑；真实服务里四个都该从内容算出来
    （`Versions.from_content()` 就是那个入口）。
    """

    prompt: str = "p0"
    corpus: str = "c0"
    index: str = "i0"
    model: str = "m0"

    def stamp(self) -> str:
        return f"p={self.prompt};c={self.corpus};i={self.index};m={self.model}"

    def depends_on(self, layer: str) -> dict[str, str]:
        """这一层依赖的版本子集——失效矩阵的单元格。"""
        return {k: getattr(self, k) for k in DEPENDS[layer]}

    @classmethod
    def from_content(cls, *, prompt: str, corpus: str, index: str, model: str) -> "Versions":
        """从**内容**算四个戳。四个参数都是「会变的那份东西」的原文或清单文本。"""
        return cls(prompt=content_stamp(prompt), corpus=content_stamp(corpus),
                   index=content_stamp(index), model=model)


def normalize(text: str) -> str:
    """键的前半段：把**同一个问题的不同写法**折到一起。

    折三件事：首尾空白、内部连续空白、尾部的句末标点（`？` / `?` / `。` / `!`）。
    不做同义归一——那是 5.4 的活（改写），**缓存键只认「字面相同」**：
    一旦缓存层开始猜「这两句是不是一个意思」，它就会在猜错时静默返回别人的答案，
    而这种错在账面上与命中一模一样。
    """
    folded = " ".join(text.split())
    return folded.rstrip("？?。.！!")


def cache_key(layer: str, payload, versions: Versions) -> str:
    """键 ＝ `层:载荷哈希`，而哈希里**同时**含载荷与这一层依赖的版本子集。

    `sort_keys=True` 与 `separators` 是为了**同一份载荷一定算出同一个键**——
    字典序不固定的话，冷启动两次会得到两个键，命中率凭空掉一半。
    """
    raw = json.dumps({"layer": layer, "payload": payload,
                      "v": versions.depends_on(layer)},
                     ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{layer}:{content_stamp(raw, size=16)}"


@dataclass
class Stats:
    """一层的命中账。`expired` 单列：**过期与未命中是两件事**。

    都把「没拿到值」当未命中，就永远看不出 TTL 是不是设短了——
    这是 5.6 那条「分母要写在表里」的一次搬家。
    """

    hits: int = 0
    misses: int = 0
    expired: int = 0
    stores: int = 0
    evictions: int = 0

    @property
    def lookups(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return round(self.hits / self.lookups, 4) if self.lookups else 0.0

    def as_dict(self) -> dict:
        return {"hits": self.hits, "misses": self.misses, "expired": self.expired,
                "stores": self.stores, "evictions": self.evictions,
                "lookups": self.lookups, "hit_rate": self.hit_rate}


@dataclass(frozen=True)
class Entry:
    """一条缓存记录。`expires_at` 是**绝对时刻**，不是剩余秒数。

    存剩余秒数的写法在多线程下会漂：两个线程各自 `-1`，等于扣了两次。
    这也是 Redis 的 `EXPIRE key seconds` 与 `PEXPIREAT key ms` 的区别所在
    （前者是相对时长、后者是绝对时刻），只是本树用单调钟来记。
    """

    key: str
    value: object
    expires_at: float

    def alive(self, now: float) -> bool:
        return now < self.expires_at


class MemoryTier:
    """一层内存缓存：`dict` ＋ 过期时刻 ＋ **有界容量**（满了先淘汰最早过期的）。

    有界是硬要求，不是优化：一个只进不出的缓存就是内存泄漏，
    而它在压测里表现得像「性能变好了」（进程还没 OOM 的时候确实更快）。
    """

    def __init__(self, name: str, *, max_items: int = 256,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.name = name
        self.max_items = max_items
        self.clock = clock
        self.stats = Stats()
        self._data: dict[str, Entry] = {}

    # ---- 基本操作 ----
    def get(self, key: str):
        now = self.clock()
        entry = self._data.get(key)
        if entry is None:
            self.stats.misses += 1
            return None
        if not entry.alive(now):
            del self._data[key]
            self.stats.expired += 1
            self.stats.misses += 1
            return None
        self.stats.hits += 1
        return entry.value

    def peek(self, key: str):
        """看一眼，**不记账**。单飞的复查要用它——用 `get()` 会把一次查询记成两次。

        这一处是写读数时改出来的：第一版单飞的复查直接调 `get()`，
        于是每层的 `lookups` 都多了一次、`misses` 也多了一次，
        三层命中率 **0.3333** 而真实情况是 **0.5**。
        错的不是公式，是「什么算一次查询」——与 5.6 那条「分母要写在表里」同一族。
        """
        entry = self._data.get(key)
        return entry.value if entry is not None and entry.alive(self.clock()) else None

    def set(self, key: str, value, *, ttl: float) -> None:
        """写入并**一定**带上过期时刻。

        对着 Redis 的 `EXPIRE` 文档看这一行：那边写着 TTL 会被
        `DEL`／`SET`／`GETSET` 这类**覆盖键内容**的命令清掉。也就是说
        「先 `SET` 再 `EXPIRE`」的写法只要中间被打断，键就变成永久的；
        而 `SET key value EX 60` 是一条命令、一个原子动作。
        本方法就是后者：**写入与设期不可分**。
        """
        if len(self._data) >= self.max_items and key not in self._data:
            self._evict()
        self._data[key] = Entry(key, value, self.clock() + ttl)
        self.stats.stores += 1

    def _evict(self) -> None:
        oldest = min(self._data.values(), key=lambda e: e.expires_at)
        del self._data[oldest.key]
        self.stats.evictions += 1

    def invalidate(self, *, layers_prefix: str = "") -> int:
        """按键前缀清一层（或全部）。返回清掉的条数——**账目要能对得上**。"""
        doomed = [k for k in self._data if k.startswith(layers_prefix)]
        for k in doomed:
            del self._data[k]
        return len(doomed)

    def __len__(self) -> int:
        self._prune()
        return len(self._data)

    def _prune(self) -> None:
        now = self.clock()
        for k in [k for k, e in self._data.items() if not e.alive(now)]:
            del self._data[k]


class SingleFlight:
    """同一个键同时只让**一个**请求去算，其余的等它的结果。

    这是缓存最容易被跳过的一层：缓存解决的是「算过了」，
    而并发下最常见的形态是**「都没算过、同时来了」**（缓存击穿）。
    没有它，冷启动或刚失效的那一瞬间，一次热门查询会打出 N 次嵌入／N 次模型调用。

    **等待者的返回值与发起者相同**——否则「省了调用」会以「有的请求拿到空」
    为代价，而这种代价在平均延迟上看不出来（它只体现在少数用户身上）。

    本树用线程锁实现：真实服务里是「进程内锁 ＋ Redis 分布式锁」两层，
    但**判据是一样的**——5.7.2 的读数量的就是「N 个并发里算了 M 次」。
    """

    def __init__(self) -> None:
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()
        self.saved = 0          # 被挡下来的重复计算次数

    def _lock(self, key: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    def run(self, key: str, fn: Callable[[], object], *, peek: Callable[[], object] = None):
        """`peek` 是「等待期间别人可能已经算好了」的复查入口。

        少了这一步会有一种隐蔽的错：第二个请求排队拿到锁之后**又算了一遍**——
        它手里的 `fn` 是在排队之前构造的，不会自己去看缓存。
        """
        lock = self._lock(key)
        with lock:
            if peek is not None:
                fresh = peek()
                if fresh is not None:
                    self.saved += 1
                    return fresh
            return fn()


class LayeredCache:
    """三层的组装。对外只有三个动作：算、拿、看账。"""

    def __init__(self, versions: Versions | None = None, *,
                 max_items: int = 256, ttl: dict[str, float] | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.versions = versions or Versions()
        self.clock = clock
        #: 各层的存活时长。默认值只是示例；**生产里由「这份数据多久会漂」决定**，
        #: 而语料／提示的漂移速度完全不同——所以它是三个数，不是一个数。
        self.ttl = {"embedding": 3600.0, "retrieval": 900.0, "answer": 300.0} | (ttl or {})
        self.tiers = {name: MemoryTier(name, max_items=max_items, clock=clock)
                      for name in LAYERS}
        self.flight = SingleFlight()
        self.computed = 0       # 真的跑了 `fn` 的次数
        self.served = 0         # 其中被单飞挡下来、改用别人结果的次数

    # ---- 版本 ----
    def set_versions(self, versions: Versions) -> dict[str, int]:
        """换版本，并按依赖矩阵作废。**返回每层清掉的条数**——这就是失效矩阵的读数。

        实现上很朴素（换族名的前缀），但有一处的选择值得看：**不清空整个缓存**。
        若把 `versions` 换掉就 `flush_all()`，嵌入层会被无谓地清掉，
        而它只依赖嵌入模型——重切分语料之后，绝大多数片的文字并没有变。
        """
        old, self.versions = self.versions, versions
        cleared: dict[str, int] = {}
        for layer in LAYERS:
            if old.depends_on(layer) == versions.depends_on(layer):
                cleared[layer] = 0
                continue
            cleared[layer] = self.tiers[layer].invalidate()
        return cleared

    # ---- 主入口 ----
    def get_or_compute(self, layer: str, payload, compute: Callable[[], object],
                       *, store_if: Callable[[object], bool] | None = None):
        """返回 `(值, 是否命中)`。**三件事在一个函数里**：查、算、记账。

        分开写（调用方自己查、自己算、自己存）的后果在 5.7.2 的读数里：
        总有一处忘了记账，于是命中率是「估的」而不是量的。

        `store_if` 是「**降级结果不许进缓存**」那个开关：一次上游故障换来的兜底回答，
        如果被当成正常结果缓存下来，故障恢复之后用户还会继续吃旧的兜底文案——
        而且**看着像缓存命中**，没有任何报错。默认全都存（调用方说了算的那一类）。
        """
        key = cache_key(layer, payload, self.versions)
        tier = self.tiers[layer]
        found = tier.get(key)
        if found is not None:
            return found, True

        def peek():
            """等锁期间别人已经算好了？那就是**一次命中**（值来自缓存，没有重算）。"""
            again = tier.peek(key)
            if again is not None:
                tier.stats.hits += 1
                self.served += 1
            return again

        def once():
            self.computed += 1
            value = compute()
            if store_if is None or store_if(value):
                tier.set(key, value, ttl=self.ttl[layer])
            return value

        return self.flight.run(key, once, peek=peek), False

    def stats(self) -> dict:
        """三层各自的账 ＋ 单飞挡下来的次数。**命中的是哪一层必须能分开看。**"""
        return {name: self.tiers[name].stats.as_dict() for name in LAYERS} | {
            "single_flight_saved": self.served}
