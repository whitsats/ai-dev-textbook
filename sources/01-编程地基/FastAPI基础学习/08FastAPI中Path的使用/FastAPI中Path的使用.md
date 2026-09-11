# FastAPI中Path的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\08FastAPI中Path的使用\FastAPI中Path的使用.pdf`
> **页数**：12（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 9,240 字符，其中汉字 1,418 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 中 Path 的使用
本文档介绍 FastAPI 中 Path 的用法，包括路径参数基础、数值约束、路由顺序、路径分组以及
类型自动转换等。
Path 是 FastAPI 中用于获取 URL 路径参数的工具，与 Query 、 Header 类似，支持类型验证、参数
约束、文档元数据等功能。
Path 参数基础
简单路径参数
使用 {param_name} 在路径中定义参数，配合类型注解获取：
代码解释：
Path(...) 中的 ... （Ellipsis）表示必填参数，与 Query(...) 含义相同
description 参数用于生成 API 文档中的参数说明
路径参数可与查询参数（ q ）同时使用，FastAPI 自动区分来源
请求示例：
响应示例：
from fastapi import FastAPI, Path
from typing import Optional
app = FastAPI()
@app.get("/items/{item_id}")
def read_item(
item_id: int = Path(..., description="项目 ID"),
q: Optional[str] = None,
):
return {"item_id": item_id, "q": q}
curl "http://127.0.0.1:8000/items/5?q=apple"
{
"item_id": 5,
"q": "apple"
}

---

<!-- p.2 -->

参数位置 示例 获取方式
/items/{item_id} /items/5 路径参数 item_id
/items?q=apple 查询字符串 查询参数 q
多个路径参数
URL 中可以包含多个路径参数：
代码解释：
路径参数按 URL 顺序依次绑定到函数参数
user_id 对应 URL 中的 {user_id} ， order_id 对应 {order_id}
请求示例：
响应示例：
路径参数与查询参数的区别
区分路径参数和查询参数的使用场景：
from fastapi import FastAPI, Path
from typing import Optional
app = FastAPI()
@app.get("/users/{user_id}/orders/{order_id}")
def get_order(
user_id: int = Path(..., description="用户 ID"),
order_id: int = Path(..., description="订单 ID"),
q: Optional[str] = None,
):
return {
"user_id": user_id,
"order_id": order_id,
"q": q,
}
curl "http://127.0.0.1:8000/users/42/orders/108?q=urgent"
{
"user_id": 42,
"order_id": 108,
"q": "urgent"
}
from fastapi import FastAPI, Path, Query
from typing import Optional
app = FastAPI()

---

<!-- p.3 -->

代码解释：
category 和 item_id 是路径参数，从 URL 路径中获取
page 、 page_size 、 keyword 是查询参数，从 ?key=value 中获取
两者可同时使用，FastAPI 自动区分来源
请求示例：
响应示例：
数值约束
对数值类型（ int 、 float ）的路径参数添加上下限约束：
@app.get("/items/{category}/{item_id}")
def read_item(
category: str = Path(..., description="商品分类"),
item_id: int = Path(..., description="商品 ID"),
page: int = Query(1, ge=1, description="页码"),
page_size: int = Query(10, ge=1, le=100, description="每页数量"),
keyword: Optional[str] = Query(None, description="搜索关键词"),
):
return {
"category": category,
"item_id": item_id,
"page": page,
"page_size": page_size,
"keyword": keyword,
}
curl "http://127.0.0.1:8000/items/electronics/123?
page=2&page_size=20&keyword=laptop"
{
"category": "electronics",
"item_id": 123,
"page": 2,
"page_size": 20,
"keyword": "laptop"
}
from fastapi import FastAPI, Path
app = FastAPI()
@app.get("/users/{user_id}")
def get_user(
user_id: int = Path(..., ge=1, le=10000, description="用户 ID（1-10000）"),
):
return {"user_id": user_id}

---

<!-- p.4 -->

参数 含义 英文全称
ge 大于等于 greater than or equal
gt 大于 greater than
le 小于等于 less than or equal
lt 小于 less than
代码解释：
ge=1, le=10000 限制用户 ID 范围在 1 到 10000 之间
ge=0.01 限制价格最小值为 0.01（避免 0 元商品）
ge=0 限制偏移量非负
gt=0 限制页码必须大于 0（ gt 不包含边界值）
请求示例（合法）：
响应示例：
请求示例（超出范围）：
@app.get("/products/{price}")
def get_by_price(
price: float = Path(..., ge=0.01, description="商品价格（最低 0.01）"),
):
return {"price": price}
@app.get("/files/{offset}")
def read_file(
offset: int = Path(..., ge=0, description="读取起始偏移量（非负整数）"),
):
return {"offset": offset}
@app.get("/articles/{page}")
def get_page(
page: int = Path(..., gt=0, description="页码（必须大于 0）"),
):
return {"page": page}
curl "http://127.0.0.1:8000/users/500"
{
"user_id": 500
}
curl "http://127.0.0.1:8000/users/99999"

