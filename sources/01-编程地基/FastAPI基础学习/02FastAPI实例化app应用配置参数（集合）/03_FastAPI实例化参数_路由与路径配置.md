# 03_FastAPI实例化参数_路由与路径配置

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\02FastAPI实例化app应用配置参数（集合）\03_FastAPI实例化参数_路由与路径配置.pdf`
> **页数**：5（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 3,428 字符，其中汉字 1,085 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 实例化参数：路由与路径配置
本文档介绍 FastAPI 实例化时控制路由行为的路径相关参数，包括路由注册、斜杠重定向、根路径配置
等功能。
routes 参数
routes 参数允许在创建应用时批量注册预定义的路由列表，这些路由会在应用启动时被统一挂载到路
由表中。
代码解释：
APIRoute 是 FastAPI 中表示路由的底层类
path 参数指定路由的路径，如 "/fastapi/index"
endpoint 参数指向处理请求的函数，这里是 fastapi_index
methods 参数列出该路由支持的 HTTP 方法列表
from fastapi import FastAPI, APIRoute
from fastapi.responses import JSONResponse
# 定义第一个路由的异步处理函数
async def fastapi_index():
return JSONResponse({"index": "fastapi_index"})
# 定义第二个路由的异步处理函数
async def fastapi_about():
return JSONResponse({"about": "fastapi_about"})
# 将路由配置封装成列表，每个元素是一个 APIRoute 对象
routes = [
APIRoute(
path="/fastapi/index",
endpoint=fastapi_index,
methods=["GET", "POST"],
response_class=JSONResponse
),
APIRoute(
path="/fastapi/about",
endpoint=fastapi_about,
methods=["GET"],
response_class=JSONResponse
),
]
# 创建应用时传入 routes 参数，所有路由会被一次性注册
app = FastAPI(routes=routes)

---

<!-- p.2 -->

routes 列表将多个路由配置封装在一起
创建应用时传入 routes=routes ，所有路由会被一次性注册
使用 routes 参数的好处是可以将路由配置集中管理
适合从其他框架迁移或动态生成路由的场景
redirect_slashes 参数
redirect_slashes=True （默认）时，FastAPI 会自动处理路径斜杠的一致性：访问 /users （不带斜
杠）会 307 重定向到 /users/ （补斜杠），访问 /users// （多斜杠）或 /users/ （带斜杠）会重定
向到 /users （去斜杠，取决于路由定义）；若设为 False ， /users 和 /users/ 会被识别为两个独
立路由，未注册的一方返回 404。
代码解释：
redirect_slashes=True 开启自动斜杠重定向功能
访问 /users 和 /users/ 会被视为同一路由
当用户访问不带斜杠的路径时，FastAPI 会自动重定向到带斜杠的路径（或者相反）
默认为 True
建议保持默认开启，以避免用户因忘记添加或添加斜杠导致 404 错误
如果设为 False ，则 /users 和 /users/ 是两个完全不同的路由
root_path 参数
root_path 参数设置 API 的根路径前缀，主要用于在反向代理（如 Nginx）后面运行的 FastAPI 应用。
当 FastAPI 不直接暴露在公网，而是通过反向代理转发请求时，需要设置这个参数。
代码解释：
root_path="/api/v1" 设置 API 的根路径前缀
当应用通过反向代理（如 Nginx）运行时，代理可能将请求转发到 FastAPI 的某个子路径
root_path 告知 FastAPI 实际的基础路径是什么
例如：Nginx 配置将 /api/v1 路径的请求转发到 FastAPI
FastAPI 需要知道这个前缀才能正确生成路由和文档
默认为空字符串 ""
root_path_in_servers 参数
app = FastAPI(redirect_slashes=True)
app = FastAPI(root_path="/api/v1")

---

<!-- p.3 -->

root_path_in_servers 参数控制是否将 root_path 包含到 OpenAPI 文档的 servers 字段中。设为
True 时，生成的 OpenAPI Schema（Swagger/ReDoc 文档）中，所有 API 示例请求 URL 会自动带上
root_path 前缀（如 http://localhost:8000/api/v1/ ），前端开发者可直接复制文档中的 URL 测
试，无需手动拼接根路径，确保调用路径正确。
代码解释：
root_path_in_servers=True 将 root_path 加入 OpenAPI 文档的 servers 字段
设为 True 时，OpenAPI Schema 中会显示类似 {"url": "/api/v1"} 的服务端点
方便前端开发者知道实际请求需要加上 /api/v1 前缀
默认为 True
如果设为 False ，OpenAPI 文档中的 URL 不会包含根路径前缀
通常配合 root_path 一起使用
openapi_prefix 参数
openapi_prefix 参数主要为 OpenAPI 文档设置路径前缀（现代 FastAPI 版本（≥0.68.0）中不影响实
际路由匹配），而 root_path 会同时影响「路由匹配」+「OpenAPI 文档」。默认情况下不需要设
置，仅兼容旧版本场景时可能用到。
代码解释：
openapi_prefix="/api" 为 OpenAPI 文档设置路径前缀
默认为空字符串 ""
现代 FastAPI 版本推荐使用 root_path 参数代替此功能
通常不需要手动设置，保持默认即可
综合配置示例
以下是一个完整展示所有路由与路径参数的配置示例：
app = FastAPI(
root_path="/api/v1",
root_path_in_servers=True
)
app = FastAPI(openapi_prefix="/api")
from fastapi import FastAPI, APIRoute
from fastapi.responses import JSONResponse
# 定义路由处理函数
async def home_handler():
return JSONResponse({"message": "Welcome to API"})
# 配置路由列表

---

<!-- p.4 -->

代码解释：
导入 FastAPI 、 APIRoute 和 JSONResponse
定义一个处理函数 home_handler ，返回欢迎消息
将路由配置封装成列表，使用 APIRoute 创建路由对象
routes 参数批量注册路由列表
root_path="/api/v1" 设置反向代理场景下的根路径前缀
root_path_in_servers=True 将根路径包含到 OpenAPI 文档中
redirect_slashes=True 开启斜杠重定向，避免用户因斜杠问题 404
openapi_prefix="" 保持默认空字符串，这是兼容旧版本参数
routes = [
APIRoute(path="/", endpoint=home_handler, methods=["GET"]),
]
# 创建应用并配置路由与路径参数
app = FastAPI(
routes=routes, # 批量注册路由列表
root_path="/api/v1", # 设置 API 根路径前缀（反向代理场景）
root_path_in_servers=True, # 将 root_path 加入 OpenAPI servers
redirect_slashes=True, # 开启自动斜杠重定向
openapi_prefix="" # OpenAPI 路径前缀（保持默认）
)
