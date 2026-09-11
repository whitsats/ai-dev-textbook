# FastAPI中基础中间件的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\20FastAPI的中间件（集合）\02FastAPI中基础中间件的使用\FastAPI中基础中间件的使用.pdf`
> **页数**：6（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 4,453 字符，其中汉字 709 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

方式 代码量 能否传参数 性能 适用场景
@app.middleware 装饰器 少 不能 中等 简单逻辑：计时、日志
BaseHTTPMiddleware 类 中等 能 中等 大多数场景
纯 ASGI 类 多 能 最高 高性能需求
FastAPI 中基础中间件的使用
本节介绍自定义中间件的三种定义方式，以及常用的自定义中间件示例。
三种定义方式对比
方式一：装饰器方式（最简单）
适合简单的请求拦截逻辑，不能传参数：
代码讲解：
@app.middleware("http") ：注册中间件，参数 "http" 表示处理 HTTP 请求
request ：请求对象，包含 method 、 url 、 headers 等
call_next(request) ：调用下一个处理器，返回 response
call_next 之前的代码在请求前执行
call_next 之后的代码在响应后执行
方式二：类方式（推荐）
继承 BaseHTTPMiddleware ，可以传递初始化参数：
from fastapi import FastAPI, Request
import time
app = FastAPI()
@app.middleware("http")
async def add_process_time(request: Request, call_next):
# 1. 请求前：记录开始时间
start_time = time.time()
# 2. 调用下一个处理器（路由）
response = await call_next(request)
# 3. 响应后：计算耗时，添加到响应头
process_time = time.time() - start_time
response.headers["X-Process-Time"] = str(process_time)
return response

---

<!-- p.2 -->

代码讲解：
BaseHTTPMiddleware ：Starlette 提供的中间件基类
__init__ ：接收初始化参数（如配置、密钥等）
super().__init__(app) ：必须调用父类构造函数
dispatch 方法：处理请求的核心逻辑
app.add_middleware() ：注册时传递参数
方式三：纯 ASGI 类（最高性能）
直接操作 ASGI 规范，性能最高，但代码复杂：
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, Request
app = FastAPI()
class AuthMiddleware(BaseHTTPMiddleware):
def __init__(self, app, header_value: str = "default"):
# 必须先调用父类构造函数
super().__init__(app)
# 可以保存配置参数
self.header_value = header_value
async def dispatch(self, request: Request, call_next):
# 请求前：添加自定义头
print(f"收到请求: {request.method} {request.url.path}")
# 调用下一个处理器
response = await call_next(request)
# 响应后：添加自定义头
response.headers["X-Custom-Auth"] = self.header_value
return response
# 注册时可以传参数
app.add_middleware(AuthMiddleware, header_value="MyAuth")
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse
import typing
app = FastAPI()
class IPWhiteListMiddleware:
def __init__(self, app: ASGIApp, allow_ips: typing.Sequence[str] = ()) ->
None:
self.app = app
self.allow_ips = allow_ips

---

<!-- p.3 -->

使用场景：需要直接操作 ASGI scope、精确控制请求处理流程时使用。
常用示例
示例 1：请求耗时统计
效果：客户端可以在响应头中看到处理耗时
示例 2：请求超时控制
async def __call__(self, scope: Scope, receive: Receive, send: Send) ->
None:
# 获取客户端 IP
conn = HTTPConnection(scope=scope)
client_ip = conn.client.host if conn.client else ""
# 检查是否在白名单
if self.allow_ips and client_ip not in self.allow_ips:
response = PlainTextResponse("IP 不在白名单内", status_code=403)
await response(scope, receive, send)
return
# 继续处理请求
await self.app(scope, receive, send)
app = IPWhiteListMiddleware(app, allow_ips=["127.0.0.1", "192.168.1.1"])
import time
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, Request
app = FastAPI()
class TimeMiddleware(BaseHTTPMiddleware):
async def dispatch(self, request: Request, call_next):
start_time = time.time()
response = await call_next(request)
# 计算耗时，添加到响应头
response.headers["X-Process-Time"] = f"{time.time() - start_time:.4f}s"
return response
app.add_middleware(TimeMiddleware)
响应头：X-Process-Time: 0.0523s
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

---

<!-- p.4 -->

示例 3：自定义响应头
中间件注册顺序
中间件按注册顺序执行：
建议顺序（从外到内）：
1. TrustedHostMiddleware - 主机验证
app = FastAPI()
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
try:
# 显式创建任务，确保异步超时生效
task = asyncio.create_task(call_next(request))
response = await asyncio.wait_for(task, timeout=5.0)
except asyncio.TimeoutError:
return JSONResponse(status_code=504, content={"detail": "请求超时"})
# 补充捕获其他异常（可选，根据业务需求）
except Exception as e:
return JSONResponse(status_code=500, content={"detail": f"服务器错误:
{str(e)}"})
else:
return response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, Request
app = FastAPI()
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
async def dispatch(self, request: Request, call_next):
response = await call_next(request)
# 添加安全相关的响应头
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["X-XSS-Protection"] = "1; mode=block"
return response
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(中间件A) # 先注册，在外层
app.add_middleware(中间件B) # 后注册，在内层
# 执行流程：
# 请求：中间件A → 中间件B → 路由
# 响应：路由 → 中间件B → 中间件A

---

<!-- p.5 -->

定义方式 特点 选择建议
@app.middleware 简单，不能传参 简单拦截逻辑
BaseHTTPMiddleware 可传参，推荐 大多数场景
纯 ASGI 性能最高，代码复杂 高性能需求
2. CORSMiddleware - 跨域处理
3. HTTPSRedirectMiddleware - HTTPS 重定向
4. 自定义中间件（如认证、限流）
5. GZipMiddleware - 压缩
总结
自定义中间件的典型应用：
请求/响应日志记录
请求耗时统计
添加自定义响应头
IP 白名单/黑名单
请求超时控制
