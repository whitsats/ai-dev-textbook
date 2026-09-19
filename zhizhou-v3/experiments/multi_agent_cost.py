"""实验：同一个任务，单代理与多代理各花多少、拿到多少。

    python experiments/multi_agent_cost.py            # 离线、可复现（默认）
    python experiments/multi_agent_cost.py --real     # 真机（需要凭据）

**离线那一份用剧本驱动，但「花多少」是真的**：每一次请求的体量都由本地编码器数
（`tiktoken`），数的是**实际会发出去的东西**——消息体 ＋ 这一次请求带的工具 schema。
工具结果用的是可运行树里那篇真文章。所以「峰值上下文」「串行阶段」这几列不是估的。

三件事必须一起数，少一样就会得出相反的结论：

  · **消息体**：单代理每多一轮，前面的工具结果就要重发一次（累积），
    多代理把三份材料放进三个上下文，各自只发一次；
  · **每次请求都带的固定开销**：系统提示 ＋ 工具 schema。多代理的模型调用更多，
    固定开销就付更多次——只数消息体会把这一项漏掉，正好漏掉多代理最贵的那一块；
  · **主管汇总那一次调用**：`default_synthesis` 是离线验收用的拼接，不调模型。
    真机上汇总一定要调一次（它要把几份结论一起读进去），那一次会把差距吃掉一大截。
    所以下面并排给出「拼接汇总」与「主管再调一次」两行。

要看的不是「谁更省」：多代理几乎一定更贵（官方数据：Agent ≈ 4× chat，多代理 ≈ 15× chat）。
要看的是它**买到了什么**：

  · 串行阶段（关键路径）：单代理的动作必须一环等一环，多代理可以同时开；
  · 峰值上下文：多代理把「三份材料」切成三份独立上下文，峰值由最大的一份决定；
  · 覆盖率与重复：多代理少了「一份上下文里塞满东西」，但多了「两份交接单撞车」的风险。

任务选的是**广度优先**的那种（官方说的适用场景）：三个互不依赖的方向各查一点，
最后汇成一段话。反过来，像「改一段代码」这种每一步依赖上一步的任务，
切给子代理只会让它们互相等——那类任务的对照结论是「不要用多代理」，本章正文里会写。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tiktoken  # noqa: E402

from app.agent.loop import Budget, bind_tools, run_agent                 # noqa: E402
from app.agent.orchestrator import EFFORT_LADDER, Handoff, orchestrate    # noqa: E402
from app.agent.policy import ModelPolicy                                  # noqa: E402
from app.agent.tools import zhizhou                                       # noqa: E402
from app.llm.client import Config, RawChat, ToolCall, chat                # noqa: E402

ENC = tiktoken.get_encoding("o200k_base")
SYSTEM = "你是知舟的助手。回答只用工具给的事实，不要编。"
LEAD_SYSTEM = "你是主管。把各子代理的结论合成一段话，不要新增事实。"

TASK = "知舟上那篇讲刷新令牌的文章讲了哪几种做法？它的标签有哪些？站内一共多少篇文章？"
KEYWORDS = ("滑动过期", "黑名单", "版本号", "安全", "128")

# 每个方向交回的那句话，以及单代理最后那句话。
# **两边拿到的信息一样多**——比的是「同样的工作怎么组织」，不是「谁多干了活」。
ANSWERS = {
    "做法": "三种：滑动过期、黑名单、版本号。",
    "标签": "标签：安全、后端、JWT、部署。",
    "数量": "站内共 128 篇。",
}
FULL_ANSWER = ("三种做法：滑动过期、黑名单、版本号；标签：安全、后端、JWT、部署；"
               "站内共 128 篇。")

# 三个方向：互不依赖，所以能切给三个子代理（这就是「广度优先」的可切性判据）
DIRECTIONS = (
    ("做法", "读 42 号文章，列出它讲的几种做法，每种一行", "三行要点",
     ("search_article", "read_article"), [("read_article", '{"article_id": 42}')]),
    ("标签", "查站内标签有哪几个", "一行，逗号分隔",
     ("get_tags",), [("get_tags", "{}")]),
    ("数量", "查站内一共多少篇文章", "一行，给出数字",
     ("articles",), [("articles", '{"mode":"count"}')]),
)


class Meter:
    """数每一次请求的体量：消息体与工具 schema 分开记，因为它们的归属不同。

    消息体是「上下文」，schema 是「这一次请求的固定开销」——后者随调用次数走，
    多代理调用更多，这一项就更贵。合成一个数就看不见这个区别了。
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []      # (角色, 消息体, schema)

    def count(self, role: str, messages, tools=None) -> int:
        body = 0
        for m in messages:
            body += len(ENC.encode(str(m.get("content") or "")))
            for c in m.get("tool_calls") or []:
                body += len(ENC.encode(c["function"]["name"] + c["function"]["arguments"]))
        schema = len(ENC.encode(json.dumps(tools or [], ensure_ascii=False)))
        self.calls.append((role, body, schema))
        return body + schema

    @property
    def total(self) -> int:
        return sum(b + s for _, b, s in self.calls)

    @property
    def body_total(self) -> int:
        return sum(b for _, b, _ in self.calls)

    @property
    def schema_total(self) -> int:
        return sum(s for _, _, s in self.calls)

    @property
    def peak(self) -> int:
        return max((b + s for _, b, s in self.calls), default=0)

    @property
    def peak_at(self) -> str:
        return max(self.calls, key=lambda c: c[1] + c[2])[0] if self.calls else "—"

    def stages(self) -> int:
        """串行阶段（关键路径）：这张表里唯一和「快不快」有关的一列。

        同一个角色内部的调用必须一环等一环；不同角色之间并行，所以只算最长的那个。
        """
        per: dict[str, int] = {}
        for role, _, _ in self.calls:
            per[role] = per.get(role, 0) + 1
        return max(per.values(), default=0)


