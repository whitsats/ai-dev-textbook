# 01_FastAPI实例化参数_应用基础与参数概览

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\02FastAPI实例化app应用配置参数（集合）\01_FastAPI实例化参数_应用基础与参数概览.pdf`
> **页数**：18（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 20,166 字符，其中汉字 5,235 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 实例化参数：应用基础与参数概览
FastAPI 实例化概述
FastAPI 的核心是一个 FastAPI 类，通过实例化这个类来创建应用对象：
代码解释：
from fastapi import FastAPI 从 fastapi 包中导入 FastAPI 类
app = FastAPI() 实例化一个应用对象 app ，这个对象是整个 Web 服务的入口
所有的路由、中间件、异常处理等都是挂载在这个 app 对象上的
FastAPI 构造函数签名详解
以下展示了 FastAPI 类的完整构造函数参数，每个参数都有其特定的用途：
from fastapi import FastAPI
app = FastAPI()
FastAPI(
title: str = "FastAPI", # API 文档标题
version: str = "0.1.0", # API 版本号
description: str = "", # API 详细描述
debug: bool = False, # 调试模式开关
routes: Sequence[BaseRoute] | None = None, # 预定义路由列表
dependency_overrides_provider: Any = None, # 依赖覆盖提供者
dependencies: Sequence[Depends] | None = None, # 全局依赖列表
default_response_class: Type[Response] = JSONResponse, # 默认响应类
redirect_slashes: bool = True, # 自动处理斜杠重定向
docs_url: str | None = "/docs", # Swagger UI 访问路径
redoc_url: str | None = "/redoc", # Redoc 文档访问路径
openapi_url: str | None = "/openapi.json", # OpenAPI Schema 路径
openapi_tags: Sequence[Dict[str, Any]] | None = None, # OpenAPI 标签定义
servers: List[Dict[str, str]] | None = None, # 服务端点列表
root_path_in_servers: bool = True, # 是否将 root_path 包含到 servers 中
root_path: str = "", # API 根路径前缀
openapi_prefix: str = "", # OpenAPI 路径前缀（兼容旧版）
lifespan: Lifespan | None = None, # 应用生命周期管理器
middleware: Sequence[Middleware] | None = None, # 中间件列表
exception_handlers: Dict[Any, Callable] | None = None, # 异常处理器
responses: Dict[int | str, Dict[str, Any]] | None = None, # 全局响应定义
terms_of_service: str | None = None, # 服务条款 URL
contact: Dict[str, str] | None = None, # 联系人信息
license_info: Dict[str, str] | None = None, # 许可证信息
deprecated: bool | None = None, # 标记 API 是否废弃
swagger_ui_parameters: Dict[str, Any] | None = None, # Swagger UI 自定义参数
**kwargs # 其他额外参数
)

---

<!-- p.2 -->

代码解释：
title 设置 API 文档的标题，默认为 "FastAPI"
version 声明 API 的版本号，默认为 "0.1.0"
description 提供 API 的详细描述，支持 Markdown 格式
debug 控制调试模式开关，开启后显示详细错误堆栈
routes 用于批量注册预定义的路由列表
dependency_overrides_provider 提供依赖覆盖的功能
dependencies 为所有路由添加全局依赖项
default_response_class 设置全局默认的响应类，默认为 JSONResponse
redirect_slashes 控制是否自动重定向带斜杠和不带斜杠的路径
docs_url 设置 Swagger UI 的访问路径，设为 None 可关闭
redoc_url 设置 Redoc 文档的访问路径，设为 None 可关闭
openapi_url 设置 OpenAPI Schema 文件的访问路径，设为 None 可关闭
openapi_tags 用于在文档中定义分组标签
servers 列出多个服务端点，方便在文档中切换不同环境
root_path_in_servers 决定是否将 root_path 包含到 OpenAPI servers 中
root_path 设置 API 的根路径前缀，适用于反向代理场景
openapi_prefix 为 OpenAPI 文档设置路径前缀，用于兼容旧版本
lifespan 是应用生命周期管理器，替代已废弃的 on_startup/on_shutdown
middleware 用于配置全局中间件列表
exception_handlers 用于注册全局异常处理器
responses 定义全局默认的响应模型
terms_of_service 设置服务条款的 URL 链接
contact 字典包含联系人信息：name、email、url
license_info 字典包含许可证信息：name、url
deprecated 标记整个 API 是否已废弃
swagger_ui_parameters 允许自定义 Swagger UI 的行为参数
**kwargs 接收其他额外的未列出的关键字参数
这些参数按功能可分为七大类别：基础配置、路由配置、文档配置、响应配置、异常处理、依赖管理和
生命周期。接下来的章节会逐个讲解这些参数的用法。
最简实例化
创建一个可运行的 FastAPI 应用只需下面这几行代码：
代码解释：
from fastapi import FastAPI 从 fastapi 包中导入 FastAPI 类
app = FastAPI() 实例化应用对象，这个 app 是整个服务的核心
@app.get("/") 使用装饰器定义了一个 GET 请求的路由
from fastapi import FastAPI
app = FastAPI()
@app.get("/")
def read_root():
return {"Hello": "World"}

---

<!-- p.3 -->

当用户访问根路径 / 时会触发 read_root 函数
函数返回一个字典，FastAPI 会自动将其序列化为 JSON 响应返回给客户端
基础配置参数
debug 参数控制调试模式， title 设置文档标题， description 提供详细的 API 描述， version 声
明 API 版本。 terms_of_service 、 contact 和 license_info 用于在文档中展示法律和联系信息。
基础配置示例：
代码解释：
title 设置在 Swagger UI 和 Redoc 中显示的 API 标题为"用户管理系统 API"
summary 提供了一段简短的描述文字："提供用户增删改查接口"
description 支持 Markdown 格式，可以写多行详细说明
这里定义了"功能模块"标题和两个子项：用户管理、权限控制
version 标记当前 API 的版本号为 "1.0.0"
terms_of_service 是一个 URL 链接，指向服务条款页面
contact 字典包含三个键： name 是联系人或团队的名称
email 是联系邮箱地址， url 是联系页面地址
license_info 字典包含许可证名称和对应的 URL
这些元数据都会显示在 API 交互式文档中
Debug 模式
代码解释：
app = FastAPI(
title="用户管理系统 API",
summary="提供用户增删改查接口",
description="""
这是一个基于 FastAPI 开发的后端 API。
## 功能模块
- 用户管理
- 权限控制
""",
version="1.0.0",
terms_of_service="https://example.com/terms",
contact={
"name": "技术支持",
"email": "support@example.com",
"url": "https://example.com"
},
license_info={
"name": "MIT License",
"url": "https://opensource.org/licenses/MIT"
}
)
app = FastAPI(debug=True)

---

<!-- p.4 -->

debug=True 会开启调试模式
在此模式下，当代码发生错误时，FastAPI 会返回详细的错误堆栈信息，帮助开发者快速定位问题
需要注意的是，生产环境务必将此参数设为 False ，否则会暴露敏感的服务器信息
如果已经定义了全局异常处理器，开启调试模式可能会导致异常处理器被 FastAPI 内置的调试错误
页面覆盖
注意：生产环境务必将此参数设为 False ：
开启后会暴露详细的错误堆栈和服务器路径等敏感信息；
调试模式会降低应用性能，且与 uvicorn 多 worker 模式不兼容（生产环境通常用多
worker）；
若开启 debug=True ，FastAPI 内置的调试页面会覆盖自定义的全局异常处理器，导致异常
响应格式不统一。
路由与路径配置
routes 参数允许批量注册预定义的路由。 redirect_slashes 控制是否自动重定向带斜杠和不带斜杠
的路径。 root_path 设置 API 的根路径前缀，这在反向代理场景下非常有用。
root_path_in_servers 决定是否将 root_path 包含到 OpenAPI 文档的 servers 字段中。
路由与路径配置示例：
代码解释：
root_path="/api/v1" 在反向代理（如 Nginx）后运行时，FastAPI 需要知道实际的路径前缀
root_path_in_servers=True 将 root_path 加入 OpenAPI 文档，方便前端知道正确的请求地址
redirect_slashes=True 开启后，访问 /users 和 /users/ 会被视为同一路由，FastAPI 会自
动重定向
全局 routes 参数
使用 routes 参数可以在创建应用时一次性注册多个路由，而不是逐个使用装饰器：
app = FastAPI(
root_path="/api/v1", # 在反向代理（如 Nginx）后运行时，FastAPI 需要知道实际的路径前
缀
root_path_in_servers=True, # 将 root_path 加入 OpenAPI 文档，方便前端知道正确的请
求地址
redirect_slashes=True # 开启后，访问 /users 和 /users/ 会被视为同一路由，FastAPI
会自动重定向
)
from fastapi import FastAPI, APIRoute
from fastapi.responses import JSONResponse
# 定义第一个路由的异步处理函数
async def fastapi_index():
return JSONResponse({"index": "fastapi_index"})
# 定义第二个路由的异步处理函数
async def fastapi_about():
return JSONResponse({"about": "fastapi_about"})

---

<!-- p.5 -->

代码解释：
APIRoute 是 FastAPI 中表示路由的底层类
path 参数指定路由的路径
endpoint 参数指向处理请求的函数
methods 参数列出该路由支持的 HTTP 方法
routes 列表将多个路由配置封装在一起
创建应用时传入 routes=routes ，所有路由会被一次性注册
使用 routes 参数的好处是可以将路由配置集中管理，适合从其他框架迁移或动态生成路由的场景
文档与 OpenAPI 配置
FastAPI 自动为每个 API 生成交互式文档，这些文档的访问路径和显示内容都可以通过参数定制。
openapi_url 设置 OpenAPI Schema 文件的访问路径，设为 None 可以完全关闭。 docs_url 控制
Swagger UI 的访问路径， redoc_url 控制 Redoc 的访问路径。 openapi_tags 用于在文档中定义分
组标签。 swagger_ui_parameters 允许自定义 Swagger UI 的行为参数。 servers 列出多个服务端
点，方便在文档中切换不同环境。
文档与 OpenAPI 配置示例：
代码解释：
# 将路由配置封装成列表，每个元素是一个 APIRoute 对象
routes = [
APIRoute(path="/fastapi/index", endpoint=fastapi_index, methods=["GET",
"POST"]),
APIRoute(path="/fastapi/about", endpoint=fastapi_about, methods=["GET"]),
]
# 创建应用时传入 routes 参数，所有路由会被一次性注册
app = FastAPI(routes=routes)
app = FastAPI(
# 定义分组标签，用于对 API 端点进行分类展示
openapi_tags=[
{"name": "用户", "description": "用户相关接口"},
{"name": "订单", "description": "订单相关接口"}
],
# 自定义 Swagger UI 的显示参数
swagger_ui_parameters={
"deepLinking": True, # 开启深度链接，URL 会反映当前展开的端点
"displayOperationId": True, # 在文档中显示每个端点的操作 ID
"defaultModelsExpandDepth": 2, # 默认展开的模型层级深度
"persistAuthorization": True # 刷新页面后保留授权信息
},
# 定义多个服务端点，文档右上角可以切换
servers=[
{"url": "http://localhost:8000", "description": "本地开发环境"},
{"url": "https://api.example.com", "description": "生产环境"}
]
)

---

<!-- p.6 -->

openapi_tags 定义分组标签，用于对 API 端点进行分类展示
swagger_ui_parameters 自定义 Swagger UI 的显示参数
deepLinking: True 开启深度链接，URL 会反映当前展开的端点
displayOperationId: True 在文档中显示每个端点的操作 ID
defaultModelsExpandDepth: 2 默认展开的模型层级深度为 2
persistAuthorization: True 刷新页面后保留授权信息
servers 定义多个服务端点，文档右上角可以切换
通常包括本地开发环境和生产环境两个入口
关闭交互式文档
在生产环境中，建议关闭 API 文档以减少安全风险：
代码解释：
docs_url=None 禁用了 Swagger UI，访问 /docs 会返回 404
redoc_url=None 禁用了 Redoc，访问 /redoc 会返回 404
openapi_url=None 禁用了 OpenAPI Schema 文件的生成
这对于安全要求较高的生产环境是推荐的做法
推荐方式：通过环境变量动态控制
代码解释：
使用三元表达式判断环境变量 ENVIRONMENT 的值
当环境为 production 时，三个文档路径都设为 None 关闭文档
其他环境（如 development 、 staging ）则正常开启文档
这样在开发和生产环境中不需要手动修改代码
响应与异常配置
FastAPI 提供了灵活的异常处理机制，通过 exception_handlers 参数可以自定义各类异常发生时的响
应格式。 default_response_class 设置全局默认的响应类型， responses 定义全局的响应模型。
app = FastAPI(
docs_url=None, # 关闭 Swagger UI 文档
redoc_url=None, # 关闭 Redoc 文档
openapi_url=None # 关闭 OpenAPI Schema 文件
)
import os
from fastapi import FastAPI
app = FastAPI(
# 生产环境下关闭文档，开发环境保持开启
docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
openapi_url="/openapi.json" if os.getenv("ENVIRONMENT") != "production" else
None
)

---

<!-- p.7 -->

自定义异常处理器
当应用中出现 HTTP 异常或通用异常时，可以通过自定义处理器返回统一格式的错误信息：
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
app = FastAPI()
# 定义处理 HTTPException 的异步函数
# request 参数可以获取客户端请求的详细信息
# exc 参数是 HTTPException 实例，包含状态码和详细信息
async def http_exception_handler(request: Request, exc: HTTPException):
return JSONResponse(
status_code=exc.status_code,
content={
"code": exc.status_code, # 将状态码放入响应的 code 字段
"message": exc.detail, # 将异常详情放入 message 字段
"path": str(request.url) # 将请求路径放入 path 字段，便于排查
}
)
# 定义处理通用异常的异步函数
# 这个处理器捕获所有未被其他处理器捕获的异常
async def general_exception_handler(request: Request, exc: Exception):
return JSONResponse(
status_code=500,
content={
"code": 500,
"message": "服务器内部错误",
"detail": str(exc) # 将异常信息转为字符串放入 detail 字段
}
)
# 在实例化时注册异常处理器
app = FastAPI(
exception_handlers={
HTTPException: http_exception_handler, # 映射 HTTPException 到自定义处理
器
Exception: general_exception_handler # 映射通用 Exception 到自定义处理
器
}
)
@app.get("/items/{item_id}")
def get_item(item_id: int):
if item_id == 0:
raise HTTPException(status_code=404, detail="商品不存在")
return {"item_id": item_id}
@app.get("/error")
def trigger_error():
raise ValueError("这是一个测试错误")

---

<!-- p.8 -->

代码解释：
exception_handlers 是一个字典，将异常类型作为键，对应的处理函数作为值
当 FastAPI 捕获到相应类型的异常时，就会调用对应的处理函数
http_exception_handler 函数接收两个参数： request 和 exc
request 提供了请求的上下文信息（如路径、查询参数等）
exc 是 HTTPException 实例，包含状态码和详细信息
general_exception_handler 捕获所有其他未被捕获的异常，返回 500 状态码
在实例化时通过 exception_handlers 参数注册处理器
HTTPException: http_exception_handler 映射 HTTPException 到自定义处理器
Exception: general_exception_handler 映射通用 Exception 到自定义处理器
路由函数中通过 raise HTTPException 手动抛出异常
统一异常响应格式
为了保持 API 响应的一致性，可以创建一个统一的响应格式：
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
app = FastAPI()
# 通用的异常处理函数，根据异常类型返回统一格式的响应
async def custom_exception_handler(request, exc):
# 判断是否为 HTTP 异常
if isinstance(exc, HTTPException):
return JSONResponse(
status_code=exc.status_code,
content={
"success": False, # 统一标识请求失败
"error": { # 错误信息统一放在 error 字段中
"code": exc.status_code, # 错误码
"message": exc.detail # 错误消息
}
}
)
# 非 HTTP 异常统一返回 500 错误
return JSONResponse(
status_code=500,
content={
"success": False,
"error": {
"code": 500,
"message": "Internal Server Error"
}
}
)
# 注册处理器，使用 StarletteHTTPException 可以捕获更多类型的 HTTP 异常
app = FastAPI(
exception_handlers={
StarletteHTTPException: custom_exception_handler
}

---

<!-- p.9 -->

代码解释：
isinstance(exc, HTTPException) 用于判断异常的具体类型
如果是 HTTP 异常，返回包含 success: False 和 error 对象的统一格式
success 字段统一标识请求是否成功
error 字段统一包含 code 和 message 信息
非 HTTP 异常（如 ValueError 、 KeyError 等）统一返回 500 状态码
使用 StarletteHTTPException 可以捕获更多类型的 HTTP 异常
前端只需要按照统一的格式处理响应即可，不需要针对每种错误类型做特殊处理
生命周期管理（Lifespan）
lifespan 是 FastAPI 推荐的应用生命周期管理方式，替代了已废弃的 on_startup 和 on_shutdown
参数。它使用上下文管理器来定义应用启动和关闭时需要执行的代码。
基本用法
代码解释：
@asynccontextmanager 装饰器将一个异步函数转换为上下文管理器
yield 关键字是核心，分隔了启动和关闭两个阶段
yield 之前的代码在应用启动时执行（称为"进入"阶段）
yield 之后的代码在应用关闭时执行（称为"退出"阶段）
app: FastAPI 参数允许在生命周期函数中访问应用实例
await init_database() 在启动时初始化数据库连接
await load_cache() 在启动时加载缓存数据
await close_database() 在关闭时关闭数据库连接
)
from contextlib import asynccontextmanager
from fastapi import FastAPI
# 使用 @asynccontextmanager 装饰器定义一个异步上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
# ========== 应用启动阶段 ==========
# 在 yield 之前的代码会在应用启动时执行一次
print("应用启动中...")
await init_database() # 初始化数据库连接
await load_cache() # 加载缓存数据
# yield 关键字分隔启动和关闭阶段
yield
# ========== 应用关闭阶段 ==========
# 在 yield 之后的代码会在应用关闭时执行
print("应用关闭中...")
await close_database() # 关闭数据库连接
await save_cache() # 保存缓存数据
# 创建应用时通过 lifespan 参数传入生命周期管理器
app = FastAPI(lifespan=lifespan)

---

<!-- p.10 -->

await save_cache() 在关闭时保存缓存数据
创建应用时通过 lifespan 参数传入生命周期管理器
连接池管理示例
数据库连接池在应用启动时创建，在关闭时释放，这是 lifespan 最常见的用法之一：
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncpg
from typing import AsyncGenerator
# 模块级别的全局变量，用于存储连接池实例
db_pool: asyncpg.Pool | None = None
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
global db_pool
# ========== 启动阶段：创建数据库连接池 ==========
print("正在创建数据库连接池...")
# asyncpg.create_pool 创建异步 PostgreSQL 连接池
# host 和 port 指定数据库服务器地址
# user 和 password 用于认证
# database 指定要连接的数据库名
# min_size 和 max_size 控制连接池的最小和最大连接数
db_pool = await asyncpg.create_pool(
host="localhost",
port=5432,
user="user",
password="password",
database="mydb",
min_size=5, # 始终保持至少 5 个可用连接
max_size=20 # 最多同时持有 20 个连接
)
print("数据库连接池创建成功")
yield
# ========== 关闭阶段：释放连接池 ==========
print("正在关闭数据库连接池...")
if db_pool:
await db_pool.close() # 关闭所有连接并清理资源
print("数据库连接池已关闭")
app = FastAPI(lifespan=lifespan)
@app.get("/users/{user_id}")
async def get_user(user_id: int):
# 通过连接池获取一个连接执行查询
async with db_pool.acquire() as conn:
# fetchrow 执行查询并返回一行结果，$1 是参数占位符
row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
return dict(row) if row else {"error": "用户不存在"}

---

<!-- p.11 -->

代码解释：
asyncpg 是 Python 中高效的异步 PostgreSQL 驱动
db_pool 是模块级别的全局变量，用于存储连接池实例
asyncpg.create_pool 创建异步 PostgreSQL 连接池
host 和 port 指定数据库服务器地址
user 和 password 用于数据库认证
database 指定要连接的数据库名
min_size=5 表示始终保持至少 5 个可用连接
max_size=20 表示最多同时持有 20 个连接
db_pool.acquire() 从池中获取一个连接
fetchrow 执行 SQL 查询并返回一行记录
$1 是 PostgreSQL 的参数占位符，可以防止 SQL 注入攻击
yield 之后注册的关闭逻辑确保应用退出时连接池被正确清理
await db_pool.close() 关闭所有连接并清理资源
Redis 缓存管理示例
类似数据库连接池，Redis 连接也在 lifespan 中管理：
from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as redis
from redis.exceptions import ConnectionError
redis_client: redis.Redis | None = None
@asynccontextmanager
async def lifespan(app: FastAPI):
global redis_client
try:
# 建立 Redis 连接
redis_client = redis.from_url( # 新版 redis 无需 await from_url
"redis://localhost:6379",
encoding="utf-8",
decode_responses=True,
# 新增连接超时配置，避免无限等待
socket_connect_timeout=5.0
)
# 测试连接
await redis_client.ping()
print("Redis 连接成功")
except ConnectionError as e:
print(f"Redis 连接失败: {e}")
raise # 连接失败时终止应用启动
yield
# 关闭连接（新版推荐使用 async with 或 wait_closed）
if redis_client:
await redis_client.aclose() # 新版 redis 推荐 aclose() 替代 close()
# 等待连接完全关闭
await redis_client.wait_closed()
print("Redis 连接已关闭")

---

<!-- p.12 -->

代码解释：
redis.asyncio 是 Redis 的异步客户端模块，适合在 FastAPI 的异步路由中使用
redis_client 是全局变量，用于存储 Redis 客户端实例
redis.from_url 根据 URL 建立异步 Redis 连接
"redis://localhost:6379" 是 Redis 的连接字符串格式
encoding="utf-8" 指定字符编码
decode_responses=True 让返回的值自动解码为字符串而非字节
await redis_client.ping() 测试连接是否正常
await redis_client.aclose() 关闭 Redis 连接，并添加 wait_closed() 确保连接完全释放
redis_client.get(key) 从 Redis 中根据键名获取值
redis_client.set(key, value) 将键值对存入 Redis
全局中间件
中间件是在请求到达路由处理函数之前和响应返回给客户端之前执行的代码。通过 add_middleware 方
法可以添加多个中间件。
CORS 中间件配置
CORS（跨源资源共享）中间件允许浏览器跨域请求：
app = FastAPI(lifespan=lifespan)
@app.get("/cache/{key}")
async def get_cache(key: str):
# 从 Redis 中根据键名获取值
value = await redis_client.get(key)
return {"key": key, "value": value}
@app.post("/cache/{key}/{value}")
async def set_cache(key: str, value: str):
# 将键值对存入 Redis
await redis_client.set(key, value)
return {"message": "设置成功"}

---

<!-- p.13 -->

代码解释：
CORSMiddleware 是 FastAPI 内置的 CORS 中间件
allow_origins 指定允许访问的源（域名），只有这个地址的页面可以请求本 API
allow_credentials=True 允许请求携带 Cookie 和 Authorization 等凭证信息
allow_methods 允许所有 HTTP 方法，也可以只写特定的方法如 ["GET", "POST"]
allow_headers 允许所有请求头，也可以只写特定的头如 ["Authorization"]
CORS 是浏览器的同源安全策略，用于防止跨域请求攻击
浏览器会先发送预检请求（OPTIONS 方法）询问服务器是否允许跨域
CORSMiddleware 会自动处理这些预检请求
注意：
当 allow_credentials=True （允许携带 Cookie/Authorization 凭证）时， allow_origins
不能设为 ["*"] （浏览器同源策略限制），必须指定具体的允许域名（如
["https://example.com", "https://admin.example.com"] ）。生产环境严禁使用
allow_origins=["*"] ，避免跨域安全风险。
多个中间件组合
可以为应用添加多个中间件，它们会按照添加顺序依次执行：
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
# 通过 add_middleware 方法添加 CORS 中间件
app.add_middleware(
CORSMiddleware,
allow_origins=["http://localhost:3000"], # 指定允许访问的源（域名），只有这个地址
的页面可以请求本 API
allow_credentials=True, # 允许请求携带 Cookie 和 Authorization 等凭证信息
allow_methods=["*"], # 允许所有 HTTP 方法（GET、POST、PUT、DELETE 等），也可
以只写 ["GET", "POST"]
allow_headers=["*"], # 允许所有请求头，也可以只写特定的头如 ["Authorization",
"Content-Type"]
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
import secrets
import os
app = FastAPI()
# 生产环境建议从环境变量读取密钥，而非动态生成
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", secrets.token_hex(32))
# 添加多个中间件时，先添加的会先执行（洋葱模型）
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(

---

<!-- p.14 -->

代码解释：
生产环境中 SESSION_SECRET_KEY 应写入环境变量，避免每次重启应用生成新密钥导致会话失效
中间件的执行顺序遵循"洋葱模型"
请求从外到内穿过每个中间件，响应再从内到外穿过每个中间件
GZipMiddleware 用于压缩响应数据，减少网络传输量
minimum_size=1000 只压缩大于 1000 字节的响应
CORSMiddleware 处理跨域请求
SessionMiddleware 用于管理会话数据，会话数据存储在 Cookie 中
secret_key 对会话数据进行签名加密
secrets.token_hex(32) 生成一个安全的 32 字节随机密钥
先添加的中间件会先执行
全局依赖注入
通过 dependencies 参数可以为所有路由添加统一的依赖项，所有路由在处理请求前都会先执行这些依
赖：
CORSMiddleware,
allow_origins=["https://example.com"],
allow_credentials=True,
allow_methods=["GET", "POST"],
allow_headers=["Authorization"],
)
# 注意：使用 SessionMiddleware 需提前安装 itsdangerous（pip install itsdangerous）
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
security = HTTPBearer(auto_error=False) # auto_error=False 避免自动抛 403，手动处理
async def verify_token(authorization: HTTPAuthorizationCredentials | None =
Depends(security)):
if not authorization:
raise HTTPException(status_code=401, detail="未提供 Token")
if authorization.scheme != "Bearer":
raise HTTPException(status_code=401, detail="Token 格式错误（需为 Bearer 类
型）")
if authorization.credentials != "valid-token":
raise HTTPException(status_code=401, detail="无效的 Token")
return authorization.credentials
app = FastAPI(dependencies=[Depends(verify_token)])
@app.get("/items")
def get_items():
return [{"id": 1}, {"id": 2}]
@app.get("/users")
def get_users():
return [{"id": 1}, {"id": 2}]

---

<!-- p.15 -->

代码解释：
HTTPBearer 是 FastAPI 内置的安全方案，用于从请求头中提取 Bearer Token
Depends 是 FastAPI 依赖注入系统的核心
verify_token 是一个验证 Token 的依赖函数
security 是一个 HTTPBearer 方案，会自动从请求头中查找 Bearer token
将 dependencies=[Depends(verify_token)] 传入 FastAPI() 构造函数后
每一个路由在执行前都会先运行 verify_token 函数
如果 Token 无效，FastAPI 会立即返回 401 响应，而不会执行实际的路由处理函数
完整应用示例
以下是一个综合运用所有参数的完整示例：
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# 定义生命周期管理器，管理应用启动和关闭时的资源
@asynccontextmanager
async def lifespan(app: FastAPI):
print("应用启动")
yield
print("应用关闭")
# 创建 FastAPI 应用，配置所有基础参数
app = FastAPI(
title="完整示例 API",
description="展示 FastAPI 的各种配置参数",
version="1.0.0",
lifespan=lifespan, # 关联生命周期管理器
# 根据环境变量决定是否开启 API 文档
# 开发环境开启文档方便调试，生产环境关闭以保证安全
docs_url="/docs" if os.getenv("ENV") != "prod" else None,
redoc_url="/redoc" if os.getenv("ENV") != "prod" else None,
openapi_url="/openapi.json" if os.getenv("ENV") != "prod" else None,
# 配置 CORS 中间件，允许跨域请求
middleware=[
CORSMiddleware(
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)
]
)
@app.get("/")
def root():
# 通过 app 对象可以直接访问实例化时传入的配置
return {
"title": app.title,

---

<!-- p.16 -->

代码解释：
@asynccontextmanager 定义生命周期管理器，管理应用启动和关闭时的资源
title 设置 API 文档标题为"完整示例 API"
description 提供 API 的详细描述
version 声明 API 版本为 "1.0.0"
lifespan 关联生命周期管理器
docs_url 根据环境变量决定是否开启文档
redoc_url 同上，控制 Redoc 文档的开关
openapi_url 同上，控制 OpenAPI Schema 的开关
middleware 配置 CORS 中间件，允许跨域请求
@app.get("/") 定义根路径的路由处理函数
app.title 可以直接访问实例化时设置的标题
app.version 可以直接访问实例化时设置的版本号
app.docs_url 可以检查文档是否被禁用
@app.get("/items/{item_id}") 定义带路径参数的路由
raise HTTPException 当参数不合法时抛出异常
if __name__ == "__main__" 确保只有直接运行该文件时才会启动服务器
uvicorn.run 使用 uvicorn 运行应用
host="0.0.0.0" 使服务可以被外部访问
port=8000 指定监听端口
reload=True 开启热重载，代码修改后自动重启服务
配置要点总结
基础配置： title 、 version 、 description 等参数用于在 API 文档中展示元数据信息。
文档配置： docs_url 、 redoc_url 可以控制文档的访问路径，生产环境建议通过环境变量动态
控制。
异常处理：使用 exception_handlers 参数可以自定义异常发生时的响应格式，保持 API 响应的
一致性。
生命周期：优先使用 lifespan 管理应用启动和关闭时的资源，如数据库连接池、缓存连接等。
"version": app.version,
"docs": "/docs" if app.docs_url else "已禁用"
}
@app.get("/items/{item_id}")
def get_item(item_id: int):
if item_id < 1:
# 当参数不合法时抛出 HTTP 异常
raise HTTPException(status_code=400, detail="ID 必须大于 0")
return {"item_id": item_id}
if __name__ == "__main__":
# 使用 uvicorn 运行应用
# host="0.0.0.0" 使服务可以被外部访问
# port=8000 指定监听端口
# reload=True 开启热重载，代码修改后自动重启服务（仅开发环境使用）
import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

---

<!-- p.17 -->

中间件：通过 add_middleware 方法配置 CORS、GZip、Session 等功能，中间件按添加顺序执
行。
生产环境：务必关闭调试模式、禁用 API 文档、配置安全相关的中间件。
