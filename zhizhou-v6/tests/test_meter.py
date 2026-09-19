# tests/test_meter.py —— 不需要密钥、不需要网络：钱花在哪一栏、怎么把它降下来
"""十六组断言。这一份测的是**计量**（`app/meter.py`）。

四组最值钱：

1. **四栏之和必须等于总价**——差额只可能来自一个没报出来的加数，
   而那一栏正是「为什么贵了」的答案；
2. **长档的判据是输入规模**：命中 96.7% 之后仍然过线——缓存救不了长档，
   能救它的只有「把它裁到线以下」；
3. **同一批提示词段，只改排列**：可缓存 3,400 → 800 → 0，
   而这三份提示词的**字数几乎一样**；
4. **分桶键必须是「用户」**：换成「请求」，1,000 个人里有 964 个在一次实验里进过两边。
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.meter import (BATCH_X, CANONICAL, MIDDLE_VARIABLE, MIX, STAMP_FIRST,  # noqa: E402
                       Event, Usage, attribution, batch_plan, bill, board,
                       breakpoints, bucket, cross_users, guard, on_this_day,
                       shunt, stacked, thinking_share, tier_x, users_of, violations)
from app.registry import BY_NAME  # noqa: E402
from app.select import BY_PROFILE, call_cost, feasible  # noqa: E402

MID = "claude-sonnet-5"
TIERED = "gpt-5.6-terra"

#: 本章读数里那一笔标准的账：一次 5,000 词元的调用，其中 3,400 命中缓存，
#: 输出 1,200 里有 900 是思考块。**它在这份测试里被反复用**——
#: 四栏账、归因、叠加、看板都从它出发。
SAMPLE = Usage(uncached=400, write=0, read=3_400, out=1_200, thinking=900)


def test_四栏之和等于总价() -> None:
    """差额只可能来自一个**没报出来的加数**——而那一栏正是答案。"""
    page = bill(BY_NAME[MID], SAMPLE)
    four = page["uncached"] + page["write"] + page["read"] + page["out"]
    assert abs(four - page["full"]) < 1e-12
    assert violations(BY_NAME[MID], SAMPLE) == []


def test_思考块是输出的一部分而不是第六栏() -> None:
    """它超过输出就该被抓住——否则「思考块占比」可以大于 100%。"""
    assert thinking_share(SAMPLE) == 0.75
    assert violations(BY_NAME[MID], Usage(0, 0, 0, out=100, thinking=200)) != []


def test_命中读价不低于原价会被抓住() -> None:
    """读价一旦与原价持平，缓存就成了反的：命中越多账越大。"""
    bad = replace(BY_NAME[MID], cache_read=BY_NAME[MID].input_price)
    assert violations(bad, SAMPLE) != []


def test_这一笔的钱在输出那一栏() -> None:
    """**换一个输入便宜十倍的模型救不了它**——这是四栏账存在的理由。"""
    page = bill(BY_NAME[MID], SAMPLE)
    assert page["out"] / page["full"] > 0.88
    inputs = page["uncached"] + page["write"] + page["read"]
    assert inputs / page["full"] < 0.12


def test_归因指出涨幅最大的那一栏() -> None:
    """贵了 1.75 倍，六成落在未命中输入（前缀塌了）——它和「输出涨了」不是一个修法。"""
    spec = BY_NAME[MID]
    monday = bill(spec, SAMPLE)
    friday = bill(spec, Usage(uncached=3_800, write=0, read=0, out=1_600,
                              thinking=1_100))
    attr = attribution(friday, monday)
    assert attr["top"] == "uncached"
    assert abs(attr["top_share"] - 0.63) < 0.01
    assert abs(attr["ratio"] - 1.751) < 0.001


def test_长档的判据是输入规模而不是没命中的那部分() -> None:
    """**缓存救不了长档**：290,000 是从缓存读来的，它照样算进输入规模。"""
    spec = BY_NAME[TIERED]
    hot = Usage(uncached=10_000, write=0, read=290_000, out=8_000)
    assert hot.read / hot.input_tokens > 0.96
    assert tier_x(spec, hot.input_tokens) == (2.0, 1.5)


def test_裁到线以下是唯一能让整单掉出长档的动作() -> None:
    """裁掉 10% 的词元，账降 44%——出线的收益是裁掉比例的 4 倍以上。"""
    spec = BY_NAME[TIERED]
    hot = Usage(uncached=10_000, write=0, read=290_000, out=8_000)
    trimmed = Usage(uncached=10_000, write=0, read=260_000, out=8_000)
    assert tier_x(spec, trimmed.input_tokens) == (1.0, 1.0)
    cut_t = (hot.input_tokens - trimmed.input_tokens) / hot.input_tokens
    cut_m = (bill(spec, hot)["total"] - bill(spec, trimmed)["total"]) / bill(spec, hot)["total"]
    assert cut_m / cut_t > 4.0


def test_同一批段只改排列可缓存掉四分之三() -> None:
    """**提示词逐字相同**，差别在 diff 里看不见——它只出现在账上。"""
    assert breakpoints(CANONICAL)["cacheable"] == 3_400
    assert breakpoints(MIDDLE_VARIABLE)["cacheable"] == 800
    assert breakpoints(CANONICAL)["prompt_tokens"] == \
        breakpoints(MIDDLE_VARIABLE)["prompt_tokens"]
    assert breakpoints(CANONICAL)["cut_after"] == "工具定义"
    assert breakpoints(MIDDLE_VARIABLE)["cut_after"] == "系统提示"


def test_一个二十词元的时间戳能让三千四百个词元落空() -> None:
    """"当前时间"放在第一行是为了让它更准，而它把后面**全部**静态段都推出了缓存前缀。"""
    assert breakpoints(STAMP_FIRST)["cacheable"] == 0
    assert breakpoints(STAMP_FIRST)["prompt_tokens"] \
        - breakpoints(CANONICAL)["prompt_tokens"] == 20


def test_批量的两个百分比会给两个答案() -> None:
    """按次数 10%、按钱九成以上——「挪哪一批」不能交给「量最大的那一批」。"""
    movable = {"长稿压力画像", "整本书问答"}
    events = []
    for name, calls in MIX:
        profile = BY_PROFILE[name]
        model = min((m for m in BY_NAME.values() if feasible(m, profile)[0]),
                    key=lambda m: call_cost(m, profile)["total"]).name
        events += [Event(model=model, profile=name,
                         usage=Usage(uncached=profile.input_tokens, write=0, read=0,
                                     out=profile.output_tokens),
                         by_batch=name in movable)] * calls
    plan = batch_plan(events)
    assert abs(plan["calls_pct"] - 0.10) < 1e-9
    assert plan["money_pct"] > 0.90
    assert abs(plan["saving_pct"] - plan["money_pct"] * (1 - BATCH_X)) < 1e-9
    assert plan["saving_pct"] < plan["money_pct"], "省下的比例恰好是可挪比例的一半"


def test_叠加不是相加() -> None:
    """批量只能在「已经很小」的那个数上再减一半——预算要按还剩多少可省来分。

    而这一笔上**缓存能省的比例远小于批量**（5.9% 对 50.0%），原因不是缓存不行，
    是它的天花板：**缓存只能动输入那一栏，而这一笔的输入只占 11.0%**。
    这一条与「输出占 89.0%」是同一个读数的两面。
    """
    st = stacked(BY_NAME[MID], SAMPLE)
    assert abs(st["both"] - st["cached"] * BATCH_X) < 1e-12
    assert st["both_saving"] < st["cache_saving"] + st["batch_saving"]
    assert st["batch_saving"] > st["cache_saving"], \
        "这一笔的输出占九成：缓存能动的空间只有输入那一栏（11.0%）"
    assert st["cache_saving"] / st["plain"] < 0.11, \
        "缓存省下的比例不可能超过输入那一栏的占比"


def test_分流在这张价目表上退化成整体降档() -> None:
    """四个画像全部落在同一个候选上——所以「分流」的实体是**发现谁装不下**。"""
    got = shunt()
    assert got["distinct"] == 1
    assert got["chosen"] == ["gpt-5.6-luna"]
    assert got["saving_pct"] > 0.90
    assert not feasible(BY_NAME["claude-haiku-4-5"], BY_PROFILE["整本书问答"])[0]


def test_长档改变的是账而不是选择() -> None:
    """这张表上还没有一个候选因为长档而改变过排序——它先咬的是钱（+92.5%）。"""
    row = {r["profile"]: r for r in shunt()["rows"]}["长稿压力画像"]
    assert row["model"] == "gpt-5.6-luna"
    assert 0.90 < row["lift"] < 0.95


def test_分桶键必须是用户而不是请求() -> None:
    """按请求随机：每人 6 次里落进两边的概率 96.875%，于是 A/B 的样本单位没了。"""
    users = users_of(1_000)
    assert cross_users(users, calls_per_user=6, salt="exp-1", by="user")["crossed"] == 0
    crossed = cross_users(users, calls_per_user=6, salt="exp-1", by="call")["crossed"]
    assert abs(crossed - 968.75) < 8
    assert bucket("u0001", salt="exp-1") == bucket("u0001", salt="exp-1")


def test_看板的三个命中率会给三个答案() -> None:
    """按调用 95%、按词元三成多、按省下来的钱两成半——**它们说的是同一件事**。"""
    def events():
        out = [Event(model=MID, profile="单轮只读问答",
                     usage=Usage(0, 0, 2_400, 400, 300)) for _ in range(950)]
        out += [Event(model=MID, profile="整本书问答",
                      usage=Usage(80_000, 0, 0, 600, 200)) for _ in range(30)]
        out += [Event(model=MID, profile="整本书问答",
                      usage=Usage(80_000, 0, 0, 600, 200), ok=False, tried=2)
                for _ in range(20)]
        return out
    got = board(events())
    assert got["hit_calls"] > 0.90 and got["hit_tokens"] < 0.40
    assert got["cache_saving_share"] < got["hit_tokens"]
    assert got["failed_pct"] > 0.20, "失败的钱也是花掉的钱"
    assert got["retry_x"] > 1.0
    assert abs(on_this_day(events())["total"] - got["money"]) < 1e-9


def test_闸看的是已花加在飞而不是已结算() -> None:
    """批量通道可以晚 24 小时结算——照「已结算」做闸，闸会在超支之后才响。"""
    assert guard(64.0, 0.0, 100.0)[0] == "ok"
    assert guard(70.0, 12.0, 100.0)[0] == "warn"
    assert guard(95.0, 8.0, 100.0)[0] == "shunt"
    assert 95.0 / 100.0 < 1.0, "只看已结算，这一行会被判成「还没到」"
