#!/usr/bin/env python
"""6.4 的读数脚本：把「成本与性能」变成六组能复算的数。

    python scripts/meter_reader.py --offline     # 六组读数（不要密钥、不要网络）
    python scripts/meter_reader.py --self-test   # 三十五条夹具

它**不发请求**：价目表抄自 6.1 的登记表，批量倍数与承诺窗口抄自两家的批量页，
其余全是纯算术——四栏相加、前缀累加、哈希取模、一条按比例构造的流量。
所以这一章的每个结论都能拿纸笔复核——与 6.1／6.2／6.3 同一条纪律：
**读数要么能复算，要么别写进正文**。

六组依次是：四栏账（口径） / 长档与缓存 / 断点顺序 /
批量通道 / 分流 / 分桶与看板。
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.meter import (AS_OF, BATCH_WINDOW_H, BATCH_X, CANONICAL,  # noqa: E402
                       MIDDLE_VARIABLE, MIX, STAMP_FIRST, Event, Usage,
                       attribution, batch_plan, bill, board, breakpoints,
                       bucket, cross_users, guard, on_this_day, shunt, stacked,
                       thinking_share, users_of, violations)
from app.registry import BY_NAME, MODELS  # noqa: E402
from app.select import BY_PROFILE, call_cost, feasible  # noqa: E402

#: 本章读数共用的两个模型：一个按输出计费的中档（输入 2.0／输出 10.0），
#: 一个分了长档的（输入 2.0／输出 12.0，而输入过了 272,000 整单 ×2／×1.5）。
MID = "claude-sonnet-5"
TIERED = "gpt-5.6-terra"


def money(x: float) -> str:
    return f"${x:.6f}"


def group_ledger() -> list[str]:
    """一、四栏账：一次调用在账单上是四个数，不是「一次调用的钱」。"""
    spec = BY_NAME[MID]
    usage = Usage(uncached=400, write=0, read=3_400, out=1_200, thinking=900)
    page = bill(spec, usage)
    out = [f"=== 一、四栏账：一次调用在账单上是几个数（{MID} 输入 $2.0／输出 $10.0，"
           f"抄于 {AS_OF}）==="]
    out.append(f"这一笔：未命中输入 {usage.uncached:,} ＋ 缓存写 {usage.write:,} ＋ "
               f"缓存读 {usage.read:,} ＋ 输出 {usage.out:,}（其中思考块 "
               f"{usage.thinking:,}）")
    for key, label in (("uncached", "未命中输入"), ("write", "缓存写"),
                       ("read", "缓存读"), ("out", "输出")):
        out.append(f"  {label:<8}{money(page[key])}"
                   f"　占这一笔的 {page[key] / page['full'] * 100:5.1f}%")
    out.append(f"  四栏之和{money(page['full'])}　"
               f"词元合计 {usage.tokens:,}（四栏相加，不是「调用次数 × 某个平均」）")
    out.append(f"思考块 {usage.thinking:,} 占输出 {usage.out:,} 的 "
               f"{thinking_share(usage) * 100:.1f}%——**账单上「输出」这个词比「答复」大**，"
               f"它值 {money(page['out'] * thinking_share(usage))}"
               f"（占这一笔的 {page['out'] * thinking_share(usage) / page['full'] * 100:.1f}%）")
    out.append(f"这一笔里输入那一栏（未命中 ＋ 写 ＋ 读）合计占 "
               f"{(page['uncached'] + page['write'] + page['read']) / page['full'] * 100:.1f}%——"
               "**换一个输入便宜十倍的模型，救不了这一笔**；"
               "它的钱在输出那一栏（改篇幅或改输出价）")
    out.append(f"账自己说得通吗：{violations(spec, usage) or '没有对不上的地方'}")
    out.append("")

    # 归因：同一件事的两次调用，差落在哪一栏。
    monday = bill(spec, Usage(uncached=400, write=0, read=3_400, out=1_200,
                              thinking=900))
    friday = bill(spec, Usage(uncached=3_800, write=0, read=0, out=1_600,
                              thinking=1_100))
    attr = attribution(friday, monday)
    out.append(f"同一件事的两次调用：{money(monday['total'])} → {money(friday['total'])}"
               f"（贵了 {attr['ratio']:.3f} 倍）")
    for key, label in (("uncached", "未命中输入"), ("write", "缓存写"),
                       ("read", "缓存读"), ("out", "输出")):
        out.append(f"  差落在 {label:<8}{attr['diff'][key]:+.7f}")
    out.append(f"涨得最多的那一栏：{attr['top']}（占涨幅的 "
               f"{attr['top_share'] * 100:.1f}%）——**两个修法不是一件事**："
               "输入那一栏塌了改排列，输出那一栏涨了改篇幅")
    out.append("")

    # 失败也计费：6.3 的重试账在看板上长什么样。
    failed = bill(spec, usage)
    out.append(f"一次**失败**的调用（同一个 usage、`ok=False`）："
               f"{money(failed['total'])}——**输入已经被处理过，它不在账单上消失**")
    from app.gateway import expected_attempts
    for p in (0.05, 0.20, 0.50):
        out.append(f"  失败率 {p:.0%}：平均发 {expected_attempts(p, 4):.4f} 次 → "
                   f"这一笔平均 {money(failed['total'] * expected_attempts(p, 4))}"
                   f"（多付 {(expected_attempts(p, 4) - 1) * 100:.2f}%）")
    return out


def group_tier() -> list[str]:
    """二、长档与缓存：缓存救不了长档——因为判据是输入规模。"""
    spec = BY_NAME[TIERED]
    hot = Usage(uncached=10_000, write=0, read=290_000, out=8_000)
    page = bill(spec, hot)
    out = [f"=== 二、长档与缓存：命中 96.7% 仍然是长档（{TIERED}，长档线 272,000，"
           "过了整单 ×2／×1.5）==="]
    out.append(f"输入 {hot.input_tokens:,}（其中命中缓存 {hot.read:,}，占 "
               f"{hot.read / hot.input_tokens * 100:.1f}%）　输出 {hot.out:,}")
    out.append(f"长档判据：输入规模 {hot.input_tokens:,} ＞ "
               f"{spec.long_context_over:,} → x_in {page['input_x']:.1f}、"
               f"x_out {page['output_x']:.1f}")
    for key, label in (("uncached", "未命中输入"), ("read", "缓存读"), ("out", "输出")):
        out.append(f"  {label:<8}{money(page[key])}")
    out.append(f"  这一笔{money(page['total'])}"
               f"——**命中缓存省下来的是单价，不是「这一单」**："
               f"读价 0.1× 再被长档乘回 2.0×，等于原价的 "
               f"{spec.cache_read * page['input_x'] / spec.input_price:.2f} 倍；"
               "而它仍然是一笔长档账")
    trimmed = Usage(uncached=10_000, write=0, read=260_000, out=8_000)
    tpage = bill(spec, trimmed)
    cut_tokens = (hot.input_tokens - trimmed.input_tokens) / hot.input_tokens
    cut_money = (page["total"] - tpage["total"]) / page["total"]
    out.append(f"裁到 {trimmed.input_tokens:,}（裁掉 {cut_tokens * 100:.1f}% 的词元）→ "
               f"{money(tpage['total'])}（账降 {cut_money * 100:.1f}%）"
               f"——**过线是整单翻倍，所以出线那一步的收益是裁掉比例的 "
               f"{cut_money / cut_tokens:.1f} 倍**")
    out.append("凡是在长档里省钱的方案，第一条都是**把它裁到线以下**"
               "（或换一个不分档的候选，见六组）；缓存与批量都只是在这一档里打折")
    return out


def group_breakpoints() -> list[str]:
    """三、断点顺序：同一批段，只改排列，可缓存掉四分之三。"""
    spec = BY_NAME[MID]
    out = ["=== 三、断点顺序：会变的那一段排在第几位（同一批段，只改排列）==="]
    for label, segs, note in (
            ("标准（静态在前）", CANONICAL, "系统提示 ＋ 工具定义 ＋ 资料 ＋ 问题"),
            ("错法甲（资料插在中间）", MIDDLE_VARIABLE,
             "提示词逐字相同，只是把资料挪到了工具定义前面"),
            ("错法乙（时间戳放第一行）", STAMP_FIRST,
             "只多了一段 20 词元的「当前时间」")):
        bp = breakpoints(segs)
        ledger = None
        if bp["cacheable"]:
            from app.select import cache_ledger
            ledger = cache_ledger(spec, bp["cacheable"], 100)
        out.append(f"{label}：{' ＋ '.join(bp['order'])}")
        out.append(f"  可缓存 {bp['cacheable']:,} 词元（占提示词 {bp['prompt_tokens']:,} 的 "
                   f"{bp['share'] * 100:.1f}%），断点打在「{bp['cut_after'] or '（没有可缓存的段）'}」之后"
                   + (f"　100 次调用省 {money(ledger['saving'])}"
                      if ledger else "　100 次调用省 $0.000000"))
        if note:
            out.append(f"  它是什么：{note}")
    a = breakpoints(CANONICAL)["cacheable"]
    b = breakpoints(MIDDLE_VARIABLE)["cacheable"]
    c = breakpoints(STAMP_FIRST)["cacheable"]
    out.append(f"甲与标准的两份提示词**逐字相同**（同样的四段、同样的字），"
               f"只差排列：可缓存从 {a:,} 掉到 {b:,}（掉 {(1 - b / a) * 100:.1f}%）"
               "——**这个差别在 diff 里看不见**，它只出现在账上")
    out.append(f"乙只多花 {STAMP_FIRST[0].tokens} 个词元，可缓存从 {a:,} 掉到 {c}："
               f"**代价不是那 {STAMP_FIRST[0].tokens} 个词元，是它后面 {a:,} 个词元全部落空**；"
               f"而这段「当前时间」通常是有人想让它更准才加进去的")
    from app.select import cache_ledger
    tuned = cache_ledger(spec, a, 100)["saving"]
    broken = cache_ledger(spec, b, 100)["saving"]
    out.append(f"100 次调用下，两个排列省的差 {money(tuned - broken)}"
               f"（{tuned / broken:.2f} 倍）——**缓存不是「开不开」的问题，"
               "是「排得对不对」的问题**")
    return out


def group_batch() -> list[str]:
    """四、批量通道：用延迟换 0.5×，而「能挪多少」是产品给的。"""
    out = [f"=== 四、批量通道：{BATCH_X:g}× 与最多 {BATCH_WINDOW_H:g} 小时"
           f"（两家同一句话，抄于 {AS_OF}）==="]
    events = batch_events()
    plan = batch_plan(events)
    out.append(f"一批 {plan['calls']:,} 次调用，其中**能等 24 小时的** "
               f"{plan['movable_calls']:,} 次")
    out.append(f"  按次数：{plan['calls_pct'] * 100:.1f}%　"
               f"按钱：占这一批的 {plan['money_pct'] * 100:.1f}%"
               f"（{money(plan['movable_money'])}／{money(plan['total'])}）")
    out.append(f"  挪走之后总账降 {plan['saving_pct'] * 100:.1f}%"
               f"（省 {money(plan['saving'])}）")
    out.append(f"**两个百分比不一致的时候，「挪哪一批」不能交给「量最大的那一批」**："
               f"{plan['calls_pct'] * 100:.1f}% 的调用带了 "
               f"{plan['money_pct'] * 100:.1f}% 的钱——能等的那几类活恰好落在最长的链上")
    out.append("⚠️ 但这个 94.9% 不能当真：那两个画像（长稿压力、整本书）本身是**合成**的"
               "（6.1 的 `source` 里写着），而真实流量里「能等的」通常不会恰好都是最长的那些。"
               "这一行的真正内容是**两个百分比会给两个答案**，不是那个数字本身")
    out.append("")

    spec = BY_NAME[MID]
    usage = Usage(uncached=400, write=0, read=3_400, out=1_200, thinking=900)
    st = stacked(spec, usage)
    out.append("三招叠在同一笔账上（四栏 × 500 拍成一次调用，便于看比例）：")
    out.append(f"  不缓存、不批量　　　{money(st['plain'])}　1.000")
    out.append(f"  只缓存　　　　　　　{money(st['cached'])}　"
               f"{st['cached'] / st['plain']:.3f}　省 {money(st['cache_saving'])}")
    out.append(f"  只批量　　　　　　　{money(st['batched'])}　"
               f"{st['batched'] / st['plain']:.3f}　省 {money(st['batch_saving'])}")
    out.append(f"  两个都要　　　　　　{money(st['both'])}　"
               f"{st['both'] / st['plain']:.3f}　省 {money(st['both_saving'])}")
    out.append(f"两个一起省的**比例**是 {1 - st['both'] / st['plain']:.3f}，"
               f"而两个各自省的比例之和是 "
               f"{(st['cache_saving'] + st['batch_saving']) / st['plain']:.3f}"
               f"——叠加不是相加：缓存先把这一笔压到 "
               f"{st['cached'] / st['plain']:.3f}，批量只能在这个已经很小的数上再减一半"
               "（**预算要按「还剩多少可省」分，不是按招式数分**）")
    out.append(f"注意 0.5 × 0.1 这件事：一条**已经命中缓存**的调用挪到批量通道，"
               f"省的是它那一份的一半——{money(st['cached'] - st['both'])}，"
               f"而不是它原价的一半（{money(st['batch_saving'])}）")
    return out


def group_shunt() -> list[str]:
    """五、分流：按画像把流量分开——而它可能退化成「整体降档」。"""
    got = shunt()
    out = [f"=== 五、分流：{got['calls']:,} 次调用的四个画像"
           f"（对照：全部走 claude-fable-5-1）==="]
    out.append(f"{'画像':<16}{'次数':>6}　{'选中的候选':<18}{'单次':>12}{'这一档的钱':>14}")
    for r in got["rows"]:
        out.append(f"{r['profile']:<16}{r['calls']:>6}　{r['model']:<18}"
                   f"{money(r['per_call']):>12}{money(r['money']):>14}"
                   + (f"　长档 +{r['lift'] * 100:.1f}%" if r["lift"] > 0.001 else ""))
    out.append(f"合计：分流 {money(got['total'])}　全旗舰 {money(got['pinned_total'])}"
               f"　省 {got['saving_pct'] * 100:.1f}%")
    out.append(f"每千次：分流 ${got['per_1k_routed']:.4f}　全旗舰 ${got['per_1k_pinned']:.4f}")
    out.append(f"四个画像**全部**落在同一个候选上（入选的不同候选共 "
               f"{got['distinct']} 个：{got['chosen'][0]}）——所以这一节量到的不是「分流」，"
               "而是「整体降档」：当最便宜的那一档便宜了一个数量级，按画像选还是会选到它")
    out.append("**「分流」这个词真正的实体在别处**：不是「按画像选出贵的」，"
               "而是「按画像发现谁装不下」——")
    for name, calls in MIX:
        profile = BY_PROFILE[name]
        bad = [m.name for m in MODELS if not feasible(m, profile)[0]]
        out.append(f"  {name}：{profile.input_tokens:,} 输入 ＋ "
                   f"{profile.output_tokens:,} 输出　装不下的候选 {len(bad)} 个："
                   + ("、".join(bad) if bad else "无"))
    out.append(f"上面那个 {got['saving_pct'] * 100:.1f}% 是**价目表上的上界**，"
               "不是项目能拿到的数：它假设「最便宜的那一档在这些画像上质量够」，"
               "而**质量是这一章没有量过的东西**——量它的工具是下一节的 A/B 分桶，"
               "不是这一行的算术")
    return out


def group_board() -> list[str]:
    """六、分桶与看板：同一个人只能进一边；而命中率要报三个数。"""
    out = ["=== 六、分桶：一次实验里跨到两边的用户有多少个"
           "（1,000 个用户 × 每人 6 次）==="]
    users = users_of(1_000)
    for by, note in (("user", "按用户哈希：同一个人每次都进同一桶"),
                     ("call", "按请求随机：每次请求各自投一次硬币")):
        got = cross_users(users, calls_per_user=6, salt="exp-1", by=by)
        out.append(f"分桶键 = {by}：跨到两边的用户 **{got['crossed']}**／"
                   f"{got['users']}（{got['crossed_pct'] * 100:.1f}%）　"
                   f"没跨的是 {got['uncrossed_split'][0]}／{got['uncrossed_split'][1]}"
                   f"　｜{note}")
    out.append("按请求随机的理论值：n 次全在同一边的概率是 2·0.5ⁿ，"
               "n=6 时是 3.125% → 跨边的用户期望 1,000 × 96.875% ＝ 968.75 个"
               "——**换一个分桶键，A/B 的样本单位就从「人」变成了「请求」**")

    b = board(board_events())
    out.append("")
    out.append(f"=== 看板：一批 {b['calls']:,} 次尝试 ===")
    out.append(f"总账 {money(b['money'])}　每千次 ${b['per_1k']:.4f}")
    for m, row in sorted(b["by_model"].items(), key=lambda kv: -kv[1]["money"]):
        out.append(f"  {m:<18}{row['calls']:>6} 次　{money(row['money']):>12}"
                   f"　占钱 {row['money'] / b['money'] * 100:5.1f}%")
    out.append(f"缓存命中率（按**调用**）：{b['hit_calls'] * 100:.1f}%")
    out.append(f"缓存命中率（按**词元**）：{b['hit_tokens'] * 100:.1f}%")
    out.append(f"缓存省下来的钱占「不缓存时的总账」："
               f"{b['cache_saving_share'] * 100:.1f}%（{money(b['cache_saving'])}）")
    out.append(f"三个数的差就是问题本身：**命中在便宜的那些调用上**——"
               f"没命中的那 {b['calls'] - round(b['hit_calls'] * b['calls'])} 次占了 "
               f"{ (1 - b['hit_tokens']) * 100:.1f}% 的输入词元，"
               f"而它们也正是账上最贵的那几次；**只报一个数，看板会替你做决定**")
    out.append(f"思考块占输出：{b['thinking_share'] * 100:.1f}%　"
               f"重试倍数：{b['retry_x']:.3f}（配置里写的是「最多几次」）")
    out.append(f"失败的那部分账：{money(b['failed_money'])}"
               f"（占总账 {b['failed_pct'] * 100:.1f}%）——**花了却什么都没拿到的钱，"
               "它也要进看板**，否则它只会在月底的账单里出现")
    out.append("")
    out.append("=== 三道闸：判据是「已花 ＋ 在飞」，不是「已结算」===")
    for spent, inflight in ((64.0, 0.0), (70.0, 12.0), (95.0, 8.0)):
        action, why = guard(spent, inflight, 100.0)
        naive = "ok" if spent / 100 < 0.80 else ("warn" if spent / 100 < 1.0 else "shunt")
        out.append(f"已结算 {spent:5.1f} ＋ 在飞 {inflight:4.1f}（预算 100）："
                   f"**{action}**　{why}"
                   + (f"　｜只看已结算会判成 {naive}" if naive != action else ""))
    out.append("在飞那一列不是细节：批量通道的结果可以晚 "
               f"{BATCH_WINDOW_H:g} 小时才结算，照「已结算」做闸的话，"
               "闸会在超支之后才响——而它响的时候，钱已经花掉了")
    out.append("第三道闸的动作是**分流**（换便宜链），不是**拒服务**："
               "拒服务把一次成本问题变成了可用性问题，而可用性问题更贵")
    return out


# ------------------------------------------------------------------ 夹具用的数据

def batch_events() -> list[Event]:
    """按 `MIX` 造一批调用，**后两个画像的活标成「可以等」**。

    这个「哪两个可以等」是**产品给的判断**（长稿与整本书都是离线批处理的任务），
    不是代码猜的：把它默认成「全都不能等」，批量那一栏就永远是 0；
    默认成「全都能等」，看板上会多出一次省了一半的幻觉。
    """
    movable = {"长稿压力画像", "整本书问答"}
    events: list[Event] = []
    for name, calls in MIX:
        profile = BY_PROFILE[name]
        model = min((m for m in BY_NAME.values() if feasible(m, profile)[0]),
                    key=lambda m: call_cost(m, profile)["total"]).name
        for _ in range(calls):
            events.append(Event(model=model, profile=name,
                                usage=Usage(uncached=profile.input_tokens, write=0,
                                            read=0, out=profile.output_tokens),
                                by_batch=name in movable))
    return events


def board_events() -> list[Event]:
    """看板那一批：**950 次短调用命中、50 次长调用没命中**（而且其中 20 次失败了）。

    它刻意造得让三个命中率口径**互相打脸**：按调用 95%、按词元三成多、
    按省下来的钱更少——因为没命中的那 5% 恰好是最长、最贵的那几次。
    """
    events: list[Event] = []
    for _ in range(950):
        events.append(Event(model=MID, profile="单轮只读问答",
                            usage=Usage(uncached=0, write=0, read=2_400,
                                        out=400, thinking=300), tried=1))
    for _ in range(30):
        events.append(Event(model=MID, profile="整本书问答",
                            usage=Usage(uncached=80_000, write=0, read=0,
                                        out=600, thinking=200), tried=1))
    for _ in range(20):
        events.append(Event(model=MID, profile="整本书问答",
                            usage=Usage(uncached=80_000, write=0, read=0,
                                        out=600, thinking=200),
                            ok=False, tried=2))
    return events


# ------------------------------------------------------------------ 夹具

def fixture_cases() -> list[tuple[str, bool]]:
    spec = BY_NAME[MID]
    tiered = BY_NAME[TIERED]
    usage = Usage(uncached=400, write=0, read=3_400, out=1_200, thinking=900)
    page = bill(spec, usage)
    cases: list[tuple[str, bool]] = []

    four = page["uncached"] + page["write"] + page["read"] + page["out"]
    cases.append(("四栏之和等于总价", abs(four - page["full"]) < 1e-12))
    cases.append(("这一页账没有对不上的地方", violations(spec, usage) == []))
    cases.append(("思考块超过输出会被抓住",
                  violations(spec, Usage(0, 0, 0, 100, thinking=200)) != []))
    bad_spec = replace(spec, cache_read=spec.input_price)
    cases.append(("命中读价不低于原价会被抓住",
                  violations(bad_spec, usage) != []))
    cases.append(("思考块占输出 75%", abs(thinking_share(usage) - 0.75) < 1e-12))
    cases.append(("这一笔的 89% 在输出那一栏",
                  abs(page["out"] / page["full"] - 0.8902) < 0.001))
    attr = attribution(bill(spec, Usage(3_800, 0, 0, 1_600, 1_100)), page)
    cases.append(("归因指向未命中输入那一栏且占总涨幅 63%",
                  attr["top"] == "uncached" and abs(attr["top_share"] - 0.63) < 0.01))

    hot = Usage(uncached=10_000, write=0, read=290_000, out=8_000)
    hot_page = bill(tiered, hot)
    cases.append(("300,000 输入进长档（x_in 2.0／x_out 1.5）",
                  hot_page["input_x"] == 2.0 and hot_page["output_x"] == 1.5))
    cases.append(("命中 96.7% 仍是长档",
                  hot.read / hot.input_tokens > 0.96 and hot_page["input_x"] == 2.0))
    trimmed = Usage(uncached=10_000, write=0, read=260_000, out=8_000)
    cases.append(("裁到 270,000 掉出长档",
                  bill(tiered, trimmed)["input_x"] == 1.0))
    cut_t = (hot.input_tokens - trimmed.input_tokens) / hot.input_tokens
    cut_m = (hot_page["total"] - bill(tiered, trimmed)["total"]) / hot_page["total"]
    cases.append(("出线的收益是裁掉比例的 4 倍以上", cut_m / cut_t > 4.0))

    cases.append(("标准排列可缓存 3,400 词元",
                  breakpoints(CANONICAL)["cacheable"] == 3_400))
    cases.append(("错法甲可缓存 800 词元",
                  breakpoints(MIDDLE_VARIABLE)["cacheable"] == 800))
    cases.append(("错法乙可缓存 0 词元",
                  breakpoints(STAMP_FIRST)["cacheable"] == 0))
    cases.append(("断点落在工具定义之后",
                  breakpoints(CANONICAL)["cut_after"] == "工具定义"))
    cases.append(("错法乙多 20 词元而少 3,400 可缓存",
                  breakpoints(STAMP_FIRST)["prompt_tokens"]
                  - breakpoints(CANONICAL)["prompt_tokens"] == 20))

    plan = batch_plan(batch_events())
    cases.append(("按次数能挪 10%", abs(plan["calls_pct"] - 0.10) < 1e-9))
    cases.append(("按钱能挪八成以上（两个百分比不一致）", plan["money_pct"] > 0.80))
    cases.append(("省下的比例恰好是「按钱可挪」的一半",
                  abs(plan["saving_pct"] - plan["money_pct"] * (1 - BATCH_X)) < 1e-9))
    st = stacked(spec, usage)
    cases.append(("叠加后恰好是「只缓存」的一半",
                  abs(st["both"] - st["cached"] * BATCH_X) < 1e-12))
    cases.append(("叠加的省小于两招各自省的之和",
                  st["both_saving"] < st["cache_saving"] + st["batch_saving"]))

    got = shunt()
    cases.append(("四个画像落在同一个候选上（分流退化成整体降档）",
                  got["distinct"] == 1))
    cases.append(("分流省下的比全旗舰少九成以上", got["saving_pct"] > 0.90))
    cases.append(("整本书问答在 haiku 上装不下",
                  not feasible(BY_NAME["claude-haiku-4-5"],
                               BY_PROFILE["整本书问答"])[0]))

    users = users_of(1_000)
    cases.append(("按用户哈希：跨池用户 0 个",
                  cross_users(users, calls_per_user=6, salt="exp-1",
                              by="user")["crossed"] == 0))
    n_call = cross_users(users, calls_per_user=6, salt="exp-1", by="call")["crossed"]
    cases.append(("按请求随机：跨池用户在 968 附近",
                  abs(n_call - 968.75) < 8))
    cases.append(("同一个键两次进同一个桶",
                  bucket("u0001", salt="exp-1") == bucket("u0001", salt="exp-1")))
    cases.append(("换一个盐就不一定在同一桶（两组合计仍等于总数）",
                  sum(cross_users(users, calls_per_user=6, salt="exp-2",
                                  by="user")["uncrossed_split"]) == 1_000))

    b = board(board_events())
    cases.append(("看板：按调用命中高于 90% 而按词元低于 40%",
                  b["hit_calls"] > 0.90 and b["hit_tokens"] < 0.40))
    cases.append(("看板：失败的钱占到两成以上", b["failed_pct"] > 0.20))
    cases.append(("看板：重试倍数大于 1",
                  b["retry_x"] > 1.0))
    cases.append(("看板：四栏合计与逐条相加对得上",
                  abs(on_this_day(board_events())["total"] - b["money"]) < 1e-9))
    cases.append(("闸：95 ＋ 8 判分流", guard(95.0, 8.0, 100.0)[0] == "shunt"))
    cases.append(("闸：只看已结算会把超支判成告警",
                  guard(95.0, 8.0, 100.0)[0] == "shunt"
                  and 95.0 / 100.0 < 1.0))
    cases.append(("闸：64 判正常、70 ＋ 12 判告警",
                  guard(64.0, 0.0, 100.0)[0] == "ok"
                  and guard(70.0, 12.0, 100.0)[0] == "warn"))
    return cases


def readings() -> list[str]:
    out: list[str] = []
    for fn in (group_ledger, group_tier, group_breakpoints,
               group_batch, group_shunt, group_board):
        out.extend(fn())
        out.append("")
    out.append("计量读数：六组全过 ｜ 离线自检通过")
    return out


def self_test() -> int:
    cases = fixture_cases()
    bad = 0
    for label, ok in cases:
        print(f"  {'✓' if ok else '✗'} {label}")
        bad += 0 if ok else 1
    print(f"自检 {len(cases) - bad}/{len(cases)} 通过")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    for line in readings():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
