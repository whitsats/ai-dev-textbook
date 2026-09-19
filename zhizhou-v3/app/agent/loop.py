"""知舟的代理循环：决策 → 执行 → 回填 → 再问。

循环本身不认识模型，也不认识工具：`policy` 与 `tools` 都是注入的。
所以同一份循环既能跑假模型（测试），也能跑真模型（demo 与线上）。
"""
from __future__ import annotations

import time
from collections.abc import Callable

from app.agent.runtime import Budget, LoopResult, Trace, TraceEntry  # noqa: F401 —— 对外仍是这一份接口

__all__ = ["run_agent", "Budget", "Trace", "TraceEntry", "LoopResult", "bind_tools",
           "error_kind"]


def run_agent(task: str, policy, tools: dict, budget: Budget) -> LoopResult:
    """决策 → 执行 → 回填 → 再问。终止永远是运行时的责任。"""
    # 模型调用数记在 `budget` 上，而不是这里的局部变量：**抛异常时局部变量随栈一起消失**，
    # 而「这一份花掉了多少次调用」必须留得下来（见 `Budget.count_call`，3.7 实测里踩到过）。
    trace = Trace(task)

    def wrap_up(reason: str) -> LoopResult:
        """强制收口：不再探索，只要一个「基于已有信息的最佳答案」。"""
        budget.count_call()
        d = policy(task, trace, wrap_up=True)
        budget.charge(d.get("tokens", 0))
        return LoopResult(d.get("final_text"), budget.steps, budget.calls,
                          budget.tokens, f"{reason} → 收口", trace)

    while True:
        why = budget.exhausted()
        if why:
            return wrap_up(why)
        d = policy(task, trace)
        # 只有「真的问了一次模型」才计一次调用：一次响应里的第 2、3 个工具调用
        # 是排队执行，不再问模型，所以它花了步数但不该被记成模型调用（3.5.8）。
        if d.get("model_call", True):
            budget.count_call()
        budget.charge(d.get("tokens", 0))
        budget.begin_step()
        if d.get("final"):
            trace.add(TraceEntry(budget.steps, d["thought"], tokens=d["tokens"], final=True))
            return LoopResult(d["thought"], budget.steps, budget.calls, budget.tokens,
                              "模型给出最终答案", trace)
        action, arg = d["action"], d["arg"]
        if action not in tools:                  # 决策校验先于执行
            return wrap_up(f"工具 {action} 不存在")
        try:
            obs = tools[action](arg)
        except Exception as exc:                 # 工具异常不能拖垮循环
            obs = f"[工具失败] {type(exc).__name__}: {exc}"
        trace.add(TraceEntry(budget.steps, d["thought"], action, arg, obs, d["tokens"]))
        if trace.stalled_by_action(action, arg):
            return wrap_up(f"卡死：连续 {trace.repeat_limit} 次相同动作")
        if trace.stalled_by_fact(obs):
            return wrap_up("无新事实")


def error_kind(message: str) -> str:
    """把工具的失败消息收进有限档。**它的取值集合必须小**，否则「按 error.type 分组」
    会分出一堆只出现一次的柱子，那种图看一眼就知道读不出东西。

    收档的依据是「下一步该改什么」：改 schema / 改权限档 / 改提示词 / 查工具实现。
    """
    for key, bucket in (("权限不足", "权限不足"), ("缺少幂等键", "缺幂等键"),
                        ("越权", "越权"), ("不属于你", "越权"),
                        ("不存在", "目标不存在"),
                        ("多出字段", "参数不合 schema"),
                        ("不是合法", "参数不合 schema"), ("类型", "参数不合 schema"),
                        ("必填", "参数不合 schema")):
        if key in message:
            return bucket
    return "工具执行失败"


