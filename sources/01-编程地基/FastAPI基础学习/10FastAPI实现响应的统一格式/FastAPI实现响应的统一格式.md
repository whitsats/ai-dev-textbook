# FastAPI实现响应的统一格式

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\10FastAPI实现响应的统一格式\FastAPI实现响应的统一格式.pdf`
> **页数**：15（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 11,511 字符，其中汉字 1,483 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

方案 实现方式 适用场景 推荐程度
Pydantic 响应模
型
定义响应模型类 严格要求类型和文档 推荐
自定义响应类 继承 JSONResponse 统一包装数据 一般
全局异常处理器 app.exception_handler 统一错误格式 推荐
中间件包装 @app.middleware
全局统一包装所有响
应
不推荐（性能
差）
FastAPI 实现响应的统一格式
本文档介绍 FastAPI 中实现统一响应格式的几种方式，包括 Pydantic 响应模型、全局异常处理
器、自定义响应类，以及分页响应的处理和最佳实践。
在前后端分离的项目中，后端 API 返回统一的响应格式，可以让前端更容易解析和处理数据。
推荐：结合使用 Pydantic 响应模型 + 全局异常处理器，既能保证类型安全，又能统一错误格式。
方案对比
Pydantic 响应模型
定义一个基础响应模型，所有接口的响应都遵循此格式：
代码解释：
Generic[T] 定义泛型类型，支持不同 data 字段的数据结构
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional
T = TypeVar("T")
class BaseResponse(BaseModel, Generic[T]):
code: int = 200
message: str = "success"
data: Optional[T] = None
class ErrorResponse(BaseModel):
code: int = 400
message: str = "error"
error: dict = {}

---

<!-- p.2 -->

BaseResponse 包含三个标准字段： code （状态码）、 message （描述）、 data （数据）
Optional[T] = None 表示 data 可以是任意类型或为空
ErrorResponse 用于错误场景，包含 error 字段存放详细错误信息
基础使用
定义响应模型，让接口返回结构化的数据：
代码解释：
response_model=ItemListResponse 指定响应的数据模型
FastAPI 会自动验证返回数据是否符合模型定义
使用 response_model 时，FastAPI 直接返回模型字段，不会额外包装
注意：如果需要包装层 {code, message, data} ，需要手动返回 BaseResponse 实例，且必须
通过 response_model=BaseResponse 显式指定响应模型，确保类型校验和接口文档的正确性。
请求示例：
响应示例：
from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()
class Item(BaseModel):
item_id: str
class ItemListResponse(BaseModel):
items: list[Item]
@app.get("/items/", response_model=ItemListResponse)
def read_items():
items = [Item(item_id="Foo"), Item(item_id="Bar")]
return ItemListResponse(items=items)
curl http://127.0.0.1:8000/items/
{
"items": [
{"item_id": "Foo"},
{"item_id": "Bar"}
]
}

---

<!-- p.3 -->

手动包装成功响应
手动将数据包装到统一格式中：
代码解释：
user.model_dump() 将 Pydantic 模型转换为字典
BaseResponse(data=user.model_dump()) 将数据包装到统一响应格式中
response_model=BaseResponse 确保返回符合统一格式
请求示例：
响应示例：
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional
T = TypeVar("T")
class BaseResponse(BaseModel, Generic[T]):
code: int = 200
message: str = "success"
data: Optional[T] = None
class User(BaseModel):
username: str
email: str
app = FastAPI()
@app.get("/user/{user_id}", response_model=BaseResponse)
def get_user(user_id: int):
user = User(username="alice", email="alice@example.com")
return BaseResponse(data=user.model_dump())
curl http://127.0.0.1:8000/user/1
{
"code": 200,
"message": "success",
"data": {
"username": "alice",
"email": "alice@example.com"
}
}

---

<!-- p.4 -->

手动包装错误响应
手动返回结构化的错误响应：
代码解释：
ErrorResponse 与 BaseResponse 结构类似，但 error 字段改为必填
可灵活设置 code 和 message ，适应不同的错误场景
请求示例：
响应示例：
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional
T = TypeVar("T")
class BaseResponse(BaseModel, Generic[T]):
code: int = 200
message: str = "success"
data: Optional[T] = None
class ErrorResponse(BaseModel):
code: int = 400
message: str = "error"
error: dict = {}
app = FastAPI()
@app.get("/error/", response_model=ErrorResponse)
def read_error():
return ErrorResponse(
code=404,
message="Not Found",
error={"reason": "Item not found"},
)
curl http://127.0.0.1:8000/error/
{
"code": 404,
"message": "Not Found",
"error": {
"reason": "Item not found"
}
}

---

<!-- p.5 -->

全局异常处理器
通过 app.exception_handler 注册全局异常处理器，自动将所有 HTTP 异常转换为统一格式：
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
app = FastAPI()
class BaseResponse(BaseModel):
code: int
message: str
data: dict = {}
class ErrorResponse(BaseModel):
code: int
message: str
error: dict = {}
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
return JSONResponse(
status_code=exc.status_code,
content={
"code": exc.status_code,
"message": exc.detail,
"error": {"reason": exc.detail},
},
)
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
return JSONResponse(
status_code=500,
content={
"code": 500,
"message": "Internal Server Error",
"error": {"reason": str(exc)},
},
)
@app.get("/items/")
def read_items():
return {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
@app.get("/items/{item_id}")
def read_item(item_id: int):
if item_id > 10:

---

<!-- p.6 -->

代码解释：
@app.exception_handler(HTTPException) 捕获所有 HTTP 异常（如 404、401 等）
exc.status_code 和 exc.detail 提取异常的状态码和详情
@app.exception_handler(Exception) 捕获路由处理过程中未处理的通用异常，避免因未捕获
的业务异常导致接口返回非结构化错误（注：该处理器无法捕获中间件、事件钩子等路由外的异
常）
JSONResponse 直接返回 JSON 格式的响应内容
请求示例（正常接口）：
响应示例（200）：
请求示例（触发 404）：
响应示例（404）：
请求示例（触发 500）：
响应示例（500）：
raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
return {"item_id": item_id}
@app.get("/error/")
def trigger_error():
raise RuntimeError("This is a simulated error")
curl http://127.0.0.1:8000/items/
{
"items": [
{"item_id": "Foo"},
{"item_id": "Bar"}
]
}
curl http://127.0.0.1:8000/items/99
{
"code": 404,
"message": "Item 99 not found",
"error": {
"reason": "Item 99 not found"
}
}
curl http://127.0.0.1:8000/error/

---

<!-- p.7 -->

自定义响应类
继承 JSONResponse ，封装统一响应逻辑：
{
"code": 500,
"message": "Internal Server Error",
"error": {
"reason": "This is a simulated error"
}
}
from fastapi import FastAPI
from fastapi.responses import JSONResponse
class UnifiedResponse(JSONResponse):
def __init__(
self,
data: dict = None,
status_code: int = 200,
message: str = "success",
**kwargs
):
content = {
"code": status_code,
"message": kwargs.get("message", "success"),
"data": data or {},
}
super().__init__(content=content, status_code=status_code)
class ErrorResponse(JSONResponse):
def __init__(
self,
status_code: int = 400,
message: str = "error",
error: dict = None,
):
content = {
"code": status_code,
"message": message,
"error": error or {},
}
super().__init__(content=content, status_code=status_code)
app = FastAPI()
@app.get("/items/", response_class=UnifiedResponse)
def read_items():
items = [{"item_id": "Foo"}, {"item_id": "Bar"}]

---

<!-- p.8 -->

代码解释：
继承 JSONResponse 可以自定义响应格式
response_class=UnifiedResponse 指定使用自定义响应类
每次返回只需调用 UnifiedResponse(data={...}) ，无需手动构建字典
注意：使用 response_class 时，需要返回字典而非 Pydantic 模型实例。
请求示例：
响应示例（成功）：
响应示例（错误）：
中间件方案
中间件方案可以全局拦截所有响应，但性能较差（需要读取响应体两次），仅作了解：
return {"items": items}
@app.get("/error/", response_class=ErrorResponse)
def read_error():
return ErrorResponse(
status_code=404,
message="Not Found",
error={"reason": "Item not found"},
)
curl http://127.0.0.1:8000/items/
{
"code": 200,
"message": "success",
"data": {
"items": [
{"item_id": "Foo"},
{"item_id": "Bar"}
]
}
}
{
"code": 404,
"message": "Not Found",
"error": {
"reason": "Item not found"
}
}
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

---

<!-- p.9 -->

代码解释：
@app.middleware("http") 拦截所有 HTTP 请求
call_next(request) 执行后续路由逻辑，获取原始响应
response.body_iterator 用于读取响应体内容
为什么不推荐中间件方案：
1. 需要完整读取响应体再重新构建，性能开销大
2. 流式响应（如文件下载）会被破坏
import json
app = FastAPI()
@app.middleware("http")
async def unified_response_middleware(request: Request, call_next):
try:
response = await call_next(request)
# 重置响应体迭代器（关键修复）
body = b""
async for chunk in response.body_iterator:
body += chunk
response.body_iterator = iter([body]) # 重置迭代器
if response.status_code == 200:
try:
data = json.loads(body.decode("utf-8"))
except (json.JSONDecodeError, UnicodeDecodeError):
data = body.decode("utf-8", errors="replace")
# 重新构建统一响应
return JSONResponse(
status_code=200,
content={"code": 200, "message": "success", "data": data},
)
return response
# 捕获所有异常（而非仅 HTTPException）
except Exception as e:
if isinstance(e, HTTPException):
status_code = e.status_code
detail = e.detail
else:
status_code = 500
detail = "Internal Server Error"
return JSONResponse(
status_code=status_code,
content={"code": status_code, "message": detail, "error": {"reason":
str(e)}},
)
@app.get("/items/")
def read_items():
return [{"item_id": "Foo"}, {"item_id": "Bar"}]

---

<!-- p.10 -->

3. 复杂场景下容易出现双 JSON 编码问题
4. 异常处理不完整（如路由不存在时）
分页响应的统一格式
在实际业务中，分页接口需要返回总数和页码信息：
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional, List
T = TypeVar("T")
app = FastAPI()
class BaseResponse(BaseModel, Generic[T]):
code: int = 200
message: str = "success"
data: Optional[T] = None
class PageInfo(BaseModel):
page: int = Field(..., description="当前页码")
page_size: int = Field(..., description="每页数量")
total: int = Field(..., description="总数")
total_pages: int = Field(..., description="总页数")
class PaginatedData(BaseModel, Generic[T]):
items: List[T]
pagination: PageInfo
class User(BaseModel):
username: str
email: str
USERS = [
User(username=f"user{i}", email=f"user{i}@example.com")
for i in range(1, 101)
]
@app.get("/users/", response_model=BaseResponse)
def list_users(
page: int = Query(1, ge=1),
page_size: int = Query(10, ge=1, le=100),
):
total = len(USERS)
start = (page - 1) * page_size
end = start + page_size
items = USERS[start:end]

---

<!-- p.11 -->

代码解释：
PageInfo 封装分页信息，包含当前页、每页数量、总数和总页数
PaginatedData 将数据列表和分页信息组合在一起
(total + page_size - 1) // page_size 计算总页数（向上取整）
[u.model_dump() for u in items] 将 Pydantic 模型列表转为字典列表
请求示例：
响应示例：
最佳实践
total_pages = (total + page_size - 1) // page_size
return BaseResponse(
data=PaginatedData(
items=[u.model_dump() for u in items],
pagination=PageInfo(
page=page,
page_size=page_size,
total=total,
total_pages=total_pages,
),
).model_dump(),
)
curl "http://127.0.0.1:8000/users/?page=2&page_size=5"
{
"code": 200,
"message": "success",
"data": {
"items": [
{"username": "user6", "email": "user6@example.com"},
{"username": "user7", "email": "user7@example.com"},
{"username": "user8", "email": "user8@example.com"},
{"username": "user9", "email": "user9@example.com"},
{"username": "user10", "email": "user10@example.com"}
],
"pagination": {
"page": 2,
"page_size": 5,
"total": 100,
"total_pages": 20
}
}
}

---

<!-- p.12 -->

推荐方案：异常处理器 + Pydantic
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional
T = TypeVar("T")
app = FastAPI()
class BaseResponse(BaseModel, Generic[T]):
code: int = 200
message: str = "success"
data: Optional[T] = None
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
return JSONResponse(
status_code=exc.status_code,
content={
"code": exc.status_code,
"message": exc.detail,
"error": {},
},
)
@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
return JSONResponse(
status_code=500,
content={
"code": 500,
"message": "服务器内部错误",
"error": {},
},
)
@app.get("/items/")
def list_items():
return {"items": [{"id": 1}, {"id": 2}]}
@app.post("/items/")
def create_item(item: dict):
return {"id": 1, **item}
@app.get("/items/{item_id}")
def get_item(item_id: int):
if item_id > 10:

---

<!-- p.13 -->

字段 类型 说明 示例
code int
业务状态码（建议与 HTTP 状态码对齐，特殊场
景可自定义业务码，如 HTTP 200 但 code=400
表示参数校验失败）
200 , 400 , 401 ,
404 , 500
message str 状态描述
"success" , "Not
Found" , "参数错误"
data object 业务数据（成功时返回）
{"id": 1,
"name": "..."}
error object 错误详情（失败时返回）
{"code":
"INVALID_PARAM",
"detail": "..."}
code 含义 适用场景
200 成功 正常响应
400 请求错误 参数校验失败、格式错误
401 未认证 未登录、Token 过期
403 无权限 权限不足
404 资源不存在 查询的数据不存在
500 服务器错误 内部异常、数据库错误
代码解释：
全局异常处理器自动捕获 HTTPException ，无需在每个接口中手动处理错误
BaseResponse 提供统一的成功响应格式
业务接口可以专注于业务逻辑，错误处理由框架统一完成
响应格式规范建议
常见错误码规范
总结
raise HTTPException(status_code=404, detail="商品不存在")
return {"id": item_id, "name": f"Item {item_id}"}
@app.delete("/items/{item_id}")
def delete_item(item_id: int):
return {"message": f"Item {item_id} deleted"}

---

<!-- p.14 -->

方案 优点 缺点 推荐场景
Pydantic 响应
模型
类型安全、自动文档、验证 需手动包装 所有场景
全局异常处理器
自动处理所有错误、统一错误
格式
仅处理异常
所有场景（必
用）
自定义响应类 复用简单
需指定
response_class
需要统一包装时
中间件 全局拦截 性能差、破坏流式响应 不推荐
方案对比
最佳实践：使用 全局异常处理器 统一错误响应 + Pydantic 响应模型 定义数据结构，既简洁又高
效。
