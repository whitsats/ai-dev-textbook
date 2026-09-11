# FastAPI中Query的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\07FastAPI中Query的使用\FastAPI中Query的使用.pdf`
> **页数**：13（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 9,922 字符，其中汉字 1,418 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 中 Query 的使用
本文档介绍 FastAPI 中 Query 的用法，包括可选与必填参数、多种约束条件、列表参数、别名、
废弃标记等。
Query 是 FastAPI 中用于获取 URL 查询字符串参数的工具，支持类型验证、默认值、参数约束、别
名、文档元数据等功能。
Query 参数基础
可选查询参数
未使用 Query 时，默认即为可选查询参数。可以显式使用 Query(None) 表明可选：
代码解释：
Query(None) 声明参数为可选，不传时为 None
description 参数为参数添加说明，会显示在 OpenAPI 文档中
请求示例（带参数）：
响应示例：
请求示例（不带参数）：
from fastapi import FastAPI, Query
from typing import Optional
app = FastAPI()
@app.get("/items/")
def read_items(q: Optional[str] = Query(None, description="搜索关键词")):
results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
if q:
results["q"] = q
return results
curl "http://127.0.0.1:8000/items/?q=apple"
{
"items": [
{"item_id": "Foo"},
{"item_id": "Bar"}
],
"q": "apple"
}

---

<!-- p.2 -->

响应示例：
必填查询参数
设置 ... （Ellipsis）使查询参数必填：
代码解释：
Query(...) 中的 ... 表示必填参数，缺失时返回 422 验证错误
请求示例（合法）：
响应示例：
请求示例（缺失必填参数）：
响应示例（422）：
curl "http://127.0.0.1:8000/items/"
{
"items": [
{"item_id": "Foo"},
{"item_id": "Bar"}
]
}
from fastapi import FastAPI, Query
app = FastAPI()
@app.get("/items/")
def read_items(category: str = Query(..., description="商品分类（必填）")):
return {"category": category, "items": ["item1", "item2"]}
curl "http://127.0.0.1:8000/items/?category=electronics"
{
"category": "electronics",
"items": ["item1", "item2"]
}
curl "http://127.0.0.1:8000/items/"

---

<!-- p.3 -->

多个查询参数
支持多个查询参数并存：
代码解释：
函数参数定义顺序不影响 URL 中查询参数的传递顺序，FastAPI 仅根据参数名匹配查询参数值
（HTTP 规范中查询参数的顺序不影响语义）
多个查询参数可以混合使用不同类型（ str 、 int 等）
请求示例：
响应示例：
{
"detail": [
{
"loc": ["query", "category"],
"msg": "Field required",
"type": "value_error.missing"
}
]
}
from fastapi import FastAPI, Query
from typing import Optional
app = FastAPI()
@app.get("/items/")
def read_items(
q: Optional[str] = Query(None, description="搜索关键词"),
skip: int = Query(0, description="跳过的数量"),
limit: int = Query(10, description="返回的数量"),
):
items = ["Foo", "Bar", "Baz", "Qux"]
if q:
items = [i for i in items if q.lower() in i.lower()]
return {
"items": items[skip:skip + limit],
"total": len(items),
"skip": skip,
"limit": limit,
"q": q,
}
curl "http://127.0.0.1:8000/items/?q=b&skip=0&limit=2"

---

<!-- p.4 -->

参数 含义 英文全称
ge 大于等于 greater than or equal
gt 大于 greater than
le 小于等于 less than or equal
lt 小于 less than
参数约束
数值约束（ge / gt / le / lt）
对 int 、 float 类型添加上下限约束：
代码解释：
ge （greater than or equal）表示大于等于， gt （greater than）表示大于
le （less than or equal）表示小于等于， lt （less than）表示小于
约束参数可以组合使用，如 ge=1, le=100 表示范围在 1-100 之间
{
"items": ["Bar", "Baz"],
"total": 4,
"skip": 0,
"limit": 2,
"q": "b"
}
from fastapi import FastAPI, Query
from typing import Optional
app = FastAPI()
@app.get("/items/")
def read_items(
page: int = Query(1, ge=1, description="页码（从 1 开始）"),
page_size: int = Query(10, ge=1, le=100, description="每页数量（1-100）"),
min_price: float = Query(0, ge=0, description="最低价格"),
max_price: Optional[float] = Query(None, ge=0, description="最高价格"),
offset: int = Query(0, ge=0, description="偏移量（非负）"),
):
return {
"page": page,
"page_size": page_size,
"min_price": min_price,
"max_price": max_price,
"offset": offset,
}

---

<!-- p.5 -->

