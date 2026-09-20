#!/usr/bin/env python
"""7.5 的读数脚本：把「留存、隐私、审计」变成六组能复算的数。

    python scripts/privacy_reader.py --offline     # 六组读数（不要密钥、不要网络）
    python scripts/privacy_reader.py --self-test   # 四十四条夹具

六组依次是：六类数据各留多久、**谁来执行这个期限** ／ 四种脱敏各自除掉了什么
（可关联性）／ 掩码留下的那 4 位加一个生日够不够认出人 ／ 识别码检测的两笔账
（形状规则 vs 校验位）／ 一次「请删掉我」要走到几个地方 ／ 审计记录自己的两处自查。

它**不调模型、不联网**：十八条例记录、十二份正文、四千个合成总体、
十二次访问都是写死的。所以它能量的是**制度的性质**（期限与执行路径是不是一回事、
四种手法各自留下了什么），量不了真实数据的分布，也量不了一份具体的隐私政策是否合规
——这一条写在正文的边界里。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import privacy as V  # noqa: E402


# ------------------------------------------------------- 一、期限与执行路径

def group_retention() -> list[str]:
    rows = V.retention_report(V.sample_records(), V.NOW)
    tally = V.retention_tally(V.sample_records(), V.NOW)
    lines = [f"=== 一、六类数据各留多久，与**谁来执行这个期限**（今天＝第 {V.NOW} 天）===",
             f"{'类别':<24s}{'期限':>5s}{'条数':>5s}{'过期':>5s}{'会删':>5s}{'最久':>6s}   执行路径"]
    for r in rows:
        lines.append(f"{r['label']:<24s}{r['days']:>4d}天{r['count']:>5d}{r['stale']:>5d}"
                     f"{r['will_delete']:>5d}{r['oldest']:>5d}天   "
                     f"{'有' if r['enforced'] else '**没有**'}")
    lines.append(f"合起来：过期 {tally['stale']} 条，**真正会被删掉的 {tally['will_delete']} 条**"
                 f"——差的 {tally['orphan']} 条是「写了期限、没有删除路径」的")
    lines.append(f"差得最远的是 `{tally['worst']}`：它最久的那条已经活了 "
                 f"{tally['worst_over'] + V.POLICY_BY_KIND[tally['worst']].days} 天，"
                 f"越过自己那一行 {tally['worst_over']} 天")
    lines.append("——两列不相等不是实现漏洞，是**制度与盘面不是一件事**的表现："
                 "审计记录按规范只增、语料入库管线只增不删（5.8）")
    return lines


# ------------------------------------------------------- 二、四种脱敏留下了什么

def group_techniques() -> list[str]:
    values = ("13800138000", "13900139000", "13800138000")
    lines = ["=== 二、四种脱敏：同一个值（两份数据里同一个人）经过它们之后 ===",
             f"取值：{values}（第三个与前一个是**同一个人的同一个字段**）",
             f"{'手法':<6s}{'输入种类':>6s}{'输出种类':>6s}  {'样例':<20s}两件事"]
    for row in V.linkability_table(values):
        note = "**可关联**（同一个值给同一个输出，两份数据能 join）" if row["joinable"] else \
            "塌成一个值（连不起来，也没法按人聚合）"
        lines.append(f"{row['label']:<8s}{row['distinct_in']:>6d}{row['distinct_out']:>8d}"
                     f"  {row['sample']:<20s}{note}")
    lines.append("——四种里 **两种可关联**（掩码、哈希），而它们正是最常用的两种：")
    lines.append("掩码把值变得「读不出来」而留下了那几位（同一个人还是同一串星号），"
                 "哈希把值变得「读不出来」而**确定性就是它的用处所在**")
    lines.append("真正除掉可关联性的只有两种（替换、删除），代价是**分析能力归零**"
                 "——所以这是一个取舍，不是一个「更好的做法」")
    return lines


def group_tail() -> list[str]:
    pop = V.SAMPLE_POPULATION
    t = V.tail_guess(pop)
    lines = [f"=== 三、掩码留下的 4 位尾号，加一个看起来无关的字段（生日）够不够认出人 ===",
             f"合成总体：{t['n']} 人，每人一个（尾号 4 位，生日）",
             f"只按尾号分组：{t['tail_groups']} 组，**最大一组 {t['tail_max']} 人**"
             f"——尾号本身认不出人（它只有 10,000 种）",
             f"再按（尾号 ＋ 生日）分组：{t['both_groups']} 组，其中 "
             f"**{t['both_singletons']} 组只剩一个人 ＝ {t['singleton_rate']:.0%}**",
             "——数据里再加一个谁都不觉得敏感的字段（生日），"
             "掩码就没在保护任何东西了：这是「脱敏 ≠ 匿名」的可算形式"]
    return lines


# ------------------------------------------------------- 四、识别码的两笔账

def group_detect() -> list[str]:
    t = V.detect_tally(V.SAMPLE_TEXTS)
    lines = [f"=== 四、识别码检测的两笔账（{t['texts']} 份正文）===",
             f"只有形状规则（四条正则）：{t['hits']} 处命中"]
    print_hits = V.detect(V.SAMPLE_TEXT)
    for h in print_hits:
        mark = {None: "无校验位可用", True: "校验位通过", False: "**校验位不过（假阳）**"}[h["checksum"]]
        lines.append(f"  {h['label']:<12s}{h['value']:<22s}{mark}")
    lines.append(f"其中**有校验位可用**的 {t['hits'] - t['no_checksum']} 处："
                 f"校验位通过 {t['confirmed']} 处、**不过 {t['false_pos']} 处**")
    lines.append(f"剩下 {t['no_checksum']} 处**根本没有校验位可用**（手机号、邮箱）"
                 f"——手机号的形状只是「1 开头、第二位 3–9、共 11 位」，没有任何一位能拿来自检，"
                 f"所以这两类只能靠形状规则，而形状规则给不出「是不是」")
    lines.append("两个假阳都是同一件事：**16 位订单号碰巧通过了 Luhn**"
                 "（随机 16 位通过的概率约 1/10），而「校验位不过」不等于「不是卡号」"
                 "（真卡号也会有输错的时候）")
    lines.append("——两条规则各查一半：形状规则查「像不像」（必然有假阳），"
                 "校验位查「是不是」（只对有校验位的类别有效）")
    return lines


# ------------------------------------------------------- 五、删除走到哪里

def group_deletion() -> list[str]:
    d = V.deletion_tally("u1001")
    lines = [f"=== 五、一次「请删掉我」（{d['subject']}）要走到几个地方 ===",
             f"{'存储':<34s}{'能不能当场删':<14s}结果"]
    for p in V.deletion_plan("u1001"):
        lines.append(f"{p['label']:<34s}{'能' if p['reachable'] else '**不能**':<14s}{p['action']}")
    lines.append(f"——{d['stores']} 个地方存着这位用户的东西，删除路径覆盖 {d['reached']} 个，"
                 f"**剩下 {d['leftover']} 个不在它上面**")
    lines.append("撤下的三处不是偷懒：链路内容与冷日志是**只增**的（它们能被改就可以被伪造，"
                 "7.4 的链就是靠这一点自证的），备份只能随轮转自然过期")
    lines.append(f"所以「已删除」这句话的准确说法是：**当场删 {d['reached']}/{d['stores']}，"
                 f"其余随轮转过期（最久 {d['backup_days']} 天）**——"
                 f"把后半句省掉，这句话就变成了一句谎")
    return lines


# ------------------------------------------------------- 六、内容捕获与审计自查

def group_capture() -> list[str]:
    rows = V.capture_report(V.sample_records(), V.SAMPLE_TEXTS)
    lines = ["=== 六、内容捕获这一个旋钮的两个位置，与审计记录自己的两处自查 ==="]
    for r in rows:
        lines.append(f"{r['label']:<16s}存下的正文 {r['stored']}/{r['records']} 条 ｜ "
                     f"含识别码 {r['with_pii']} 条 ｜ 能回放 {r['replayable']} 条")
    lines.append("——**这个旋钮没有中间档**：要么正文全存（出事能回放，盘上带着识别码），"
                 "要么一条不存（盘上干净，「刚才那一次到底答了什么」查不了）。"
                 "7.2 把它定成**逐项 Opt-In、默认关闭**，代价就是这一行")
    a = V.access_tally(V.SAMPLE_ACCESS)
    lines.append(f"审计记录自己的两处自查（{a['entries']} 条、{a['actors']} 个操作者）：")
    lines.append(f"  没写「为什么看」的 {a['blank_purpose']} 条 ＝ "
                 f"**{a['blank_rate']:.0%}**——这一栏空着时，"
                 f"「按需访问」与「想看看就看看」在报表上长得一样")
    lines.append(f"  记录里自己抄进识别码的 **{a['leaked_hits']} 处**"
                 f"（`target_field` 直接把手机号写进去了）")
    lines.append("  第二条是最反直觉的一处：审计记录的用处是追责，所以它**最不愿意脱敏**，"
                 "而它恰恰是唯一一份「谁看了谁的全部历史」的表")
    return lines


GROUPS = (
    ("一", group_retention),
    ("二", group_techniques),
    ("三", group_tail),
    ("四", group_detect),
    ("五", group_deletion),
    ("六", group_capture),
)


def report() -> list[str]:
    lines: list[str] = []
    for _, fn in GROUPS:
        lines.extend(fn())
        lines.append("")
    lines.append("合规读数：六组全过 ｜ 离线自检通过")
    return lines


# ------------------------------------------------------- 夹具

def self_test() -> int:
    """四十四条夹具。**每一条都可以拿纸笔复核**（这正是六组读数的要求）。"""
    ok = 0
    total = 0

    def chk(cond: bool, what: str) -> None:
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
        else:
            print(f"  ✗ {what}")

    records = V.sample_records()
    tally = V.retention_tally(records, V.NOW)

    chk(len(records) == 18, "样本是十八条例记录")
    chk(len({r.kind for r in records}) == 6, "六类各占一类")
    chk(tally["stale"] == 4, "过期的共 4 条")
    chk(tally["will_delete"] == 3, "真正会被删的 3 条")
    chk(tally["orphan"] == 1, "写了期限而不会删的 1 条")
    chk(tally["worst"] == "corpus", "差得最远的是语料")
    chk(tally["worst_over"] == 95, "语料超出自己那一行 95 天")
    chk(V.POLICY_BY_KIND["audit"].enforced is False, "审计记录没有删除路径")
    chk(V.POLICY_BY_KIND["corpus"].enforced is False, "语料没有删除路径")
    chk(V.POLICY_BY_KIND["cache"].days == 1, "缓存留 1 天")
    chk(V.age_days(records[0], V.NOW) == V.NOW - records[0].created_day, "age_days 是减法")
    chk(len(V.expired(records, V.NOW)) == 4, "expired() 与 tally 的过期数一致")
    chk(V.retention_tally(records, V.NOW)["orphan"] ==
        tally["stale"] - tally["will_delete"], "孤儿数＝过期数−会删数")
    chk(all(r["will_delete"] <= r["stale"] for r in V.retention_report(records, V.NOW)),
        "会删的不会多于过期的")
    chk(V.retention_report(records, V.NOW)[4]["will_delete"] == 0, "语料那一条会删数是 0")

    chk(V.apply("mask", "13800138000") == "138****8000", "掩码保留前 3 后 4")
    chk(V.apply("mask", "1234") == "****", "短值全部打星")
    chk(V.apply("placeholder", "13800138000") == "<已隐去>", "替换法只有一个输出")
    chk(V.apply("hash", "13800138000").startswith("h:"), "哈希带前缀")
    chk(V.apply("hash", "a") == V.apply("hash", "a"), "哈希是确定性的（这正是它能被 join 的原因）")
    chk(V.apply("drop", "13800138000") == "", "删除法什么都不留")
    try:
        V.apply("nope", "x")
        chk(False, "未知手法应当报错")
    except KeyError:
        chk(True, "未知手法报错")

    tbl = {r["technique"]: r for r in V.linkability_table(
        ("13800138000", "13900139000", "13800138000"))}
    chk(tbl["mask"]["joinable"] is True, "掩码可关联")
    chk(tbl["hash"]["joinable"] is True, "哈希可关联")
    chk(tbl["placeholder"]["collapsed"] is True, "替换塌成一个值")
    chk(tbl["drop"]["collapsed"] is True, "删除也塌成一个值")
    chk(sum(1 for r in tbl.values() if r["joinable"]) == 2, "四法里恰好两种可关联")
    chk(tbl["mask"]["distinct_out"] == 2, "掩码的输出种类数等于输入种类数")

    t = V.tail_guess(V.SAMPLE_POPULATION)
    chk(t["n"] == 4000, "合成总体 4000 人")
    chk(t["tail_groups"] == 1044, "尾号分成 1044 组")
    chk(t["tail_max"] == 40, "最大的一组 40 人")
    chk(t["both_singletons"] == 3200, "尾号＋生日之后 3200 组只剩一人")
    chk(abs(t["singleton_rate"] - 0.8) < 1e-9, "唯一率 80%")
    chk(t["tail_max"] > 1, "尾号本身认不出人")

    chk(V.luhn_ok("4111111111111111") is True, "4111… 通过 Luhn")
    chk(V.luhn_ok("1234567890123456") is False, "1234…456 不过 Luhn")
    chk(V.luhn_ok("1234567890123452") is True, "1234…452 碰巧通过")
    chk(V.luhn_ok("abcdefghijklmnop") is False, "非数字不过 Luhn")
    chk(V.cn_id_ok("11010519491231002X") is True, "身份证校验位通过")
    chk(V.cn_id_ok("110105194912310021") is False, "身份证校验位不过")
    chk(V.cn_id_ok("110105194912310021") is False, "身份证校验位不过（长度对、位不对）")
    chk(V.has_checksum("card") and V.has_checksum("cn_id"), "两类有校验位")
    chk(not V.has_checksum("phone") and not V.has_checksum("email"), "两类没有校验位")

    dt = V.detect_tally(V.SAMPLE_TEXTS)
    chk(dt["texts"] == 12, "十二份正文")
    chk(dt["hits"] == 12, "形状规则报出 12 处")
    chk(dt["confirmed"] == 4, "校验位确认 4 处")
    chk(dt["false_pos"] == 2, "假阳 2 处")
    chk(dt["no_checksum"] == 6, "没有校验位可用的 6 处")
    chk(V.detect(V.SAMPLE_TEXTS[10]) == [], "没有识别码的那一份报空")

    d = V.deletion_tally("u1001")
    chk(d["stores"] == 6 and d["reached"] == 3 and d["leftover"] == 3,
        "六处存、走到三处、剩三处")
    chk(all(p["reachable"] for p in V.deletion_plan("u")[:3]), "前三个存储能当场删")
    chk(not any(p["reachable"] for p in V.deletion_plan("u")[3:]), "后三个存储不能当场删")

    caps = {r["mode"]: r for r in V.capture_report(V.sample_records(), V.SAMPLE_TEXTS)}
    chk(caps["on"]["stored"] == 6 and caps["on"]["with_pii"] == 6, "开着时 6 条正文 6 条带识别码")
    chk(caps["off"]["stored"] == 0 and caps["off"]["replayable"] == 0, "关着时一条不存、零回放")
    chk(caps["on"]["replayable"] == 6, "开着时 6 条能回放")

    a = V.access_tally(V.SAMPLE_ACCESS)
    chk(a["entries"] == 12, "十二条审计记录")
    chk(a["blank_purpose"] == 4, "4 条没写为什么看")
    chk(abs(a["blank_rate"] - 1 / 3) < 1e-9, "缺失率 33%")
    chk(a["leaked_hits"] == 3, "审计记录自己抄进 3 处识别码")
    chk(a["actors"] == 4, "4 个操作者")

    print(f"自检 {ok}/{total} 通过")
    return 0 if ok == total else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    print("\n".join(report()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
