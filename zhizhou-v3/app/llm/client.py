"""知舟的模型客户端：超时、重试、结构校验、提示版本。

**唯一模型入口**：全项目只有这里发模型请求，其它模块不得直接 httpx.post。
两种方言（OpenAI 兼容 / Anthropic）只影响传输层，上层的重试与校验完全共用——
换一家服务商要改的是 `Config.provider`，不是调用方。
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app.llm.schemas import ArticleSummary, validate

MODEL = "claude-opus-5"          # Anthropic 方言的固定快照，不用浮动别名（3.1.7）
DEFAULT_BASE_URL = {"openai": "https://api.openai.com/v1", "anthropic": "https://api.anthropic.com"}
DEFAULT_MODEL = {"openai": "gpt-4.1-mini", "anthropic": MODEL}


class LlmError(Exception):
    """统一出口：调用方只处理这一种异常，不必认识 httpx 或 pydantic 的异常。"""

    def __init__(self, kind: str, detail: str, attempts: int, spent: int = 0) -> None:
        super().__init__(f"{kind}: {detail}")
        self.kind, self.detail, self.attempts, self.spent = kind, detail, attempts, spent


# 重试有用的失败；不在这个集合里的一律不重试。
# 「服务端错误」（5xx）与「限流」同类：等一会儿再来；400 类才是参数问题，重试只会拿到同一个错。
RETRYABLE = {"超时", "限流", "连接断开", "服务端错误"}


class LlmTransportError(Exception):
    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(f"{kind}: {detail}")
        self.kind, self.detail = kind, detail


@dataclass
class Config:
    """一次调用的全部外部配置。**密钥只从环境变量来，只存在内存里。**"""

    api_key: str
    provider: str = "openai"                 # openai ｜ anthropic
    base_url: str = ""
    model: str = ""
    timeout: float = 8.0                 # 与第 3.2 节一致；线上把它调大（.env 里有 LLM_TIMEOUT）
    max_attempts: int = 2
    max_tokens: int = 1_024

    def __post_init__(self) -> None:
        self.base_url = (self.base_url or DEFAULT_BASE_URL.get(self.provider, "")).rstrip("/")
        self.model = self.model or DEFAULT_MODEL.get(self.provider, MODEL)
        if not self.base_url.startswith("http"):
            raise LlmError("参数错误", f"base_url 不合法：{self.base_url!r}", 0)

    @classmethod
    def from_env(cls) -> Config:
        if not (key := os.environ.get("LLM_API_KEY")):
            # 启动即失败，而不是第一次调用时才失败：密钥缺失是部署问题，不是请求问题
            raise LlmError("参数错误", "缺少环境变量 LLM_API_KEY", 0)
        return cls(
            api_key=key,
            provider=os.environ.get("LLM_PROVIDER", "openai"),
            base_url=os.environ.get("LLM_BASE_URL", ""),
            model=os.environ.get("LLM_MODEL", ""),
            timeout=float(os.environ.get("LLM_TIMEOUT", "30")),
            max_attempts=int(os.environ.get("LLM_MAX_ATTEMPTS", "2")),
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "1024")),
        )

    def redacted(self) -> dict:
        """日志里能安全打印的那一份：密钥只留长度与末四位。"""
        return {"provider": self.provider, "base_url": self.base_url, "model": self.model,
                "timeout": self.timeout, "api_key": f"***（{len(self.api_key)} 位）"}


@dataclass
class RawReply:
    data: dict
    tokens: int


@dataclass
class Reply:
    summary: ArticleSummary
    tokens: int
    attempts: int
    elapsed: float
    prompt_version: str


@dataclass
class ToolCall:
    """模型给的一次工具调用请求。参数是**文本**，还没有解析（3.5.5）。"""

    id: str
    name: str
    arguments: str

    def parsed(self) -> dict:
        """解析参数。坏 JSON 不在这里抛——交给注册表当成一条「参数错」处理。"""
        try:
            got = json.loads(self.arguments or "{}")
        except json.JSONDecodeError:
            return {"__bad_json__": self.arguments}
        return got if isinstance(got, dict) else {"__bad_json__": self.arguments}


@dataclass
class ChatReply:
    content: str
    tool_calls: list[ToolCall]
    tokens: int
    attempts: int
    model: str = ""
    # 输入与输出**分开报**：官方语义约定里它们是两个属性（`gen_ai.usage.input_tokens`
    # / `gen_ai.usage.output_tokens`），而且它们两笔钱的价格不同。合成一个总数之后再
    # 想拆开是拆不出来的——3.9 要看的就是「每轮重发的历史占了多少」（实测约七成）。
    in_tokens: int = 0
    out_tokens: int = 0


def prompt_version(path: Path) -> str:
    """提示版本号 = 内容哈希前 8 位。改一个字就变，日志里能定位到那次改动（3.2.10）。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def _classify(exc: Exception) -> LlmTransportError:
    if isinstance(exc, httpx.TimeoutException):
        return LlmTransportError("超时", str(exc))
    if isinstance(exc, httpx.TransportError):
        return LlmTransportError("连接断开", str(exc))
    return LlmTransportError("未知", str(exc))


