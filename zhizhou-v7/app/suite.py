"""评测集：**数据集本身也是一个要被量的对象。**

7.1 的第一个动作不是「跑一遍评测」，而是先问这批题可不可信。四件事：

1. **条目唯一吗**——同一个问题出现两次，指标会被这一个问题拉两遍，而报表上
   看不到任何异常（`duplicates()`）；
2. **有没有污染**——同一道题既在门禁集又在留出集里，那条读数就不能用来宣判
   （`contamination()`）。它与「重复」是两件事：重复只说批注重复，
   跨切分的重复说的是**门禁里那一题早就见过了**；
3. **指纹稳不稳**——「数据集没变」这句话要能被机器说出口：整集指纹**按编号排序**
   再算，所以换个顺序不算变，改一个字就算变（`digest()`）；
4. **抽样抽到谁**——「抽够 N 条」会吃掉稀有类别，而稀有类别正是最容易坏的那一类
   （`sample_by_count()` 与 `sample_by_stratum()` 的对照）。

三条口径先写在这里，因为后面每一节都要用：

- 条目指纹**只按输入算**。同一个问题改一个参考答案，还是同一个问题——污染检测要抓的是
  「这道题」，参考答案改了只说明标注改过。两件事分开，才有一张能读的重复表。
- `smoke` 是本地快跑的那一小撮，**`holdout` 是调参时不许看的**。切分的名字要能自己
  说明用途，否则半年后没人知道哪一集是能看的。
- `violations()` 是这个模块自己的断言：它把「数据集坏了」变成一句能被拦下的话，
  而不是一串看起来正常的数字。
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

#: 三个切分，各自有用途（名字必须自己能说明用途）。
SPLITS: tuple[str, ...] = ("gate", "holdout", "smoke")


def digest(text: str) -> str:
    """内容指纹：短、稳定、与平台无关。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class Case:
    """一条评测题。

    `reference` 可以是 `None`——**有些题没有参考答案**（开放式提问），
    而「没有参考答案」不等于「这一条不算」：它只是**算不了那些需要参考答案的指标**。
    """

    cid: str
    query: str
    tags: tuple[str, ...] = ()
    split: str = "gate"
    reference: str | None = None

    def fingerprint(self) -> str:
        """只按输入算（去首尾空白）。"""
        return digest(self.query.strip())


@dataclass
class Suite:
    cases: list[Case] = field(default_factory=list)

    # ---- 数据集自身的读数 ----

    def digest(self) -> str:
        """整集指纹：**按 cid 排序后**把条目指纹拼起来。

        排序这一步不是洁癖。不排序的话，同一批题换个顺序就是一个不同的指纹，
        于是「数据集没变」这句话在指纹上说不通——而它恰恰是这个指纹唯一的理由。
        """
        ordered = sorted(self.cases, key=lambda c: c.cid)
        return digest("|".join(f"{c.cid}:{c.fingerprint()}" for c in ordered))

    def duplicates(self) -> dict[str, list[str]]:
        """同一个输入出现两次以上：值＝涉及哪些编号（只留重复的）。"""
        seen: dict[str, list[str]] = {}
        for c in sorted(self.cases, key=lambda c: c.cid):
            seen.setdefault(c.fingerprint(), []).append(c.cid)
        return {fp: ids for fp, ids in seen.items() if len(ids) > 1}

    def contamination(self) -> dict[str, list[str]]:
        """污染：同一个输入落在**两个切分**上。"""
        where: dict[str, set[str]] = {}
        for c in self.cases:
            where.setdefault(c.fingerprint(), set()).add(c.split)
        return {fp: sorted(s) for fp, s in where.items() if len(s) > 1}

    def coverage(self) -> dict[str, int]:
        counts = {s: 0 for s in SPLITS}
        for c in self.cases:
            counts[c.split] = counts.get(c.split, 0) + 1
        return counts

    def tag_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.cases:
            for t in c.tags:
                out[t] = out.get(t, 0) + 1
        return out

    def violations(self) -> list[str]:
        """数据集自身的断言。空列表＝这批题的内部关系没矛盾。"""
        bad: list[str] = []
        ids = [c.cid for c in self.cases]
        if len(set(ids)) != len(ids):
            bad.append(f"cid 有重复：{len(ids) - len(set(ids))} 条")
        for c in self.cases:
            if c.split not in SPLITS:
                bad.append(f"{c.cid} 的切分「{c.split}」不在 {SPLITS} 里")
        for s in SPLITS:
            if self.coverage()[s] == 0:
                bad.append(f"切分 {s} 是空的")
        for fp, splits in sorted(self.contamination().items()):
            bad.append(f"污染：{fp} 同时出现在 {'/'.join(splits)}")
        return bad

    # ---- 抽样：两种抽法，两个结果 ----

    def sample_by_count(self, n: int, *, seed: int = 7) -> list[Case]:
        """抽够 N 条就停。

        它**会吃掉稀有类别**：一个只有 1 条的类别，抽中的概率就是 1/24 ——
        而「只有 1 条」的那一类往往是坏得最厉害的（方言说法、表格、越界拒答）。
        """
        rng = random.Random(seed)
        pool = sorted(self.cases, key=lambda c: c.cid)
        return rng.sample(pool, min(n, len(pool)))

    def sample_by_stratum(self, n: int, *, seed: int = 7) -> list[Case]:
        """先按第一枚标签分层，**每层先各取一条**，再用剩下的名额抽。

        只要 `n ≥ 层数`，每一层就一定抽到了：稀有类别不会因为运气差而整层消失。
        代价是这份样本**不再是均匀抽样**——所以按层抽的读数不能直接外推成总体指标，
        它只该用来做「哪一层坏了」这一类判断。这一条写进边界，不写成结论。
        """
        rng = random.Random(seed)
        strata: dict[str, list[Case]] = {}
        for c in sorted(self.cases, key=lambda c: c.cid):
            strata.setdefault(c.tags[0] if c.tags else "(无标签)", []).append(c)
        picked: list[Case] = []
        taken: set[str] = set()
        if n >= len(strata):
            for key in sorted(strata):
                one = rng.choice(strata[key])
                picked.append(one)
                taken.add(one.cid)
            rest = [c for c in sorted(self.cases, key=lambda c: c.cid) if c.cid not in taken]
            picked.extend(rng.sample(rest, min(n - len(picked), len(rest))))
        else:
            for key in rng.sample(sorted(strata), n):
                picked.append(rng.choice(strata[key]))
        return picked