---

<!-- p.5 -->

响应示例（422）：
正则表达式约束
说明： Path 的 regex 参数在 FastAPI 0.100.0+ 中已废弃，官方推荐两种验证方式：① 函数内部
手动添加正则验证逻辑；② 使用 Annotated 结合 Pydantic 验证器（更优雅）。
在 API 函数内部直接使用正则表达式验证，通过 HTTPException 返回 422 错误：
代码解释：
Path 只负责声明参数和生成文档，不再支持 regex 参数
{
"detail": [
{
"loc": ["path", "user_id"],
"msg": "ensure this value is less than or equal to 10000",
"type": "value_error"
}
]
}
from fastapi import FastAPI, Path, HTTPException
from pydantic import Annotated, field_validator
import re
app = FastAPI()
# 定义带正则验证的类型
ItemId = Annotated[str, Path(description="项目 ID（小写字母+数字）")]
@app.get("/items/{item_id}")
def read_item(item_id: ItemId):
if not re.match(r"^[a-z0-9]+$", item_id):
raise HTTPException(status_code=422, detail="只能包含小写字母和数字")
return {"item_id": item_id}
# 更优雅的 Pydantic 验证方式（推荐）
from pydantic import BaseModel, field_validator
class ItemParams(BaseModel):
item_id: str = Path(description="项目 ID（小写字母+数字）")
@field_validator("item_id")
def validate_item_id(cls, v):
if not re.match(r"^[a-z0-9]+$", v):
raise ValueError("只能包含小写字母和数字")
return v
@app.get("/items_v2/{item_id}")
def read_item_v2(params: ItemParams):
return {"item_id": params.item_id}

---

<!-- p.6 -->

在函数体内通过 re.match() 手动验证，不符合正则时抛出 HTTPException
FastAPI 自动将 HTTPException 转换为标准 422 响应
请求示例（合法）：
响应示例：
请求示例（包含大写字母）：
响应示例（422）：
路径参数顺序
FastAPI 按定义顺序匹配路由，静态路径必须写在动态路径前面，否则 /items/new 会被 {item_id}
匹配为 "new" ：
curl "http://127.0.0.1:8000/items/apple123"
{
"item_id": "apple123"
}
curl "http://127.0.0.1:8000/items/Apple123"
{
"detail": "只能包含小写字母和数字"
}
from fastapi import FastAPI, HTTPException
app = FastAPI()
ITEMS = {"1": "Item One", "2": "Item Two"}
PROMOTIONS = {"summer": "Summer Sale", "winter": "Winter Sale"}
@app.get("/items/new")
def get_new_items():
return {"items": ["Item New 1", "Item New 2"], "source": "static"}
@app.get("/items/promotions")
def get_promotions():
return {"promotions": ["summer", "winter"], "source": "static"}
@app.get("/items/{item_id}")
def get_item(item_id: str):
if item_id not in ITEMS:
raise HTTPException(status_code=404, detail="Item not found")
return {"item_id": item_id, "name": ITEMS[item_id], "source": "dynamic"}

---

<!-- p.7 -->

规则 示例
静态路径在前 /users/new 在 /users/{user_id} 前
详情子路径在后 /users/{user_id}/profile 在 /users/{user_id} 后
通用参数在后 /search?q=... 查询参数始终在最后
代码解释：
路由按定义顺序匹配， /items/new 在 /items/{item_id} 之前声明
如果顺序颠倒， /items/new 会被 {item_id} 捕获为 "new"
请求示例：
路径参数排序原则
预定义路径
将相同前缀的路径分组，便于管理：
@app.get("/promotions/{promo_key}")
def get_promotion(promo_key: str):
if promo_key not in PROMOTIONS:
raise HTTPException(status_code=404, detail="Promotion not found")
return {"key": promo_key, "name": PROMOTIONS[promo_key]}
curl "http://127.0.0.1:8000/items/new"
curl "http://127.0.0.1:8000/items/1"
# 推荐顺序
@app.get("/users/") # 用户列表
@app.get("/users/new") # 创建用户表单
@app.get("/users/{user_id}") # 用户详情
@app.get("/users/{user_id}/profile") # 用户资料
@app.get("/users/{user_id}/settings") # 用户设置
@app.get("/users/{user_id}/orders/{order_id}") # 用户的订单详情
# 错误顺序（会被 {user_id} 覆盖）
# @app.get("/users/{user_id}")
# @app.get("/users/new") # 永远匹配不到
from fastapi import FastAPI, Path
app = FastAPI()
@app.get("/users/", tags=["用户"])
def list_users():
return {"users": ["alice", "bob"]}

---

<!-- p.8 -->