请求示例：
响应示例：
字符串约束（min_length / max_length / pattern）
对字符串类型添加长度和正则约束：
代码解释：
min_length 和 max_length 限制字符串的最小和最大长度
curl "http://127.0.0.1:8000/items/?
page=3&page_size=50&min_price=10.5&max_price=100&offset=5"
{
"page": 3,
"page_size": 50,
"min_price": 10.5,
"max_price": 100,
"offset": 5
}
from fastapi import FastAPI, Query
from typing import Optional
app = FastAPI()
@app.get("/search/")
def search(
keyword: str = Query(
...,
min_length=2,
max_length=50,
description="搜索关键词（2-50 个字符）",
),
tag: Optional[str] = Query(
None,
min_length=1,
max_length=20,
description="标签过滤（1-20 个字符）",
),
phone: Optional[str] = Query(
None,
pattern=r"^1[3-9]\d{9}$",
description="手机号（11 位数字，以 1 开头）",
),
):
return {
"keyword": keyword,
"tag": tag,
"phone": phone,
}

---

<!-- p.6 -->

pattern 使用正则表达式约束字符串格式，此处匹配中国手机号格式
请求示例：
响应示例：
请求示例（验证失败）：
响应示例（422）：
列表参数（多值查询）
多个同名参数
同一个查询参数可以出现多次，自动收集为列表：
curl "http://127.0.0.1:8000/search/?keyword=fastapi&tag=web&phone=13812345678"
{
"keyword": "fastapi",
"tag": "web",
"phone": "13812345678"
}
curl "http://127.0.0.1:8000/search/?keyword=a&phone=12345"
{
"detail": [
{
"loc": ["query", "keyword"],
"msg": "String should have at least 2 characters",
"type": "string_too_short"
},
{
"loc": ["query", "phone"],
"msg": "String should match pattern ^1[3-9]\\d{9}$",
"type": "string_pattern_mismatch"
}
]
}
from fastapi import FastAPI, Query
from typing import Optional, List
app = FastAPI()
@app.get("/items/")
def read_items(
q: Optional[List[str]] = Query(None, description="搜索关键词（可多个）"),
tags: Optional[List[str]] = Query(None, description="标签过滤（可多个）"),
status: Optional[List[str]] = Query(None, description="状态过滤（可多个）"),

---

<!-- p.7 -->

代码解释：
List[str] 声明参数可以接收多个同名的值
URL 中多次出现同一参数时，FastAPI 自动收集为列表
如 ?q=fastapi&q=python 对应 ["fastapi", "python"]
请求示例：
响应示例：
逗号分隔列表
手动解析逗号分隔的字符串：
代码解释：
):
return {
"q": q or [],
"tags": tags or [],
"status": status or [],
}
curl "http://127.0.0.1:8000/items/?
q=fastapi&q=python&tags=web&tags=api&status=active&status=pending"
{
"q": ["fastapi", "python"],
"tags": ["web", "api"],
"status": ["active", "pending"]
}
from fastapi import FastAPI, Query
from typing import Optional
app = FastAPI()
@app.get("/filter/")
def filter_items(
categories: Optional[str] = Query(
None,
description="商品分类（逗号分隔，如 electronics,books）",
),
):
if categories:
category_list = [c.strip() for c in categories.split(",")]
else:
category_list = []
return {
"categories_input": categories,
"categories_list": category_list,
}

---

<!-- p.8 -->

