# FastAPI中Header的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\09FastAPI中Header的使用\FastAPI中Header的使用.pdf`
> **页数**：14（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 11,062 字符，其中汉字 1,258 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

HTTP Header 名称 Python 参数名
User-Agent user_agent
Accept-Encoding accept_encoding
X-Token-Value x_token_value
Content-Type content_type
Authorization authorization
FastAPI 中 Header 的使用
本文档介绍 FastAPI 中 Header 的用法，包括请求头获取、自定义 Header、认证相关 Header、
多值 Header、响应 Header 设置以及自动类型转换等。
Header 是 FastAPI 中用于获取 HTTP 请求头数据的工具，支持自动类型转换、参数验证和自动文档生
成。
Header 参数基础
自动转换（kebab-case → snake_case）
FastAPI 会自动完成双向转换：
客户端传入的 kebab-case 格式请求头（如 X-Token-Value ）→ 映射为 Python 蛇形命名参数
（ x_token_value ）；
Python 蛇形命名参数（ x_token_value ）→ 自动匹配客户端的 X-Token-Value 请求头（而非
x_token_value ）。
代码解释：
Header(None) 表示该 Header 为可选，未提供时返回 None
FastAPI 自动将 User-Agent 转换为 user_agent （kebab-case → snake_case）
无需手动解析，参数直接可用
请求示例：
from fastapi import FastAPI, Header
from typing import Optional
app = FastAPI()
@app.get("/headers/")
def read_headers(user_agent: Optional[str] = Header(None)):
return {"user_agent": user_agent}

---

<!-- p.2 -->

响应示例：
常用请求头示例
获取多个常见的 HTTP 请求头：
代码解释：
每个 Header(None) 参数对应一个 HTTP 请求头
多个参数可同时使用，FastAPI 自动提取对应的 Header 值
请求示例：
curl -X GET "http://127.0.0.1:8000/headers/" \
-H "User-Agent: curl/7.79.1"
{
"user_agent": "curl/7.79.1"
}
from fastapi import FastAPI, Header
from typing import Optional
app = FastAPI()
@app.get("/headers/")
def read_headers(
host: Optional[str] = Header(None),
user_agent: Optional[str] = Header(None),
accept: Optional[str] = Header(None),
accept_language: Optional[str] = Header(None),
accept_encoding: Optional[str] = Header(None),
connection: Optional[str] = Header(None),
content_type: Optional[str] = Header(None),
):
return {
"host": host,
"user_agent": user_agent,
"accept": accept,
"accept_language": accept_language,
"accept_encoding": accept_encoding,
"connection": connection,
"content_type": content_type,
}

---

<!-- p.3 -->

响应示例：
自定义 Header
简单自定义 Header
使用 Header(...) 接收自定义请求头：
代码解释：
自定义 Header X-Token 自动转换为参数名 x_token
Header(None) 使其可选，未提供时返回 None
请求示例（带 Token）：
响应示例：
curl -X GET "http://127.0.0.1:8000/headers/" \
-H "Host: example.com" \
-H "User-Agent: MyApp/1.0" \
-H "Accept: application/json" \
-H "Accept-Language: zh-CN,en;q=0.9" \
-H "Accept-Encoding: gzip, deflate" \
-H "Connection: keep-alive" \
-H "Content-Type: application/json"
{
"host": "example.com",
"user_agent": "MyApp/1.0",
"accept": "application/json",
"accept_language": "zh-CN,en;q=0.9",
"accept_encoding": "gzip, deflate",
"connection": "keep-alive",
"content_type": "application/json"
}
from fastapi import FastAPI, Header
from typing import Optional
app = FastAPI()
@app.get("/token-check/")
def check_token(x_token: Optional[str] = Header(None)):
if x_token:
return {"token": x_token, "valid": True}
return {"token": None, "valid": False}
curl -X GET "http://127.0.0.1:8000/token-check/" \
-H "X-Token: abc123xyz"

---

<!-- p.4 -->