def _status_error(status: int, text: str, retry_after: str = "") -> LlmTransportError:
    if status == 429:
        return LlmTransportError("限流", retry_after or text[:200])
    if status >= 500:
        return LlmTransportError("服务端错误", f"HTTP {status}：{text[:200]}")
    return LlmTransportError("参数错误", f"HTTP {status}：{text[:200]}")


def call_model(prompt_path: Path, payload: str, *, transport, config: Config,
               clock: Callable[[], float] = time.monotonic) -> Reply:
    """一次调用：受约束解码交给服务端，客户端只管超时、重试与校验。"""
    body = prompt_path.read_text(encoding="utf-8") + "\n\n" + payload
    version = prompt_version(prompt_path)
    started, spent, why, detail = clock(), 0, "", ""
    for attempt in range(1, config.max_attempts + 1):
        try:
            raw = transport(body, config)
        except LlmTransportError as exc:
            why, detail = exc.kind, exc.detail
            if why not in RETRYABLE:                    # 不可重试的失败，立刻抛
                raise LlmError(why, detail, attempt, spent) from exc
        else:
            spent += raw.tokens
            try:
                data = validate(raw.data)
            except ValueError as exc:                   # 结构错不重试：重试只会拿到同样的结构
                raise LlmError("结构不合 schema", str(exc), attempt, spent) from exc
            return Reply(data, spent, attempt, clock() - started, version)
    raise LlmError(why, f"{detail}（重试用尽）", config.max_attempts, spent)


def chat(messages: list[dict], *, config: Config, tools: list[dict] | None = None,
         tool_choice: str | None = None, response_format: dict | None = None,
         transport=None, clock: Callable[[], float] = time.monotonic,
         prompt_version_tag: str = "", max_tokens: int | None = None) -> ChatReply:
    """对话（可带工具）。与 `call_model` 同一套超时与重试分类，只是不解析成模型对象。

    `prompt_version_tag` 由调用方传入（如 `app/agent/prompts/agent.md` 的哈希），
    它进日志不进请求体——服务端不需要知道我们的版本号。

    `max_tokens` 可单次覆盖：**结构化输出撞上上限会得到一段被截断的 JSON**，
    那不是「格式不对」而是「没写完」，所以这里单独认出来当错误抛，而不是交给 json.loads 崩。
    """
    transport = transport or chat_http
    spent, why, detail = 0, "", ""
    spent_in = spent_out = 0           # 重试过的那几次也要计入：它们真的花了（OTel 也这么要求）
    for attempt in range(1, config.max_attempts + 1):
        try:
            raw = transport(messages, config, tools=tools, tool_choice=tool_choice,
                            response_format=response_format, max_tokens=max_tokens)
        except LlmTransportError as exc:
            why, detail = exc.kind, exc.detail
            if why not in RETRYABLE:
                raise LlmError(why, detail, attempt, spent) from exc
        else:
            spent += raw.tokens
            spent_in += raw.in_tokens
            spent_out += raw.out_tokens
            if raw.finish_reason == "length":
                # 不重试：同样的上限重试只会再截一次。要改的是这次调用的 max_tokens。
                raise LlmError("输出被截断",
                               f"达到 max_tokens={max_tokens or config.max_tokens}。"
                               "结构化输出被截断后不是合法 JSON，请提高上限或把任务拆小",
                               attempt, spent)
            return ChatReply(raw.content, raw.tool_calls, spent, attempt, config.model,
                             spent_in, spent_out)
    raise LlmError(why, f"{detail}（重试用尽）", config.max_attempts, spent)


