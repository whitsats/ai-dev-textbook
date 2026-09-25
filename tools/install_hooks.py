#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安装提交前校验钩子（install_hooks.py）

把仓库里的 .githooks/ 设为 git 的钩子目录，使 pre-commit 检查对**所有**提交生效，
不依赖每个人手动记着跑脚本。

用法
----
    python tools/install_hooks.py            # 安装（设置 core.hooksPath）
    python tools/install_hooks.py --status   # 查看当前状态
    python tools/install_hooks.py --uninstall  # 卸载（恢复默认 .git/hooks）
    python tools/install_hooks.py --self-test  # 用一个临时违规章节验证钩子真的会拦

说明：修改的是**本仓库**的 git 配置（core.hooksPath，本地作用域），
不动全局配置，也不影响其它仓库。
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK_DIR = ".githooks"
HOOK_FILE = ROOT / HOOK_DIR / "pre-commit"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=check,
    )


def current_hooks_path() -> str:
    try:
        return git("config", "--local", "--get", "core.hooksPath").stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def show_status() -> bool:
    installed = current_hooks_path() == HOOK_DIR
    print(f"钩子目录配置（core.hooksPath）：{current_hooks_path() or '（未设置，用默认 .git/hooks）'}")
    print(f"pre-commit 脚本：{'存在' if HOOK_FILE.exists() else '缺失'}  {HOOK_FILE}")
    print(f"状态：{'✅ 已启用（提交时自动校验）' if installed else '⬜ 未启用（校验不会自动跑）'}")
    return installed


def install() -> int:
    if not HOOK_FILE.exists():
        print(f"✖ 未找到 {HOOK_FILE}", file=sys.stderr)
        return 1
    git("config", "--local", "core.hooksPath", HOOK_DIR)
    # 让脚本在各类 clone / CI 环境里保持可执行位（Windows 上失败可忽略）
    try:
        git("update-index", "--add", "--chmod=+x", f"{HOOK_DIR}/pre-commit")
    except subprocess.CalledProcessError:
        pass
    try:
        HOOK_FILE.chmod(HOOK_FILE.stat().st_mode | 0o111)
    except OSError:
        pass
    show_status()
    print("\n以后每次 git commit 都会先跑 tools/lint_book.py，有错误直接拦下。")
    # 绕过分两档：窄的那一档只跳「联网探测新增链接」，网络不通时用它——
    # 若只有核选项，人就会为了省一次联网把本地所有的门一起关掉（见 STYLE 8.5）。
    print("网络不通：SKIP_BOOK_LINKS=1 git commit ...（只跳联网探测那一档，其余各档照跑）")
    print("镜像/紧急：SKIP_BOOK_CHECKS=1 git commit ...（跳全部；CI 仍会检查，且链接是全量）")
    return 0


def uninstall() -> int:
    git("config", "--local", "--unset", "core.hooksPath", check=False)
    show_status()
    print("\n已恢复默认钩子目录（.git/hooks）。")
    return 0


def self_test() -> int:
    """写一个必然违规的临时章节，验证钩子确实能拦下提交。"""
    print("== 自检：验证钩子会拦下违规提交 ==")
    probe = ROOT / "book" / "00-导论" / "9.9-钩子自检临时文件.md"
    probe.write_text("# 9.9 钩子自检\n\n众所周知，这段文字故意违规。\n", encoding="utf-8")
    blocked = False
    try:
        git("add", str(probe.relative_to(ROOT)))
        # 钩子是 sh 脚本：Windows 上不能直接执行，必须经由 sh/bash
        # （Git 自身也是用捆绑的 sh 跑钩子，这里复现同样的调用方式）
        shell = shutil.which("sh") or shutil.which("bash")
        cmd = [shell, HOOK_FILE.as_posix()] if shell else [str(HOOK_FILE)]
        try:
            result = subprocess.run(
                cmd, cwd=ROOT, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            blocked = result.returncode != 0
            print(f"钩子退出码：{result.returncode} → {'✅ 成功拦下' if blocked else '✖ 没拦住，检查脚本逻辑'}")
            if not blocked:
                print(result.stdout[-800:])
        except OSError as exc:
            print(f"✖ 无法执行钩子脚本：{exc}", file=sys.stderr)
    finally:
        git("rm", "--cached", "--force", str(probe.relative_to(ROOT)), check=False)
        probe.unlink(missing_ok=True)
    print(f"临时文件已清理：{not probe.exists()}")
    return 0 if blocked else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="安装/查看提交前校验钩子")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--self-test", action="store_true", dest="self_test")
    args = ap.parse_args()

    if not (ROOT / ".git").exists():
        print("✖ 当前目录不是 git 仓库根目录", file=sys.stderr)
        return 1
    if shutil.which("git") is None:
        print("✖ 找不到 git 命令", file=sys.stderr)
        return 1

    if args.uninstall:
        return uninstall()
    if args.status:
        show_status()
        return 0
    if args.self_test:
        return self_test()
    return install()


if __name__ == "__main__":
    sys.exit(main())
