"""编排：`depends_on` 保证的是**顺序**，不是**能用**。

这一块回答的是「起得来」与「起得对」之间的那一步。官方那页把这句话写得很短：
**Compose 在启动时不等到容器「就绪」，只等到它在跑。** 于是同一个依赖有三种等法：

| 写法 | 等到什么时候 |
| --- | --- |
| 不写 `depends_on` | 谁也不等：两个服务一起被创建 |
| `depends_on`（默认 `service_started`） | 等到**容器在跑**（进程起来了，但它自己的初始化可能还没做完） |
| `condition: service_healthy` | 等到 `healthcheck` **第一次报健康** |
| `condition: service_completed_successfully` | 等到**跑完并且退出码是 0**（迁移、建索引这类一次性任务） |

四行的差别不在「顺序」，而在**发起方要不要自己扛住那段时间**。所以这一块的读数
是三笔账同时报：应用侧**失败了几次请求**、它**多久之后才真的成了**、以及
「依赖判健康」这件事**花了多少个探针**。

依据：Docker 官方「Control startup and shutdown order in Compose」（上面那张表就是它的
原话）与 `healthcheck` 的四个参数（`interval` / `timeout` / `retries` / `start_period`）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Service:
    """一个服务。**`start_s` 与 `ready_s` 分开**——它们分开正是这一块的全部内容。"""

    name: str
    label: str
    start_s: int          # 容器「在跑」的时刻（秒）
    ready_s: int          # 真正能应答的时刻（秒）
    interval: int = 5
    retries: int = 5
    start_period: int = 0

    @property
    def healthy_s(self) -> int:
        """`healthcheck` **第一次报健康**的时刻：第一个「到达 `ready_s` 之后」的探针。

        探针按 `interval` 均匀发（t = k × interval）；`start_period` 不推迟健康，
        它只让「这段时间里的失败不算失败」——所以它不出现在这个式子里，
        它与「判不健康要多久」有关（见 `unhealthy_after`）。
        """
        k = -(-self.ready_s // self.interval)     # 向上取整
        return k * self.interval

    @property
    def probes(self) -> int:
        """判到健康一共发了几个探针。"""
        return self.healthy_s // self.interval

    @property
    def unhealthy_after(self) -> int:
        """**判它不健康**要多久：`start_period` ＋ `interval × retries`。

        这个数与本块的主题是同一件事的两面：`retries` 越大，启动期越不容易误判，
        而**真出事的时候也就越晚知道**。
        """
        return self.start_period + self.interval * self.retries


#: 知舟服务栈里的两个角色。数据库那一行是这一块的关键：**它在第 2 秒「在跑」，
#: 而在第 12 秒才真的能应答**——中间那 10 秒正是三种等法分出胜负的地方。
DB = Service("db", "PostgreSQL", start_s=2, ready_s=12)
#: 迁移是一次性任务：它要**跑到退出码 0**，应用才该起来。它自己在第 2 秒开始、
#: 第 14 秒跑完——**而它跑得完这件事本身已经蕴含了数据库可用**（它连的就是那个库）。
MIGRATE = Service("migrate", "建表与建索引", start_s=2, ready_s=14)


@dataclass(frozen=True)
class Draft:
    """一种编排写法。`depends_on` 的四种取值在这里是一条字段，不是四份文件。"""

    name: str
    label: str
    condition: str | None      # None / service_started / service_healthy / service_completed_successfully
    declared: bool = True      # 有没有写 depends_on


DRAFTS: tuple[Draft, ...] = (
    Draft("none", "不写 `depends_on`（两个一起起）", None, declared=False),
    Draft("started", "`depends_on: db`（默认 `service_started`）", "service_started"),
    Draft("healthy", "`condition: service_healthy`", "service_healthy"),
    Draft("completed", "`condition: service_completed_successfully`（等迁移跑完）",
          "service_completed_successfully"),
)


def waited_on(draft: Draft) -> Service:
    """这一种写法等的是谁。**第四种等的是迁移，不是数据库**——它不是同一次等待的变体，
    是另一条链上的一环（应用真正需要的是「表建好了」，而不是「库起来了」）。"""
    return MIGRATE if draft.condition == "service_completed_successfully" else DB


def app_start(draft: Draft) -> int:
    """应用**第一次发请求**的时刻。四种写法各是各的：不写就是 0 秒。"""
    if not draft.declared or draft.condition is None:
        return 0
    dep = waited_on(draft)
    if draft.condition == "service_started":
        return dep.start_s
    if draft.condition == "service_healthy":
        return dep.healthy_s
    if draft.condition == "service_completed_successfully":
        return dep.ready_s
    raise KeyError(draft.condition)


def startup(draft: Draft, *, retry_s: int | None = 3) -> dict:
    """一份编排的启动账：**失败几次、什么时候真的成了**。

    `retry_s=None` 表示这个应用**自己没有重试**（很多脚手架就是这么写的：
    启动时连一次，连不上就退出）。此时唯一的指望是「起来的时候依赖已经能用」
    ——于是四种写法的差别从「快不快」变成「成不成」。
    """
    dep = waited_on(draft)
    start = app_start(draft)
    if retry_s is None:
        # 一次机会：那一刻依赖没应答，这一次启动就废了（进程退出，交给重启策略）
        ok = start >= dep.ready_s
        return {
            "draft": draft.name, "label": draft.label, "dep": dep.name,
            "app_start": start, "dep_ready": dep.ready_s, "dep_running": dep.start_s,
            "attempts": 1, "failures": 0 if ok else 1,
            "first_ok": start if ok else None,
            "healthy_s": dep.healthy_s, "probes": dep.probes,
        }
    k = -(-(dep.ready_s - start) // retry_s) if dep.ready_s > start else 0
    return {
        "draft": draft.name, "label": draft.label, "dep": dep.name,
        "app_start": start, "dep_ready": dep.ready_s, "dep_running": dep.start_s,
        "attempts": k + 1, "failures": k,
        "first_ok": start + k * retry_s,
        "healthy_s": dep.healthy_s, "probes": dep.probes,
    }


def startup_table(*, retry_s: int | None = 3) -> list[dict]:
    """四种写法各一行。**两种前提各算一遍**（有重试 / 没重试）——见 `startup()` 的说明。"""
    return [startup(d, retry_s=retry_s) for d in DRAFTS]


def healthcheck_table() -> list[dict]:
    """`healthcheck` 的四个参数各自管什么：用四种组合把「判健康」与「判不健康」两个时刻分开。"""
    rows: list[dict] = []
    for interval, retries, start_period in ((5, 5, 0), (1, 10, 0), (5, 5, 30), (10, 3, 0)):
        s = Service("db", "PostgreSQL", start_s=2, ready_s=12,
                    interval=interval, retries=retries, start_period=start_period)
        rows.append({
            "interval": interval, "retries": retries, "start_period": start_period,
            "healthy_s": s.healthy_s, "probes": s.probes,
            "unhealthy_after": s.unhealthy_after,
        })
    return rows