必填 Header
设置 ... （Ellipsis）使 Header 必填：
代码解释：
Header(...) 中的 ... 表示该 Header 为必填项
缺失必填 Header 时，FastAPI 自动返回 422 Unprocessable Entity 错误（Validation Error），错
误信息明确指向缺失的 Header；
若需自定义缺失 Header 的错误码（如 401 Unauthorized），需手动捕获并抛出
HTTPException 。
请求示例（合法）：
响应示例：
请求示例（缺失 Header）：
响应示例（422）：
{
"token": "abc123xyz",
"valid": true
}
from fastapi import FastAPI, Header, HTTPException
app = FastAPI()
@app.get("/secure/")
def secure_endpoint(x_api_key: str = Header(..., description="API 密钥")):
if x_api_key != "secret-key-12345":
raise HTTPException(status_code=401, detail="无效的 API Key")
return {"message": "访问成功", "api_key": x_api_key}
curl -X GET "http://127.0.0.1:8000/secure/" \
-H "X-Api-Key: secret-key-12345"
{
"message": "访问成功",
"api_key": "secret-key-12345"
}
curl -X GET "http://127.0.0.1:8000/secure/"

---

<!-- p.5 -->

Header 验证规则
Header 支持与 Query 、 Path 相同的验证参数：
代码解释：
min_length 和 max_length 限制 Header 值的长度范围
pattern 使用正则表达式验证格式，如版本号必须为 x.x.x 格式
请求示例：
响应示例：
{
"detail": [
{
"loc": ["header", "x-api-key"],
"msg": "Field required",
"type": "value_error.missing"
}
]
}
from fastapi import FastAPI, Header
app = FastAPI()
@app.get("/validate-headers/")
def validate_headers(
x_request_id: str = Header(
...,
min_length=8,
max_length=36,
pattern=r"^[a-zA-Z0-9-]+$",
description="请求 ID（8-36 位字母数字）",
),
x_app_version: str = Header(
...,
pattern=r"^\d+\.\d+\.\d+$",
description="应用版本号（格式：x.x.x）",
),
):
return {
"request_id": x_request_id,
"app_version": x_app_version,
}
curl -X GET "http://127.0.0.1:8000/validate-headers/" \
-H "X-Request-Id: abc-12345-XYZ" \
-H "X-App-Version: 1.2.3"

---

<!-- p.6 -->

