"""知舟的词元账：官方 count_tokens 为准，本地编码器只给估算值。"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

ORDER = ("tools", "system", "messages")   # 也是前缀缓存的命中顺序


@dataclass
class Prompt:
    """一次请求的全部文本。顺序就是计费与前缀缓存的顺序（3.1.6），所以要显式给。"""

    parts: dict[str, str]
    order: tuple[str, ...] = ORDER

    def serialize(self) -> str:
        return "".join(self.parts[k] for k in self.order if k in self.parts)


@dataclass
class Count:
    parts: dict[str, int]
    source: str = "official"        # official ｜ local-estimate

    @property
    def input_tokens(self) -> int:
        return sum(self.parts.values())

    def heavy(self) -> list[tuple[str, int, float]]:
        if not self.input_tokens:          # 空请求也要能报账，而不是在除零上崩掉
            return []
        return sorted(((k, v, v / self.input_tokens) for k, v in self.parts.items()),
                      key=lambda x: -x[1])


class Counter:
    """官方计数为主；本地编码器只用于没有凭据时的估算，且必须标注来源。"""

    def __init__(self, official: Callable[[str], int], local: Callable[[str], int]) -> None:
        self.official, self.local = official, local
        self.cache: dict[str, int] = {}
        self.calls = 0          # 真正算过的文本段数（去重后）
        self.hits = 0

    def count(self, text: str, *, exact: bool = True) -> int:
        key = ("o" if exact else "l") + ":" + text
        if key in self.cache:                  # tools 与 system 每轮逐字相同，只该问一次
            self.hits += 1
            return self.cache[key]
        self.calls += 1
        n = self.official(text) if exact else self.local(text)
        self.cache[key] = n
        return n

    def report(self, p: Prompt, *, exact: bool = True) -> Count:
        return Count({k: self.count(p.parts[k], exact=exact)
                      for k in p.order if k in p.parts},
                     "official" if exact else "local-estimate")


def local_counter(model: str = "o200k_base") -> Callable[[str], int]:
    """本地估算器：只用来预警，不用来判定（3.1.6 的结论）。"""
    import tiktoken

    enc = tiktoken.get_encoding(model)
    return lambda s: len(enc.encode(s))


def official_counter(local: Callable[[str], int] | None = None) -> Callable[[str], int]:
    """官方口径的替身。

    真实项目里这里是一次 `count_tokens` 请求；本参考实现没有该端点的凭据，
    所以按官方文档对新分词器的说明（同一段文本约多 30%）构造。
    **它只保证形状与调用点正确，不保证数字等于线上计费值**——要精确计费，
    请把函数体换成服务商的计数接口，或者用响应里的 usage 回填。
    """
    base = local or local_counter()
    return lambda s: int(base(s) * 1.3)


def usage_tokens(usage: dict | None) -> int:
    """把服务端返回的 usage 折算成一个数：输入与输出都算这次请求的花费。"""
    if not usage:
        return 0
    return int(usage.get("prompt_tokens", 0)) + int(usage.get("completion_tokens", 0))


def tools_json(specs: list[dict]) -> str:
    """工具定义进提示的那一段文本。顺序稳定，否则前缀缓存每一轮都失效。"""
    return json.dumps(specs, ensure_ascii=False, sort_keys=False)