def bind_tools(registry, *, run_id: str, allow_write: bool = False,
               approve: Callable[[str, dict], bool] | None = None,
               require_approval: tuple[str, ...] = ("publish_article",),
               on_tool: Callable[[dict], None] | None = None) -> dict:
    """把注册表绑成循环要的 `{名字: 参数文本 → 结果文本}`。

    三件事都在这层收口，循环一行都不用改：
      · 参数从 JSON 文本解析，坏 JSON 变成一条可读的失败而不是异常；
      · 写操作按 `run_id` 生成幂等键——**同一任务内、参数相同的写只执行一次**，
        跨任务换一个 run_id（重放不被静默吞掉，也不会重复写）；
      · 需要人工确认的动作（默认发布）先问 `approve`，不问就不执行。

    `on_tool` 是 3.9 加的追踪回呼。**被拒绝的那两类也要上报**（参数错、未获批准）：
    它们不是「没发生的事」——一个总被拒的工具正是要看的那根柱子，漏记它就等于把
    「工具不可用」这类失败从图上抹掉。
    """
    import hashlib
    import json

    def binding(name: str):
        def emit(*, ok: bool, error: str = "", arguments: str = "", result: str = "",
                 ms: float, idem: str = "") -> None:
            if on_tool is not None:
                on_tool({"tool": name, "ok": ok, "error_type": error, "arguments": arguments,
                         "result": result, "duration_ms": ms, "idem": idem})

        def call(arg: str) -> str:
            started = time.perf_counter()
            try:
                args = json.loads(arg) if (arg or "").strip() else {}
            except json.JSONDecodeError:
                text = "[参数不是合法 JSON] 请给出对象形式的参数"
                emit(ok=False, error="参数不是合法 JSON", arguments=arg or "", result=text,
                     ms=(time.perf_counter() - started) * 1000)
                return text
            if not isinstance(args, dict):
                text = "[参数必须是对象] 例如 {\"q\": \"刷新令牌\"}"
                emit(ok=False, error="参数不是对象", arguments=arg or "", result=text,
                     ms=(time.perf_counter() - started) * 1000)
                return text
            if name in require_approval and not (approve and approve(name, args)):
                text = f"[等待人工确认] {name} 未获批准，本轮不执行。请向用户说明并停下。"
                emit(ok=False, error="未获人工确认", arguments=arg or "", result=text,
                     ms=(time.perf_counter() - started) * 1000)
                return text
            digest = hashlib.sha1(json.dumps(args, sort_keys=True, ensure_ascii=False)
                                  .encode("utf-8")).hexdigest()[:12]
            idem = f"{run_id}:{name}:{digest}"
            res = registry.call(name, args, idem=idem, allow_write=allow_write)
            text = res.payload()
            emit(ok=res.ok, error="" if res.ok else error_kind(res.error), arguments=arg or "",
                 result=text, ms=(time.perf_counter() - started) * 1000, idem=idem)
            return text
        return call

    return {name: binding(name) for name in registry.tools}


# ---- 3.3 阶段的知舟：只挂两个只读工具；真实工具集在 3.5（app/agent/tools/zhizhou.py）----
ARTICLES = {1: "知舟博客 API 从零到一", 2: "FastAPI 依赖注入的两种写法", 3: "JWT 刷新令牌怎么做"}
_tick = {"n": 0}


def search_article(q: str) -> str:
    """搜索结果会轻微变化：所以「同参数重复」不等于「结果相同」，两个口径都要装。"""
    _tick["n"] += 1
    return "；".join(f"{i}:{t}" for i, t in ARTICLES.items()) + f"（命中 {30 + _tick['n']} 条）"


TOOLS = {"search_article": search_article,
         "read_article": lambda i: f"《{ARTICLES[int(i)]}》正文…（略）" if int(i) in ARTICLES else "[没有这篇文章]"}


def scripted(*decisions):
    """把「模型」换成背好剧本的函数；真实实现里这一行是一次模型调用。"""
    def policy(task, trace, wrap_up=False):
        if wrap_up:
            return {"thought": "按已有信息给结论", "final": True, "tokens": 60,
                    "final_text": "共 3 篇，最相关的是《JWT 刷新令牌怎么做》"}
        n = len([e for e in trace.entries if not e.final])
        return decisions[min(n, len(decisions) - 1)]
    return policy


def slow_clock(step: float = 12.0):
    """假时钟：每读一次前进 12 秒，把「墙钟超时」变成可重复的用例。"""
    t = {"v": 0.0}

    def now() -> float:
        t["v"] += step
        return t["v"]
    return now


def show(name: str, policy, kw=None) -> None:
    r = run_agent("找一篇讲令牌的文章", policy, TOOLS, Budget(**(kw or {})))
    print(f"\n=== {name} ===")
    print(f"  终止：{r.reason}｜步数 {r.steps}｜模型调用 {r.calls}（含收口 1 次）｜词元 {r.tokens}")
    print(f"  答案：{r.answer}")
    for e in r.trace.entries:
        tail = "→ 最终答案" if e.final else f"→ {e.action}({e.arg}) → {str(e.observation)[:26]}"
        print(f"  [{e.n}] {e.thought} {tail}")


if __name__ == "__main__":
    show("正常收敛", scripted(
        {"thought": "先列文章", "action": "search_article", "arg": "令牌", "tokens": 120},
        {"thought": "读第三篇", "action": "read_article", "arg": "3", "tokens": 140},
        {"thought": "信息够，给结论", "final": True, "tokens": 80,
         "final_text": "《JWT 刷新令牌怎么做》最相关：它讲了刷新令牌与黑名单"}))
    show("卡死：同参数重复三次", scripted(
        {"thought": "再搜一次", "action": "search_article", "arg": "令牌", "tokens": 110}))
    show("换着说法没进展（同动作口径拦不住）", scripted(
        *[{"thought": f"换个说法搜第 {n} 次", "action": "read_article", "arg": "3", "tokens": 110}
          for n in range(1, 9)]))
    show("工具不存在", scripted(
        {"thought": "删掉那篇", "action": "delete_article", "arg": "3", "tokens": 90}))
    show("词元预算 240", scripted(
        *[{"thought": f"读第 {n} 篇", "action": "read_article", "arg": str(n), "tokens": 130}
          for n in range(1, 9)]),
        {"max_tokens": 240})
    show("墙钟超时 30s（注入假时钟）", scripted(
        *[{"thought": f"读第 {n} 篇", "action": "read_article", "arg": str(n), "tokens": 40}
          for n in range(1, 9)]),
        {"max_tokens": 9999, "clock": slow_clock(12.0)})
