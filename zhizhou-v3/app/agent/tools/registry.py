"""知舟的工具注册表：一处定义、一处校验、一处调用。

三个约束都落在同一个文件里，因为它们是同一件事的三面：
  · 给模型看的 schema 与实现必须同源，否则说明书写着必填、代码却有默认值；
  · 参数在调用工具**之前**校验，工具的职责是干活，不是过滤坏输入；
  · 写操作必须带幂等键——重试与并行是常态，重跑不能变成重复写入。
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

READONLY, WRITE = "readonly", "write"
MAX_RESULT_CHARS = 2_000        # 单条工具结果的体积上限（第 3.5.6 节）


@dataclass(frozen=True)
class Problem:
    """参数问题：kind 用来分类报账，detail 用来回给模型（第 3.5.7 节）。"""

    kind: str
    detail: str

    def message(self) -> str:
        return f"{self.kind}：{self.detail}"


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str = ""
    retryable: bool = False

    def payload(self) -> str:
        """回给模型的那一段文本：成功给数据，失败给可执行的建议，绝不截断成空。"""
        body = self.error if not self.ok else json.dumps(self.data, ensure_ascii=False)
        if len(body) > MAX_RESULT_CHARS:
            body = body[:MAX_RESULT_CHARS] + f"……（已截断，原文 {len(body)} 字）"
        return body

    def __str__(self) -> str:                      # 循环里直接 f"{res}" 也不会变成对象地址
        return self.payload()


class ToolError(Exception):
    """工具自己抛的错。retryable 为真表示「可以再试」，否则「别试了，换方法」。"""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.message, self.retryable = message, retryable


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    access: str
    handler: Callable[..., Any]
    guard: Callable[..., None] | None = None      # 授权：只读参数，绝不碰数据

    def spec(self) -> dict:
        """给模型看的定义（规范形）。additionalProperties=False 与 required 齐全，才开得了严格模式。"""
        return {"name": self.name, "description": self.description,
                "input_schema": {**self.schema, "additionalProperties": False}}


@dataclass
class Registry:
    tools: dict[str, Tool] = field(default_factory=dict)
    executed: list[str] = field(default_factory=list)   # 记账：每次真的执行了什么
    audit: list[str] = field(default_factory=list)      # 被拒的调用也要留痕（第 3.8 节）
    _seen: dict[str, ToolResult] = field(default_factory=dict)

    def add(self, tool: Tool) -> Tool:
        if tool.name in self.tools:
            raise ValueError(f"工具名重复：{tool.name}")
        self.tools[tool.name] = tool
        return tool

    def specs(self) -> list[dict]:
        return [t.spec() for t in self.tools.values()]

    def specs_openai(self) -> list[dict]:
        """同一份定义换一个键名：`input_schema` → `parameters`（OpenAI 兼容方言）。"""
        return [{"name": t.name, "description": t.description,
                 "parameters": {**t.schema, "additionalProperties": False}}
                for t in self.tools.values()]

    def validate(self, name: str, args: dict) -> list[Problem]:
        t = self.tools.get(name)
        if t is None:
            return [Problem("未知工具", f"没有注册名为 {name} 的工具")]
        props, required = t.schema.get("properties", {}), t.schema.get("required", [])
        out = [Problem("缺必填", f"{k} 未提供") for k in required if k not in args]
        for k, v in args.items():
            rule = props.get(k)
            if rule is None:
                out.append(Problem("多出字段", f"{k} 不在 schema 里"))
            else:
                out += _check(k, v, rule)
        return out

    def call(self, name: str, args: dict, *, idem: str | None = None,
             allow_write: bool = False) -> ToolResult:
        """唯一入口。顺序固定：校验 → 授权 → 权限档 → 幂等 → 执行。"""
        t = self.tools.get(name)
        if probs := self.validate(name, args):
            result = ToolResult(False, error="；".join(p.message() for p in probs))
        elif t.guard is not None and (denied := _run_guard(t.guard, args)) is not None:
            result = ToolResult(False, error=denied)
        elif t.access == WRITE and not allow_write:
            result = ToolResult(False, error=f"权限不足：{name} 是写操作，本轮未获授权")
        elif t.access == WRITE and not idem:
            result = ToolResult(False, error=f"缺少幂等键：重复调用 {name} 会写入两次")
        elif t.access == WRITE and idem in self._seen:
            return self._seen[idem]                     # 重跑返回第一次的结果，不重复写
        else:
            self.executed.append(name)
            try:
                result = ToolResult(True, data=t.handler(**args))
            except ToolError as exc:
                result = ToolResult(False, error=exc.message, retryable=exc.retryable)
        if not result.ok:
            self.audit.append(f"{name}({json.dumps(args, ensure_ascii=False)}) → {result.error}")
        elif t.access == WRITE and idem:
            self._seen[idem] = result
        return result


def _run_guard(guard: Callable[..., None], args: dict) -> str | None:
    """授权钩子：通过返回 None，拒绝返回一句可执行的说明。它只能看参数。"""
    try:
        guard(**args)
    except ToolError as exc:
        return exc.message
    return None


def _check(key: str, value: Any, rule: dict) -> list[Problem]:
    kind = rule.get("type")
    if kind == "string" and not isinstance(value, str):
        return [Problem("类型错", f"{key} 应为 string，实为 {type(value).__name__}")]
    if kind == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
        return [Problem("类型错", f"{key} 应为 integer，实为 {type(value).__name__}")]
    if "minimum" in rule and isinstance(value, int) and value < rule["minimum"]:
        return [Problem("范围越界", f"{key}={value} 小于下限 {rule['minimum']}")]
    if "enum" in rule and value not in rule["enum"]:
        return [Problem("枚举越界", f"{key}={value!r} 不在 {rule['enum']} 里")]
    return []