使用单个 str 类型接收逗号分隔的字符串
在函数内部通过 split(",") 手动解析为列表
适用于前端不便于发送重复参数的场景
请求示例：
响应示例：
别名参数
使用 alias 将 URL 参数名映射为不同的 Python 变量名：
代码解释：
alias 解决前端参数命名风格（kebab-case）与后端（snake_case）不一致的问题
URL 使用 ?item-type=electronics ，Python 参数名为 item_type
请求示例：
响应示例：
curl "http://127.0.0.1:8000/filter/?categories=electronics,books,clothing"
{
"categories_input": "electronics,books,clothing",
"categories_list": ["electronics", "books", "clothing"]
}
from fastapi import FastAPI, Query
from typing import Optional
app = FastAPI()
@app.get("/items/")
def read_items(
item_type: Optional[str] = Query(None, alias="item-type", description="商品类
型"),
page_size: Optional[int] = Query(10, alias="page-size", description="每页数
量"),
):
return {
"item_type": item_type,
"page_size": page_size,
}
curl "http://127.0.0.1:8000/items/?item-type=electronics&page-size=20"
{
"item_type": "electronics",
"page_size": 20
}

---

<!-- p.9 -->

废弃参数（deprecated）
将查询参数标记为废弃，FastAPI 自动在文档中提示：
代码解释：
deprecated=True 在 /docs 中会显示删除线样式，提示调用者该参数即将移除
废弃参数仍然可用，便于平滑迁移
访问 /docs 查看文档，废弃参数会显示删除线样式。
类型自动转换
查询参数值均为字符串，FastAPI 按声明的类型自动转换：
from fastapi import FastAPI, Query
from typing import Optional
app = FastAPI()
@app.get("/items/")
def read_items(
page: int = Query(1, ge=1, description="页码"),
page_size: int = Query(10, ge=1, le=100, description="每页数量"),
limit: Optional[int] = Query(
None,
deprecated=True,
description="已废弃，请使用 page_size 替代",
),
):
effective_limit = page_size if limit is None else limit
return {
"page": page,
"page_size": page_size,
"limit": effective_limit,
}
from fastapi import FastAPI, Query
app = FastAPI()
@app.get("/typed/")
def typed_params(
page: int = Query(1, description="页码（自动转为 int）"),
price: float = Query(0.0, description="价格（自动转为 float）"),
is_active: bool = Query(True, description="是否激活（自动转为 bool）"),
timeout: float = Query(30.5, description="超时（自动转为 float）"),
):
return {
"page": page,
"page_type": type(page).__name__,

---

<!-- p.10 -->

代码解释：
FastAPI 根据函数参数的类型注解自动将字符串转换为对应类型
响应中返回 page_type 、 price_type 等字段，便于观察实际转换结果
请求示例：
响应示例：
注意： bool 类型转换遵循 Pydantic 规则： "true"/"1"/"on"/"yes" （大小写不敏感）转为
True ， "false"/"0"/"off"/"no" （大小写不敏感）转为 False ；空字符串或其他值会触发类
型验证错误。
参数验证失败处理
展示完整的验证失败响应：
"price": price,
"price_type": type(price).__name__,
"is_active": is_active,
"is_active_type": type(is_active).__name__,
"timeout": timeout,
"timeout_type": type(timeout).__name__,
}
curl "http://127.0.0.1:8000/typed/?
page=5&price=99.9&is_active=false&timeout=120.5"
{
"page": 5,
"page_type": "int",
"price": 99.9,
"price_type": "float",
"is_active": false,
"is_active_type": "bool",
"timeout": 120.5,
"timeout_type": "float"
}
from fastapi import FastAPI, Query
app = FastAPI()
@app.get("/validate/")
def validate_params(
page: int = Query(1, ge=1, description="页码（>=1）"),
page_size: int = Query(10, ge=1, le=50, description="每页数量（1-50）"),
keyword: str = Query(..., min_length=3, max_length=20, description="关键词（3-
20 字符）"),
):
return {"page": page, "page_size": page_size, "keyword": keyword}

---

<!-- p.11 -->

场景 代码
可选参数 q: Optional[str] = Query(None)
必填参数 q: str = Query(...)
带默认值 page: int = Query(1)
数值范围 page: int = Query(1, ge=1, le=100)
字符串长度 keyword: str = Query(..., min_length=2, max_length=50)
正则匹配 phone: str = Query(..., pattern=r"^1[3-9]\d{9}$")
多值列表 tags: List[str] = Query(None)
参数别名 item_type: str = Query(None, alias="item-type")
废弃参数 ld O ti l[ t ] Q (N d t d T )
代码解释：
多个参数同时验证失败时，FastAPI 返回包含所有错误的完整列表
错误响应中的 loc 字段指明错误位置（如 ["query", "page"] ）
type 字段表示错误类型（如 string_too_short 、 value_error ）
请求示例（全部违规）：
响应示例（422）：
总结
Query 参数速查
curl "http://127.0.0.1:8000/validate/?page=-1&page_size=999&keyword=a"
{
"detail": [
{
"loc": ["query", "page"],
"msg": "ensure this value is greater than or equal to 1",
"type": "value_error"
},
{
"loc": ["query", "page_size"],
"msg": "ensure this value is less than or equal to 50",
"type": "value_error"
},
{
"loc": ["query", "keyword"],
"msg": "String should have at least 3 characters",
"type": "string_too_short"
}
]
}

---

<!-- p.12 -->

场景 代码
废弃参数 old_param: Optional[str] = Query(None, deprecated=True)
特点 Query Path Header
来源 URL ?key=value URL 路径 {key} HTTP 请求头
必填默认 可选 必填 可选
SEO 友好 否 是 否
适合标识符 否 是 否
适合过滤/分页 是 否 部分（认证）
多值 同名重复 &tag=a&tag=b 否 同名重复
常见约束 ge / lt / min_length ge / lt 类型转换
Query vs Path vs Header 对比
关键要点
1. 可选参数： Query(None) 表示可选，不提供时不报错
2. 必填参数： Query(...) （Ellipsis）表示必填，缺失返回 422
3. 数值约束： ge / gt / le / lt 控制 int/float 的范围
4. 字符串约束： min_length / max_length / pattern 控制字符串长度和格式
5. 正则参数更名：FastAPI 0.115+ 中将 Query 的 regex 参数标记为废弃（deprecated），推荐使用
pattern 参数替代（regex 仍可运行，但文档中会提示废弃）
6. 类型自动转换：查询参数都是字符串，FastAPI 按声明类型自动转换
7. 多值参数：同名参数多次出现会自动收集为 List[...]
8. 废弃参数： deprecated=True 在文档中显示提示
