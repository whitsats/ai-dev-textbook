# FastAPI的路由

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\04FastAPI的路由\FastAPI的路由.pdf`
> **页数**：13（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 9,151 字符，其中汉字 1,810 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 的路由
本文档介绍 FastAPI 中路由的定义方式、路由分组、路由优先级、同步与异步处理等核心内容。
基本路由创建
根路径路由
代码解释：
FastAPI() 创建 FastAPI 应用实例
@app.get("/") 使用 GET 装饰器注册路由， "/" 表示根路径
read_root 是路由处理函数，返回值会自动序列化为 JSON 响应
启动服务后，访问 http://127.0.0.1:8000/ 即可看到响应：
带参数的路由
代码解释：
路径参数 item_id 在大括号中声明，FastAPI 会自动进行类型校验
查询参数 q 通过函数参数定义，可选（ None ）时不传递也不会报错
请求示例： GET http://127.0.0.1:8000/items/42?q=runoob
响应示例：
from fastapi import FastAPI
app = FastAPI()
@app.get("/")
def read_root():
return {"Hello": "World"}
uvicorn main:app --reload
from fastapi import FastAPI
app = FastAPI()
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
return {"item_id": item_id, "q": q}

---

<!-- p.2 -->

方法 说明 常见用途
GET 读取资源 获取数据列表或详情
POST 创建资源 新增数据
PUT 完整更新 替换整个资源
PATCH 部分更新 更新资源的部分字段
DELETE 删除资源 删除指定数据
OPTIONS 查询支持的方法 获取服务器能力
HEAD 获取元数据 检查资源是否存在
七种 HTTP 方法
FastAPI 支持 RESTful API 规范，常用的 HTTP 方法如下：
{
"item_id": 42,
"q": "runoob"
}
from fastapi import FastAPI
from fastapi import Response
app = FastAPI()
@app.get("/items")
def get_items():
return {"method": "GET"}
@app.post("/items")
def create_item():
return {"method": "POST"}
@app.put("/items/{item_id}")
def update_item(item_id: int):
return {"method": "PUT", "item_id": item_id}
@app.patch("/items/{item_id}")
def patch_item(item_id: int):
return {"method": "PATCH", "item_id": item_id}
@app.delete("/items/{item_id}")
def delete_item(item_id: int):

---

<!-- p.3 -->

代码解释：
OPTIONS 方法返回服务器支持的 HTTP 方法列表，常用于 CORS 预检请求
HEAD 方法与 GET 类似，但只返回响应头，不返回响应体，常用于检查资源是否存在
路由装饰器详解
同一路由绑定多个 URL
一个视图函数可以绑定多个 URL 地址：
代码解释：
同一函数可以使用多个装饰器，FastAPI 会将多个路径注册到同一处理函数
response_class 指定响应类型，只需在最外层装饰器设置
同一 URL 支持多种 HTTP 方法
一个 URL 可以同时支持多种 HTTP 方法：
代码解释：
return {"method": "DELETE", "item_id": item_id}
@app.options("/items")
def options_items():
return {"method": "OPTIONS", "allow": "GET,POST,PUT,PATCH,DELETE,OPTIONS"}
@app.head("/items")
def head_items():
return Response(status_code=200)
from fastapi import FastAPI
from fastapi.responses import JSONResponse
app = FastAPI()
@app.get("/", response_class=JSONResponse)
@app.get("/index", response_class=JSONResponse)
def home():
return {"message": "Welcome"}
from fastapi import FastAPI
app = FastAPI()
@app.api_route(path="/index", methods=["GET", "POST"])
async def index():
return {"index": "index"}

---

<!-- p.4 -->

访问地址 匹配路由 输出
/user/userid 动态路由（先注册） {"type": "dynamic", "userid": "userid"}
/user/john 动态路由 {"type": "dynamic", "userid": "john"}
api_route 支持通过 methods 参数指定多个 HTTP 方法
适合同一端点需要处理不同操作（如同时支持 GET 和 POST）的场景
使用 add_api_route 注册路由
除装饰器外，也可以使用 add_api_route 方法显式注册路由：
路由优先级
静态路由 vs 动态路由
当静态路由和动态路由同时存在时，先注册的路由优先匹配。
访问结果：
代码解释：
动态路由 /user/{userid} 先注册，匹配了所有以 /user/ 开头的路径
静态路由 /user/userid 后注册，实际被动态路由"抢走"了
调换注册顺序后，静态路由会优先匹配
from fastapi import FastAPI
from fastapi.responses import JSONResponse
app = FastAPI()
async def index():
return JSONResponse({"index": "index"})
app.add_api_route(path="/index2", endpoint=index, methods=["GET", "POST"])
from fastapi import FastAPI
app = FastAPI()
@app.get('/user/{userid}')
async def get_user_dynamic(userid: str):
return {"type": "dynamic", "userid": userid}
@app.get('/user/userid')
async def get_user_static():
return {"type": "static"}

---

<!-- p.5 -->

最佳实践：
避免创建可能冲突的路由
将静态路由放在动态路由前面注册
RESTful 设计规范建议使用明确的路径层级
APIRouter 路由分组
基本用法
使用 APIRouter 实现模块化的路由分组，类似 Flask 的蓝图：
代码解释：
prefix 参数为该组下所有路由添加统一前缀，如 /user 、 /pay
tags 参数为该组下所有路由设置文档分组标签
include_router 将路由分组注册到应用，路径会自动拼接
注册后的完整路由：
from fastapi import FastAPI, APIRouter
app = FastAPI()
# 创建用户模块路由
router_user = APIRouter(prefix="/user", tags=["用户模块"])
@router_user.get("/login")
def user_login():
return {"ok": "登录成功"}
@router_user.get("/info")
def user_info():
return {"username": "john", "email": "john@example.com"}
# 创建支付模块路由
router_pay = APIRouter(prefix="/pay", tags=["支付模块"])
@router_pay.get("/order")
def pay_order():
return {"ok": "订单支付成功"}
@router_pay.post("/refund")
def pay_refund():
return {"ok": "退款成功"}
app.include_router(router_user)
app.include_router(router_pay)

---

<!-- p.6 -->

URL 说明
/user/login 用户登录接口
/user/info 用户信息接口
/pay/order 支付订单接口
/pay/refund 退款接口
参数 说明 示例
prefix URL 前缀 prefix="/api/v1"
tags 文档分组标签 tags=["用户模块"]
dependencies 路由依赖注入 dependencies=[Depends(auth)]
responses 响应配置 responses={404: {"model": ErrorModel}}
APIRouter 常用参数
完整示例
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from pydantic import BaseModel
app = FastAPI()
class UserCreate(BaseModel):
username: str
email: str
password: str
class UserOut(BaseModel):
id: int
username: str
email: str
router = APIRouter(prefix="/api/users", tags=["用户管理"])
users_db = {}
user_id_counter = 1
@router.post("/", response_model=UserOut, status_code=201)
def create_user(user: UserCreate):
global user_id_counter
new_user = UserOut(id=user_id_counter, username=user.username,
email=user.email)
users_db[user_id_counter] = new_user

---

<!-- p.7 -->

代码解释：
response_model 指定响应的 Pydantic 模型，FastAPI 会自动进行数据验证和序列化
status_code 指定 HTTP 状态码，如 201 表示创建成功
router.get("/{user_id}") 中 {user_id} 是路径参数，与函数参数名对应
路由元数据配置
常用元数据参数
user_id_counter += 1
return new_user
@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int):
if user_id not in users_db:
raise HTTPException(status_code=404, detail="用户不存在")
return users_db[user_id]
@router.get("/", response_model=list[UserOut])
def list_users(skip: int = 0, limit: int = 10):
return list(users_db.values())[skip:skip + limit]
@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int):
if user_id not in users_db:
raise HTTPException(status_code=404, detail="用户不存在")
del users_db[user_id]
app.include_router(router)
from fastapi import FastAPI
app = FastAPI()
@app.get(
"/items/{item_id}",
summary="获取商品详情",
description="根据商品ID获取商品的详细信息，包括名称、描述、价格等",
response_description="返回商品详情对象",
tags=["商品管理"],
deprecated=False,
)
def get_item(item_id: int):
return {"item_id": item_id, "name": "示例商品"}

---

<!-- p.8 -->

参数 说明
summary 简短的接口描述（显示在文档中）
description 详细的接口描述（支持 Markdown）
response_description 响应说明
tags 接口分组标签
deprecated 标记接口是否已废弃
operation_id 自定义操作 ID
废弃接口
代码解释：
deprecated=True 在 /docs 中会显示警告标识，提示调用者该接口即将移除
废弃接口仍然可以正常工作，直到正式移除
同步与异步路由
同步路由
使用 def 定义的同步函数，FastAPI 会在线程池中执行：
@app.get("/old-endpoint", deprecated=True)
def old_endpoint():
return {"message": "此接口已废弃，请使用新接口"}
from fastapi import FastAPI
import threading
import time
app = FastAPI()
@app.get("/sync")
def sync_endpoint():
time.sleep(1)
return {
"type": "sync",
"thread_id": threading.current_thread().ident,
}

---

<!-- p.9 -->

特性 同步路由 异步路由
关键字 def async def
执行方式 线程池 单线程事件循环
适用场景 CPU 密集型、同步 IO IO 密集型、异步操作
阻塞处理 time.sleep() await asyncio.sleep()
并发能力 依赖线程数 高并发
异步路由
使用 async def 定义的异步函数，在同一个事件循环中执行：
性能对比
选择建议
使用同步：数据库查询、文件操作等同步 IO
使用异步：HTTP 客户端调用、消息队列等异步操作
避免混用：不要在 async def 中使用 time.sleep() ，应使用 await asyncio.sleep()
路由依赖注入
路由级依赖注入
from fastapi import FastAPI
import asyncio
app = FastAPI()
@app.get("/async")
async def async_endpoint():
await asyncio.sleep(1)
return {
"type": "async",
"thread_id": threading.current_thread().ident,
}
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
app = FastAPI()
security = HTTPBearer()
async def verify_token(credentials: HTTPAuthorizationCredentials =
Depends(security)):
# 提取 token 字符串进行校验
if credentials.credentials != "secret-token":

---

<!-- p.10 -->

代码解释：
Depends(verify_token) 将认证函数声明为依赖项，每个请求在到达处理函数前会先执行
dependencies=[...] 在路由级别注册依赖，无需在每个处理函数中显式声明参数
适合认证、权限校验、请求日志等横切关注点
路由响应配置
代码解释：
responses 参数在 OpenAPI 文档中声明该路由可能返回的多种响应状态码
每个状态码可以指定 description （描述）和 model （响应模型）
查看路由信息
打印所有路由
raise HTTPException(status_code=401, detail="无效的 Token")
return credentials.credentials
@app.get("/protected", dependencies=[Depends(verify_token)])
def protected_endpoint():
return {"message": "访问受保护的接口"}
from fastapi import FastAPI
app = FastAPI()
@app.get(
"/custom-response",
responses={
200: {"description": "成功响应"},
404: {"description": "资源不存在"},
500: {"description": "服务器错误"},
},
)
def custom_response():
return {"message": "custom response"}

---

<!-- p.11 -->

输出示例：
过滤路由类型
代码解释：
app.routes 包含应用的所有路由，包括内置的 /docs 和 /openapi.json
使用 hasattr 过滤出 APIRoute 实例，避免访问非路由对象的属性
常见问题
1. 路由参数类型不匹配
代码解释：
FastAPI 根据函数参数类型注解（ int ）自动进行路径参数类型校验
类型不匹配时返回 422 Unprocessable Entity 错误
from fastapi import FastAPI
app = FastAPI()
@app.get("/items")
def get_items():
return []
for route in app.routes:
print(route.path, route.methods)
/items {'GET'}
/docs {'GET'}
/openapi.json {'GET'}
for route in app.routes:
if hasattr(route, 'path') and hasattr(route, 'methods'):
print(f"{list(route.methods)} {route.path}")
# 路径参数期望整数，传入会自动校验
# /items/abc → 422 验证错误
# /items/123 → 正常工作
@app.get("/items/{item_id}")
def get_item(item_id: int):
return {"item_id": item_id}

---

<!-- p.12 -->

2. 路由顺序问题
代码解释：
FastAPI 按照路由注册顺序匹配，先注册的路由优先级更高
动态路由放在前面会导致所有匹配都被它捕获
3. async/await 混用问题
代码解释：
time.sleep() 是同步阻塞，会冻结整个事件循环，导致高并发场景下性能急剧下降
asyncio.sleep() 是异步非阻塞，等待期间事件循环可以处理其他请求
总结
1. 路由创建：使用 @app.method(path) 装饰器创建基本路由
2. 路由分组：使用 APIRouter 实现模块化管理
3. 优先级：先注册的路由优先匹配，注意静态和动态路由的顺序
4. 同步异步：根据业务场景选择合适的函数类型
5. 元数据：使用 summary 、 description 、 tags 等完善 API 文档
6. 依赖注入：使用 dependencies 实现认证、限流等横切功能
# 动态路由放在前面会"吞掉"静态路由
@app.get("/{username}")
@app.get("/about")
# 推荐：静态路由优先注册
@app.get("/about")
@app.get("/{username}")
# 错误：在 async 函数中使用同步阻塞
async def bad_example():
time.sleep(1) # 阻塞整个事件循环
return {}
# 正确：使用异步等待
async def good_example():
await asyncio.sleep(1) # 非阻塞，事件循环可处理其他请求
return {}
