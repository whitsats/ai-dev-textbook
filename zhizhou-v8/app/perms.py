"""权限与密钥：**流水线里跑着的每一行代码，权限面与 `GITHUB_TOKEN` 一样大。**

这块与 8.1 的 `runtime` 是从两侧看同一件事：8.1 量的是**容器里那个进程以什么身份在跑**
（`USER`、只读根文件系统、密钥三档），这一块量的是**流水线里那个 job 以什么身份在跑**
（`permissions:`、密钥在哪种事件下可见、`pull_request_target` 的权限面）。

四条官方口径，每条都在说「默认值站在权限更大的那一边」或者「你以为有，其实没有」：

1. **有写权限的人就能读仓库里的全部密钥。**官方原话如此——所以「密钥保管得好不好」
   不是这件事的关键，**关键是拿到写权限以后能干什么**；
2. **fork 来的 PR 拿不到密钥**（`GITHUB_TOKEN` 除外）。而更值得记住的是它的**表现方式**：
   表达式取不到密钥时的返回值是**空字符串**——那一行会带着空值跑，然后失败在一个看起来
   与服务端有关的地方。所以「配了密钥」与「这一步拿得到密钥」是两件事；
3. **OIDC 换掉的是「长期凭证」这件事本身**：不用再把云凭证复制一份到仓库里，
   换来一次性 job 的短期令牌（官方示例里 `exp − iat` ＝ **300 秒**）。
   它的使用代价只有一个，而且是必要的：**要按 job 显式声明 `id-token: write`**；
4. **三方 action 钉到完整 SHA 是目前唯一「不可变」的形式**。标签可以被移动或删除——
   这与第 6 组（镜像的钉法）是同一件事的另一个现场：**可变的引用等于把「你审过的那一版」
   交给别人保管。**

还有一条不属于权限、但同样「看不见」的：`pull_request_target` 跑在 base 上下文里，
所以它**共享 main 的缓存作用域**、可能带写 token 与密钥。官方那句
「必须不显式 checkout 不受信任的代码」说的就是它——而这一条在配置里长得很正常。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Grant:
    """一个工作流（或一个 job）的权限面。`token` 是 `GITHUB_TOKEN` 拿得到的权限。"""

    name: str
    token: tuple[str, ...]
    secrets: bool
    oidc: bool
    note: str = ""


#: 四种写法。第 1 行是「什么都不写」的两种默认值（官方给的默认可以是
#: **受控（只读）** 或 **宽松（读写）**——安全文档的建议是把它设成只读），
#: 后三行是显式声明。第四行是「按 job 提权」的写法：整个工作流只读，
#: 只有真正要访问云端的那一个 job 拿到 `id-token: write`。
GRANTS: tuple[Grant, ...] = (
    Grant("不写 permissions:（宽松默认）",
          ("contents: write", "packages: write", "pull-requests: write"), True, False,
          "一个被投毒的三方 action 可以改代码、改 workflow、推镜像"),
    Grant("不写 permissions:（受控默认）",
          ("contents: read",), True, False,
          "只读代码——但「改 workflow」这条路断了，提权链也就断了"),
    Grant("permissions: {}", (), True, False,
          "全关：token 什么都不能做（checkout 仍能读这一份代码），也因此换不到 OIDC 令牌"),
    Grant("contents: read ＋ 部署 job 的 id-token: write",
          ("contents: read",), True, True,
          "按 job 提权：写权限只活在需要它的那一个 job 里"),
    Grant("pull_request_target ＋ checkout PR 的头",
          ("contents: write", "pull-requests: write"), True, False,
          "**最危险的一格**：不受信任的代码 ＋ 写 token ＋ 密钥，三样同时在手"),
)


@dataclass(frozen=True)
class Event:
    """一种触发事件下的可见性。`secret_value` 是「取不到时得到什么」。"""

    name: str
    secrets: bool
    token_write: bool
    secret_value: str
    note: str


EVENTS: tuple[Event, ...] = (
    Event("push 到本仓", True, True, "<密钥的值>", "正常"),
    Event("同仓分支的 PR", True, True, "<密钥的值>", "正常"),
    Event("fork 来的 PR", False, False, "",
          "**密钥不传给 runner**（`GITHUB_TOKEN` 除外）；表达式取到的是空字符串"),
    Event("pull_request_target", True, True, "<密钥的值>",
          "跑在 base 上下文里，密钥与写 token 都在手——所以它不能 checkout PR 的头"),
    Event("Dependabot 触发", False, True, "",
          "官方口径：Dependabot 事件触发的工作流拿不到密钥"),
)


def blast_radius(grant: Grant) -> dict:
    """一个被投毒的三方 action 在这个权限面下能做什么（逐项问，不求和）。"""
    can = set(grant.token)
    return {
        "grant": grant.name,
        "write_code": "contents: write" in can,
        "write_workflow": "contents: write" in can,      # 改 workflow ＝ 下一次拿更多权限
        "push_image": "packages: write" in can,
        "read_secrets": grant.secrets,
        "cloud_creds": grant.oidc,
    }


def secret_value(event: Event) -> dict:
    """这一步拿到的密钥是什么——**注意它永远不会是「没有这个变量」**。"""
    return {
        "event": event.name,
        "value": event.secret_value,
        "empty": event.secret_value == "",
        "symptom": "401／403，而原因看起来像服务端的问题" if not event.secret_value else "正常",
    }


# ------------------------------------------------------- 长期凭证 vs OIDC

#: 两栏对照：谁存着它、活多久、轮换要不要人、一次泄漏的影响面。
CREDENTIALS: tuple[dict, ...] = (
    {"kind": "长期密钥（存进仓库 secret）",
     "copies": 2,                 # 云厂商一份 ＋ GitHub 一份
     "valid_seconds": 90 * 24 * 3600,
     "rotate_by": "人（到期前记得换，忘了也不报错）",
     "leak_window": "最多 90 天"},
    {"kind": "OIDC 换的短期令牌",
     "copies": 0,
     "valid_seconds": 300,        # 官方示例里 exp − iat ＝ 300 秒
     "rotate_by": "没有人：每一个 job 自己换一次",
     "leak_window": "一次 job（之后它自己过期）"},
)


# ------------------------------------------------------- 三方 action 的钉法

@dataclass(frozen=True)
class Pin:
    """一个 action 的引用方式。"""

    form: str
    mutable: bool
    note: str


PINS: tuple[Pin, ...] = (
    Pin("uses: actions/checkout@v4", True,
        "标签可以被移动、也可以被删除——你审过的那一版由别人保管"),
    Pin("uses: actions/checkout@8f4b7f8…（40 位 SHA）", False,
        "官方口径：钉到完整 SHA 是目前唯一把 action 当作不可变版本的方式"),
)
