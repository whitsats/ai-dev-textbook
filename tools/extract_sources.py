#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 raw/ 中的原始资料转换为 sources/ 下的纯文本素材库。

设计要点
--------
1. 原件只读：raw/ 里的 PDF / zip / md 一律不改动，也不删除。
2. 可重复执行：重复运行会覆盖 sources/ 中由本脚本生成的产物，不会叠加。
3. 保留溯源信息：每个转换出的 md 顶部写入源文件名与页数，正文按页插入 <!-- p.N --> 标记，
   方便写书时回查原文。
4. 仅保留文本类资产：zip 中的图片、.pyc 等二进制不进入 sources/（它们仍在 raw/ 完整留存）。

用法
----
    python tools/extract_sources.py            # 全量转换
    python tools/extract_sources.py --report   # 只统计文本密度，不写文件
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
SRC = ROOT / "sources"

# ---------------------------------------------------------------- PDF 映射表
# 原始 PDF 文件名 -> sources 下的相对路径
PDF_MAP: dict[str, str] = {
    # 第一篇 · 编程地基
    "Python语法手册-核心内容.pdf": "01-编程地基/Python核心语法手册.md",
    # 第二篇 · AI 编程工具链
    "Claude Code 从小白到实战高手：大厂工程化实战手册.pdf":
        "02-AI编程工具链/Claude-Code从入门到实战.md",
    "Codex 从小白到实战高手：大厂工程化实战手册.pdf":
        "02-AI编程工具链/Codex从入门到实战.md",
    "Vibe Coding指南-AI编辑器全栈开发-Qoder.pdf":
        "02-AI编程工具链/Vibe-Coding与AI编辑器全栈开发.md",
    "AI Harness 入门与实践.pdf":
        "02-AI编程工具链/AI-Harness入门与实践.md",
    # 第三篇 · 大模型与 Agent 原理
    "大模型AI Agent知识从0-1笔记.pdf":
        "03-大模型与Agent原理/大模型与AI-Agent从0到1笔记.md",
    # 第四篇 · AI 应用开发框架
    "AI开发基础：Langchain框架从入门到实战开发-附代码 .pdf":
        "04-AI应用开发框架/LangChain从入门到实战.md",
    "AI开发基础：Langgraph框架从入门到实战开发智能体-附带完整可运行代码.pdf":
        "04-AI应用开发框架/LangGraph智能体从入门到实战.md",
    # 第五篇 · RAG 与生产级系统
    "AI应用开发：RAG技术从小白到深入理解-详细版.pdf":
        "05-RAG与生产级系统/RAG技术从入门到深入.md",
    "生产级RAG系统构建实战.pdf":
        "05-RAG与生产级系统/生产级RAG系统构建实战.md",
    "AI应用开发实战：  实战智能出行Agent助手-附代码和前后端可视化界面 .pdf":
        "05-RAG与生产级系统/实战-智能出行Agent助手.md",
    # 第六篇 · 求职冲刺
    "后端高频面试题大集合.pdf":
        "06-求职冲刺/后端高频面试题大集合.md",
}

# 原始 md（已是 markdown，直接归档进 sources）
MD_MAP: dict[str, str] = {
    "AI_Agent面试题合集_1038道.md": "06-求职冲刺/AI-Agent面试题合集-1038道.md",
    "Android面试题合集_1136道.md": "06-求职冲刺/Android面试题合集-1136道.md",
    "Flutter_Dart面试题合集_714道.md": "06-求职冲刺/Flutter-Dart面试题合集-714道.md",
}

ZIP_NAME = "FastAPI基础学习文档.zip"
ZIP_OUT = "01-编程地基/FastAPI基础学习"

# zip 内进入 sources/ 的文本类扩展名（图片/pyc 等留在 raw/）
ZIP_TEXT_EXT = {".md", ".py", ".vue", ".js", ".ts", ".sql", ".sh", ".toml", ".json", ".html"}

HAN = re.compile(r"[\u4e00-\u9fff]")