@dataclass
class RawChat:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens: int = 0
    finish_reason: str = ""          # stop ｜ length（被 max_tokens 截断）｜ tool_calls
    in_tokens: int = 0               # 服务商分开报的两笔：默认 0 —— 假传输层可以不给
    out_tokens: int = 0


def chat_http(messages: list[dict], cfg: Config, *, tools=None, tool_choice=None,
              response_format=None, max_tokens: int | None = None) -> RawChat:
    """按方言组装请求、按方言读回响应。这是全项目唯一发模型请求的地方。"""
    if cfg.provider == "anthropic":
        body = _anthropic_body(messages, cfg, tools, tool_choice, response_format,
                               max_tokens=max_tokens or cfg.max_tokens)
        headers = {"x-api-key": cfg.api_key, "anthropic-version": "2023-06-01"}
        url = f"{cfg.base_url}/v1/messages"
    else:
        body = _openai_body(messages, cfg, tools, tool_choice, response_format,
                            max_tokens=max_tokens or cfg.max_tokens)
        headers = {"Authorization": f"Bearer {cfg.api_key}"}
        url = f"{cfg.base_url}/chat/completions"
    try:
        resp = httpx.post(url, timeout=cfg.timeout, headers=headers, json=body)
    except Exception as exc:                      # noqa: BLE001 —— 分类后统一从 LlmTransportError 出去
        raise _classify(exc) from exc
    if resp.status_code >= 400:
        raise _status_error(resp.status_code, resp.text, resp.headers.get("retry-after", ""))
    return _parse_reply(resp.json(), cfg)


def _openai_body(messages, cfg, tools, tool_choice, response_format=None,
                 max_tokens: int | None = None) -> dict:
    body: dict = {"model": cfg.model, "messages": messages,
                  "max_tokens": max_tokens or cfg.max_tokens}
    if tools:
        body["tools"] = [{"type": "function", "function": t} for t in tools]
        body["tool_choice"] = tool_choice or "auto"
    if response_format:
        body["response_format"] = response_format
    return body


def _anthropic_body(messages, cfg, tools, tool_choice, response_format=None,
                    max_tokens: int | None = None) -> dict:
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [_to_anthropic_message(m) for m in messages if m["role"] != "system"]
    body: dict = {"model": cfg.model, "max_tokens": max_tokens or cfg.max_tokens,
                  "messages": rest}
    if system:
        body["system"] = system
    if tools:
        body["tools"] = [{"name": t["name"], "description": t.get("description", ""),
                          "input_schema": t["parameters"]} for t in tools]
        if tool_choice:
            body["tool_choice"] = {"type": {"auto": "auto", "required": "any",
                                            "none": "none"}.get(tool_choice, "auto")}
    if response_format:
        body["output_config"] = {"format": {"type": "json_schema",
                                            "schema": response_format.get("json_schema", {})
                                            .get("schema", {})}}
    return body


def _to_anthropic_message(m: dict) -> dict:
    """OpenAI 形的消息 → Anthropic 形。工具结果在 Anthropic 里是 user 消息里的块。"""
    if m["role"] == "tool":
        return {"role": "user", "content": [{"type": "tool_result",
                                             "tool_use_id": m["tool_call_id"],
                                             "content": m.get("content") or ""}]}
    if m["role"] == "assistant" and m.get("tool_calls"):
        blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
        blocks += [{"type": "tool_use", "id": c["id"], "name": c["function"]["name"],
                    "input": json.loads(c["function"]["arguments"] or "{}")}
                   for c in m["tool_calls"]]
        return {"role": "assistant", "content": blocks}
    return {"role": m["role"], "content": m.get("content") or ""}