def offline_transport(meter: Meter, script: list[tuple[str, str]], final: str, role: str):
    """按剧本回响应，但**请求体量是真的**。剧本用完就给最后那句答案。"""
    def transport(messages, cfg, **kw):
        meter.count(role, messages, kw.get("tools"))
        if script:
            name, arg = script.pop(0)
            return RawChat("", [ToolCall(f"c{len(meter.calls)}", name, arg)], 40)
        return RawChat(final, [], 40)
    return transport


def offline_chat(meter: Meter, role: str, script: list[tuple[str, str]], final: str = ""):
    def chat_fn(messages, **kw):
        return chat(messages, transport=offline_transport(meter, script, final, role), **kw)
    return chat_fn


def run_single() -> dict:
    """单代理：一个上下文里串行做完三件事——每多一轮，前面的工具结果就要**重发一次**。"""
    meter = Meter()
    steps: list[tuple[str, str]] = []
    for _, _, _, _, calls in DIRECTIONS:
        steps += calls
    registry = zhizhou.build(7, {})
    policy = ModelPolicy(config=Config(api_key="x"), system=SYSTEM,
                         tool_specs=registry.specs_openai(),
                         chat_fn=offline_chat(meter, "单代理", steps, FULL_ANSWER))
    tools = bind_tools(registry, run_id="single")
    started = time.monotonic()
    result = run_agent(TASK, policy, tools, Budget(max_steps=8, max_tokens=99_999))
    return {"answer": result.answer or "", "calls": len(meter.calls), "steps": result.steps,
            "meter": meter, "wall": time.monotonic() - started, "tools": registry.executed,
            "rounds": meter.stages(),
            "report": {"gaps": [], "duplicates": [], "degraded": []}}


def pad(text: str, target: int) -> str:
    """把一句话补到大约 `target` 个词元。**长度是设定的，词元数是数出来的**。

    子代理交回多长，是设计决定（官方管这叫「压缩后再交回」）；这里把它变成可调的旋钮，
    是为了让「交接单交回多长 → 主管汇总多贵」这条关系能被看见，而不是被断言。
    """
    line = "（细节：来源、边界、未确认的部分各记一行。）"
    while len(ENC.encode(text)) < target:
        text += line
    return text


