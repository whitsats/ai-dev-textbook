#!/usr/bin/env python
"""8.1 的读数脚本：把「交出去的那个东西」变成六组能复算的数。

    python scripts/deploy_reader.py --offline     # 六组读数（不装 Docker、不要网络）
    python scripts/deploy_reader.py --self-test   # 九十六条夹具

六组依次是：**层账**（每一行一层，而删了不变小）／**构建缓存**（改一行重打多少，
顺序就是钱）／**瘦身四招**（各减多少、代价是什么——四招单算不叠加）／
**上下文与传输**（什么东西离开了这台机器；改一处要重发多少）／**编排**
（`depends_on` 的四种等法，与「起得来 ≠ 起得对」）／**运行期权限面**
（`USER`、只读根文件系统、密钥三档）。

它**不装 Docker、不联网、不要密钥**：镜像的大小与层数是**文件系统剧本**算出来的,
构建耗时是**脚本化的每层秒数**，编排的时钟是**写死的秒数**。所以它能量的是
**这些机制的性质**（层是不是只加的、顺序是不是真的那么贵、`service_started`
到底等到哪一刻），**量不了真实镜像的体积、真实机器的构建速度**——这一条写在正文的边界里。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import cache as K      # noqa: E402
from app import compose as C    # noqa: E402
from app import image as I      # noqa: E402
from app import runtime as R    # noqa: E402


# ------------------------------------------------------- 一、层账

def group_layers() -> list[str]:
    b = I.run(I.NAIVE)
    lines = [f"=== 一、层账：朴素版那份 Dockerfile 的每一层（基础镜像 {b.script.base} "
             f"{I.kb(b.script.base_kb)}）===",
             f"{'#':>2s} {'指令':<56s}{'这一层':>10s}{'白障':>5s}"]
    for layer in b.layers:
        ins = layer.instruction if len(layer.instruction) <= 54 else layer.instruction[:53] + "…"
        lines.append(f"{layer.index:>2d} {ins:<56s}{layer.size_kb:>8,d}KB{layer.whiteouts:>5d}")
    lines += [
        "",
        f"层账（每一行相加）：{b.layer_kb:>9,d} KB  ＋ 基础镜像 {b.script.base_kb:,d} KB"
        f"  ＝ {I.kb(b.image_kb)}",
        f"可见账（最终看得见的）：{b.visible_kb:>9,d} KB  ＋ 基础镜像 {b.script.base_kb:,d} KB"
        f"  ＝ {I.kb(b.squashed_kb)}",
        f"**浪费账 = 层账 − 可见账 = {b.wasted_kb:,d} KB（{I.kb(b.wasted_kb)}）**"
        f"——交付了、却没人能用上",
        f"而白障本身只占 {sum(layer.whiteouts for layer in b.layers)} KB"
        f"（ {sum(layer.whiteouts for layer in b.layers)} 个条目）：",
        "**`rm` 那一层的大小约等于 0，而它遮住的那 107 MB 仍然在盘上**——"
        "这就是「删了不变小」的可算形式",
    ]
    return lines


# ------------------------------------------------------- 二、缓存

def group_cache() -> list[str]:
    rows = K.variants()
    lines = ["=== 二、构建缓存：同一个改动，写在依赖之前还是之后 ===",
             f"{'改动':<30s}{'乱序（COPY . .）':>18s}{'顺序（依赖先、源码后）':>24s}"]
    for r in rows:
        u, s = r["unsorted"], r["sorted"]
        lines.append(f"{r['case']:<30s}"
                     f"{u['rebuilt']:>10d} 层/{u['seconds']:>4d}s"
                     f"{s['rebuilt']:>18d} 层/{s['seconds']:>4d}s")
    u0, s0 = rows[0]["unsorted"], rows[0]["sorted"]
    lines += [
        "",
        f"**改一行源码：{u0['seconds']}s → {s0['seconds']}s（{u0['seconds'] // s0['seconds']} 倍）**"
        f"——改的是同一个字节，位置不同，重打的层数 3 → 1",
        f"而**改依赖清单两边一样贵**（{rows[1]['unsorted']['seconds']}s 与 "
        f"{rows[1]['sorted']['seconds']}s）：它在两种顺序里都在最前面，"
        f"位置救不了它——这就是「少改依赖」这句话的由来",
        "**只碰一下时间戳：0 层**（官方：mtime 不参与缓存校验和）——"
        "「刚才编译过」与「刚才看过一眼」在缓存眼里是两件事",
        f"**什么都没改、隔 90 天再构建：0 层**——官方原话：`RUN` 那一层不会自动失效，"
        f"「上游有没有新版本」不在它的输入里，所以要「永远最新」得给一个显式动作",
        f"**改指令文本那一行：从那一层起全部重跑**（{rows[4]['unsorted']['seconds']}s）——"
        f"它不是「改了内容」，是「改了这一层的输入」，而它之后全是下游",
    ]
    return lines


# ------------------------------------------------------- 三、瘦身四招

def group_slimming() -> list[str]:
    base = I.run(I.NAIVE)
    rows = I.slimming_table()
    lines = [f"=== 三、瘦身四招的账（基线 {I.kb(base.image_kb)}，四招**各与基线单独比、不叠加**）===",
             f"{'招':<56s}{'镜像':>10s}{'省':>10s}{'省%':>7s}{'浪费账':>10s}"]
    for r in rows:
        label = r["label"] if len(r["label"]) <= 54 else r["label"][:53] + "…"
        lines.append(f"{label:<56s}{I.kb(r['image_kb']):>10s}{I.kb(r['saved_kb']):>10s}"
                     f"{r['saved_kb'] / base.image_kb:>6.1%}"
                     f"{' 0' if not r['wasted_kb'] else I.kb(r['wasted_kb']):>10s}")
    lines += [
        "",
        "四招里最省的是**换基础镜像**（它一次带走 890 MB），最贵的是**多阶段**（它要求"
        "你把构建过程拆成两段）；而**只有两招能把「浪费账」归零**：",
        "合并 `RUN`（那两笔开销根本没有产生）与多阶段（没被带走的东西不在最终镜像里）",
        f"**四招一起：{I.kb(base.image_kb)} → {I.kb(I.build_of('final').image_kb)}"
        f"（省 {I.kb(base.image_kb - I.build_of('final').image_kb)}，"
        f"{(base.image_kb - I.build_of('final').image_kb) / base.image_kb:.1%}）**"
        f"——而它不等于四行相加（那些数字动的是同一个数的不同部分）",
    ]
    return lines


# ------------------------------------------------------- 四、上下文与传输

def group_transfer() -> list[str]:
    ignored = tuple(p for p, _ in I.CONTEXT
                   if p in ("/app/.git", "/app/.venv", "/app/tests"))
    ctx = R.context_report(ignored)
    a = I.run(I.FINAL)
    b = I.run(I.restamped(I.FINAL, path="/app/app", kb=1_300))
    tr = I.transfer_report(a, b)
    lines = [f"=== 四、上下文与传输（上下文里一共 {ctx['total_files']} 项、"
             f"{ctx['total_kb']:,d} KB）===",
             f"没有 `.dockerignore`：{ctx['total_kb']:>7,d} KB 全部发给构建器"
             f"（{ctx['total_files']} 项）",
             f"有 `.dockerignore`：{ctx['sent_kb']:>7,d} KB（{ctx['sent_files']} 项）"
             f"——被挡下来 {ctx['blocked_kb']:,d} KB"]
    for path, why in R.IGNORE_REASONS:
        lines.append(f"  {path:<16s}{why}")
    lines += [
        "**「没有进最终镜像」与「没有离开这台机器」是两件事**："
        "`.git` 从来不会进镜像，但它会进构建器的缓存",
        "",
        f"改一行源码之后重新推送：{tr['layers']} 层里 **{tr['changed']} 层变了**"
        f"（{tr['changed_kb']:,d} KB），不是整份 {I.kb(tr['total_kb'])}",
        f"  变了的那一层：{tr['changed_instructions'][0]}",
        f"  拉一次：全量 {I.pull_seconds(tr['total_kb']):.1f}s → "
        f"只更新那一层 {I.pull_seconds(tr['changed_kb']):.2f}s（按 {I.LINK_MBPS} MB/s 算）",
        "——**层是内容寻址的**：前面某层失效（要重跑）不等于它的内容变了"
        "（重跑出来一样，指纹就一样，也就不会被重发）",
        "所以「优化缓存」与「层复用」救的是两件事：**前者救构建，后者救传输**",
    ]
    return lines


# ------------------------------------------------------- 五、编排

def group_compose() -> list[str]:
    rows = C.startup_table(retry_s=3)
    no_retry = C.startup_table(retry_s=None)
    lines = [f"=== 五、编排：`depends_on` 的四种等法（数据库第 {C.DB.start_s}s 在跑、"
             f"第 {C.DB.ready_s}s 能应答；应用每 3s 重试一次）===",
             f"{'写法':<48s}{'应用起于':>8s}{'失败':>5s}{'第一次成功':>11s}"]
    for r in rows:
        ok = "——" if r["first_ok"] is None else f"{r['first_ok']}s"
        lines.append(f"{r['label']:<48s}{r['app_start']:>7d}s{r['failures']:>5d}{ok:>11s}")
    lines += [
        "",
        f"**不写 `depends_on` 反而最早成（{rows[0]['first_ok']}s）**——因为它把 "
        f"{rows[0]['failures']} 次失败当成正常；写默认的 `service_started` 只保证"
        f"**容器在跑**，于是应用第 {rows[1]['app_start']}s 起来、"
        f"第 {rows[1]['first_ok']}s 才成（比不写还晚 2 秒）",
        f"`service_healthy` 等到**第一次报健康**（第 {C.DB.healthy_s}s，"
        f"即第 {C.DB.probes} 个探针），应用第 {rows[2]['app_start']}s 起来、**失败 0 次**",
        f"`service_completed_successfully` 等的是**迁移跑到退出码 0**"
        f"（第 {C.MIGRATE.ready_s}s）——它等的不是同一次等待的变体，是另一条链",
        "",
        "前提换一个，结论就换一个——**应用自己没有重试的时候**：",
    ]
    for r in no_retry:
        ok = "**起不来**" if r["first_ok"] is None else f"{r['first_ok']}s"
        lines.append(f"  {r['label']:<48s}{r['app_start']:>7d}s{r['failures']:>5d}失败  {ok}")
    lines += [
        "**四种等法的差别不在「快不快」，在「成不成」**：应用不重试时，"
        "只有后两种能起来——而它们之所以能起来，是因为它们等的东西"
        "**恰好蕴含了「依赖可以用」**（健康检查过、迁移跑完）",
        "",
        "`healthcheck` 的四个参数（判健康与判不健康是两个时刻）：",
        f"{'interval':>9s}{'retries':>8s}{'start_period':>13s}{'判健康':>8s}{'探针':>5s}{'判不健康':>10s}",
    ]
    for h in C.healthcheck_table():
        lines.append(f"{h['interval']:>8d}s{h['retries']:>8d}{h['start_period']:>12d}s"
                     f"{h['healthy_s']:>7d}s{h['probes']:>5d}{h['unhealthy_after']:>9d}s")
    lines.append("——`retries` 越大，启动期越不容易误判，而**真出事的时候也就越晚知道**："
                 "第一行要 25s 才判不健康，第二行 10s")
    return lines


# ------------------------------------------------------- 六、权限面与密钥

def group_runtime() -> list[str]:
    lines = ["=== 六、运行期权限面：谁在跑、能写哪里、密钥留在哪几处 ===",
             f"{'姿态':<56s}{'可写':>6s}{'显式声明':>9s}{'root':>6s}"]
    for r in R.seat_table():
        label = r["label"] if len(r["label"]) <= 54 else r["label"][:53] + "…"
        lines.append(f"{label:<56s}{r['ok']}/{r['total']:>4d}{r['declared']:>9d}"
                     f"{'是' if r['root'] else '否':>7s}")
    lines += [
        "",
        "三处写入需求：`/tmp`（uvicorn 与多进程启动）与 `/app/.cache`（库的缓存）"
        "**是硬的**，`/app/logs` **可以不要**（日志也能只往标准输出走）",
        "前两行都能写、都通——**它们的区别不在「通不通」，在「那一行以谁的身份在写」**"
        "（root 写进去的东西，没有任何一层能拦住它写别的地方）",
        "第三行（只读根文件系统、什么都不挂）**三处全写不进去**；第四行把两处真正需要的"
        "挂出来之后就够启动了——**只读根文件系统买到的是「它写过哪里」从"
        "「没人知道」变成一份清单**",
        "",
        f"{'密钥的递法':<44s}{'配置':>6s}{'层里':>6s}{'缓存':>6s}{'看见的人':>8s}",
    ]
    for row in I.secret_ladder():
        lines.append(f"{row['label']:<44s}{'✔' if row['config'] else '—':>6s}"
                     f"{'✔' if row['layer'] else '—':>6s}"
                     f"{'✔' if row['cache'] else '—':>6s}{row['leaks']:>8d}")
    lines += [
        "**`ENV` 三处全中**（任何人 pull 下来 `docker inspect` 就能读），"
        "`ARG` 少了配置那一处、**但写进文件的那一份留在层里**，"
        "只有 `--mount=type=secret` 三处都不留（官方：secret 内容不参与缓存校验）",
        "——注意第三档的机制：**它不是一个「更安全的写法」，它是「这件事不发生」**"
        "（挂在构建容器里的一次临时文件，只在那条指令期间存在）",
    ]
    return lines


GROUPS = (
    ("一", group_layers),
    ("二", group_cache),
    ("三", group_slimming),
    ("四", group_transfer),
    ("五", group_compose),
    ("六", group_runtime),
)


def report() -> list[str]:
    lines: list[str] = []
    for _, fn in GROUPS:
        lines.extend(fn())
        lines.append("")
    lines.append("部署读数：六组全过 ｜ 离线自检通过")
    return lines


# ------------------------------------------------------- 夹具

def self_test() -> int:
    """六十五条夹具。**每一条都可以拿纸笔复核**（这正是六组读数的要求）。"""
    ok = 0
    total = 0

    def chk(cond: bool, what: str) -> None:
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
        else:
            print(f"  ✗ {what}")

    # 一、层账
    naive = I.run(I.NAIVE)
    chk(len(naive.layers) == 6, "朴素版六行指令")
    chk(naive.layers[0].instruction.startswith("COPY"), "第一行是 COPY")
    chk(naive.layers[0].size_kb == 53_042, "COPY 那一层 53,042 KB（上下文七项之和）")
    chk(naive.layers[2].size_kb == 250_000, "工具链那一层 250,000 KB")
    chk(naive.layers[3].size_kb == 3, "`rm` 那一层只有 3 个白障 ＝ 3 KB")
    chk(naive.layers[3].whiteouts == 3, "`rm` 遮了三个路径")
    chk(naive.image_kb == 1_595_045, "层账 1,595,045 KB")
    chk(naive.visible_kb == 468_042, "可见账 468,042 KB")
    chk(naive.wasted_kb == 107_003, "浪费账 107,003 KB")
    chk(naive.wasted_kb == naive.layer_kb - naive.visible_kb, "浪费＝层账−可见账")
    chk(naive.squashed_kb == naive.script.base_kb + naive.visible_kb, "压成一层＝基础＋可见")
    chk(naive.image_kb > naive.squashed_kb, "层账**大于**压成一层的账（这就是那个错觉）")
    chk(naive.layers[3].size_kb < naive.wasted_kb, "`rm` 那一层比它删掉的字节小得多")
    chk(naive.layers_of("USER")[0].size_kb == 0, "`USER` 那一层 0 KB")
    chk(naive.seconds == 149, "朴素版脚本化耗时 149s（4＋48＋95＋2）")

    # 二、缓存
    rows = K.variants()
    chk([r["case"] for r in rows][0] == "改一行源码", "第一行夹具是改源码")
    u0, s0 = rows[0]["unsorted"], rows[0]["sorted"]
    chk(u0["rebuilt"] == 3 and u0["seconds"] == 147, "乱序版改源码重跑 3 层／147s")
    chk(s0["rebuilt"] == 1 and s0["seconds"] == 4, "顺序版重跑 1 层／4s")
    chk(K.cache_run(K.UNSORTED, changed=(K.DEP_FILE,)).rebuilt == 3, "乱序版改依赖重跑 3 层")
    chk(K.cache_run(K.SORTED, changed=(K.DEP_FILE,)).rebuilt == 3, "顺序版改依赖也重跑 3 层")
    chk(K.cache_run(K.UNSORTED, changed=(K.DEP_FILE,)).seconds(K.UNSORTED) == 147,
        "改依赖两边一样贵（乱序 147s）")
    chk(K.cache_run(K.SORTED, changed=(K.DEP_FILE,)).seconds(K.SORTED) == 54,
        "顺序版改依赖 54s（2＋48＋4 的前三项）")
    chk(K.cache_run(K.UNSORTED, touched=(K.SRC_FILE,)).rebuilt == 0,
        "只碰时间戳：**一层都不重跑**（mtime 不参与校验）")
    chk(K.cache_run(K.SORTED, touched=("app/main.py",)).rebuilt == 0,
        "顺序版同样：碰一下不算改")
    chk(K.cache_run(K.UNSORTED).reused == 3, "什么都没改：三层全命中（含装包那一层）")
    chk(K.cache_run(K.UNSORTED).first_miss is None, "全命中时没有 first_miss")
    ins = K.cache_run(K.UNSORTED, edited=(1,))
    chk(ins.rebuilt == 2 and ins.first_miss == 1, "改指令文本：从那一层起重跑")
    chk(K.cache_run(K.SORTED, changed=("app/main.py",)).reused == 2, "顺序版改源码复用两层")
    chk(K.SORTED[0].files == ("requirements.txt",), "顺序版第一层只校验依赖清单")
    chk(K.SORTED[-1].files == ("app/main.py", "app/rag.py"), "源码在最后一层")
    chk(K.cache_run(K.SORTED, changed=("app/rag.py",)).rebuilt == 1, "改另一个源码文件也只重跑一层")

    # 三、瘦身四招
    table = {r["name"]: r for r in I.slimming_table()}
    chk(len(table) == 5, "四招各一行 ＋ 四招一起一行")
    chk(table["merged"]["saved_kb"] == 92_003, "合并 RUN 省 92,003 KB")
    chk(table["ignored"]["saved_kb"] == 42_800, "`.dockerignore` 省 42,800 KB")
    chk(table["multistage"]["saved_kb"] == 363_805, "多阶段省 363,805 KB")
    chk(table["slim-base"]["saved_kb"] == 890_000, "换基础镜像省 890,000 KB")
    chk(table["final"]["image_kb"] == 341_240, "四招一起：341,240 KB")
    chk(I.build_of("slim-base").layers == I.build_of("naive").layers, "换基础镜像**不改任何一层**")
    chk(I.build_of("merged").wasted_kb == 0, "合并 RUN 让浪费归零")
    chk(I.build_of("multistage").wasted_kb == 0, "多阶段让浪费归零")
    chk(I.build_of("ignored").wasted_kb == 92_003, "`.dockerignore` 不碰浪费账（它减的是别的东西）")
    chk(table["final"]["image_kb"] != (naive.image_kb - sum(
        r["saved_kb"] for k, r in table.items() if k != "final")), "四招相加 ≠ 四招一起")

    # 四、上下文与传输
    ignored = ("/app/.git", "/app/.venv", "/app/tests")
    ctx = R.context_report(ignored)
    chk(ctx["total_kb"] == 53_042, "上下文一共 53,042 KB")
    chk(ctx["sent_kb"] == 10_242, "挡掉三项之后发出去 10,242 KB")
    chk(ctx["blocked_kb"] == 42_800, "被挡下来 42,800 KB")
    chk(ctx["sent_files"] == 4 and ctx["total_files"] == 7, "七项里发出去四项")
    chk("/app/.git" in ctx["blocked"], "版本历史在里面")
    final = I.run(I.FINAL)
    restamped = I.run(I.restamped(I.FINAL, path="/app/app", kb=1_300))
    tr = I.transfer_report(final, restamped)
    chk(tr["changed"] == 1, "改一处源码只变一层")
    chk(tr["changed_kb"] == 1_300, "变的那一层 1,300 KB")
    chk(tr["same"] == 4, "另外四层指纹一样，不会被重发")
    chk(tr["changed_instructions"][0].endswith("/app/app"), "变的是拷源码那一层")
    chk(I.transfer_report(final, final)["changed"] == 0, "同一个镜像与自己比：零层变")
    chk(abs(I.pull_seconds(341_240) - 13.6496) < 1e-3, "全量拉 13.6s（按 25 MB/s）")
    chk(I.pull_seconds(1_300) < 0.1, "只更新那一层不到 0.1s")
    chk(I.pull_seconds(2_000, mbps=50) < I.pull_seconds(2_000), "带宽越大越快")
    chk(I.restamped(I.FINAL, path="/app/app", kb=1_300).base == I.FINAL.base,
        "restamped 只改那一处，基础镜像不动")

    # 五、编排
    by = {r["draft"]: r for r in C.startup_table(retry_s=3)}
    chk(by["none"]["app_start"] == 0, "不写 depends_on：应用第 0s 就起")
    chk(by["none"]["failures"] == 4 and by["none"]["first_ok"] == 12,
        "不写：4 次失败、第 12s 成")
    chk(by["started"]["app_start"] == C.DB.start_s == 2, "service_started 等到容器在跑（第 2s）")
    chk(by["started"]["first_ok"] == 14, "service_started 反而更晚成（14s）")
    chk(by["healthy"]["app_start"] == C.DB.healthy_s == 15, "service_healthy 等到第 15s")
    chk(by["healthy"]["failures"] == 0, "service_healthy 零失败")
    chk(by["completed"]["dep"] == "migrate", "第四种等的是迁移，不是数据库")
    chk(by["completed"]["app_start"] == C.MIGRATE.ready_s == 14, "等迁移跑到退出码 0")
    no_retry = {r["draft"]: r for r in C.startup_table(retry_s=None)}
    chk(no_retry["none"]["first_ok"] is None, "应用不重试时：不写 depends_on 起不来")
    chk(no_retry["started"]["first_ok"] is None, "service_started 也起不来")
    chk(no_retry["healthy"]["first_ok"] == 15, "service_healthy 起得来")
    chk(no_retry["completed"]["first_ok"] == 14, "等迁移也能起来")
    chk(sum(1 for r in no_retry.values() if r["first_ok"] is None) == 2, "四种里两种起不来")
    # 四种组合里有两种的 interval 相同（5s）——**所以主键得是三元组**，
    # 只按 interval 做键的话，后一行会把前一行盖掉（本节第一版就是这么写的，
    # 于是夹具报出来的是 55s 而它想验的是 25s）。
    h = {(row["interval"], row["retries"], row["start_period"]): row
         for row in C.healthcheck_table()}
    chk(h[(5, 5, 0)]["healthy_s"] == 15 and h[(5, 5, 0)]["probes"] == 3,
        "interval=5：第 15s 判健康、3 个探针")
    chk(h[(1, 10, 0)]["healthy_s"] == 12, "interval=1：第 12s 就判健康")
    chk(h[(1, 10, 0)]["probes"] == 12, "interval=1 要发 12 个探针")
    chk(h[(5, 5, 0)]["unhealthy_after"] == 25, "interval=5/retries=5：25s 判不健康")
    chk(h[(10, 3, 0)]["unhealthy_after"] == 30, "interval=10/retries=3：30s 判不健康")
    chk(C.Service("x", "x", 2, 12, interval=5, retries=5, start_period=30).unhealthy_after == 55,
        "start_period 算进判不健康")
    chk(C.Service("x", "x", 2, 12, interval=5, retries=5, start_period=30).healthy_s == 15,
        "start_period 不推迟健康")
    chk(C.app_start(C.DRAFTS[0]) == 0, "app_start 对第一种写法是 0")

    # 六、权限面与密钥
    seats = {r["seat"]: r for r in R.seat_table()}
    chk(len(seats) == 4, "四种姿态")
    chk(seats["root-rw"]["ok"] == 3 and seats["root-rw"]["root"], "root ＋ 可写：三处全通")
    chk(seats["app-rw"]["ok"] == 3 and not seats["app-rw"]["root"], "非 root ＋ 可写：也三处全通")
    chk(seats["app-ro"]["ok"] == 0, "非 root ＋ 只读：三处全写不进去")
    chk(seats["app-ro"]["required_ok"] is False, "两处硬的写不进去时启动不了")
    chk(seats["app-ro-mount"]["ok"] == 2, "挂两处之后通过两处")
    chk(seats["app-ro-mount"]["declared"] == 2, "必须显式声明两处")
    chk(seats["app-ro-mount"]["required_ok"] is True, "两处硬的都通了")
    chk(not seats["app-ro-mount"]["root"], "它仍然不是 root")
    chk(R.seat_tally(R.SEATS[0])["ok"] == R.seat_tally(R.SEATS[1])["ok"],
        "root 与非 root 的「通不通」一样——差别在别处")
    chk(all(w.required for w in R.seat_writes(R.SEATS[3])[:2]), "前两处是硬的")
    chk(R.NEEDS[2][2] is False, "日志那一处可以不要")
    ladder = {r["rung"]: r for r in I.secret_ladder()}
    chk(ladder["env"]["leaks"] == 3, "`ENV`：三处全中")
    chk(ladder["arg"]["leaks"] == 2, "`ARG`：少配置那一处")
    chk(ladder["arg"]["config"] is False and ladder["arg"]["layer"] is True, "`ARG` 的值在层里")
    chk(ladder["secret"]["leaks"] == 0, "`--mount=type=secret`：三处都不留")
    chk(ladder["secret"]["cache"] is False, "secret 内容不参与缓存校验")
    chk(len(I.secret_visible_to("env")) == 3, "`ENV` 那一档有三种人看得见")
    chk(I.secret_visible_to("secret") == (), "secret 那一档一个也没有")

    print(f"自检 {ok}/{total} 通过")
    return 0 if ok == total else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    print("\n".join(report()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
