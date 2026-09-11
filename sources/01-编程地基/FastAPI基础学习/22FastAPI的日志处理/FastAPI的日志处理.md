# FastAPI的日志处理

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\22FastAPI的日志处理\FastAPI的日志处理.pdf`
> **页数**：11（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 11,111 字符，其中汉字 2,088 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

要素 比喻 实际作用
Logger 不同的服务员 每个模块用自己的 logger 记录日志，互不干扰
Handler 日志本/打印机 决定日志输出到哪里（屏幕？文件？）
Level 重要程度筛选 决定什么级别的日志该被记录
Formatter 填写格式 决定日志长什么样子（时间？颜色？）
FastAPI 的日志处理
日志系统的核心价值是在生产环境中还原事故现场，告诉你：谁、什么时候、请求了什么、为什么失
败。
FastAPI 集成 Python 标准 logging 模块。
日志配置四要素
想象你要管理一家餐厅的日志系统：
举例：
输出效果：
简单说：logger 决定谁来记，handler 决定记到哪里，level 决定记多少，formatter 决定记成什么
样。
日志配置示例
# logger = 不同的服务员
logger_api = logging.getLogger("api") # API 模块的服务员
logger_db = logging.getLogger("database") # 数据库模块的服务员
# handler = 输出目的地
console_handler = logging.StreamHandler() # 输出到屏幕
file_handler = logging.FileHandler("a.log") # 输出到文件
# level = 筛选重要程度
console_handler.setLevel(logging.DEBUG) # 屏幕上显示所有日志
file_handler.setLevel(logging.WARNING) # 文件里只记重要的
# formatter = 日志格式
formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")
console_handler.setFormatter(formatter)
2026-05-05 10:30:00 - api - 用户登录了
2026-05-05 10:30:01 - api - 数据库查询失败 ← WARNING 级别，进入文件
import logging
import logging.handlers # 日志轮转处理器

---

<!-- p.2 -->

import sys
from pathlib import Path
# ── 1. 定义日志输出目录 ──────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True) # 如果目录不存在，自动创建
# ── 2. 定义日志格式 ─────────────────────────────────────────
# 详细格式：包含文件名和行号，排查问题时用
DETAIL_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%
(lineno)d - %(message)s"
# 简洁格式：只有时间和消息，控制台快速浏览用
SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
def setup_logging(level: int = logging.INFO):
"""统一日志配置函数"""
# 获取根记录器（所有自定义 logger 会继承根 logger 的 level/handler，除非显式覆盖）
logger = logging.getLogger()
logger.setLevel(level)
# 只清除当前函数添加的 handler（而非全部），或判断 handler 类型后清除
# 记录已添加的 handler，仅清除自身创建的（更安全）
current_handlers = []
# 先移除之前由该函数添加的 handler
for handler in logger.handlers[:]: # 遍历副本避免迭代中修改
if isinstance(handler, (logging.StreamHandler,
logging.handlers.TimedRotatingFileHandler,logging.handlers.RotatingFileHandler))
:
logger.removeHandler(handler)
# ═══════════════════════════════════════════════════════════
# 第一个 Handler：控制台输出（开发调试用）
# ═══════════════════════════════════════════════════════════
console = logging.StreamHandler(sys.stdout) # 输出到标准输出（屏幕）
console.setLevel(logging.DEBUG) # 控制台显示所有级别（方便调试）
console.setFormatter(logging.Formatter(SIMPLE_FORMAT))
logger.addHandler(console)
# ═══════════════════════════════════════════════════════════
# 第二个 Handler：文件输出（日常日志，按天轮转）
# ═══════════════════════════════════════════════════════════
# TimedRotatingFileHandler = 按时间轮转的日志处理器
# when="midnight" = 每天零点新建一个文件
# backupCount=30 = 最多保留 30 天的日志
file_handler = logging.handlers.TimedRotatingFileHandler(
LOG_DIR / "app.log", # 日志文件路径
when="midnight", # 每天零点切换文件
interval=1, # 间隔 1 天
backupCount=30, # 保留 30 个旧文件
encoding="utf-8", # 中文编码
errors="replace", # 替换无法UTF-8编码的字符
utc=True # 按 UTC 时间轮转（避免服务器时区偏差）
)

---

<!-- p.3 -->

Handler 用途 轮转策略
StreamHandler 控制台 无
TimedRotatingFileHandler 日常日志 每天零点，保留 30 天
RotatingFileHandler 错误日志 单文件最大 10MB，保留 5 个
在 FastAPI 中使用日志
基本用法
file_handler.setLevel(logging.INFO) # 文件只记录 INFO 以上（减少噪音）
file_handler.setFormatter(logging.Formatter(DETAIL_FORMAT))
logger.addHandler(file_handler)
# ═══════════════════════════════════════════════════════════
# 第三个 Handler：文件输出（错误日志，按大小轮转）
# ═══════════════════════════════════════════════════════════
# RotatingFileHandler = 按文件大小轮转的日志处理器
# maxBytes=10MB = 单个文件超过 10MB 就新建一个
# backupCount=5 = 最多保留 5 个旧文件
error_handler = logging.handlers.RotatingFileHandler(
LOG_DIR / "error.log", # 错误日志路径
maxBytes=10 * 1024 * 1024, # 单文件最大 10MB
backupCount=5, # 保留 5 个旧文件
encoding="utf-8", # 中文编码
errors="replace" # 替换无法UTF-8编码的字符
)
error_handler.setLevel(logging.ERROR) # 只记录 ERROR 及以上（只关心错误）
error_handler.setFormatter(logging.Formatter(DETAIL_FORMAT))
logger.addHandler(error_handler)
# ── 3. 压制第三方框架的日志噪音 ─────────────────────────
# uvicorn 是 FastAPI 内置的 ASGI 服务器，它的日志太 verbose
# 这里把它的日志级别调高，减少干扰
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("uvicorn.asgi").setLevel(logging.WARNING)
import logging
from fastapi import FastAPI, HTTPException
from log_config import setup_logging
setup_logging() # 启动时初始化一次（只需调用一次）
# __name__ 在运行时是 "main"（直接运行）或模块路径（如 "routers.users"）
# 这样在日志中能一眼看出是哪个文件输出的
logger = logging.getLogger(__name__)
app = FastAPI()
@app.get("/items/{item_id}")

---

<!-- p.4 -->

请求日志中间件
推荐用中间件统一记录每个请求，一次定义，所有路由自动生效：
async def read_item(item_id: int):
# logger.debug() 在 INFO 级别下不输出，不会污染日志
# logger.info() 用于记录正常流程
# logger.warning() 用于记录需要关注但不是错误的情况
# logger.error() 用于记录错误
if item_id < 0:
logger.error(f"Invalid item_id: {item_id}") # 记录错误日志
raise HTTPException(status_code=400, detail="Item ID must be positive")
return {"item_id": item_id}
import time
import logging
from fastapi import FastAPI, Request
logger = logging.getLogger(__name__)
app = FastAPI()
@app.middleware("http")
async def log_requests(request: Request, call_next):
"""
中间件：记录每个请求的完整信息
中间件执行逻辑：
1. 请求进入中间件，先执行前置逻辑（如记录请求信息）；
2. 调用 call_next(request) 触发下游路由/中间件处理请求，阻塞直到获取响应；
3. 路由处理完成后，回到中间件执行后置逻辑（如记录响应、修改响应头）；
4. 返回最终响应给客户端。
"""
start_time = time.time() # 记录开始时间，用于计算耗时
# ── 步骤1：记录请求信息 ──────────────────────────────
# request.method = GET/POST/PUT/DELETE
# request.url.path = /users/123（不含域名）
logger.info(f"Request: {request.method} {request.url.path}")
try:
# ── 步骤2：调用下游路由处理 ─────────────────────
# ⚠️ 必须调用 call_next(request)：否则请求会被中断，客户端永远无法收到响应
response = await call_next(request)
# ── 步骤3：记录响应信息 ─────────────────────────
elapsed = time.time() - start_time # 计算耗时
logger.info(
f"Response: {request.method} {request.url.path} "
f"-> {response.status_code} ({elapsed:.4f}s)"
)
# ⚠️ 响应头修改：FastAPI/Starlette 的 Response.headers 支持修改，可添加自定义头
（如耗时
# 将处理耗时写入响应头，方便前端或监控脚本读取

---

<!-- p.5 -->

结构化日志（JSON 格式）
接入 ELK、Sentry 等日志收集系统时用 JSON 格式，便于检索和聚合：
response.headers["X-Process-Time"] = f"{elapsed:.4f}s"
except Exception as ex:
# ── 步骤4：捕获异常并记录 ───────────────────────
# type(ex).__name__ 获取异常类型名，如 "ValueError"
# ex 是异常实例，str(ex) 是异常消息
logger.error(
f"Error: {request.method} {request.url.path} "
f"-> {type(ex).__name__}: {ex}"
)
raise # 重新抛出异常，交给 FastAPI 的异常处理器处理
return response
import logging
import json
from datetime import datetime, timezone
class JSONFormatter(logging.Formatter):
"""
自定义 JSON 格式日志格式化器，适配 ELK/Sentry 等日志收集系统。
优势：
- 结构化数据便于程序解析、检索和聚合；
- 支持自定义字段（如 UTC 时间、堆栈信息）；
- 保留中文，避免转义。
"""
def format(self, record: logging.LogRecord):
"""
每条日志都会调用这个方法
Args:
record: 日志记录对象，包含所有日志信息
Returns:
JSON 字符串
"""
# 基础字段：时间、级别、消息
log_data = {
"timestamp": datetime.fromtimestamp(record.created,
timezone.utc).isoformat(),
"level": record.levelname, # INFO / ERROR
等
"logger": record.name, # logger 名称（模
块名）
"message": record.getMessage(), # 日志消息内容
"module": record.module, # 源文件名（不含路
径）
"line": record.lineno, # 源代码行号

---

<!-- p.6 -->

输出示例：
按环境切换日志级别
"process_id": record.process, # 进程 ID（多进程
时区分）
"thread_id": record.thread # 线程 ID（多线程
时区分）
}
# 如果有异常信息，附加上堆栈（分析 crash 根因的关键）
if record.exc_info:
# exc_info 是一个三元组：(异常类型, 异常实例, traceback对象)
log_data["exception"] = {
"type": record.exc_info[0].__name__, # 如
"ZeroDivisionError"
"message": str(record.exc_info[1]), # 如 "division
by zero"
"traceback": self.formatException(record.exc_info) # 完整的堆栈信
息
}
# ensure_ascii=False：保留中文，不转义
return json.dumps(log_data, ensure_ascii=False)
{
"timestamp": "2026-04-05T10:30:00+00:00",
"level": "INFO",
"logger": "__main__",
"message": "Request: GET /users",
"module": "main",
"line": 25,
"process_id": 12345,
"thread_id": 45678
}
import os
import logging
ENV = os.getenv("ENV", "development")
LEVEL_MAP = {
"development": logging.DEBUG,
"testing": logging.INFO,
"production": logging.INFO
}
setup_logging(level=LEVEL_MAP.get(ENV, logging.INFO))

---

<!-- p.7 -->

环境 级别 说明
开发 DEBUG 详细日志，包含 SQL 等
测试 INFO 关键流程
生产 INFO 避免性能损耗
敏感信息过滤
生产环境禁止将密码、Token 等敏感信息写入日志：
# 敏感字段列表（大小写不敏感，会匹配 password / Password / PASSWORD）
SENSITIVE_FIELDS = {
# 认证凭据
"password", "token", "secret", "api_key", "authorization",
# 个人隐私
"id_card", "phone", "id_number", "passport",
# 支付信息
"credit_card", "cvv", "card_number", "bank_account"
}
def mask_sensitive(data: Any, max_depth: int = 10) -> Any:
"""
递归过滤敏感信息（增加最大深度限制）
Args:
data: 原始数据（支持 dict/list/tuple/set）
max_depth: 最大递归深度，防止栈溢出
Returns: 脱敏后的数据
"""
# 终止条件：深度为0 或 非容器类型
if max_depth <= 0 or not isinstance(data, (dict, list, tuple, set)):
return data
if isinstance(data, dict):
result = {}
for key, value in data.items():
if key.lower() in SENSITIVE_FIELDS:
result[key] = "***MASKED***"
else:
result[key] = mask_sensitive(value, max_depth - 1)
return result
elif isinstance(data, (list, tuple)):
return [mask_sensitive(item, max_depth - 1) for item in data]
elif isinstance(data, set):
return {mask_sensitive(item, max_depth - 1) for item in data}
else:
return data
@app.post("/login")
async def login(request: Request):

---

<!-- p.8 -->

原始日志 脱敏后
{"username":"tom","password":"123456"} {"username":"tom","password":"***MASKED***"}
{"user":
{"phone":"13800138000","token":"abc"}}
{"user":
{"phone":"***MASKED***","token":"***MASKED***"}}
禁止记录 示例
认证凭据 password 、 token 、 api_key
个人隐私 id_card 、 phone
支付信息 credit_card 、 cvv
项目 说明
问题现象 写了 logger.info() 但控制台/文件什么都没显示
原因一 日志级别设置过高，比如设置了 WARNING ，那 INFO 和 DEBUG 都不会显示
原因二 忘了 logger.addHandler() ，日志没有出口
脱敏效果对比：
常见问题
问题 1：日志不输出
理解日志级别：
日志级别优先级（从低到高）：DEBUG < INFO < WARNING < ERROR < CRITICAL
# 处理 JSON 请求
if request.headers.get("content-type") == "application/json":
body = await request.json()
# 处理表单请求
elif request.headers.get("content-type") == "application/x-www-form-
urlencoded":
body = dict(await request.form())
# 处理 URL 参数
query_params = dict(request.query_params)
# 脱敏所有参数
logger.info(f"Login attempt - body: {mask_sensitive(body)}, query:
{mask_sensitive(query_params)}")
return {"status": "ok"}
# ❌ 错误示例：级别是 WARNING，但只记录了 INFO
logger.setLevel(logging.WARNING) # 只显示 WARNING 及以上
logger.info("这条不会显示") # INFO < WARNING，被过滤掉了
# ✅ 正确示例
logger.setLevel(logging.INFO) # 显示 INFO 及以上
logger.addHandler(console) # 添加输出处理器
logger.info("这条会显示")

---

<!-- p.9 -->

项目 说明
问题现象 同样一条日志，显示了好几次
原因 setup_logging() 被调用了多次，每次都添加了新的 handler
项目 说明
问题现象 日志文件从几十 MB 涨到几 GB，磁盘满了
原因 使用普通 FileHandler ，文件会无限增长
解决 使用带轮转功能的 handler，自动切分文件
设置级别为 X → 仅放行 X 及更高优先级的日志：
设置 WARNING → 仅 WARNING/ERROR/CRITICAL 能过
设置 INFO → 仅 INFO/WARNING/ERROR/CRITICAL 能过
设置 DEBUG → 所有级别都能过
问题 2：日志重复输出
问题 3：日志文件过大
# ❌ 错误示例：热重载时可能多次调用
def setup_logging():
console = logging.StreamHandler()
logger.addHandler(console) # 每次调用都添加一个
# 第1次调用：添加1个 handler
# 第2次调用：添加2个 handler（总共3个）
# 第3次调用：添加3个 handler（总共6个）
# 日志会被重复打印！
# ✅ 正确示例：先清除旧的
def setup_logging():
logger = logging.getLogger()
logger.handlers.clear() # 关键！先清除旧的 handler
logger.addHandler(console)
# ❌ 错误示例：文件会无限增长
file_handler = logging.FileHandler("app.log") # 单个文件无限大
# ✅ 正确示例：按时间轮转
# 每天零点新建一个文件，保留 30 天
file_handler = logging.handlers.TimedRotatingFileHandler(
"app.log",
when="midnight", # 每天零点切换
backupCount=30 # 只保留 30 个旧文件
)
# ✅ 正确示例：按大小轮转

---

<!-- p.10 -->

轮转效果（以按时间轮转为例）：
总结
# 单文件超过 10MB 就新建一个
file_handler = logging.handlers.RotatingFileHandler(
"app.log",
maxBytes=10 * 1024 * 1024, # 10MB
backupCount=5 # 保留 5 个旧文件
)
app.log ← 当前正在写的文件
app.log.2026-05-04 ← 昨天的日志
app.log.2026-05-03 ← 前天的日志
app.log.2026-05-02 ← 大前天的日志
...
app.log.2026-04-05 ← 30天前的日志
↓
被自动删除了
日志配置要点：
Handlers → 控制台 + 文件双输出
→ 错误日志单独记录
中间件 → 统一记录每个请求
→ 包含状态码、耗时
敏感信息 → 递归过滤敏感字段
环境切换 → 生产用 INFO，避免 DEBUG 性能损耗