def run_multi(max_workers: int = 3, synth_model: bool = False, note_tokens: int = 40) -> dict:
    """多代理：三个方向各一个子代理（自己的上下文与工具子集）＋ 一段汇总。

    `synth_model=True` 时汇总由主管再调一次模型（真机的做法）；否则用离线拼接。
    `note_tokens` 是每个子代理交回结论的目标长度——**交接单的「压缩率」就是这个旋钮**：
    压缩得狠，主管读得少；压缩得松，主管那一次调用就把省下的钱花回去。
    """
    meter = Meter()
    handoffs = [Handoff(role=role, objective=obj, deliverable=out, tools=tools,
                        boundaries="只回答自己那一条，不要顺手把别人的也查了")
                for role, obj, out, tools, _ in DIRECTIONS]
    scripts = {role: list(calls) for role, _, _, _, calls in DIRECTIONS}
    notes = {role: pad(ANSWERS[role], note_tokens) for role in ANSWERS}

    def chat_fn(messages, **kw):
        text = "\n".join(str(m.get("content") or "") for m in messages)
        role = next((r for r in scripts if f"你是「{r}」" in text), "主管汇总")
        meter.count(role, messages, kw.get("tools"))
        if role in scripts:
            script = scripts[role]
            if script:
                name, arg = script.pop(0)
                return RawChat("", [ToolCall(f"c_{role}", name, arg)], 40)
            return RawChat(notes[role], [], 40)
        return RawChat(FULL_ANSWER, [], 40)          # 汇总那一次

    synthesize = None
    if synth_model:
        def synthesize(goal, results):               # noqa: E306 —— 主语在下面一行
            reports = "\n\n".join(f"## {r.role}\n{r.answer}" for r in results)
            msgs = [{"role": "system", "content": LEAD_SYSTEM},
                    {"role": "user", "content": f"目标：{goal}\n\n各子代理结论：\n{reports}"}]
            return chat_fn(msgs).content

    started = time.monotonic()
    out = orchestrate(TASK, handoffs, config=Config(api_key="x"),
                      registry_factory=lambda names: zhizhou.build_for(7, {}, names),
                      system=SYSTEM, total_tokens=30_000, max_workers=max_workers,
                      synthesize=synthesize, chat_fn=chat_fn)
    answer = (synthesize and FULL_ANSWER) or "\n".join(notes[r.role] for r in out.results)
    return {"answer": answer, "calls": len(meter.calls), "meter": meter,
            "steps": out.lead_steps + sum(r.steps for r in out.results),
            "wall": time.monotonic() - started, "tools": [r.role for r in out.results],
            "rounds": meter.stages(), "report": out.report()}