认证相关 Header
Authorization Bearer Token
最常用的 API 认证方式：
代码解释：
Authorization: Bearer <token> 是标准的 OAuth 2.0 认证格式
parts[0].lower() != "bearer" 检查认证类型是否正确
认证失败时返回 401 状态码
{
"request_id": "abc-12345-XYZ",
"app_version": "1.2.3"
}
from fastapi import FastAPI, Header, HTTPException
from typing import Optional
app = FastAPI()
USERS_DB = {
"user_token_001": {"id": 1, "username": "alice", "role": "admin"},
"user_token_002": {"id": 2, "username": "bob", "role": "user"},
}
def get_current_user(authorization: Optional[str] = Header(None)):
if not authorization:
raise HTTPException(status_code=401, detail="未提供认证信息")
parts = authorization.split()
if len(parts) != 2 or parts[0].lower() != "bearer":
raise HTTPException(status_code=401, detail="认证格式错误，请使用 Bearer
token")
token = parts[1]
user = USERS_DB.get(token)
if not user:
raise HTTPException(status_code=401, detail="无效的 Token")
return user
@app.get("/profile/")
def get_profile(authorization: Optional[str] = Header(None)):
user = get_current_user(authorization)
return {
"id": user["id"],
"username": user["username"],
"role": user["role"],
}

---

<!-- p.7 -->

请求示例（已认证）：
响应示例：
请求示例（未认证）：
响应示例（401）：
API Key 认证
部分接口使用 X-API-Key 或 X-API-Token 进行认证：
curl -X GET "http://127.0.0.1:8000/profile/" \
-H "Authorization: Bearer user_token_001"
{
"id": 1,
"username": "alice",
"role": "admin"
}
curl -X GET "http://127.0.0.1:8000/profile/"
{
"detail": "未提供认证信息"
}
from fastapi import FastAPI, Header, HTTPException
from typing import Optional
app = FastAPI()
API_KEYS = {
"key_dev_123": {"app": "dev-app", "tier": "free"},
"key_prod_456": {"app": "prod-app", "tier": "premium"},
}
@app.get("/api-data/")
def get_api_data(x_api_key: Optional[str] = Header(None)):
if not x_api_key:
raise HTTPException(status_code=401, detail="缺少 X-API-Key")
key_info = API_KEYS.get(x_api_key)
if not key_info:
raise HTTPException(status_code=403, detail="无效的 API Key")
return {
"data": {"items": ["item1", "item2"]},
"app": key_info["app"],
"tier": key_info["tier"],
}

---

<!-- p.8 -->

代码解释：
X-API-Key 是另一种常见的 API 认证方式
x_api_key 自动映射到 X-API-Key Header
不同的 API Key 可对应不同的权限等级
请求示例：
响应示例：
多值 Header
HTTP 多值 Header 有两种合法传递方式，FastAPI 均支持：
1. 多个同名 Header： -H "X-Token: token1" -H "X-Token: token2" ；
2. 单个 Header 逗号分隔： -H "X-Token: token1,token2" ；

FastAPI 会将两种方式均解析为列表 ["token1", "token2"] ，无需手动拆分。
代码解释：
List[str] 类型声明用于接收多个同名的 Header 值
多个 X-Token Header 会合并为一个字符串列表
请求示例：
curl -X GET "http://127.0.0.1:8000/api-data/" \
-H "X-API-Key: key_prod_456"
{
"data": {
"items": ["item1", "item2"]
},
"app": "prod-app",
"tier": "premium"
}
from fastapi import FastAPI, Header
from typing import List, Optional
app = FastAPI()
@app.get("/multi-values/")
def multi_value_headers(
x_token: Optional[List[str]] = Header(None, description="多个 Token"),
x_tag: Optional[List[str]] = Header(None, description="多个标签"),
):
return {
"tokens": x_token,
"tags": x_tag,
}

---

<!-- p.9 -->

响应示例：
响应 Header
除了读取请求 Header，还可以设置响应 Header。
使用 Response 参数设置
代码解释：
注入 Response 对象后，通过 response.headers["key"] = value 设置响应头
响应头会在 HTTP 响应中返回给客户端
请求示例：
响应头：
curl -X GET "http://127.0.0.1:8000/multi-values/" \
-H "X-Token: token1" \
-H "X-Token: token2" \
-H "X-Token: token3" \
-H "X-Tag: vip" \
-H "X-Tag: premium"
{
"tokens": ["token1", "token2", "token3"],
"tags": ["vip", "premium"]
}
from fastapi import FastAPI, Response
app = FastAPI()
@app.get("/set-headers/")
def set_custom_headers(response: Response):
response.headers["X-App-Name"] = "FastAPI Demo"
response.headers["X-Request-Id"] = "req-12345"
response.headers["Cache-Control"] = "no-cache"
return {"message": "响应头已设置"}
curl -X GET "http://127.0.0.1:8000/set-headers/" -i
HTTP/1.1 200 OK
content-type: application/json
x-app-name: FastAPI Demo
x-request-id: req-12345
cache-control: no-cache

---

<!-- p.10 -->

方式 代码示例 适用场景
直接使用
Response
def xxx(response:
Response)
仅需设置响应头，无需访问请求上下文
Request +
Response
async def
xxx(request,
response)
需要同时访问请求信息（如请求头、客户端 IP、
路径参数）和设置响应头
响应头设置方式对比
代码解释：
直接在路由函数中注入 Response 对象即可设置响应头
同步函数和异步函数都支持 Response 参数
可用于分页、统计等场景的自定义响应头
请求示例：
响应头：
自动类型转换
Header 值都是字符串，FastAPI 会根据声明的类型自动转换：
from fastapi import FastAPI, Request, Response
app = FastAPI()
@app.get("/items/")
async def read_items(request: Request, response: Response):
response.headers["X-Total-Count"] = "100"
response.headers["X-Page"] = "1"
return {"items": [{"id": 1}, {"id": 2}]}
curl -X GET "http://127.0.0.1:8000/items/" -i
HTTP/1.1 200 OK
content-type: application/json
x-total-count: 100
x-page: 1
from fastapi import FastAPI, Header
app = FastAPI()
@app.get("/typed-headers/")
def typed_headers(
x_page: int = Header(1, description="页码"),

---

<!-- p.11 -->

代码解释：
Header(1) 设置默认值，类型为 int ，自动将 "5" 转换为 5
bool 类型转换规则（大小写不敏感）：
转为 True ： "true" / "True" 、 "1" 、 "yes" / "Yes" 、 "on" / "On"
转为 False ：除上述值外的所有字符串（包括空字符串、 "false" 、 "0" 、 "no" 等）
请求示例：
响应示例：
禁用下划线转换
如果参数名本身就是 kebab-case 格式，可以禁用自动转换：
x_page_size: int = Header(10, description="每页数量"),
x_is_active: bool = Header(True, description="是否激活"),
x_timeout: float = Header(30.5, description="超时时间（秒）"),
):
return {
"page": x_page,
"page_size": x_page_size,
"is_active": x_is_active,
"timeout": x_timeout,
"type_check": {
"page_type": type(x_page).__name__,
"is_active_type": type(x_is_active).__name__,
},
}
curl -X GET "http://127.0.0.1:8000/typed-headers/" \
-H "X-Page: 5" \
-H "X-Page-Size: 20" \
-H "X-Is-Active: false" \
-H "X-Timeout: 60.5"
{
"page": 5,
"page_size": 20,
"is_active": false,
"timeout": 60.5,
"type_check": {
"page_type": "int",
"is_active_type": "bool"
}
}
from fastapi import FastAPI, Header
app = FastAPI()
@app.get("/no-convert/")

---

<!-- p.12 -->

请求头 说明 示例
Authorization 认证信息 Bearer <token>
User-Agent 客户端标识 Mozilla/5.0 ...
Content-Type 请求体类型 application/json
Accept 可接受的响应类型 application/json
X-API-Key API 密钥 key_abc123
X-Token 自定义 Token token_xyz
X-Request-ID 请求唯一 ID uuid-string
Accept-Language 可接受的语言 zh-CN,en;q=0.9
Accept-Encoding 可接受的编码 gzip, deflate
代码解释：
convert_underscores=False 禁用下划线自动转换
通常不需要禁用，保持默认配置即可
总结
常用 HTTP 请求头速查
def no_convert(
# 禁用转换后，参数名需与请求头完全一致（含连字符）
custom_header: str = Header(None, convert_underscores=False),
# 正确示例：匹配客户端传入的 "X-Custom-Header"（而非自动转 x_custom_header）
x_custom_header: str = Header(None, convert_underscores=False),
):
return {
"custom_header": custom_header, # 匹配请求头 "custom_header"（非标准）
"x_custom_header": x_custom_header # 匹配请求头 "x_custom_header"（非标
准），若要匹配 "X-Custom-Header" 需参数名写 "X-Custom-Header"（不推荐）
}

---

<!-- p.13 -->

场景 代码
可选 Header x_token: Optional[str] = Header(None)
必填 Header x_token: str = Header(...)
带验证 x_token: str = Header(..., min_length=8)
多值 Header x_token: List[str] = Header(None)
设置响应头 def handler(response: Response):
Header 用法速查
关键要点
1. 自动转换： Header 自动将 kebab-case（如 X-Token ）转为 snake_case（如 x_token ）
2. 类型转换：Header 值均为字符串，FastAPI 按声明类型自动转换
3. 必填/可选： Header(...) 必填， Header(None) 可选
4. 验证规则：支持 min_length 、 max_length 、 pattern 等验证
5. 多值 Header：使用 List[str] 接收多个同名 Header
6. 认证场景： Authorization: Bearer <token> 和 X-API-Key 是最常见的认证方式