# ---------------------------------------------------------------- 工具函数
def run_pdftotext(pdf: Path) -> str:
    """用 pdftotext 抽取文本；-raw 保留阅读顺序（对这批 PDF 明显优于 -layout）。"""
    proc = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", "-raw", str(pdf), "-"],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pdftotext 失败：{pdf.name} -> {proc.stderr.decode('utf-8', 'ignore')}")
    return proc.stdout.decode("utf-8", "ignore")


def tidy(text: str) -> list[str]:
    """规范换行、去行尾空白、压缩多余空行，返回按页切分后的文本块。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    pages = [p.strip("\n") for p in text.split("\f")]
    cleaned: list[str] = []
    for page in pages:
        lines = [ln.rstrip() for ln in page.split("\n")]
        # 去掉页内的连续空行（代码块内部的单个空行保留）
        out: list[str] = []
        blanks = 0
        for ln in lines:
            if ln.strip():
                blanks = 0
                out.append(ln)
            else:
                blanks += 1
                if blanks <= 1:
                    out.append("")
        cleaned.append("\n".join(out).strip())
    return cleaned


def to_markdown(pdf: Path, origin_label: str) -> tuple[str, dict]:
    pages = tidy(run_pdftotext(pdf))
    han = sum(len(HAN.findall(p)) for p in pages)
    total = sum(len(p) for p in pages)
    empty = sum(1 for p in pages if len(p) < 30)

    body = []
    for i, page in enumerate(pages, 1):
        if not page:
            continue
        body.append(f"<!-- p.{i} -->\n\n{page}")
    stats = {
        "pages": len(pages),
        "empty_pages": empty,
        "chars": total,
        "han": han,
        "han_ratio": (han / total) if total else 0.0,
    }
    header = (
        f"# {pdf.stem}\n\n"
        f"> **素材来源**：`{origin_label}`\n"
        f"> **页数**：{stats['pages']}（其中无文本页 {empty} 页，多为截图/图示）\n"
        f"> **正文规模**：约 {total:,} 字符，其中汉字 {han:,} 个\n"
        f"> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，"
        f"未做人工校订；引用时请以原文为准。\n\n---\n"
    )
    return header + "\n\n---\n\n".join(body) + "\n", stats


def convert_pdfs(report_only: bool) -> list[dict]:
    results = []
    for name, rel in PDF_MAP.items():
        pdf = RAW / "pdf" / name
        if not pdf.exists():
            results.append({"name": name, "status": "缺失", "stats": None})
            continue
        if report_only:
            pages = tidy(run_pdftotext(pdf))
            han = sum(len(HAN.findall(p)) for p in pages)
            total = sum(len(p) for p in pages)
            stats = {
                "pages": len(pages),
                "empty_pages": sum(1 for p in pages if len(p) < 30),
                "chars": total, "han": han,
                "han_ratio": (han / total) if total else 0.0,
            }
            results.append({"name": name, "status": "统计", "stats": stats})
            continue
        md, stats = to_markdown(pdf, f"raw/pdf/{name}")
        dest = SRC / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(md, encoding="utf-8")
        results.append({"name": name, "status": f"→ {rel}", "stats": stats})
    return results


def copy_original_mds() -> list[dict]:
    out = []
    for name, rel in MD_MAP.items():
        src = RAW / "md" / name
        if not src.exists():
            out.append({"name": name, "status": "缺失"})
            continue
        dest = SRC / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8", errors="ignore")
        dest.write_text(text.rstrip() + "\n", encoding="utf-8")
        out.append({"name": name, "status": f"→ {rel}（{len(text.splitlines()):,} 行）"})
    return out


def extract_zip() -> list[dict]:
    """zip 完整解包到 raw/（保留图片等全部资产），文本类文件另存一份到 sources/。"""
    zpath = RAW / "zip" / ZIP_NAME
    if not zpath.exists():
        return [{"name": ZIP_NAME, "status": "缺失"}]

    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
        inner_root = names[0].split("/")[0]  # FastAPI基础学习文档

        # 1) 完整解包到 raw/，跳过 mac 垃圾文件
        full_dir = RAW / inner_root
        for item in names:
            if item.endswith("/") or "__MACOSX" in item:
                continue
            target = full_dir / item
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(item) as fsrc, open(target, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)

        # 2) 文本类文件 + 章节 PDF 转换结果进入 sources/
        out_dir = SRC / ZIP_OUT
        kept, pdfs = 0, []
        for item in names:
            if item.endswith("/") or "__MACOSX" in item:
                continue
            suffix = Path(item).suffix.lower()
            rel = Path(item).relative_to(inner_root)
            if suffix == ".pdf":
                pdfs.append(Path(item))
            elif suffix in ZIP_TEXT_EXT:
                dest = out_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(item) as fsrc, open(dest, "wb") as fdst:
                    shutil.copyfileobj(fsrc, fdst)
                kept += 1

        # 3) 章节 PDF -> md
        conv = 0
        for item in pdfs:
            name = Path(item).name
            rel = Path(item).relative_to(inner_root).with_suffix(".md")
            src_pdf = full_dir / item
            try:
                md, _ = to_markdown(src_pdf, f"raw/{inner_root}/{item}")
            except Exception as exc:  # 单个失败不影响整体
                print(f"  ! 转换失败 {name}: {exc}", file=sys.stderr)
                continue
            dest = out_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(md, encoding="utf-8")
            conv += 1

    return [{"name": ZIP_NAME,
             "status": f"完整解包 → raw/{inner_root}/；文本 {kept} 个 → sources/{ZIP_OUT}/；PDF→md {conv} 个"}]


def write_index(pdf_rows, md_rows, zip_rows) -> None:
    lines = [
        "# 素材库索引（sources/）",
        "",
        "本目录由 `tools/extract_sources.py` 从 `raw/` 自动生成，是编写教材正文的素材来源。",
        "原件永久保留在 `raw/`（未纳入 git，见 `.gitignore`）。",
        "",
        "## PDF 提取结果",
        "",
        "| 原始文件 | 素材文件 | 页数 | 无文本页 | 汉字占比 |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for r in pdf_rows:
        s = r.get("stats")
        if not s:
            lines.append(f"| {r['name']} | {r['status']} | - | - | - |")
            continue
        lines.append(
            f"| {r['name']} | {r['status'].replace('→ ', '')} | {s['pages']} | "
            f"{s['empty_pages']} | {s['han_ratio']:.1%} |"
        )
    lines += ["", "## Markdown 归档", ""]
    for r in md_rows:
        lines.append(f"- `{r['name']}` {r['status']}")
    lines += ["", "## 压缩包", ""]
    for r in zip_rows:
        lines.append(f"- `{r['name']}`：{r['status']}")
    lines.append("")
    (SRC / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="只统计，不写文件")
    args = ap.parse_args()

    if not RAW.exists():
        print(f"raw/ 不存在：{RAW}", file=sys.stderr)
        return 1

    pdf_rows = convert_pdfs(args.report)
    print("PDF 提取：")
    for r in pdf_rows:
        s = r.get("stats")
        extra = (f" | 页 {s['pages']:>5} | 无文本 {s['empty_pages']:>4} | 汉字 {s['han_ratio']:>5.1%} | "
                 f"{s['chars']:>9,} 字符") if s else ""
        print(f"  - {r['name'][:52]:<54} {r['status']}{extra}")

    if args.report:
        return 0

    md_rows = copy_original_mds()
    print("\nMarkdown 归档：")
    for r in md_rows:
        print(f"  - {r['name']:<34} {r['status']}")

    print("\n压缩包处理：")
    zip_rows = extract_zip()
    for r in zip_rows:
        print(f"  - {r['name']}: {r['status']}")

    write_index(pdf_rows, md_rows, zip_rows)
    print("\n已生成 sources/README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