def _parse_reply(data: dict, cfg: Config) -> RawChat:
    usage = data.get("usage") or {}
    # 两家方言的字段名不同（OpenAI `prompt/completion`、Anthropic `input/output`），
    # 分开读之后再求和——**先合并就读不出比例了**。
    in_tokens = int(usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0))
    out_tokens = int(usage.get("completion_tokens", 0) or usage.get("output_tokens", 0))
    tokens = in_tokens + out_tokens
    if cfg.provider == "anthropic":
        blocks = data.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        calls = [ToolCall(b["id"], b["name"], json.dumps(b.get("input", {}), ensure_ascii=False))
                 for b in blocks if b.get("type") == "tool_use"]
        finish = "length" if data.get("stop_reason") == "max_tokens" else "stop"
    else:
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = msg.get("content") or ""
        calls = [ToolCall(c.get("id", ""), (c.get("function") or {}).get("name", ""),
                          (c.get("function") or {}).get("arguments", ""))
                 for c in (msg.get("tool_calls") or [])]
        finish = choice.get("finish_reason") or ""
    return RawChat(text, calls, tokens, finish, in_tokens=in_tokens, out_tokens=out_tokens)


def http_transport(body: str, cfg: Config) -> RawReply:
    """结构化输出专用的一次调用：提示是整段文本，输出按 schema 约束。"""
    if cfg.provider == "anthropic":
        return _anthropic_structured(body, cfg)
    return _openai_structured(body, cfg)


