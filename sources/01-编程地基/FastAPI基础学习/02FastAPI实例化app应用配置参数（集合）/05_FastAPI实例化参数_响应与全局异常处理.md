# 05_FastAPI实例化参数_响应与全局异常处理

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\02FastAPI实例化app应用配置参数（集合）\05_FastAPI实例化参数_响应与全局异常处理.pdf`
> **页数**：7（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 5,779 字符，其中汉字 1,436 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 实例化参数：响应与全局异常处理
本文档介绍 FastAPI 实例化时配置全局响应模型和异常处理的参数。通过这些参数，可以自定义 API 的
响应格式和处理各类异常时的行为。
default_response_class 参数
default_response_class 参数设置全局默认的响应类型。FastAPI 会根据路由函数的返回值自动选择
合适的响应类，这个参数指定了默认使用的响应类。
代码解释：
default_response_class 设置全局默认的响应类
默认为 JSONResponse ，会自动将返回值序列化为 JSON
可以设置为其他响应类，如 ORJSONResponse （性能更高）
或 HTMLResponse 、 PlainTextResponse 等
该参数影响所有未明确指定响应类的路由
responses 参数
responses 参数用于声明全局默认的响应文档（OpenAPI 规范），可以为每个路由声明可能返回的多
种 HTTP 状态码及其响应格式，仅作用于接口文档展示，不影响实际响应逻辑。
代码解释：
from fastapi import FastAPI
from fastapi.responses import JSONResponse
app = FastAPI(default_response_class=JSONResponse)
from fastapi import FastAPI
from pydantic import BaseModel
class ErrorResponse(BaseModel):
code: int
message: str
app = FastAPI(
responses={
404: {"model": ErrorResponse, "description": "资源不存在"},
500: {"model": ErrorResponse, "description": "服务器内部错误"}
}
)

---

<!-- p.2 -->

responses 字典定义全局默认的响应模型
键是 HTTP 状态码（如 404、500）
值是响应配置，包含 model 和 description
model 指定响应体的 Pydantic 模型
description 是对该响应的描述
这些响应会在 OpenAPI 文档中显示
帮助前端开发者了解可能的各种响应情况
exception_handlers 参数
exception_handlers 参数用于注册全局异常处理器。当应用中抛出相应类型的异常时，FastAPI 会自
动调用对应的处理函数返回统一格式的响应。
处理 HTTPException
当应用中出现 HTTP 异常时，可以通过自定义处理器返回统一格式的错误信息：
代码解释：
exception_handlers 是一个字典，将异常类型作为键，对应的处理函数作为值
http_exception_handler 函数接收两个参数： request 和 exc
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
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
# 在实例化时注册异常处理器
app = FastAPI(
exception_handlers={
HTTPException: http_exception_handler # 映射 HTTPException 到自定义处理器
}
)
@app.get("/items/{item_id}")
def get_item(item_id: int):
if item_id == 0:
raise HTTPException(status_code=404, detail="商品不存在")
return {"item_id": item_id}

---

<!-- p.3 -->

request 提供了请求的上下文信息（如路径、查询参数等）
exc 是 HTTPException 实例，包含状态码和详细信息
exc.status_code 获取 HTTP 状态码
exc.detail 获取异常的详细信息
str(request.url) 获取请求的完整 URL 路径
status_code 指定返回响应的 HTTP 状态码
在实例化时通过 exception_handlers 参数注册处理器
当路由中 raise HTTPException 时，会自动调用自定义处理器
处理通用异常
对于非 HTTP 异常（如 ValueError 、 KeyError 等），可以注册一个捕获所有异常的处理器：
代码解释：
Exception 是 Python 的通用异常基类
注册 Exception 处理器可以捕获所有未被其他处理器捕获的异常
统一返回 500 状态码表示服务器内部错误
str(exc) 将异常对象转换为字符串描述
trigger_error 路由中故意抛出 ValueError 用于测试
所有未捕获的异常都会被 general_exception_handler 处理
确保客户端不会看到原始的异常堆栈信息
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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
app = FastAPI(
exception_handlers={
Exception: general_exception_handler # 映射通用 Exception 到自定义处理
器
}
)
@app.get("/error")
def trigger_error():
raise ValueError("这是一个测试错误")

---

<!-- p.4 -->

统一异常响应格式
为了保持 API 响应的一致性，可以创建一个统一的响应格式。使用 StarletteHTTPException 可以捕
获更多类型的 HTTP 异常：
代码解释：
StarletteHTTPException 是 Starlette 框架的 HTTP 异常类
使用 StarletteHTTPException 可以捕获更多类型的 HTTP 异常
isinstance(exc, HTTPException) 用于判断异常的具体类型
如果是 HTTP 异常，返回包含 success: False 和 error 对象的统一格式
success 字段统一标识请求是否成功
error 字段统一包含 code 和 message 信息
非 HTTP 异常（如 ValueError 、 KeyError 等）统一返回 500 状态码
前端只需要按照统一的格式处理响应即可
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
# 通用的异常处理函数，根据异常类型返回统一格式的响应
async def custom_exception_handler(request: Request, exc:
StarletteHTTPException):
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
)

---

<!-- p.5 -->

不需要针对每种错误类型做特殊处理
完整异常处理配置
以下是一个同时处理 HTTP 异常和通用异常的完整配置示例：
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
# 定义处理 HTTPException 的异步函数
async def http_exception_handler(request: Request, exc: HTTPException):
return JSONResponse(
status_code=exc.status_code,
content={
"code": exc.status_code,
"message": exc.detail,
"path": str(request.url)
}
)
# 定义处理通用异常的异步函数
async def general_exception_handler(request: Request, exc: Exception):
return JSONResponse(
status_code=500,
content={
"code": 500,
"message": "服务器内部错误",
"detail": str(exc)
}
)
# 在实例化时同时注册两种异常处理器
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

<!-- p.6 -->

代码解释：
http_exception_handler 处理所有 HTTPException 类型的异常
general_exception_handler 处理所有其他未被捕获的异常
在实例化时通过 exception_handlers 字典同时注册两种处理器
HTTPException: http_exception_handler 映射 HTTP 异常到自定义处理器
Exception: general_exception_handler 映射通用异常到自定义处理器
exception_handlers 会优先匹配最具体的异常类型（子类异常优先于父类），例如
HTTPException 会优先匹配自身处理器，而非通用 Exception 处理器
get_item 路由中 raise HTTPException 会触发第一个处理器
trigger_error 路由中的 ValueError 会被第二个处理器捕获
FastAPI 会根据异常类型自动选择对应的处理器
注意：当 FastAPI 实例化时设置 debug=True （仅建议开发环境使用），未被自定义处理器捕获
的异常会触发内置的调试错误页面，覆盖全局异常处理器的响应；生产环境务必设置
debug=False ，确保自定义异常处理器生效。