def report(rows: list[tuple[str, dict]]) -> None:
    width = max(len(n) for n, _ in rows) + 2
    print(f"任务：{TASK}")
    print(f"依赖的事实关键词：{'、'.join(KEYWORDS)}（各行拿到的信息一样多）\n")
    head = f"{'配置':<{width}} | 模型调用 | 串行阶段 | 请求体词元 | 其中消息体 | 其中 schema | 峰值 | 覆盖"
    print(head)
    print("-" * len(head))
    for name, r in rows:
        m: Meter = r["meter"]
        covered = sum(1 for k in KEYWORDS if k in r["answer"])
        print(f"{name:<{width}} | {r['calls']:>8} | {r['rounds']:>8} | {m.total:>10} | "
              f"{m.body_total:>10} | {m.schema_total:>11} | {m.peak:>4} | "
              f"{covered}/{len(KEYWORDS)}")
    print()
    for name, r in rows:
        m: Meter = r["meter"]
        print(f"  {name}：峰值出现在「{m.peak_at}」，各次调用 "
              f"{[b + s for _, b, s in m.calls]}")

    single, multi = rows[0][1], rows[1][1]
    print()
    print("读数五句（都是这张表里的数，没有一句是估的）：")
    print(f"1. 总量：{single['meter'].total:,} → {multi['meter'].total:,}"
          f"（{multi['meter'].total / single['meter'].total - 1:+.0%}）。"
          " 单代理每一轮都要把前面的工具结果重发一次；")
    print("   多代理把它们分进三个上下文，各自只发一次。")
    print(f"2. 每次请求的固定开销（系统提示 ＋ 工具 schema）：{single['meter'].schema_total:,} "
          f"→ {multi['meter'].schema_total:,}"
          f"（{multi['meter'].schema_total / single['meter'].schema_total - 1:+.0%}）。")
    print(f"   多代理的调用次数更多（{single['calls']} → {multi['calls']}），这一项却更小——"
          "因为子代理只带自己那 1–2 个工具的 schema，")
    print("   而单代理每一次都背着全部 6 个。**工具子集既是权限边界，也是每一轮的成本**。")
    print(f"3. 峰值：{single['meter'].peak:,} → {multi['meter'].peak:,}。"
          " **峰值不由「有几份材料」决定，由最大的一份决定**——")
    print("   这里最大的一份就是那篇正文（它必须被完整读进某个上下文），切分降不下它。")
    print(f"4. 串行阶段：{single['rounds']} → {multi['rounds']}。"
          " 子代理互不等待，所以关键路径是「最长的那一个子代理」而不是「全部之和」；")
    print("   官方那个「复杂查询省 90% 时间」就是从这一列来的。汇总那一步（若调模型）要加回去。")

    synth_rows = list(rows[2:])
    if synth_rows:
        print()
        print("5. 交接单交回多长，主管那一次就多贵（这是「压缩率」这个旋钮的账）：")
        for name, r in synth_rows:
            m: Meter = r["meter"]
            lead = next((b + s for role, b, s in m.calls if role == "主管汇总"), 0)
            print(f"   {name:<24}汇总那一次 {lead:>5} 词元 ｜ 总计 {m.total:>6} 词元"
                  f"（比单代理 {m.total / single['meter'].total - 1:+.0%}）")
        print("   汇总那一次的体量 ≈ 固定部分 ＋ Σ（各份结论）：它随结论长度涨，"
              "而单代理的账里没有这一栏；")
        print("   这就是「子代理要先压缩、再交回」不是可选项的原因——省下的重发费，"
              "会从这一栏流回去。")
    print()
    print(f"档位表（官方经验值，复杂度的名字 → 子代理数、每个的工具调用上限）：{EFFORT_LADDER}")
    print("官方那组对照（Agent ≈ 4× chat，多代理 ≈ 15× chat）说的是**真机、含汇总、含重试**，")
    print("本表是离线剧本，两者不能直接相减——只能比**结构**：谁的上下文在重复，谁在并行。")


def real_single() -> int:
    """真机基线：**同一个任务**交给一个代理做，不切分、不并行、自己汇总。

    没有这一行，本章那张表就只是「两种装配的算术」；有了它，才有「同一件事
    单代理花多少、多代理花多少」的真机对照。
    """
    try:
        cfg = Config.from_env()
    except Exception as exc:                                  # noqa: BLE001
        print(f"未配置模型：{exc}")
        return 2
    print(f"模型：{cfg.redacted()}")
    registry = zhizhou.build(7, {})
    policy = ModelPolicy(config=cfg, system=SYSTEM, tool_specs=registry.specs_openai())
    tools = bind_tools(registry, run_id="real-single")
    started = time.monotonic()
    result = run_agent(TASK, policy, tools, Budget(max_steps=8, max_tokens=99_999))
    elapsed = time.monotonic() - started
    print(f"\n终止：{result.reason}｜步数 {result.steps}｜模型调用 {result.calls}｜"
          f"词元 {result.tokens}｜耗时 {elapsed:.1f}s")
    print(f"工具调用：{registry.executed}")
    print(f"\n{result.answer or '（没有答案）'}")
    covered = sum(1 for k in KEYWORDS if k in (result.answer or ""))
    print(f"\n关键词覆盖 {covered}/{len(KEYWORDS)}")
    return 0