def _openai_structured(body: str, cfg: Config) -> RawReply:
    payload = {"model": cfg.model, "max_tokens": cfg.max_tokens,
               "messages": [{"role": "user", "content": body}],
               "response_format": {"type": "json_schema",
                                   "json_schema": {"name": "ArticleSummary", "strict": True,
                                                   "schema": ArticleSummary.json_schema_strict()}}}
    try:
        resp = httpx.post(f"{cfg.base_url}/chat/completions", timeout=cfg.timeout,
                          headers={"Authorization": f"Bearer {cfg.api_key}"}, json=payload)
    except Exception as exc:                      # noqa: BLE001
        raise _classify(exc) from exc
    if resp.status_code >= 400:
        raise _status_error(resp.status_code, resp.text, resp.headers.get("retry-after", ""))
    got = resp.json()
    usage = got.get("usage") or {}
    choice = (got.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    if choice.get("finish_reason") == "length":
        # 真实撞到过：schema 是对的、模型也在按 schema 写，但它没写完就被上限截断了。
        raise LlmTransportError("输出被截断", f"max_tokens={cfg.max_tokens} 不够写完这份 schema")
    return RawReply(json.loads(text), int(usage.get("prompt_tokens", 0))
                    + int(usage.get("completion_tokens", 0)))


def _anthropic_structured(body: str, cfg: Config) -> RawReply:
    payload = {"model": cfg.model, "max_tokens": cfg.max_tokens,
               "messages": [{"role": "user", "content": body}],
               "output_config": {"format": {"type": "json_schema",
                                            "schema": ArticleSummary.model_json_schema()}}}
    try:
        resp = httpx.post(f"{cfg.base_url}/v1/messages", timeout=cfg.timeout,
                          headers={"x-api-key": cfg.api_key,
                                   "anthropic-version": "2023-06-01"}, json=payload)
    except Exception as exc:                      # noqa: BLE001
        raise _classify(exc) from exc
    if resp.status_code >= 400:
        raise _status_error(resp.status_code, resp.text, resp.headers.get("retry-after", ""))
    got = resp.json()
    if got.get("stop_reason") == "max_tokens":
        raise LlmTransportError("输出被截断", f"max_tokens={cfg.max_tokens} 不够写完这份 schema")
    text = next(b["text"] for b in got["content"] if b["type"] == "text")
    usage = got["usage"]
    return RawReply(json.loads(text), usage["input_tokens"] + usage["output_tokens"])


if __name__ == "__main__":
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    good = tmp / "article_summary.md"
    bad = tmp / "article_summary_v4.md"
    CONSTRAINT = "tags 只能从清单里选，最多三个"
    good.write_text(f"你是知舟的编辑助手。把正文压成三句话以内的摘要。\n{CONSTRAINT}。",
                    encoding="utf-8")
    bad.write_text("你是知舟的编辑助手。把正文压成三句话以内的摘要。\n"
                   "给这篇文章挑几个贴切的标签。", encoding="utf-8")
    ARTICLE = "《JWT 刷新令牌怎么做》：黑名单与滑动过期两种做法，以及各自的失效边界。"

    now = {"t": 0.0}
    clock = lambda: now["t"]                                          # noqa: E731

    def tick(cfg: Config, step: str) -> None:
        now["t"] += {"成功": 1.5, "超时": cfg.timeout}.get(step, 0.2)  # 成功的调用也花时间

    def script(*steps: str, data=None, tokens: int = 412):
        """假传输层：按剧本依次返回，剧本用完后重复最后一步。"""
        seq = list(steps) or ["成功"]

        def transport(body: str, cfg: Config) -> RawReply:
            step = seq.pop(0) if len(seq) > 1 else seq[0]
            tick(cfg, step)
            if step == "成功":
                return RawReply(data if data is not None else
                                {"summary": "讲两种做法", "tags": ["后端"]}, tokens)
            raise LlmTransportError(step, "连接尝试失败")
        return transport

    cfg = Config(api_key="来自环境变量")
    cases = [
        ("首次成功", script("成功"), good),
        ("超时后成功", script("超时", "成功"), good),
        ("限流后成功", script("限流", "成功"), good),
        ("结构不合 schema", script("成功", data={"summary": "讲两种做法", "tags": ["安全"]}), good),
        ("参数错误", script("参数错误"), good),
        ("一直超时", script("超时"), good),
    ]
    print("=== 一、失败分类决定重试策略（超时 8s ／ 最多 2 次）===")
    print(f"  {'剧本':<16}{'结果':<30}{'重试':>4}{'总耗时':>8}{'累计词元':>10}")
    for label, transport, prompt in cases:
        now["t"] = 0.0
        try:
            r = call_model(prompt, ARTICLE, transport=transport, config=cfg, clock=clock)
            out, retries, tokens = (f"返回 {r.summary.tags}，版本 {r.prompt_version}",
                                    r.attempts - 1, r.tokens)
        except LlmError as exc:
            out = f"抛 LlmError（{exc.kind}）"
            retries = max(exc.attempts - 1, 0) if exc.kind in RETRYABLE else 0
            tokens = exc.spent
        print(f"  {label:<16}{out:<30}{retries:>4}{now['t']:>7.1f}s{tokens:>10}")

    print()
    print("=== 二、回归集：5 条用例，两个提示版本各跑一次（第 3.2.10 节）===")
    CORPUS = [("《FastAPI 依赖注入的两种写法》", "后端"),
              ("《SQLAlchemy 的关系映射》", "数据库"),
              ("《前端的 fetch 该封装到什么程度》", "前端"),
              ("《用模型做文章摘要》", "AI"),
              ("《Nginx 上的部署清单》", "运维")]

    def fake_model(prompt_path: Path):
        """假模型：只有提示里写了那条约束才守规矩。

        它模拟的是「模型会跟着提示走」这一件事，用来证明回归集拦得住改动；
        它给出的通过率不是模型的实际通过率。
        """
        strict = CONSTRAINT in prompt_path.read_text(encoding="utf-8")

        def transport(body: str, cfg: Config) -> RawReply:
            title = next(t for t, _ in CORPUS if t in body)
            want = dict(CORPUS)[title]
            tags = [want] if strict else ["AI"]      # 去掉约束后：合法但常常不对
            return RawReply({"summary": f"讲 {want}", "tags": tags}, 260)
        return transport

    print(f"  {'提示版本':<26}{'通过':>7}  失败明细")
    for label, prompt in (("v3（含标签清单约束）", good), ("v4（删掉清单约束）", bad)):
        passed, fails = 0, []
        for i, (title, want) in enumerate(CORPUS, 1):
            try:
                r = call_model(prompt, title, transport=fake_model(prompt),
                               config=cfg, clock=clock)
                if r.summary.tags == [want]:
                    passed += 1
                else:
                    fails.append(f"#{i} 返回 {r.summary.tags[0]!r}，期望 {want!r}")
            except LlmError as exc:
                fails.append(f"#{i} {exc.kind}")
        print(f"  {label:<26}{passed}/{len(CORPUS):>5}  {'；'.join(fails) if fails else '—'}")

    print()
    print("=== 三、提示版本与密钥边界 ===")
    print(f"  含约束的提示哈希 {prompt_version(good)}；删掉约束后 {prompt_version(bad)}")
    os.environ.pop("LLM_API_KEY", None)
    try:
        Config.from_env()
    except LlmError as exc:
        print(f"  未设 LLM_API_KEY：{exc}（attempts={exc.attempts}，在启动时抛而不是调用时）")