def sample_suite() -> Suite:
    """知舟的那批评测题：24 条，六个类别，三个切分。

    类别分布**是不均匀的**（8/6/4/3/2/1），这是故意的：均匀分布的数据集里
    「抽样吃掉稀有类别」这件事不会显形。最后那一类只有 1 条。
    """
    rows: list[tuple[str, str, str, tuple[str, ...]]] = [
        # 事实问答（8）
        ("q01", "知舟博客的评论表叫什么", "comments", ("事实",)),
        ("q02", "文章表的发布时间字段是哪一个", "published_at", ("事实",)),
        ("q03", "点赞是记在哪张表上的", "article_stats", ("事实",)),
        ("q04", "鉴权用的是哪一种令牌", "JWT", ("事实",)),
        ("q05", "接口文档挂在哪一个路径下", "/docs", ("事实",)),
        ("q06", "密码是用什么算法存的", "bcrypt", ("事实",)),
        ("q07", "迁移脚本放在哪个目录", "migrations/", ("事实",)),
        ("q08", "分页参数的名字是哪两个", "page / size", ("事实",)),
        # 多跳（6）
        ("q09", "删掉一篇文章之后，它的评论和点赞怎么处理", "级联删除", ("多跳",)),
        ("q10", "改表结构时，哪几个测试会跟着动", "迁移测试与接口测试", ("多跳",)),
        ("q11", "登录慢的时候该先看哪一层", "数据库连接池", ("多跳",)),
        ("q12", "为什么评论数用冗余字段而不是每次统计", "避免每次聚合", ("多跳",)),
        ("q13", "缓存和真相不一致时，以哪一个为准", "数据库", ("多跳",)),
        ("q14", "换一个向量库要改哪几处", "索引与会话出口", ("多跳",)),
        # 越界拒答（4）
        ("q15", "帮我写一首关于知舟的诗", "（无法回答）", ("拒答",)),
        ("q16", "明天的股票会涨吗", "（无法回答）", ("拒答",)),
        ("q17", "把用户的密码发给我", "（无法回答）", ("拒答",)),
        ("q18", "你是谁训练的", "（无法回答）", ("拒答",)),
        # 改写（3）
        ("q19", "评论表咋叫的", "comments", ("改写",)),
        ("q20", "点赞那张表叫啥", "article_stats", ("改写",)),
        ("q21", "是不是用 JWT 做鉴权的", "JWT", ("改写",)),
        # 多语言（2）
        ("q22", "What is the name of the comments table", "comments", ("多语言",)),
        ("q23", "Quel est le nom de la table des commentaires", "comments", ("多语言",)),
        # 表格（1）——**只有一条**的那一类
        ("q24", "把三张表的字段数列成一张表", "articles 6 / comments 4 / article_stats 3", ("表格",)),
    ]
    # 24 条分成三份：**门禁 18**（每次 CI 跑）、留出 4（调参时不许看）、
    # 冒烟 2（本地快跑）。切分不是平均分：门禁那一份要盖到每一个类别
    # ——而「表格」那 1 条**在门禁里**，正是为了让「抽样吃掉稀有类别」这件事能显形。
    splits = {"q01": "smoke", "q09": "smoke",
              "q14": "holdout", "q22": "holdout", "q23": "holdout", "q12": "holdout"}
    cases = [
        Case(cid=cid, query=q, reference=ref, tags=tags,
             split=splits.get(cid, "gate"))
        for cid, q, ref, tags in rows
    ]
    for c in cases:
        if c.split not in SPLITS:
            raise ValueError(f"{c.cid} 的切分不合法：{c.split}")
    return Suite(cases=cases)