代码解释：
tags=["用户"] 将路由分组到 Swagger 文档的"用户"分类下
同一资源的不同操作（GET/POST/PUT/DELETE）使用相同的路径前缀
实际项目中推荐使用 APIRouter 进行路由分组，见后续文档
路径参数中的斜杠
默认情况下，路径参数不包含 / 。如果希望参数中包含路径分隔符，使用 :path 类型声明：
@app.post("/users/", tags=["用户"])
def create_user(name: str):
return {"id": 1, "name": name}
@app.get("/users/{user_id}", tags=["用户"])
def get_user(user_id: int = Path(..., ge=1)):
return {"id": user_id}
@app.put("/users/{user_id}", tags=["用户"])
def update_user(user_id: int = Path(..., ge=1)):
return {"id": user_id, "updated": True}
@app.delete("/users/{user_id}", tags=["用户"])
def delete_user(user_id: int = Path(..., ge=1)):
return {"id": user_id, "deleted": True}
@app.get("/products/", tags=["商品"])
def list_products():
return {"products": ["p1", "p2"]}
@app.get("/products/{product_id}", tags=["商品"])
def get_product(product_id: int = Path(..., ge=1)):
return {"id": product_id}
from fastapi import FastAPI, Path
app = FastAPI()
@app.get("/files/{file_path:path}")
def read_file(file_path: str = Path(..., description="文件路径（可包含斜杠）")):
return {
"file_path": file_path,
"parts": file_path.split("/"),
}

---

<!-- p.9 -->

代码解释：
{file_path:path} 中的 :path 声明参数类型，允许包含 /
正常情况下 {file_path} 会在第一个 / 处截断
使用 :path 后，整个 docs/api/guide.md 都会被捕获
请求示例：
响应示例：
注意：使用 path 类型时，参数末尾不要加 / ，否则可能匹配不到。
类型转换
路径参数值均为字符串，FastAPI 按声明的类型自动转换：
curl "http://127.0.0.1:8000/files/docs/api/guide.md"
{
"file_path": "docs/api/guide.md",
"parts": ["docs", "api", "guide.md"]
}
from fastapi import FastAPI, Path
app = FastAPI()
@app.get("/typed/{item_id}")
def typed_param(item_id: int = Path(...)):
return {
"item_id": item_id,
"type": type(item_id).__name__,
}
@app.get("/float/{price}")
def float_param(price: float = Path(..., ge=0)):
return {
"price": price,
"type": type(price).__name__,
}
@app.get("/str/{name}")
def str_param(name: str = Path(...)):
return {
"name": name,
"type": type(name).__name__,
}
@app.get("/bool/{flag}")

---

<!-- p.10 -->

场景 代码
整型必填参数 item_id: int = Path(...)
带数值约束 item_id: int = Path(..., ge=1, le=1000)
可选参数（不推
荐）
item_id: Optional[int] = Path(None)
路径参数含斜杠
file_path: str = Path(...) # 路由声明为
/files/{file_path:path}
带正则验证 函数内使用 re.match() 手动验证
代码解释：
int 类型：URL 中的 "42" 自动转换为整数 42
float 类型：URL 中的 "99.99" 自动转换为浮点数 99.99
str 类型：保持原字符串
bool 类型：大小写不敏感的 "true" / "1" / "yes" 转换为 True ； "false" / "0" / "no" 转换为
False ，其他非空字符串转换为 True （空字符串转 False ）。
请求示例：
响应示例：
总结
Path 参数速查
路径参数 vs 查询参数
def bool_param(flag: bool = Path(...)):
return {
"flag": flag,
"type": type(flag).__name__,
}
curl "http://127.0.0.1:8000/bool/yes"
curl "http://127.0.0.1:8000/bool/1"
curl "http://127.0.0.1:8000/bool/true"
{
"flag": true,
"type": "bool"
}

---

<!-- p.11 -->

特点 路径参数 查询参数
必填/可选 默认必填（可声明可选，但不推荐） 可选（可省略）
SEO 友好 是（语义清晰） 否
适合标识符 是（如 /users/1 ） 否
适合过滤/分页 否 是（ ?page=1&size=10 ）
多值 否 是（重复参数）
关键要点
1. 路径参数必填： Path(...) 中的 ... 表示必填，路径参数通常设计为必填（URL 必须提供），
虽可通过 Path(None) 声明可选，但不推荐（违背 RESTful 设计）。
2. 数值约束： ge / gt / le / lt 控制数值范围，防止越界数据
3. 静态优先：静态路径（ /items/new ）必须写在动态路径（ /items/{item_id} ）前面
4. 类型自动转换：路径参数按声明类型自动转换，无需手动处理
5. 路径含斜杠：使用 {param:path} 允许参数中包含 /
6. 正则已废弃： regex 参数在 FastAPI 0.115+ 废弃，需在函数内手动验证
