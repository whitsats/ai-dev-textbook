# FastAPI的中间件

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\20FastAPI的中间件（集合）\01FastAPI的中间件\FastAPI的中间件.pdf`
> **页数**：4（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 1,801 字符，其中汉字 528 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

文档 内容 难度
01FastAPI的中间件.md 中间件概念、定义方式、执行原理 入门
02基础中间件.md 三种定义方式、自定义中间件 入门
03CORS中间件.md 跨域资源共享 入门
04GZip压缩中间件.md 响应体压缩 入门
05HTTPS重定向中间件.md HTTP 转 HTTPS 入门
06JWT认证中间件.md 基于 JWT 的全局认证 进阶
07请求限流中间件.md 防止暴力请求 进阶
08日志记录中间件.md 请求监控 进阶
09数据库连接池中间件.md 数据库连接管理 进阶
10信任代理头部中间件.md 主机头验证 进阶
FastAPI 中间件系列
本系列文档介绍 FastAPI 中间件的使用方法。中间件是拦截请求/响应的"关卡"，可以统一处理跨域、日
志、认证等通用功能。
文档目录
什么是中间件？
中间件就像餐厅的"传菜员"：
请求前：记录日志、检查身份、验证权限
响应后：添加响应头、压缩数据、统计耗时
中间件的执行顺序
顾客下单 → 传菜员A记录信息（请求前）→ 传菜员B检查菜品（请求前）→ 厨房做菜 → 传菜员B摆盘（响应
后）→ 传菜员A核对账单（响应后）→ 上菜
↑ ↑ ↑
↑
中间件A请求前 中间件B请求前 中间件B响应后
中间件A响应后
from fastapi import FastAPI, Request
app = FastAPI()
# 中间件A（先注册）
@app.middleware("http")
async def middleware_a(request: Request, call_next):

---

<!-- p.2 -->

先注册的中间件在外层
响应返回顺序与注册顺序相反
快速开始
内置中间件一览
print("A - 请求前")
response = await call_next(request)
print("A - 响应后")
return response
# 中间件B（后注册）
@app.middleware("http")
async def middleware_b(request: Request, call_next):
print("B - 请求前")
response = await call_next(request)
print("B - 响应后")
return response
@app.get("/")
async def root():
print("路由处理")
return {"msg": "hello"}
# 执行结果：
# A - 请求前 → B - 请求前 → 路由处理 → B - 响应后 → A - 响应后
请求 → 中间件A(请求前) → 中间件B(请求前) → 路由 → 中间件B(响应后) → 中间件A(响应后) → 响应
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
app = FastAPI()
@app.middleware("http")
async def log_middleware(request: Request, call_next):
# 请求前
print(f"收到请求: {request.method} {request.url}")
try:
# 调用下一个处理器（路由/中间件）
response = await call_next(request)
except Exception as e:
# 异常处理
print(f"请求处理异常: {str(e)}")
response = JSONResponse(status_code=500, content={"detail": "服务器内部错
误"})
# 响应后
print(f"返回状态: {response.status_code}")
return response

---

<!-- p.3 -->

中间件 作用 文档
CORSMiddleware 处理跨域请求 03
GZipMiddleware 压缩响应数据 04
HTTPSRedirectMiddleware HTTP 转 HTTPS 05
TrustedHostMiddleware 验证主机头 10
自定义中间件 日志、认证、限流等 02
