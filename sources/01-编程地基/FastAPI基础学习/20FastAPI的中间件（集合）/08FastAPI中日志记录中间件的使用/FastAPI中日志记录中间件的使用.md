# FastAPI中日志记录中间件的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\20FastAPI的中间件（集合）\08FastAPI中日志记录中间件的使用\FastAPI中日志记录中间件的使用.pdf`
> **页数**：5（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 3,170 字符，其中汉字 489 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 中日志记录中间件的使用
本节介绍如何使用日志中间件记录请求和响应信息。
什么是日志中间件？
记录每个请求的详细信息，便于监控、调试和排查问题。
基本使用
日志输出示例：
日志级别
请求进来 → 记录请求信息 → 处理 → 记录响应信息 → 返回
import logging
from fastapi import FastAPI, Request
app = FastAPI()
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
@app.middleware("http")
async def log_requests(request: Request, call_next):
# 记录请求
logger.info(f"请求: {request.method} {request.url}")
try:
response = await call_next(request)
except Exception as e:
logger.error(f"异常: {str(e)}")
raise
# 记录响应
logger.info(f"响应状态: {response.status_code}")
return response
INFO:uvicorn.access:请求: GET http://localhost:8000/users
INFO:uvicorn.access:响应状态: 200

---

<!-- p.2 -->

级别 数值（越小越详细） 用途
DEBUG 10 详细调试信息（开发时用）
INFO 20 一般信息
WARNING 30 警告信息
ERROR 40 错误信息
CRITICAL 50 严重错误
日志级别数值越小，日志输出越详细，例如 DEBUG（10）会包含 INFO（20）、WARNING（30）等所
有更高数值级别的日志。
进阶用法
请求耗时统计
结构化日志（JSON 格式）
便于日志收集系统（如 ELK）分析：
import time
import logging
from fastapi import FastAPI, Request
app = FastAPI()
logger = logging.getLogger(__name__)
@app.middleware("http")
async def timed_logging(request: Request, call_next):
start_time = time.time()
response = await call_next(request)
elapsed = time.time() - start_time
logger.info(
f"{request.method} {request.url.path} "
f"耗时 {elapsed:.4f}s 状态 {response.status_code}"
)
# 添加到响应头，客户端也能看到耗时
response.headers["X-Process-Time"] = f"{elapsed:.4f}s"
return response
import json
import logging
from fastapi import FastAPI, Request
app = FastAPI()
logger = logging.getLogger(__name__)

---

<!-- p.3 -->

JSON 日志示例：
日志配置
不同环境不同级别
注意：
logging.basicConfig 仅在第一次调用时生效，若项目中有多处调用，需确保环境判断逻辑
在最开始执行；生产环境建议通过配置文件（如 logging.conf ）管理日志，而非硬编码判断环
境。
文件日志（滚动）
@app.middleware("http")
async def structured_log(request: Request, call_next):
logger.info(json.dumps({
"event": "request",
"method": request.method,
"path": request.url.path,
"ip": request.client.host if request.client else "unknown"
}))
response = await call_next(request)
logger.info(json.dumps({
"event": "response",
"status": response.status_code
}))
return response
{"event": "request", "method": "GET", "path": "/users", "ip": "127.0.0.1"}
{"event": "response", "status": 200}
import os
import logging
env = os.getenv("ENV", "development")
if env == "production":
logging.basicConfig(level=logging.WARNING) # 只记录警告以上
elif env == "staging":
logging.basicConfig(level=logging.INFO) # 记录信息
else:
logging.basicConfig(level=logging.DEBUG) # 记录所有
import logging
from logging.handlers import RotatingFileHandler
import os

---

<!-- p.4 -->

功能 实现方式
基础日志 logging.getLogger() + @app.middleware
请求耗时 time.time() 计算 + response.headers
结构化日志 JSON 格式输出
滚动日志 RotatingFileHandler
滚动效果：
总结
日志最佳实践：
1. 生产环境记录 WARNING 以上
2. 开发环境记录 DEBUG 以上
3. 使用结构化日志便于分析
4. 配置滚动日志防止文件过大
5. 记录耗时便于性能分析
os.makedirs("logs", exist_ok=True)
# 文件处理器（滚动日志）
file_handler = RotatingFileHandler(
"logs/app.log",
maxBytes=10 * 1024 * 1024, # 10MB
backupCount=5 # 保留 5 个备份
)
file_handler.setFormatter(logging.Formatter(
"%(asctime)s - %(levelname)s - %(message)s"
))
# 同时输出到控制台和文件
logging.basicConfig(
level=logging.INFO,
handlers=[file_handler, logging.StreamHandler()]
)
logs/
├── app.log # 当前日志（未达到10MB）
├── app.log.1 # 第1个备份（达到10MB后切割）
├── app.log.2 # 第2个备份
└── ...
└── app.log.5 # 第5个备份（新日志产生时会删除该文件）