def real(synth: bool = False, workers: int = 3) -> int:
    """真机：同一任务交给编排器跑一次（子代理各自调模型）。

    `--real --synth` 时汇总由主管再调一次模型——**那一次的词元也算给主管**，
    所以两种配置的差就是「交接单交回多长」在真机上值多少钱。
    """
    try:
        cfg = Config.from_env()
    except Exception as exc:                                  # noqa: BLE001
        print(f"未配置模型：{exc}")
        return 2
    print(f"模型：{cfg.redacted()}")
    handoffs = [Handoff(role=role, objective=obj, deliverable=out, tools=tools,
                        boundaries="只回答自己那一条，不要顺手把别人的也查了", max_steps=5)
                for role, obj, out, tools, _ in DIRECTIONS]

    synthesize = None
    if synth:
        def synthesize(goal, results):                        # noqa: E306 —— 主管那一次
            reports = "\n\n".join(f"## {r.role}\n{r.answer}" for r in results)
            messages = [{"role": "system", "content": LEAD_SYSTEM},
                        {"role": "user", "content": f"目标：{goal}\n\n各子代理结论：\n{reports}"}]
            reply = chat(messages, config=cfg)
            synthesize.spent = reply.tokens                   # type: ignore[attr-defined]
            return reply.content
        synthesize.spent = 0                                  # type: ignore[attr-defined]

    started = time.monotonic()
    out = orchestrate(TASK, handoffs, config=cfg,
                      registry_factory=lambda names: zhizhou.build_for(7, {}, names),
                      system=SYSTEM, total_tokens=40_000, max_workers=workers,
                      synthesize=synthesize)
    rep = out.report()
    print(f"\n角色：{'、'.join(rep['roles'])}｜并发上限 {workers}")
    print(f"汇总：{'主管再调一次模型' if synth else '拼接（default_synthesis，不调模型）'}")
    print(f"词元：主管 {rep['tokens']['lead']} ＋ 子代理 {rep['tokens']['sub']} "
          f"＝ {rep['tokens']['total']}")
    print(f"步数：主管 {rep['steps']['lead']} ＋ 子代理 {rep['steps']['sub']}")
    print(f"缺口：{rep['gaps'] or '无'}｜被打折：{rep['degraded'] or '无'}"
          f"｜重复：{rep['duplicates'] or '无'}")
    print()
    print(f"  {'角色':<6}{'状态':<9}{'步':>3}{'调用':>5}{'词元':>8}  交付")
    for r in out.results:
        print(f"  {r.role:<6}{r.status:<9}{r.steps:>3}{r.calls:>5}{r.tokens:>8}  "
              f"{r.answer.strip()[:34] or '—'}")
    print(f"耗时 {time.monotonic() - started:.1f}s\n")
    print(out.answer[:1_200])
    covered = sum(1 for k in KEYWORDS if k in out.answer)
    print(f"\n关键词覆盖 {covered}/{len(KEYWORDS)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--single", action="store_true", help="真机：同一个任务交给单代理（基线）")
    ap.add_argument("--synth", action="store_true", help="汇总由主管再调一次模型（真机时生效）")
    ap.add_argument("--workers", type=int, default=3, help="并发上限（真机：用来量并行到底兑不兑现）")
    args = ap.parse_args()
    if args.real:
        return real_single() if args.single else real(synth=args.synth, workers=args.workers)
    rows = [("单代理", run_single()),
            ("多代理·拼接汇总", run_multi()),
            ("多代理·主管汇总（40）", run_multi(synth_model=True, note_tokens=40)),
            ("多代理·主管汇总（300）", run_multi(synth_model=True, note_tokens=300)),
            ("多代理·主管汇总（900）", run_multi(synth_model=True, note_tokens=900))]
    report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
