# FastAPI处理表单

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\11FastAPI处理表单\FastAPI处理表单.pdf`
> **页数**：11（其中无文本页 2 页，多为截图/图示）
> **正文规模**：约 7,826 字符，其中汉字 879 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

语法 含义
Form(...) 必填字段，等同于 Query(...) / Path(...)
Form(None) 可选字段，未提供时为 None
FastAPI 处理表单
FastAPI 通过 Form 类和 UploadFile 提供简洁强大的表单处理能力：
普通表单（无文件）：使用 application/x-www-form-urlencoded 编码
含文件的表单：使用 multipart/form-data 编码（必选）
前置条件
使用表单功能前需安装依赖：
Form 类基本用法
登录表单
使用 Form 类接收表单字段，与 Query 、 Path 用法一致：
请求示例
响应示例
核心说明
pip install python-multipart
from fastapi import FastAPI, Form
app = FastAPI()
@app.post("/login/")
def login(username: str = Form(...), password: str = Form(...)):
return {"username": username, "password": password}
curl -X POST "http://127.0.0.1:8000/login/" \
-d "username=zhangsan&password=123456"
{
"username": "zhangsan",
"password": "123456"
}

---

<!-- p.2 -->

语法 含义
Form(default=...) 设置默认值
Form 与默认的 JSON 类型 Body 互斥，一个请求体只能使用 application/json （JSON Body）
或 multipart/form-data （Form/File）编码格式，不能混合使用。
可选字段与默认值
请求示例
响应示例
类型自动转换：表单数据原始均为字符串，FastAPI 会自动转换为声明的类型 —— bool 类型会将
"true"/"false" （大小写不敏感）转换为布尔值， int/float 会将数字字符串转换为对应数
值；若转换失败（如 "abc" 转 int），会返回 422 验证错误。
from fastapi import FastAPI, Form
from typing import Optional
app = FastAPI()
@app.post("/profile/")
def update_profile(
username: str = Form(...),
email: str = Form(...),
bio: Optional[str] = Form(None),
subscribe: bool = Form(False)
):
return {
"username": username,
"email": email,
"bio": bio,
"subscribe": subscribe
}
curl -X POST "http://127.0.0.1:8000/profile/" \
-d "username=alice&email=alice@example.com"
{
"username": "alice",
"email": "alice@example.com",
"bio": null,
"subscribe": false
}

---

<!-- p.3 -->

表单字段验证
结合 Field 为表单字段添加验证规则：
验证通过请求示例
响应示例（200）
验证失败请求示例
响应示例（422）
from fastapi import FastAPI, Form
app = FastAPI()
@app.post("/register/")
def register(
username: str = Form(
...,
min_length=3,
max_length=20,
pattern=r"^[a-zA-Z0-9_]+$",
description="用户名（3-20位字母、数字、下划线）"
),
email: str = Form(..., description="邮箱地址"),
password: str = Form(
...,
min_length=8,
description="密码（至少8位）"
)
):
return {
"username": username,
"email": email,
"password": "******"
}
curl -X POST "http://127.0.0.1:8000/register/" \
-d "username=alice&email=alice@example.com&password=secret123"
{
"username": "alice",
"email": "alice@example.com",
"password": "******"
}
curl -X POST "http://127.0.0.1:8000/register/" \
-d "username=al&email=alice@example.com&password=123"
{
"detail": [

---

<!-- p.4 -->

参数 说明
min_length / max_length 字符串最小/最大长度
pattern 正则表达式验证
description API 文档参数说明
支持的验证参数
Request.form() 原始方式
获取所有表单数据
当字段名未知或数量不固定时，通过 request.form() 直接获取原始字典：
请求示例
响应示例
{
"loc": ["body", "username"],
"msg": "String should have at least 3 characters",
"type": "string_too_short"
},
{
"loc": ["body", "password"],
"msg": "String should have at least 8 characters",
"type": "string_too_short"
}
]
}
from fastapi import FastAPI, Request
app = FastAPI()
@app.post("/submit/")
async def submit_form(request: Request):
form_data = await request.form()
return dict(form_data)
curl -X POST "http://127.0.0.1:8000/submit/" \
-d "name=张三&age=25&city=北京"
{
"name": "张三",
"age": "25",
"city": "北京"
}

---

<!-- p.5 -->

遍历所有字段
请求示例
响应示例
request.form() 返回的是 Starlette 提供的 FormData 对象（类字典结构），可通过
dict(form_data) 转换为标准 Python 字典，其值可能是 str （表单字段）或 UploadFile
（文件）。
多选字段（同名表单字段）
HTML <select multiple> 或多个同名的 <input> 会发送多个同名字段，使用 getlist() 方法接
收：
from fastapi import FastAPI, Request, File, UploadFile
app = FastAPI()
@app.post("/debug-form/")
async def debug_form(request: Request):
form_data = await request.form()
results = {}
for field_name, field_value in form_data.items():
# 区分普通字段和文件字段
if isinstance(field_value, UploadFile):
value_str = f"File: {field_value.filename}"
field_type = "UploadFile"
else:
value_str = str(field_value)
field_type = type(field_value).__name__
results[field_name] = {
"value": value_str,
"type": field_type
}
return {"fields": results, "total": len(form_data)}
curl -X POST "http://127.0.0.1:8000/debug-form/" \
-F "name=alice" -F "role=admin" -F "active=true" -F "avatar=@avatar.png"
{
"fields": {
"name": {"value": "alice", "type": "str"},
"role": {"value": "admin", "type": "str"},
"active": {"value": "true", "type": "str"},
"avatar": {"value": "File: avatar.png", "type": "UploadFile"}
},
"total": 4
}

---

<!-- p.6 -->

请求示例
响应示例
表单 + 文件混合上传
一个请求中同时包含表单字段和文件上传：
from fastapi import FastAPI, Request
app = FastAPI()
@app.post("/filter/")
async def filter_items(request: Request):
form_data = await request.form()
categories = form_data.getlist("category")
return {"categories": categories}
curl -X POST "http://127.0.0.1:8000/filter/" \
-d "category=tech&category=news&category=sports"
{
"categories": ["tech", "news", "sports"]
}
from fastapi import FastAPI, Form, File, UploadFile
from typing import List
app = FastAPI()
@app.post("/article/publish/")
async def publish_article(
title: str = Form(...),
content: str = Form(...),
tags: str = Form(""),
cover: UploadFile = File(...),
attachments: List[UploadFile] = File(default=[])
):
return {
"title": title,
"content": content,
"tags": tags.split(",") if tags else [],
"cover": {
"filename": cover.filename,
"content_type": cover.content_type,
"size": len(await cover.read())
},
"attachments": [
{"filename": f.filename, "content_type": f.content_type}
for f in attachments

---

<!-- p.7 -->

请求示例
响应示例
对应 HTML 表单示例
JSON + 表单混合
如果请求体中包含 JSON 字符串和文件，需分步处理：
]
}
curl -X POST "http://127.0.0.1:8000/article/publish/" \
-F "title=FastAPI 教程" \
-F "content=这是一篇关于 FastAPI 的教程文章" \
-F "tags=python,fastapi,web" \
-F "cover=@logo.png" \
-F "attachments=@readme.txt" \
-F "attachments=@diagram.svg"
{
"title": "FastAPI 教程",
"content": "这是一篇关于 FastAPI 的教程文章",
"tags": ["python", "fastapi", "web"],
"cover": {
"filename": "logo.png",
"content_type": "image/png",
"size": 12345
},
"attachments": [
{"filename": "readme.txt", "content_type": "text/plain"},
{"filename": "diagram.svg", "content_type": "image/svg+xml"}
]
}
<form action="/article/publish/" method="post" enctype="multipart/form-data">
<input name="title" type="text" />
<textarea name="content"></textarea>
<input name="tags" type="text" placeholder="逗号分隔" />
<input name="cover" type="file" />
<input name="attachments" type="file" multiple />
<button type="submit">发布</button>
</form>
from fastapi import FastAPI, Request
import json
app = FastAPI()
@app.post("/data-upload/")

---

<!-- p.8 -->

请求示例
响应示例
常见陷阱
1. Form 与 Body 混用
FastAPI 不支持在同一个请求中同时使用 JSON body 和 Form 字段。
2. 文件上传漏写 async
3. 文件未关闭
async def data_upload(request: Request):
form_data = await request.form()
metadata_str = form_data.get("metadata", "{}")
metadata = json.loads(metadata_str)
file = form_data.get("file")
if file:
content = await file.read()
return {"metadata": metadata, "file_size": len(content)}
return {"metadata": metadata}
curl -X POST "http://127.0.0.1:8000/data-upload/" \
-F "metadata={\"user\":\"alice\",\"version\":1}" \
-F "file=@data.json"
{
"metadata": {"user": "alice", "version": 1},
"file_size": 256
}
# 错误：Form 和 Body 不能混用
@app.post("/wrong/")
async def wrong(body: str = Body(...), name: str = Form(...)):
pass
# 正确：文件操作必须用 async
@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
content = await file.read() # 需要 await

---

<!-- p.9 -->

场景 推荐方式 说明
明确知道字段名，需要类型验证 str = Form(...) 声明式，推荐优先使用
可选字段 Optional[str] = Form(None) 未提供时为 None
带默认值的字段 bool = Form(False) 未提供时使用默认值
字段数量不确定，需遍历处理 await request.form() 返回字典，可遍历
同名字段（多选框） form_data.getlist("name") 返回列表
表单字段 + 文件同时上传 Form + File 混合 UploadFile 处理文件
4. File(...) 与 Form(...) 的默认值
用法对比速查表
总结
1. 安装依赖： pip install python-multipart
2. 声明式优先：明确字段名时使用 Form(...) 声明式参数，自动完成验证和类型转换
3. 原始方式兜底：字段名未知或数量不固定时，使用 await request.form() 获取原始数据
4. Form 与 JSON 互斥：请求体编码格式二选一
5. 文件上传： UploadFile = File(...) 声明，异步读写
6. 多选字段： form_data.getlist("name") 获取同名多个值
# 推荐：使用上下文管理器自动关闭
@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
contents = await file.read()
# 或手动关闭
async def upload(file: UploadFile = File(...)):
try:
contents = await file.read()
finally:
await file.close()
# 必填文件：File(...)
cover: UploadFile = File(...)
# 可选文件：File(default=None) 或 File(None)
thumbnail: UploadFile = File(default=None)
