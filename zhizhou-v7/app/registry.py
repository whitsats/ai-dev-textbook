"""版本与配置：一个提示词要能被指认，靠的不是「第 7 版」，是**内容戳**。

提示词与配置属于「**说了算的文本**」：改一个字，线上行为就变。它比代码更难管——
短、改起来没有成本、写它的人往往不跑发布流程。本章只做一件事：
**让「改了」这件事留下痕迹**。四件事按顺序：

1. **内容戳（`stamp`）**——把「提示词 ＋ 配置」规范化成一个字符串再取哈希。
   Git 是这一条的出处（「Git 里一切都被校验和标记过，所以任何内容的改动 Git 都不会
   不知道」），而这里要的正是那个性质：**改一个字就变，改回来又一样**。于是两件事
   立刻分开：**版本号是时间那一半**（第几版），**内容戳是内容那一半**（是哪一版）。
   线上要的是后者——因为「第 7 版」这三个字在一个仓库里指向一份文本，
   在另一个仓库里可以指向另一份；
2. **同内容连续保存不产生新版本**——复制粘贴、脚本重跑都会把同一份文本再存一次。
   一个「原样保存」出来的第 9 版会让 diff 看起来是空的、而版本列表看起来是活的：
   **版本号长了，内容没有动**；
3. **标签一次只指一版**（`label → 版本`）：发布 ＝ 把 `production` 挪到某一版，
   回滚 ＝ 挪回去。两件事都是**数据动作**，不需要重新部署——所以「回滚能不能快」
   这个问题在架构上等价于「发布是不是一次数据动作」。但它还差一半：
   官方 SDK 默认把提示词缓存在进程里、**TTL 60 秒**，所以「挪标签」到「现场真的换了」
   最坏差一个 TTL。**回滚时间不是一个数，是两项之和**（改标签 ＋ 等缓存过期）；
4. **受保护的标签**——`production` 被保护之后，成员角色改不动它，
   于是「谁能改生产」从一条约定变成一条权限。

另外两件**只有版本化之后才看得见**的事，各自也是本章的一半：

· **diff 有三条线，不止文本行**：文本行的增删、**变量集合**的增删、**配置键**的增删。
  中间那条最容易被漏掉——文本 diff 只显示「这一行改了」，而 `{{question}}` 改成
  `{{query}}` 之后调用方传的还是 `question`：**文本上是一次改动，运行上是一次缺席**；
  配置那条同理：文本一字未动、`temperature` 从 0.2 变成 0.9，只比文本的 diff 会说「没变」；
· **静默漂移**（`drift`）——现场跑的那一份与注册表里那一版的内容戳对不上，
  也就是「有人改了提示词但没换版本」。这件事在版本化之前**无法与「没改」分开**：
  线上表现变差，而版本列表一动不动。
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import dataclass, field

#: 内容戳取哈希的前多少位。12 位十六进制 ＝ 48 位：撞车概率低到可以当「就是那一份」用，
#: 而它短到能印在报表上、能贴进对话里——这一点比「理论上更安全」重要。
STAMP_LEN = 12

#: 占位符的语法（官方 SDK 的写法：`{{变量名}}`，允许中间有空格）。
PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}")

#: 角色。受保护的标签只有后两个角色能挪（官方是 admin 与 owner）。
ROLES = ("viewer", "member", "admin", "owner")
PRIVILEGED = ("admin", "owner")

#: 官方 SDK 默认把提示词缓存在进程里 60 秒、后台重新校验。**回滚要等它一次**。
DEFAULT_TTL_S = 60


def canonical(text: str, config: dict | None = None) -> str:
    """把「文本 ＋ 配置」规范化成一个字符串。**只有它稳定，内容戳才稳定。**

    三件都必须做（少一件就会造出两个戳指向同一份东西，或者一个戳指向两份）：

    · 换行统一成 `\\n`——同一份提示词在 Windows 上编辑一次就会多出 `\\r`，
      而那**是一个字符的改动**，线上行为一字不差，戳却会变；
    · 每行去尾空白——编辑器自动去掉行尾空格也是同一个陷阱；
    · 配置按键排序再序列化——`{"a": 1, "b": 2}` 与 `{"b": 2, "a": 1}`
      是同一个配置，字面不同。
    """
    body = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    payload = json.dumps(config or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"{body}\n--config--\n{payload}"


def stamp(text: str, config: dict | None = None) -> str:
    """内容戳：**只由内容决定**，与版本号、时间、作者都无关。"""
    return hashlib.sha256(canonical(text, config).encode("utf-8")).hexdigest()[:STAMP_LEN]


def placeholders(text: str) -> tuple[str, ...]:
    """文本里用到的变量，**按出现顺序去重**（顺序不是随便定的：它是阅读顺序）。"""
    seen: list[str] = []
    for name in PLACEHOLDER_RE.findall(text):
        if name not in seen:
            seen.append(name)
    return tuple(seen)


@dataclass(frozen=True)
class Version:
    """一版。**冻结的**：版本一旦存在，它的文本、配置、内容戳都不再改。"""

    name: str
    number: int
    text: str
    config: dict
    stamp: str
    author: str
    note: str = ""

    @property
    def variables(self) -> tuple[str, ...]:
        return placeholders(self.text)


@dataclass
class Diff:
    """两版之间的差，**三条线各报一栏**（只报第一条的那种 diff 会漏掉后两条）。"""

    lines_added: tuple[str, ...] = ()
    lines_removed: tuple[str, ...] = ()
    vars_added: tuple[str, ...] = ()
    vars_removed: tuple[str, ...] = ()
    config_changed: tuple[str, ...] = ()
    same_stamp: bool = False

    def silent_risk(self) -> list[str]:
        """「文本看起来没大改、但运行时会出事」的那些地方。空列表才是正常。"""
        notes: list[str] = []
        if self.vars_added:
            notes.append("新增变量：" + "、".join(self.vars_added) + "——调用方不传就是空值")
        if self.vars_removed:
            notes.append("变量消失：" + "、".join(self.vars_removed) + "——调用方还在传，而它已经没有位置了")
        if self.config_changed:
            notes.append("配置变了：" + "、".join(self.config_changed) + "——文本一字未动")
        return notes


@dataclass
class Experiment:
    """一次实验在台账里的样子。**`ends_by` 是必填**——没有失效线的实验会永远挂着。"""

    key: str
    hypothesis: str
    metric: str
    versions: tuple[int, int]
    split: float
    started: str
    ends_by: str
    owner: str

    def expired(self, today: str) -> bool:
        """`today` 与 `ends_by` 都用 `YYYY-MM-DD`，字符串比较即可（同格式定长）。"""
        return today > self.ends_by


@dataclass
class Registry:
    """版本表 ＋ 标签表 ＋ 审计流水。**标签是这棵树里唯一可变的指针。**"""

    protected: tuple[str, ...] = ("production",)
    versions: dict[str, list[Version]] = field(default_factory=dict)
    labels: dict[str, dict[str, int]] = field(default_factory=dict)
    audit: list[str] = field(default_factory=list)

    # ---------------------------------------------------------------- 保存

    def save(self, name: str, text: str, config: dict | None = None, *,
             labels: tuple[str, ...] = (), author: str = "—", note: str = "") -> tuple[Version, bool]:
        """存一版。返回 `(版本, 是否新版本)`。

        **与最新一版内容相同 → 不产生新版本**（返回已有那一版）。理由在第 2 条：
        原样保存出来的版本会让「版本多了」与「内容变了」这两件事看起来一样。
        内容等于**更早**某一版是另一回事——那是回滚，它必须产生新版本
        （线上要能看见「谁在什么时候改回去了」），而它的内容戳与那一版相同。
        """
        cfg = dict(config or {})
        new_stamp = stamp(text, cfg)
        chain = self.versions.setdefault(name, [])
        if chain and chain[-1].stamp == new_stamp:
            version, created = chain[-1], False
        else:
            version = Version(name, len(chain) + 1, text, cfg, new_stamp, author, note)
            chain.append(version)
            created = True
            self.audit.append(f"{author} 保存 {name} 第 {version.number} 版（{new_stamp}）{note}")
        for label in labels:
            self.set_label(name, label, version.number, actor=author)
        return version, created

    def number_of(self, name: str, target: str) -> int | None:
        """某个内容戳在这一串版本里是第几版（回滚的可读版本）。查不到返回 `None`。"""
        for version in self.versions.get(name, []):
            if version.stamp == target:
                return version.number
        return None

    # ---------------------------------------------------------------- 标签

    def set_label(self, name: str, label: str, number: int, *, actor: str = "—") -> None:
        """把标签挪到某一版。**这就是一次发布**（回滚是把同一个动作反过来做）。"""
        chain = self.versions.get(name, [])
        if not chain:
            raise LookupError(f"没有这个提示词：{name}")
        if not 1 <= number <= len(chain):
            raise LookupError(f"{name} 没有第 {number} 版（现有 {len(chain)} 版）")
        if label in self.protected and actor not in PRIVILEGED and actor != "—":
            raise PermissionError(f"{label} 是受保护的标签，{actor} 挪不动它（需要 {' 或 '.join(PRIVILEGED)}）")
        moved_from = self.labels.setdefault(name, {}).get(label)
        if moved_from == number:
            return                                    # 原地不动不写流水（否则审计里全是噪声）
        self.labels[name][label] = number
        self.audit.append(f"{actor} 把 {name} 的 {label} 从第 {moved_from} 版挪到第 {number} 版")

    def label_number(self, name: str, label: str = "production") -> int:
        """标签当前指向第几版。**没有这个标签就报错**，不返回默认值。"""
        table = self.labels.get(name, {})
        if label not in table:
            raise LookupError(f"{name} 上没有 {label} 标签（现有：{'、'.join(sorted(table)) or '一个都没有'}）")
        return table[label]

    def get(self, name: str, label: str = "production") -> Version:
        """按标签取一版（线上就是这么取提示词的）。"""
        return self.versions[name][self.label_number(name, label) - 1]

    def by_number(self, name: str, number: int) -> Version:
        return self.versions[name][number - 1]

    def rollback(self, name: str, label: str = "production", *, actor: str = "—", steps: int = 1) -> int:
        """回滚：把标签挪回前一版。**返回挪到第几版**（不删任何版本）。"""
        current = self.label_number(name, label)
        target = current - steps
        if target < 1:
            raise LookupError(f"{name} 的第 {current} 版前面没有版可回滚")
        self.set_label(name, label, target, actor=actor)
        return target

    def holders(self, label: str) -> dict[str, int]:
        """此刻哪些提示词的 `label` 指着哪一版——**一次一版的检查就是它**。"""
        return {name: table[label] for name, table in self.labels.items() if label in table}

    # ---------------------------------------------------------------- 比较

    def diff(self, a: Version, b: Version) -> Diff:
        """三条线一起比：文本行、变量、配置。"""
        matcher = difflib.SequenceMatcher(a=a.text.splitlines(), b=b.text.splitlines())
        added: list[str] = []
        removed: list[str] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ("replace", "delete"):
                removed.extend(a.text.splitlines()[i1:i2])
            if tag in ("replace", "insert"):
                added.extend(b.text.splitlines()[j1:j2])
        keys = set(a.config) | set(b.config)
        changed = tuple(sorted(k for k in keys if a.config.get(k) != b.config.get(k)))
        return Diff(tuple(added), tuple(removed),
                    tuple(v for v in b.variables if v not in a.variables),
                    tuple(v for v in a.variables if v not in b.variables),
                    changed, a.stamp == b.stamp)

    def drift(self, name: str, live_text: str, live_config: dict | None = None,
              label: str = "production") -> str | None:
        """现场那一份与标签指的那一版对不对得上。**一致返回 `None`。**

        对不上就是静默漂移：有人改了提示词，而版本表一动不动。它在旧世界里
        与「没改」长得完全一样——线上开始变差，而所有版本都在原处。
        """
        expected = self.get(name, label)
        seen = stamp(live_text, live_config)
        if seen == expected.stamp:
            return None
        where = self.number_of(name, seen)
        origin = (f"它是这个注册表里的第 {where} 版" if where else "这个内容戳不在注册表里")
        return (f"{name} 的现场内容戳 {seen} 与 {label} 指的 "
                f"第 {expected.number} 版（{expected.stamp}）不同——{origin}")


def alias_conflicts(mine: Registry, theirs: Registry, name: str) -> list[str]:
    """两个注册表里**同名同号而内容不同**的那些版本。

    这是「版本号会骗人」的最小形态：都说「第 3 版」，而它们不是同一份东西。
    真要回答「线上跑的是哪一份」，只能比内容戳。
    """
    bad: list[str] = []
    for version in mine.versions.get(name, []):
        other = theirs.versions.get(name, [])
        if version.number <= len(other) and other[version.number - 1].stamp != version.stamp:
            bad.append(f"{name} 第 {version.number} 版：这边 {version.stamp} ／ 那边 "
                       f"{other[version.number - 1].stamp}")
    return bad


def expired_experiments(records: list[Experiment], today: str) -> list[Experiment]:
    """过了失效线还在跑的实验。**它们每挂一天，就有一版永久留在小黑屋里。**"""
    return [r for r in records if r.expired(today)]


# ---------------------------------------------------------------- 样本
#
# 与 7.1 把 `sample_suite()` 放在 `app/suite.py` 同一个约定：**样本是模块的一部分**，
# 所以测试模块能直接拿它断言，而不必启动脚本。这一份样本是一段真的提示词
# （知舟的客服问答），四个版本之间的差是这一章要讲的四类差。

V1_TEXT = """你是知舟的客服助手，只根据下面的资料回答。
资料：
{{context}}
用户问题：{{question}}
资料里没有答案时，直接说「我没有找到相关说明」。"""

V2_TEXT = """你是知舟的客服助手，只根据下面的资料回答，不要补充资料以外的内容。
资料：
{{context}}
用户问题：{{question}}
资料里没有答案时，直接说「我没有找到相关说明」，并建议用户联系人工客服。"""

#: 第 3 版：变量改名（`question` → `query`）——**文本上是一次改动，运行上是一次缺席**。
V3_TEXT = """你是知舟的客服助手，只根据下面的资料回答，不要补充资料以外的内容。
资料：
{{context}}
用户问题：{{query}}
资料里没有答案时，直接说「我没有找到相关说明」，并建议用户联系人工客服。"""

#: 第 4 版：同一份文本配了另一个温度——**文本一字未动，行为变了**。
V4_CONFIG = {"temperature": 0.9, "max_tokens": 512}


def sample_registry() -> Registry:
    """知舟的客服提示词：四版、三个标签、一条审计流水。

    四版分别演示：**改写一句话**（v2）、**改一个变量名**（v3）、
    **同一份文本换配置**（v4）；而 `production` 停在 v2 —— 也就是说，
    v3 与 v4 都在候选状态，本章的分桶正是给它们用的。
    """
    reg = Registry()
    reg.save("zhizhou-support", V1_TEXT, {"temperature": 0.2, "max_tokens": 512},
             labels=("staging",), author="—", note="初版")
    reg.save("zhizhou-support", V2_TEXT, {"temperature": 0.2, "max_tokens": 512},
             labels=("production", "latest"), author="admin", note="补一句兜底话术")
    reg.save("zhizhou-support", V3_TEXT, {"temperature": 0.2, "max_tokens": 512},
             labels=("staging",), author="member", note="把 question 改名 query")
    reg.save("zhizhou-support", V3_TEXT, V4_CONFIG,
             labels=("canary",), author="member", note="同一份文本、换温度")
    return reg


def sample_twin() -> Registry:
    """另一个注册表（比如另一套环境）：同名 `zhizhou-support`，而第 2 版不是同一份东西。"""
    twin = Registry()
    twin.save("zhizhou-support", V1_TEXT.replace("知舟", "知舟（旧）"), {"temperature": 0.2, "max_tokens": 512},
              labels=("production",), author="—")
    twin.save("zhizhou-support", V2_TEXT.replace("不要补充", "不要编造"), {"temperature": 0.2, "max_tokens": 512},
              labels=("production",), author="—")
    return twin


def sample_experiments() -> tuple[Experiment, Experiment]:
    """一次在跑的、一次过期的。后者是本层最愿意报出来的那类东西。"""
    return (
        Experiment("support-v4-temp", "温度 0.9 让兜底话术的通过率上升", "answer_pass_rate",
                   (2, 4), 0.10, "2026-09-15", "2026-09-25", "member"),
        Experiment("support-v3-rename", "改变量名之后答得更准", "answer_pass_rate",
                   (2, 3), 0.10, "2026-08-20", "2026-09-05", "member"),
    )
