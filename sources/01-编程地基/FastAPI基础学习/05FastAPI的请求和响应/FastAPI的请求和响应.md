# FastAPI的请求和响应

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\05FastAPI的请求和响应\FastAPI的请求和响应.pdf`
> **页数**：15（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 10,621 字符，其中汉字 1,599 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

传参方式 说明 示例
查询参数
放在 URL 末尾 ? 之后，键值对以 & 分
割
?page=1&size=10
路径参数 嵌入在 URL 路径中 /users/{user_id}
请求体 POST、PUT、PATCH 请求中的数据 JSON 或表单数据
请求头 /
Cookie
HTTP Header 中的元数据
Authorization: Bearer
xxx
FastAPI 的请求和响应
本文档介绍 FastAPI 中请求数据的解析方式和响应的构建方法，涵盖查询参数、路径参数、请求
体、请求头、Cookie 以及各种响应类型的使用。
请求数据概述
请求传参主要分为四种方式：
HTTP 请求体结构
了解 HTTP 请求体的基本结构，有助于理解 FastAPI 如何处理请求数据：
代码解释：
第一行包含 HTTP 方法、路径和协议版本
中间部分是请求头（Header），包含服务器地址、内容类型和 Cookie 等元数据
空行之后是请求体（Body），包含实际传输的数据
查询参数
查询参数缀在 URL 末尾，以 ? 开头，键值对以 & 分割。FastAPI 会自动将查询参数绑定到函数中同名
的参数上。
POST /login HTTP/1.1
Host: www.example.com
Content-Type: application/json
Cookie: session_id=abc123; csrftoken=def456
{
"username": "zhangsan",
"password": "123456",
"email": "zhangsan@example.com",
"age": 25,
"is_vip": true
}

---

<!-- p.2 -->

基础示例
代码解释：
函数参数 skip 和 limit 自动映射到 URL 中的查询参数
有默认值的参数为可选，不传时使用默认值
请求示例： GET http://127.0.0.1:8000/items/?skip=1&limit=5
响应示例：
必填查询参数
如果不设置默认值，查询参数将成为必填项：
代码解释：
不提供默认值时，客户端必须传递该参数，否则 FastAPI 返回 422 验证错误
路径参数
路径参数通过在 URL 中使用 {} 大括号定义。FastAPI 会自动将 URL 路径中的值绑定到函数中同名的参
数上。
from fastapi import FastAPI
app = FastAPI()
@app.get("/items/")
def read_item(skip: int = 0, limit: int = 10):
return {"skip": skip, "limit": limit}
{
"skip": 1,
"limit": 5
}
from fastapi import FastAPI
app = FastAPI()
@app.get("/items/")
def read_item(skip: int, limit: int = 10):
return {"skip": skip, "limit": limit}

---

<!-- p.3 -->

基础示例
代码解释：
路径参数 item_id 在大括号中声明，FastAPI 会自动进行类型校验和转换
查询参数 q 为可选，不传递时为 None
请求示例： GET http://127.0.0.1:8000/items/5/?q=search
响应示例：
类型转换
FastAPI 根据参数类型注解自动进行类型转换。如果 item_id 声明为 int 但传入字符串 "abc" ，将返
回 422 验证错误（表示请求格式正确但数据验证失败）。
请求体
请求体用于接收客户端发送的数据，主要用于 POST、PUT、PATCH 请求。GET 请求不应使用请求体。
使用 Pydantic 模型
from fastapi import FastAPI
app = FastAPI()
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
return {"item_id": item_id, "q": q}
{
"item_id": 5,
"q": "search"
}
from pydantic import BaseModel
from fastapi import FastAPI
app = FastAPI()
class Item(BaseModel):
name: str
description: str | None = None
price: float
tax: float | None = None
@app.post("/items/")
def create_item(item: Item):
return item

---

<!-- p.4 -->

代码解释：
使用 Pydantic 模型定义请求体结构，FastAPI 自动解析 JSON 并进行数据校验
BaseModel 的字段即为请求体的 JSON 键名
请求示例：
响应示例：
可选字段
使用 | None 表示可选字段：
代码解释：
description 和 tax 字段为可选，不传时为 None
使用 (item.tax or 0) 安全处理 None 值
请求头和 Cookie
{
"name": "示例商品",
"description": "这是一个测试商品",
"price": 99.9,
"tax": 10.0
}
{
"name": "示例商品",
"description": "这是一个测试商品",
"price": 99.9,
"tax": 10.0
}
from pydantic import BaseModel
from fastapi import FastAPI
app = FastAPI()
class Item(BaseModel):
name: str
description: str | None = None
price: float
tax: float | None = None
@app.post("/items/")
def create_item(item: Item):
total = item.price + (item.tax or 0)
return {"name": item.name, "total": total}

---

<!-- p.5 -->

获取请求头
使用 Header 获取请求头数据。FastAPI 会自动将连字符（ - ）转换为下划线（ _ ），并忽略大小写：
代码解释：
Header(None) 表示该请求头为可选，不传时参数值为 None
User-Agent → user_agent （自动转换）， Accept-Language → accept_language
获取 Cookie
使用 Cookie 获取客户端发送的 Cookie 数据：
同时使用多种传参方式
from fastapi import FastAPI, Header
app = FastAPI()
@app.get("/client-info")
def read_item(
user_agent: str | None = Header(None),
accept_language: str | None = Header(None),
):
return {
"user_agent": user_agent,
"accept_language": accept_language,
}
from fastapi import FastAPI, Cookie
app = FastAPI()
@app.get("/cookies")
def read_cookies(session_id: str | None = Cookie(None)):
return {"session_id": session_id}
from fastapi import FastAPI, Path, Query, Header, Cookie
app = FastAPI()
@app.get("/mixed/{user_id}")
def mixed_params(
user_id: int = Path(..., description="用户ID"),
name: str = Query(..., min_length=2, description="用户名"),
page: int = Query(1, ge=1, description="页码"),
token: str = Header(...),
session: str | None = Cookie(None),
):
return {

---

<!-- p.6 -->

代码解释：
Path(...) 声明路径参数， Query(...) 声明查询参数， Header(...) 声明请求头，
Cookie(...) 声明 Cookie
... 表示必填， None 表示可选
min_length 、 ge 等验证器用于约束参数范围
响应数据
FastAPI 默认将返回值转换为 JSON 格式，并设置 Content-Type: application/json 响应头。
返回字典
返回 Pydantic 模型
代码解释：
返回 Pydantic 模型时，FastAPI 自动将其序列化为 JSON
模型中定义的字段类型用于响应数据的校验
"user_id": user_id,
"name": name,
"page": page,
"token": token,
"session": session,
}
from fastapi import FastAPI
app = FastAPI()
@app.get("/items/")
def read_item(skip: int = 0, limit: int = 10):
return {"skip": skip, "limit": limit}
from pydantic import BaseModel
from fastapi import FastAPI
app = FastAPI()
class Item(BaseModel):
name: str
description: str | None = None
price: float
tax: float | None = None
@app.post("/items/")
def create_item(item: Item):
return item

---

<!-- p.7 -->

状态码 说明 使用场景
200 OK 成功响应
201 Created 资源创建成功
204 No Content 删除成功，无返回内容
400 Bad Request 请求参数错误
401 Unauthorized 未认证
403 Forbidden 无权限
404 Not Found 资源不存在
500 Internal Server Error 服务器内部错误
状态码
使用装饰器指定状态码
使用 HTTPException 抛出异常
常见状态码：
自定义响应头
from fastapi import FastAPI
app = FastAPI()
@app.get("/happy", status_code=200)
def happy():
return {"message": "happy"}
from fastapi import FastAPI, HTTPException
app = FastAPI()
@app.get("/items/{item_id}")
def read_item(item_id: int):
if item_id == 42:
raise HTTPException(status_code=404, detail="Item not found")
return {"item_id": item_id}

---

<!-- p.8 -->

响应类型 说明 使用场景
JSONResponse JSON 响应（默认） API 接口
HTMLResponse HTML 响应 网页、模板
PlainTextResponse 纯文本响应 文本数据
RedirectResponse 重定向响应 页面跳转
FileResponse 文件响应 下载文件
StreamingResponse 流式响应 大文件、流媒体
使用 Response 对象
代码解释：
注入 Response 对象后，可以直接操作响应头 response.headers
适用于动态设置自定义响应头的场景
使用 JSONResponse
代码解释：
JSONResponse 的 headers 参数允许同时设置多个自定义响应头
适用于需要精确控制响应头内容的场景
响应类型
FastAPI 支持多种响应类型，位于 fastapi.responses 模块中：
from fastapi import FastAPI, Response
app = FastAPI()
@app.get("/header/{name}/{value}")
def read_item(name: str, value: str, response: Response):
response.headers[name] = value
return {"message": "success"}
from fastapi import FastAPI
from fastapi.responses import JSONResponse
app = FastAPI()
@app.get("/items/{item_id}")
def read_item(item_id: int):
content = {"item_id": item_id}
headers = {"X-Custom-Header": "custom-value", "X-API-Version": "v1"}
return JSONResponse(content=content, headers=headers)

---

<!-- p.9 -->

HTMLResponse
PlainTextResponse
RedirectResponse
FileResponse
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
app = FastAPI()
@app.get("/html", response_class=HTMLResponse)
def read_html():
return """
<html>
<head><title>FastAPI</title></head>
<body>
<h1>Hello FastAPI!</h1>
</body>
</html>
"""
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
app = FastAPI()
@app.get("/text", response_class=PlainTextResponse)
def read_text():
return "Hello, World!"
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
app = FastAPI()
@app.get("/redirect")
def redirect():
return RedirectResponse(url="/items/", status_code=302)

---

<!-- p.10 -->

代码解释：
FileResponse 自动设置 Content-Disposition 响应头，触发浏览器下载
file_path:path 中的 path 类型可以匹配包含斜杠的路径
StreamingResponse
代码解释：
StreamingResponse 接收一个生成器或异步迭代器，流式返回数据
适用于大文件下载、日志流、实时数据推送等场景
response_model
response_model 用于定义响应的数据结构。FastAPI 会自动过滤返回对象中不属于 response_model
的字段，并按模型约束做数据校验 / 转换。
from fastapi import FastAPI
from fastapi.responses import FileResponse
app = FastAPI()
@app.get("/download/{file_path:path}")
def download_file(file_path: str):
return FileResponse(
path=f"./files/{file_path}",
filename=file_path,
media_type="application/octet-stream",
)
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
app = FastAPI()
async def generate_csv():
for i in range(10):
yield f"row_{i},data_{i}\n"
@app.get("/csv")
def get_csv():
return StreamingResponse(
generate_csv(),
media_type="text/csv",
headers={"Content-Disposition": "attachment; filename=data.csv"},
)

---

<!-- p.11 -->

为什么要使用 response_model
在实际开发中，通常需要定义多个数据模型：
输入模型：接收用户请求
输出模型：返回给客户端
内部模型：供内部逻辑使用
实际应用场景
代码解释：
UserCreate 定义输入格式（包含 password ）
UserDB 定义数据库存储格式（包含 password 哈希和时间戳）
UserOut 定义输出格式（不包含 password ），通过 response_model 过滤敏感字段
请求示例：
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI
app = FastAPI()
class UserCreate(BaseModel):
username: str
password: str
email: str
class UserDB(BaseModel):
username: str
password: str
email: str
created_at: datetime
is_active: bool = True
class UserOut(BaseModel):
username: str
email: str
created_at: datetime
is_active: bool
@app.post("/users/", response_model=UserOut)
def create_user(user: UserCreate) -> UserOut:
db_user = UserDB(
username=user.username,
password="hashed_" + user.password,
email=user.email,
created_at=datetime.now(),
)
return db_user

---

<!-- p.12 -->

响应示例（只有安全的字段）：
使用列表作为 response_model
设置 Cookie
代码解释：
{
"username": "john",
"password": "secret123",
"email": "john@example.com"
}
{
"username": "john",
"email": "john@example.com",
"created_at": "2024-01-01T12:00:00",
"is_active": true
}
from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()
class Item(BaseModel):
id: int
name: str
price: float
@app.get("/items/", response_model=list[Item])
def get_items():
return [
{"id": 1, "name": "苹果", "price": 5.5},
{"id": 2, "name": "香蕉", "price": 3.2},
]
from fastapi import FastAPI, Response
app = FastAPI()
@app.post("/login")
def login(response: Response):
response.set_cookie(key="session_id", value="abc123", httponly=True)
return {"message": "登录成功"}

---

<!-- p.13 -->

httponly=True 禁止前端 JavaScript 读取该 Cookie，可大幅降低 XSS 攻击导致的 Cookie 泄露风
险
还可以设置 secure=True （仅 HTTPS）、 samesite （防止 CSRF）等参数
完整示例：CRUD 路由
代码解释：
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional
app = FastAPI()
class Item(BaseModel):
name: str
description: Optional[str] = None
price: float
quantity: int = 0
items_db = {}
@app.post("/items/", status_code=status.HTTP_201_CREATED, response_model=Item)
def create_item(item: Item):
if item.name in items_db:
raise HTTPException(status_code=400, detail="商品已存在")
items_db[item.name] = item
return item
@app.get("/items/{name}", response_model=Item)
def get_item(name: str):
if name not in items_db:
raise HTTPException(status_code=404, detail="商品不存在")
return items_db[name]
@app.put("/items/{name}", response_model=Item)
def update_item(name: str, item: Item):
if name not in items_db:
raise HTTPException(status_code=404, detail="商品不存在")
items_db[name] = item
return item
@app.delete("/items/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(name: str):
if name not in items_db:
raise HTTPException(status_code=404, detail="商品不存在")
del items_db[name]

---

<!-- p.14 -->

status_code 使用 status.HTTP_201_CREATED 等常量而非硬编码数字，便于维护
response_model=Item 确保响应数据符合 Item 定义，防止内部字段泄露
删除操作返回 204 No Content，响应体为空
总结
1. 请求方式选择：
路径参数用于定位资源（REST 风格）
查询参数用于过滤、分页等可选条件
请求体用于提交复杂数据
请求头和 Cookie 用于传递认证和会话信息
2. 响应处理：
使用 response_model 过滤敏感字段，分离输入输出模型
根据需求选择合适的响应类型（JSON、HTML、文件等）
使用 HTTPException 处理业务异常，返回合适的状态码
3. 最佳实践：
为所有参数提供类型注解，FastAPI 自动进行数据校验
使用 Pydantic 模型处理请求体和响应体
Cookie 设置 httponly=True 防止 XSS 攻击
