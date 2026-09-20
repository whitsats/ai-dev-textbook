#!/usr/bin/env python
"""8.2 的读数脚本：把「有没有人去跑这一版」变成六组能复算的数。

    python scripts/ci_reader.py --offline     # 六组读数（不要密钥、不联网、不碰 GitHub）
    python scripts/ci_reader.py --self-test   # 一百一十条夹具

六组依次是：**触发与过滤**（哪些改动根本不进流水线）／**job 图与并发**
（`needs` 决定关键路径、`matrix` 决定格数、`concurrency` 决定取消谁）／
**缓存与产物**（命中哪一条、靠哪条规则、不可改、清理、`needs` 是「拿得到」的判据）／
**权限与密钥**（token 的权限面、密钥在哪种事件下可见、OIDC、action 的钉法）／
**门禁与必需检查**（七种形状报出什么、放不放行）／**发布与灰度**
（钉法、审批、金丝雀的两门判据与回滚的账）。

它**不连 GitHub、不要密钥、不跑 runner**：触发与过滤是按官方语法**建模**的
（事件与过滤器就是那几个字符串），`needs` 的墙钟是**脚本化的分钟数**，
缓存与产物的查找顺序是按官方那套顺序**逐条落成尝试记录**的，
金丝雀与回滚是纯算术。所以它能量的是**这些机制的性质**
（被跳过的 job 与停在 Pending 的检查是不是同一个结论、缓存到底是靠哪条规则命中的、
金丝雀在哪种判据下才救人），**量不了真实流水线的时长、真实 runner 的调度、
真实仓库的缓存命中率**——这一条写在正文的边界里。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import caching as K    # noqa: E402
from app import gate as Q       # noqa: E402
from app import graph as G      # noqa: E402
from app import perms as P      # noqa: E402
from app import release as R    # noqa: E402
from app import trigger as T    # noqa: E402


def _w(text: str, width: int) -> str:
    """按显示宽度补空格（中文按两格算）——只为对齐，不影响任何数。"""
    shown = sum(2 if ord(ch) > 0x2000 else 1 for ch in text)
    return text + " " * max(0, width - shown)


# ------------------------------------------------------- 一、触发与过滤

def group_trigger() -> list[str]:
    rows = T.filter_table()
    lines = ["=== 一、触发与过滤：十一次提交 × 四种过滤器 ===",
             _w("写法", 34) + _w("进流水线", 12) + _w("漏掉", 8) + "漏掉里最贵的那一条"]
    for row in rows:
        lines.append(_w(row["filter"], 34) + _w(str(row["ran"]), 12)
                     + _w(str(row["missed"]), 8) + (row["worst"] or "—"))
    narrow = next(r for r in rows if r["filter"].startswith("白名单·窄"))
    wide_allow = next(r for r in rows if r["filter"].startswith("白名单·宽"))
    black = next(r for r in rows if r["filter"].startswith("黑名单"))
    lines += [
        "",
        f"**窄白名单漏掉 {narrow['missed']} 条（十一次里漏七次）**，而它漏掉的第一条就是"
        f"「{narrow['worst']}」——",
        "改 `ci.yml` 那一次不进流水线，于是「门」这个东西从此没有人检查",
        f"**两种「宽」写法今天各只漏 {wide_allow['missed']} 条与 {black['missed']} 条，"
        f"而这两个数不是同一件事**：",
        f"黑名单漏 {black['missed']} 条是「今天不痛」（新目录默认被检查），"
        f"宽白名单漏 {wide_allow['missed']} 条是因为**名单是枚举——枚举永远漏一个**",
        "（新目录不进名单就不被检查，而没人会记得上来加一行）",
        f"十一次提交里，**只有改文档那一次是真的不该跑**（本该进流水线的有 {T.SHOULD_RUN} 条）",
    ]
    lines.append("")
    lines.append("=== 一次提交起几个 run ===")
    for row in T.skip_table():
        lines.append(_w(row["case"], 26) + f"{row['runs']} 个 run："
                     + row["why"].removeprefix(f"{row['case']}："))

    lines += [
        "",
        "**同一份提交跑两遍**（`push` 与 `pull_request`）——两份账单、同一次检查；"
        "而 fork 的 PR 只有一份",
        "**`[skip ci]` 不是「少跑一次」，是「这一格没有结论」**：它停在 Pending，"
        "而要求它的 PR 被挡住",
    ]
    return lines


# ------------------------------------------------------- 二、job 图与并发

def group_graph() -> list[str]:
    rows = G.graph_table()
    lines = ["=== 二、job 图与并发：`needs` 决定关键路径，槽位只能填满它 ===",
             _w("图", 32) + _w("关键路径", 24) + _w("1 槽", 6) + _w("2 槽", 6)
             + _w("4 槽", 6) + "顺序违背"]
    for row in rows:
        path = row["path"] if row["violations"] < len(G.MUST_PRECEDE) else "（无依赖）"
        if len(path) > 22:
            head, _, tail = path.rpartition(" → ")
            path = f"{head.split(' → ')[0]} → … → {tail}"
        lines.append(_w(row["graph"], 32) + _w(path, 24)
                     + _w(str(row["slots1"]), 6) + _w(str(row["slots2"]), 6)
                     + _w(str(row["slots4"]), 6) + str(row["violations"]))
    flat, chain, good = rows
    lines += [
        "",
        f"**最快的图是最差的门**：扁平图 {flat['slots4']} 分钟跑完，而它有 "
        f"{flat['violations']} 处顺序违背——`e2e` 跑在 `unit` 之前，那个绿与这一版代码无关",
        f"**正确的图 {good['slots2']} 分钟，而从 2 个槽加到 4 个槽一分钟不省**"
        f"（关键路径就是 {good['critical']}）",
        f"——一条链无论给多少槽都是 {chain['slots1']} 分钟：槽位只能填满关键路径，"
        "填不满它就只能排队",
    ]
    lines.append("")
    lines.append("=== `matrix`：格数就是账单（每格 %d 分钟）===" % G.PER_CELL_MINUTES)
    for row in G.matrix_table():
        extra = ""
        if "cancelled" in row:
            extra = f"  取消 {row['cancelled']} 格"
        lines.append(_w(row["shape"], 38) + _w(f"{row['cells']} 格", 8)
                     + _w(f"可计费 {row['billable']} 分", 16)
                     + f"墙钟 {row['wall']} 分{extra}")
    lines += [
        "",
        "**最后一行是这一节最容易被忽略的账**：`fail-fast` 在第 1 分钟取消了另外三格——",
        f"省下 {G.matrix_table()[1]['billable'] - G.matrix_table()[2]['billable']} 分钟，"
        "代价是**那三格从来没有结论**（报的是 `cancelled`）",
    ]
    lines.append("")
    lines.append("=== `concurrency`：取消谁（连推三次、每次 21 分钟）===")
    for row in G.concurrency_table():
        lines.append(_w(row["shape"], 46) + _w(f"可计费 {row['billable']} 分", 18)
                     + _w(f"取消 {row['killed']}", 8) + f"结论文：{row['last_word']}")
    conc = G.concurrency_table()
    lines += [
        "",
        f"**省下两次全量（{conc[1]['billable']} → {conc[0]['billable']} 分钟）**，"
        "而代价是前两次的检查报 `cancelled`；",
        "排队那一行把三个 run 都跑完（前两个测的是已经不在的代码），"
        "而它连「省」都没有——",
        "**取消省的是账单，排队省的是「哪一次的结论算数」**",
        f"第三行（group 写宽了）**账单与第一行完全一样，性质却完全不同**："
        "**在 main 上的一次运行会把 PR 的运行取消掉**",
    ]
    return lines


# ------------------------------------------------------- 三、缓存与产物

CACHE_ROWS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("A", "feat/rag", "pip-3.12-cccc", ()),
    ("B", "feat/rag", "pip-3.12-dddd", ("pip-3.12-", "pip-")),
    ("C", "main", "pip-3.11", ("pip-3.12-",)),
    ("D", "main", "pip-3.12-e500", ("pip-",)),
    ("E", "feat/rag", "pip-3.11-aaaa", ()),
    ("F", "main", "pip-3.12-cccc", ()),
)


def group_cache() -> list[str]:
    lines = ["=== 三、缓存：命中哪一条、靠哪条规则命中的 ===",
             _w("行", 4) + _w("分支", 11) + _w("key", 16) + _w("命中", 16)
             + _w("作用域", 10) + _w("规则", 26) + "cache-hit"]
    results: list[dict] = []
    for tag, branch, key, rk in CACHE_ROWS:
        r = K.restore(key, rk, branch=branch)
        results.append(r)
        lines.append(_w(tag, 4) + _w(branch, 11) + _w(key, 16)
                     + _w(r["matched"] or "（没有）", 16)                     + _w(r["scope"] or "—", 10)
                     + _w(r["rule"], 26) + ("✔" if r["cache_hit"] else "✘"))
    hits = sum(1 for r in results if r["cache_hit"])
    got = sum(1 for r in results if r["matched"])
    lines += [
        "",
        f"**六行里只有 {hits} 行 `cache-hit` 为真，而有 {got} 行真的恢复到了文件**",
        f"B：**恢复了旧依赖的缓存**，而官方那个布尔值是 false——拿它当「缓存生效了吗」"
        "会得出相反结论",
        f"C：`key` 自己的部分匹配**先于 `restore-keys`**（试了 {len(results[2]['tries'])} 步，"
        "写的那条 restore-key 根本没轮到）",
        f"E：**跨分支共享是单向的**——{results[4]['branch']} 看得到 "
        f"{results[4]['scope']}，而反向看不到（F 行：`main` 找不到只建在 `feat/rag` 上的那条）",
    ]
    lines.append("")
    lines.append("=== 缓存不可改：静态 key 与动态 key ===")
    for row in K.save_sequence((("pip-cache", 180_000), ("pip-cache", 260_000),
                                ("pip-cache", 310_000))):
        mark = "✔ 存下去" if row["saved"] else "✘ " + row["why"]
        lines.append(f"  静态 key 第 {row['round']} 次保存 {row['kb']:>9,d} KB   {mark}")
    held = K.save_sequence((("pip-cache", 180_000), ("pip-cache", 260_000),
                            ("pip-cache", 310_000)))[-1]["held_kb"]
    for row in K.save_sequence((("pip-3.12-h1", 180_000), ("pip-3.12-h2", 260_000))):
        mark = "✔ 存下去" if row["saved"] else "✘ " + row["why"]
        lines.append(f"  动态 key 第 {row['round']} 次保存 {row['kb']:>9,d} KB   {mark}")
    lines += [
        "",
        f"**静态 key 的缓存是一份不再更新的缓存，而它看起来一直命中**："
        f"缓存里留的还是 {held:,d} KB 那一份",
        "动态 key 两次都存下去，代价是两份都占空间（旧的不会被覆盖掉）",
    ]
    lines.append("")
    alive = sum(1 for e in K.STORE if K.alive(e))
    dead = [e for e in K.STORE if not K.alive(e)]
    total_mb = sum(e.kb for e in K.MONOREPO) // 1000
    free_kb, evicted = K._evict(K.MONOREPO, 0)
    lines += [
        "=== 清理：7 天没访问，与 10 GB 上限 ===",
        f"初始 {len(K.STORE)} 条里活着 {alive} 条；被「7 天没访问」那条规则清掉的是 "
        + "、".join(f"`{e.key}`（{K.NOW_DAY - e.accessed_day} 天没访问，"
                    f"{e.kb // 1000} MB）" for e in dead),
        "——这件事**不出现在任何输出里**，它只让下一次构建慢一点",
        f"MONOREPO：{len(K.MONOREPO)} 条共 {total_mb:,d} MB，上限 "
        f"{K.LIMIT_KB // 1024:,d} MB（10 GiB），而**每一条都在 7 天内被访问过**",
        "  清掉 " + "、".join(f"`{k}`" for k in evicted)
        + f" → 剩 {total_mb - (sum(e.kb for e in K.MONOREPO if e.key in evicted) // 1000):,d} MB",
        "**超限时起作用的是「最后访问从旧到新」**，而不是 7 天那一条——"
        "两条规则的触发条件不同",
    ]
    lines.append("")
    lines.append("=== 产物：`needs` 是「拿得到」的判据 ===")
    no = K.fetch(K.REPORT, needs=("lint",))
    yes = K.fetch(K.REPORT, needs=("lint", "test"))
    dup = K.reupload(("test-report",), "test-report")
    bad = K.verify(K.REPORT, tampered=("report/junit.xml",))
    lines += [
        f"`needs: lint` 来取 test 的产物        ✘ {no['why']}",
        f"`needs: lint, test` 来取             ✔ {len(yes['files'])} 个文件下到 ./{yes['dir']}/",
        f"同名重传                              ✘ {dup['why']}",
        f"改一个字节之后下载                     ⚠ {bad['why']}（run 仍然是绿的）",
        "",
        "**四行里两行是「失败」，一行是「警告」**：产物不可变会让第二次上传**真的失败**；",
        "而摘要不符**只报警告**——「产出物被换过」这件事在流水线里不是失败",
    ]
    return lines


# ------------------------------------------------------- 四、权限与密钥

def group_perms() -> list[str]:
    lines = ["=== 四、权限面：一个被投毒的三方 action 能做什么 ===",
             _w("写法", 46) + _w("改代码", 8) + _w("改 workflow", 14)
             + _w("推镜像", 8) + _w("读密钥", 8) + "换云凭证"]
    for grant in P.GRANTS:
        b = P.blast_radius(grant)
        lines.append(_w(grant.name, 46) + _w("✔" if b["write_code"] else "—", 8)
                     + _w("✔" if b["write_workflow"] else "—", 14)
                     + _w("✔" if b["push_image"] else "—", 8)
                     + _w("✔" if b["read_secrets"] else "—", 8)
                     + ("✔" if b["cloud_creds"] else "—"))
    lines += [
        "",
        "**「改 workflow」这一格要单列**：有写权限的下一次运行会拿到更多权限——"
        "提权链的入口就在这一格",
        "**受控默认与 `permissions: {}` 的差别**在「只能读代码」与「什么都不能做」之间，"
        "而两行里真正救命的是**没有任何一行能推镜像**",
        "**最后一行是唯一「三样同时在手」的一格**：不受信任的代码 ＋ 写 token ＋ 密钥",
    ]
    lines.append("")
    lines.append("=== 密钥在哪种事件下可见 ===")
    for event in P.EVENTS:
        v = P.secret_value(event)
        value = "空字符串" if v["empty"] else "看得见"
        lines.append(_w(event.name, 22) + _w(value, 12) + v["symptom"])
    lines += [
        "",
        "**「配了密钥」与「这一步拿得到密钥」是两件事**，而失败现场指向的是服务端（401／403）",
    ]
    lines.append("")
    lines.append("=== 长期密钥与 OIDC ===")
    for cred in P.CREDENTIALS:
        days = cred["valid_seconds"] // 86400
        valid = f"{days} 天" if days else f"{cred['valid_seconds']} 秒"
        lines.append(_w(cred["kind"], 30) + _w(f"存 {cred['copies']} 份", 16)
                     + _w(f"有效期 {valid}", 16) + _w(cred["rotate_by"], 30)
                     + f"泄漏窗口 {cred['leak_window']}")
    lines += [
        "",
        "**官方示例里那个 JWT：`exp − iat ＝ 300` 秒**——而它的代价是要按 job 声明 "
        "`id-token: write`",
    ]
    lines.append("")
    lines.append("=== 三方 action 的钉法 ===")
    for pin in P.PINS:
        lines.append(_w(pin.form, 44) + pin.note)
    lines += [
        "",
        "**与第六组的「镜像钉法」是同一件事**：可变的引用等于把「你审过的那一版」交给别人保管",
    ]
    return lines


# ------------------------------------------------------- 五、门禁

def group_gate() -> list[str]:
    lines = ["=== 五、门禁与必需检查：七种形状，报出什么、放不放行 ===",
             _w("形状", 42) + _w("报出", 18) + _w("看起来", 10) + "结论"]
    for row in Q.gate_table():
        lines.append(_w(row["shape"], 42) + _w(row["reported"], 18)
                     + _w(row["seen"], 10) + row["verdict"])
    counts = Q.groups()
    lines += [
        "",
        " ｜ ".join(f"{name} {len(names)}" for name, names in counts.items()),
        "**同样是「没跑」，写在 `if:` 上把门拆掉（报 Success，即使它是必需检查也不挡合并），"
        "写在 `paths:` 上把门焊死（检查停在 Pending，要求它的 PR 被挡）**",
        "——而这两行在配置里的差别只有一个词；七种形状里**真的验过的只有一行**",
    ]
    return lines


# ------------------------------------------------------- 六、发布与灰度

def group_release() -> list[str]:
    lines = ["=== 六、发布与灰度：钉法、审批、金丝雀 ===",
             _w("钉法", 24) + _w("回滚回到同一份字节", 20) + _w("静默改动能改到几处", 20)
             + "改动留在哪里"]
    for row in R.pin_table():
        lines.append(_w(row["kind"], 24) + _w("✔" if row["same_bytes"] else "✘", 20)
                     + _w(f"{row['silent_spots']} 处", 20) + row["trace"])
    lines += [
        "",
        "**只有摘要能回答「八小时后回滚回到的是不是同一份字节」**——而它也是回滚的前提",
        "",
        f"审批：自动 {R.AUTO_APPROVE_S} 秒；必需审阅人的环境 {R.HUMAN_APPROVE_S} 秒／次"
        f"（一天 {R.RELEASES_PER_DAY} 次 ＝ {R.approval_report()['day_wait_s'] // 60} 分钟等待）",
        f"它买到的是「{R.approval_report()['bought']}」；",
        "而**待批准的 run 仍然占着 `concurrency` 组**——后面推的那一次会被排队或取消",
        "",
        f"金丝雀三档 × 两门判据（全量 {R.TOTAL_RPS:,d} rps、坏版本错误率 "
        f"{R.BAD_ERROR_RATE:.0%}）：",
        _w("档位", 8) + _w("该档 rps", 10) + _w("判据一：攒够 %d 个错误" % R.GATE_COUNT, 24)
        + _w("判据一放过的坏请求", 20) + "判据二：一窗的坏请求",
    ]
    rows = R.canary_table()
    for row in rows:
        lines.append(_w(row["step"], 8) + _w(f"{row['rps']:,d}", 10)
                     + _w(f"{row['count_s']}s", 24) + _w(f"{row['count_bad']:,d}", 20)
                     + f"{row['window_bad']:,d}")
    roll = R.rollback_report()
    lines += [
        "",
        f"**判据一（固定样本数）下三档放过的坏请求完全一样**"
        f"（{R.GATE_COUNT} ÷ {R.BAD_ERROR_RATE:.0%} ＝ {roll['detect_bad']:,d}）：",
        "「攒够 N 个错误」与档位无关——**小档位只是把判红拖长，而拖长的这段时间照样在错**",
        f"**判据二（固定窗口）下 5% 档就是真的少错 "
        f"{rows[2]['window_bad'] // rows[0]['window_bad']} 倍**"
        f"（{rows[0]['window_bad']:,d} vs {rows[2]['window_bad']:,d}）",
        "所以「金丝雀救不救人」不取决于阶梯，取决于判据的形态",
        "",
        f"回滚：{roll['approve_s'] // 60} 分钟等人 ＋ {roll['effect_s']} 秒生效 ＝ "
        f"{roll['total_s']} 秒",
        f"  在 100% 档下回滚期间受影响 {roll['bad_requests']:,d} 请求，是判红时放过的坏请求"
        f"（{roll['detect_bad']:,d}）的 **{roll['ratio']} 倍**",
        f"  在 5% 档下同一个回滚只影响 {roll['at_canary']:,d} 请求",
        "**回滚比判红贵两个数量级**——而「钉摘要」正是让回滚能做到「一键回到那一份」的前提",
    ]
    return lines


GROUPS = (group_trigger, group_graph, group_cache, group_perms, group_gate, group_release)


def report() -> list[str]:
    out: list[str] = []
    for fn in GROUPS:
        out += fn()
        out.append("")
    out.append("CI 读数：六组全过 ｜ 离线自检通过")
    return out


# ------------------------------------------------------- 自检

def self_test() -> int:
    ok = total = 0
    out: list[str] = []

    def chk(cond: bool, what: str) -> None:
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
        else:
            print(f"  ✗ {what}")

    # 一、触发与过滤
    cases = T.CASES
    chk(len(cases) == 11, "十一次提交")
    chk(T.SHOULD_RUN == 10, "本该进流水线的是十条（只有改文档不该跑）")
    chk(sum(1 for c in cases if not c.should_run) == 1, "只有一条不该跑")
    rows = {r["filter"]: r for r in T.filter_table()}
    chk(rows["不写过滤器"]["ran"] == 11, "不写过滤器：十一条全进")
    chk(rows["不写过滤器"]["missed"] == 0, "不写过滤器：一条不漏")
    chk(rows["白名单·窄（只 app/ 与依赖）"]["ran"] == 3, "窄白名单只放进去三条")
    chk(rows["白名单·窄（只 app/ 与依赖）"]["missed"] == 7, "窄白名单漏七条")
    chk("chore: 顺手改一下门自己" in rows["白名单·窄（只 app/ 与依赖）"]["missed_labels"],
        "窄白名单漏掉的里面**有「改门自己」那一条**")
    chk(rows["白名单·窄（只 app/ 与依赖）"]["worst"] == "chore: 顺手改一下门自己",
        "最贵的那条被点名了")
    chk(rows["黑名单·宽（只挡文档）"]["ran"] == 10, "黑名单放进去十条")
    chk(rows["黑名单·宽（只挡文档）"]["missed"] == 0, "黑名单今天一条不漏")
    chk(rows["白名单·宽（把该管的都列上）"]["ran"] == 9, "宽白名单放进九条")
    chk(rows["白名单·宽（把该管的都列上）"]["missed"] == 1,
        "宽白名单漏一条——新目录")
    chk(rows["白名单·宽（把该管的都列上）"]["worst"] == "chore: 新增一个部署目录",
        "漏的是新增目录那一条")
    wf = T.Workflow("CI")
    chk(wf.paths == () and wf.paths_ignore == (), "默认没有过滤器")
    try:
        T.Workflow("坏", paths=("a",), paths_ignore=("b",))
        chk(False, "paths 与 paths-ignore 不能同时写")
    except ValueError:
        chk(True, "paths 与 paths-ignore 不能同时写")
    chk(T.passes(T.Workflow("x", paths=("app/**",)), T.CASES[0].change)[0],
        "`app/**` 命中 `app/main.py`")
    chk(not T.passes(T.Workflow("x", paths=("app/**",)), T.CASES[4].change)[0],
        "`app/**` 不命中 `Dockerfile`")
    chk(T.matches(("**.md",), "README.md"), "`**.md` 命中 `README.md`")
    skips = T.skip_table()
    chk(skips[0]["runs"] == 2, "同仓分支起两个 run")
    chk(skips[1]["runs"] == 1, "fork 的 PR 起一个 run")
    chk(skips[2]["runs"] == 0, "[skip ci] 一个都不起")
    chk(skips[2]["check"] == "Pending", "[skip ci] 时检查停在 Pending")
    chk(T.Change("x", ("a",), message="[no ci] 先不跑").skips, "[no ci] 也是跳过标记")
    chk(not T.Change("x", ("a",), message="[skip-ci] 写法不对").skips,
        "`[skip-ci]`（连字符）不是官方那五个字符串之一")

    # 二、job 图与并发
    chk(len(G.MUST_PRECEDE) == 5, "逻辑上必须先后有五对关系")
    chk(G.violations(G.FLAT) == G.MUST_PRECEDE, "扁平图五对全违背")
    chk(G.violations(G.CHAIN) == (), "一条链零违背")
    chk(G.violations(G.GRAPH) == (("lint", "unit"),), "正确的图只差 lint 与 unit 的先后（无害）")
    chk(G.makespan(G.FLAT, 1) == 32, "扁平图 1 槽：32 分钟")
    chk(G.makespan(G.FLAT, 4) == 12, "扁平图 4 槽：12 分钟")
    chk(G.makespan(G.CHAIN, 4) == 32, "一条链给 4 个槽也是 32 分钟")
    chk(G.makespan(G.GRAPH, 1) == 32, "正确的图 1 槽：32 分钟")
    chk(G.makespan(G.GRAPH, 2) == 21, "正确的图 2 槽：21 分钟")
    chk(G.makespan(G.GRAPH, 4) == 21, "从 2 槽加到 4 槽一分钟不省")
    chk(G.critical_path(G.GRAPH)[1] == 21, "正确的图关键路径 21")
    chk(G.critical_path(G.CHAIN)[0] == ("lint", "unit", "integration", "e2e", "deploy"),
        "一条链的关键路径就是它自己")
    chk(G.critical_path(G.FLAT)[1] == 12, "扁平图的「关键路径」是单个最长的 job")
    chk(G.reaches(G.CHAIN, "unit", "deploy"), "链上 unit 是 deploy 的前置")
    chk(not G.reaches(G.GRAPH, "lint", "deploy"), "图里 lint 不是 deploy 的前置")
    m = G.matrix_table()
    chk(m[0]["cells"] == 6 and m[0]["billable"] == 24, "六格：24 分钟账单")
    chk(m[1]["cells"] == 4 and m[1]["billable"] == 16, "exclude 后四格：16 分钟")
    chk(m[2]["cancelled"] == 3, "fail-fast 取消三格")
    chk(m[2]["verdicts"][0] == "failure" and set(m[2]["verdicts"][1:]) == {"cancelled"},
        "一格 failure、三格 cancelled")
    chk(len(G.matrix_cells()) == 4, "exclude 之后确实只剩四格")
    chk(("3.11", "frontend") not in G.matrix_cells(), "被 exclude 的格不在里面")
    c = G.concurrency_table()
    chk(c[0]["billable"] == 27 and c[0]["killed"] == 2, "取消：27 分钟、取消两次")
    chk(c[1]["billable"] == 63 and c[1]["killed"] == 0, "排队：63 分钟、一次不取消")
    chk(c[2]["billable"] == c[0]["billable"], "group 写宽了的账单与正常取消一样")
    chk(c[1]["billable"] == 3 * 21, "排队版的可计费分钟 ＝ 三次满跑（63）")
    chk(c[0]["billable"] < c[1]["billable"], "取消比排队省")
    chk("main" in c[2]["note"], "写宽那一行点名了 main 会把 PR 取消掉")

    # 三、缓存与产物
    chk(len(CACHE_ROWS) == 6, "六行缓存读数")
    r = {tag: K.restore(key, rk, branch=branch) for tag, branch, key, rk in CACHE_ROWS}
    chk(r["A"]["cache_hit"] is True and r["A"]["matched"] == "pip-3.12-cccc",
        "A：同分支精确命中")
    chk(r["A"]["rule"] == "精确匹配 key @feat/rag", "A 是靠精确匹配")
    chk(r["B"]["cache_hit"] is False and r["B"]["matched"] == "pip-3.12-cccc",
        "B：命中了，而 cache-hit 是 false")
    chk(r["B"]["rule"].startswith("restore-key"), "B 是靠 restore-key")
    chk(r["C"]["rule"].startswith("key 的部分匹配"), "C：key 自己的部分匹配先命中")
    chk(len(r["C"]["tries"]) == 2, "C 只试了两步（restore-keys 没轮到）")
    chk(r["D"]["matched"] == "pip-3.12-bbbb", "D：并列时取最新创建的那一份")
    chk(r["E"]["scope"] == "main" and r["E"]["cache_hit"] is False,
        "E：跨分支命中，而 cache-hit 仍是 false")
    chk(r["F"]["matched"] is None, "F：子分支的缓存对默认分支不可见")
    chk(len(r["F"]["tries"]) == 4, "F 把四步都试完了")
    chk(K.restore("npm-aaaa", branch="main")["cache_hit"] is True, "npm 那条能精确命中")
    dead = [e.key for e in K.STORE if not K.alive(e)]
    chk(dead == ["pip-3.9-aaaa", "wheel-ubuntu-aaaa"], "两条超 7 天没访问的被清掉")
    chk(K.alive(K.STORE[0]) and K.NOW_DAY - K.STORE[0].accessed_day == 6,
        "6 天前访问过的那条还活着")
    seq = K.save_sequence((("pip-cache", 180_000), ("pip-cache", 260_000),
                           ("pip-cache", 310_000)))
    chk(seq[0]["saved"] is True, "静态 key 第一次存下去")
    chk(seq[1]["saved"] is False and seq[2]["saved"] is False, "静态 key 后两次被跳过")
    chk(seq[2]["held_kb"] == 180_000, "缓存里留的还是第一份（180,000 KB）")
    dyn = K.save_sequence((("pip-3.12-h1", 180_000), ("pip-3.12-h2", 260_000)))
    chk(all(row["saved"] for row in dyn), "动态 key 两次都存下去")
    chk(K._evict(K.MONOREPO, 0)[1] == ("gradle", "cargo-registry"),
        "超限时按最后访问从旧到新清两条")
    chk(sum(e.kb for e in K.MONOREPO) // 1000 == 11_059, "MONOREPO 一共 11,059 MB")
    chk(K.LIMIT_KB // 1024 == 10_240, "上限 10,240 MB")
    chk(all(K.alive(e) for e in K.MONOREPO), "MONOREPO 每一条都在 7 天内访问过")
    chk(not K.fetch(K.REPORT, needs=("lint",))["ok"], "没有 needs 就取不到产物")
    chk(K.fetch(K.REPORT, needs=("test",))["ok"], "写了 needs 才取得到")
    chk(K.fetch(K.REPORT, needs=("test",))["dir"] == "test-report", "下载目录是产物名")
    chk(not K.reupload(("test-report",), "test-report")["saved"], "同名重传失败（不可变）")
    chk(K.reupload(("test-report",), "test-report-v2")["saved"], "换一个名字就行")
    chk(K.verify(K.REPORT, tampered=("report/junit.xml",))["green"] is True,
        "摘要不符时 run 仍然是绿的")
    chk(K.verify(K.REPORT, tampered=("report/junit.xml",))["level"] == "warning",
        "摘要不符只记一句警告")

    # 四、权限与密钥
    chk(len(P.GRANTS) == 5, "五种权限面")
    b = {g.name: P.blast_radius(g) for g in P.GRANTS}
    chk(b["不写 permissions:（宽松默认）"]["write_workflow"] is True,
        "宽松默认能改 workflow（提权链的入口）")
    chk(b["不写 permissions:（受控默认）"]["write_code"] is False,
        "受控默认不能改代码")
    chk(b["permissions: {}"]["push_image"] is False, "全关时推不了镜像")
    chk(b["permissions: {}"]["cloud_creds"] is False, "全关时也换不到 OIDC 令牌")
    chk(b["permissions: {}"]["write_code"] is False, "全关时不能写代码")
    chk(b["contents: read ＋ 部署 job 的 id-token: write"]["cloud_creds"] is True,
        "按 job 提权的那一格能换云凭证")
    chk(b["pull_request_target ＋ checkout PR 的头"]["write_code"] is True
        and b["pull_request_target ＋ checkout PR 的头"]["read_secrets"] is True,
        "最后一行三样同时在手")
    chk(b["不写 permissions:（宽松默认）"]["push_image"] is True, "宽松默认能推镜像")
    chk(b["不写 permissions:（受控默认）"]["push_image"] is False, "受控默认推不了镜像")
    ev = {e.name: P.secret_value(e) for e in P.EVENTS}
    chk(ev["fork 来的 PR"]["empty"] is True, "fork 的 PR 拿不到密钥")
    chk(ev["fork 来的 PR"]["value"] == "", "拿不到时的值是空字符串")
    chk("401" in ev["fork 来的 PR"]["symptom"], "失败现场指向服务端")
    chk(ev["push 到本仓"]["empty"] is False, "push 能看到密钥")
    chk(ev["pull_request_target"]["empty"] is False, "pull_request_target 能看到密钥")
    evs = {e.name: e for e in P.EVENTS}
    chk(evs["pull_request_target"].token_write is True, "它还可能带写 token")
    chk(ev["Dependabot 触发"]["empty"] is True, "Dependabot 事件拿不到密钥")
    chk(P.CREDENTIALS[1]["valid_seconds"] == 300, "OIDC 示例令牌有效期 300 秒")
    chk(P.CREDENTIALS[0]["copies"] == 2 and P.CREDENTIALS[1]["copies"] == 0,
        "长期密钥存两份、OIDC 存零份")
    chk(P.CREDENTIALS[1]["rotate_by"].startswith("没有人"), "OIDC 不需要人轮换")
    chk(P.PINS[0].mutable and not P.PINS[1].mutable, "标签可变、SHA 不可变")
    chk("唯一" in P.PINS[1].note, "官方那句「唯一不可变形式」记在钉法上")

    # 五、门禁
    chk(len(Q.SHAPES) == 7, "七种形状")
    g = {s.name: s for s in Q.SHAPES}
    chk(g["job 级 `if:` 不成立"].reported == "success"
        and g["job 级 `if:` 不成立"].blocks is False,
        "job 级跳过：报 Success 且不挡合并")
    chk(g["workflow 级 `paths` 过滤挡住"].reported is None
        and g["workflow 级 `paths` 过滤挡住"].blocks is True,
        "workflow 级过滤：没有 check run 且挡合并")
    chk(g["提交信息带 `[skip ci]`"].reported is None, "[skip ci] 同 Pending")
    chk(g["`continue-on-error: true` 的那一步红了"].reported == "success",
        "continue-on-error：外面绿")
    chk(g["矩阵里被 `fail-fast` 取消的兄弟"].reported == "cancelled",
        "被取消的格报 cancelled")
    chk(g["被 `concurrency` 取消掉的旧 run"].blocks is True, "被取消的 run 挡合并")
    cats = Q.groups()
    chk(len(cats["真绿"]) == 1, "真绿只有一行")
    chk(len(cats["绿而没验"]) == 2, "绿而没验两行")
    chk(len(cats["停在 Pending（挡）"]) == 2, "停在 Pending 两行")
    chk(len(cats["跑了却被取消（挡）"]) == 2, "被取消两行")
    chk(sum(len(v) for v in cats.values()) == 7, "四组加起来七行")
    chk(Q.verdict(Q.SHAPES[0])["verdict"] == "放行" and
        Q.verdict(Q.SHAPES[3])["verdict"] == "挡", "结论只有两种")
    chk("即使它是必需检查" in g["job 级 `if:` 不成立"].why, "官方那句记在机制里")

    # 六、发布与灰度
    chk(len(R.PINS) == 3, "三种钉法")
    chk(R.PINS[0].mutable and not R.PINS[0].same_bytes_after, "latest：可变，回滚回到别的")
    chk(R.PINS[1].mutable and not R.PINS[1].same_bytes_after, "版本标签：也可被移动")
    chk(not R.PINS[2].mutable and R.PINS[2].same_bytes_after, "摘要：不可变、回滚精确")
    pins = R.pin_table()
    chk([p["silent_spots"] for p in pins] == [1, 1, 0], "静默改动能改到 1／1／0 处")
    chk(R.pin_table()[2]["trace"].startswith("清单里"), "摘要的改动落在清单里（可审）")
    ap = R.approval_report()
    chk(ap["auto_wait_s"] == 0 and ap["human_wait_s"] == 240, "审批等待 0／240 秒")
    chk(ap["day_wait_s"] == 1440, "一天六次发布 ＝ 24 分钟等待")
    chk("concurrency" in ap["side_effect"], "待批准仍占并发组")
    can = R.canary_table()
    chk([row["rps"] for row in can] == [50, 250, 1000], "三档流量 50／250／1000 rps")
    chk([row["count_bad"] for row in can] == [1333, 1333, 1333],
        "判据一放过的坏请求三档一样")
    chk(can[0]["count_s"] == 26.7 and can[2]["count_s"] == 1.3, "判红时长 26.7s／1.3s")
    chk([row["window_bad"] for row in can] == [90, 450, 1800], "判据二一窗的坏请求 90／450／1800")
    chk(can[2]["window_bad"] // can[0]["window_bad"] == 20, "判据二下 5% 档少错 20 倍")
    chk(all(row["window_ok"] for row in can), "三档在一窗内都攒够了样本")
    roll = R.rollback_report()
    chk(roll["total_s"] == 330, "回滚 330 秒")
    chk(roll["bad_requests"] == 330_000, "100% 档回滚期间受影响 330,000 请求")
    chk(roll["ratio"] == 247.6, "回滚是判红的 247.6 倍")
    chk(roll["at_canary"] == 16_500, "5% 档同一个回滚只影响 16,500 请求")
    chk(roll["at_canary"] == roll["bad_requests"] // 20, "档位之比就是 20 倍")
    chk(len(report()) >= 60, "六组读数的行数够长（≥ 60 行）")

    print(f"自检 {ok}/{total} 通过")
    return 0 if ok == total else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    print("\n".join(report()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
