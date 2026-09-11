# FastAPI中Body的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\06FastAPI中Body的使用\FastAPI中Body的使用.pdf`
> **页数**：10（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 6,590 字符，其中汉字 1,256 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 中 Body 的使用
本文档介绍 FastAPI 中 Body 的基础用法、Pydantic 模型处理请求体、Field 验证规则以及 Body
与模型的适用场景选择。
在 FastAPI 中， Body 允许从请求体中获取数据并转换为 Python 对象，主要用于 POST、PUT、
PATCH 等请求。
提示：对于复杂的数据结构，推荐使用 Pydantic 模型而非直接使用 Body(...) 手动声明每个字
段。 Body 更多用于需要精细控制或嵌入单个字段的场景。
基础用法
简单参数（使用 Body）
当需要从请求体中获取单个简单类型的参数时，必须使用 Body 显式声明：
代码解释：
Body(...) 中的 ... 是 Python 的 Ellipsis 对象，表示该参数为必填
alias="用户名" 指定 JSON 中的字段别名，增加 API 的可读性
ge=0, le=150 是 Pydantic 的验证器，限制 age 的范围为 0-150
Body(False) 设置默认值为 False ，使参数变为可选
请求示例：
响应示例：
from fastapi import FastAPI, Body
app = FastAPI()
@app.post("/simple")
def simple_param(
name: str = Body(..., alias="用户名"),
age: int = Body(..., ge=0, le=150),
is_vip: bool = Body(False),
):
return {"name": name, "age": age, "is_vip": is_vip}
{
"用户名": "张三",
"age": 25
}

---

<!-- p.2 -->

Pydantic 模型（推荐方式）
使用 Pydantic 模型是处理请求体数据的推荐方式，它提供了更好的类型验证、文档生成和代码组织：
代码解释：
BaseModel 是 Pydantic 的基础模型类，用于定义数据结构
is_vip: bool = False 设置默认值，使该字段为可选
函数参数 user: UserInfo 表示从请求体中解析数据
FastAPI 自动进行类型验证和 JSON 解析
请求示例：
响应示例：
复杂嵌套实体对象
当数据包含嵌套对象或列表时，Pydantic 模型可以优雅地处理：
{
"name": "张三",
"age": 25,
"is_vip": false
}
from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()
class UserInfo(BaseModel):
name: str
age: int
is_vip: bool = False
@app.post("/user")
def create_user(user: UserInfo):
return user
{
"name": "张三",
"age": 25
}
{
"name": "张三",
"age": 25,
"is_vip": false
}

---

<!-- p.3 -->

代码解释：
Address 嵌套模型用于定义地址结构，内部字段使用 Field(...) 标记必填
List[Address] 定义地址列表类型， default_factory=list 确保不传时为空列表
User 模型中的 addresses 字段自动解析为 Address 对象列表
请求示例：
响应示例：
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List
app = FastAPI()
class Address(BaseModel):
street: str = Field(..., description="街道地址")
city: str = Field(..., description="城市")
zip_code: str = Field(..., description="邮政编码")
class User(BaseModel):
name: str = Field(..., description="用户名")
age: int = Field(..., ge=0, le=150, description="年龄")
addresses: List[Address] = Field(default_factory=list, description="地址列表")
@app.post("/complex-user")
def create_complex_user(user: User):
return user
{
"name": "张三",
"age": 25,
"addresses": [
{
"street": "中关村大街1号",
"city": "北京市",
"zip_code": "100080"
},
{
"street": "张江高科技园区博云路2号",
"city": "上海市",
"zip_code": "201203"
}
]
}
{
"name": "张三",
"age": 25,
"addresses": [
{

---

<!-- p.4 -->

Body 的高级用法
使用 embed 嵌入单个字段
当请求体只有一个根字段时，可以使用 embed=True 将其包装在一个额外的 JSON 对象中：
代码解释：
不使用 embed=True 时，请求体直接是 {"name": "张三", "age": 25}
使用 embed=True 后，请求体变为 {"user": {"name": "张三", "age": 25}}
适用于某些第三方 API 规范要求所有请求体都有根键的场景
请求示例：
响应示例：
"street": "中关村大街1号",
"city": "北京市",
"zip_code": "100080"
},
{
"street": "张江高科技园区博云路2号",
"city": "上海市",
"zip_code": "201203"
}
]
}
from fastapi import FastAPI, Body
from pydantic import BaseModel
app = FastAPI()
class User(BaseModel):
name: str
age: int
@app.post("/user-embed")
def create_user(user: User = Body(..., embed=True)):
return user
{
"user": {
"name": "张三",
"age": 25
}
}

---

<!-- p.5 -->

数组集合参数
如果需要接收数组类型的请求体：
代码解释：
List[Item] 声明请求体为 Item 对象的列表
Body(...) 标记请求体为必填
返回值中包含批量数据的统计信息
请求示例：
响应示例：
{
"name": "张三",
"age": 25
}
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List
app = FastAPI()
class Item(BaseModel):
name: str
price: float
@app.post("/items-batch")
def create_items(items: List[Item] = Body(...)):
return {"count": len(items), "items": items}
[
{"name": "苹果", "price": 5.5},
{"name": "香蕉", "price": 3.2},
{"name": "橙子", "price": 4.8}
]
{
"count": 3,
"items": [
{"name": "苹果", "price": 5.5},
{"name": "香蕉", "price": 3.2},
{"name": "橙子", "price": 4.8}
]
}

---

<!-- p.6 -->

日期时间参数
FastAPI 支持自动解析 ISO 8601 格式的日期时间字符串：
代码解释：
datetime 类型自动解析 "2023-01-01T00:00:00" 等 ISO 8601 格式字符串
解析后的 datetime 对象可以直接进行日期计算
请求示例：
响应示例：
支持的日期格式： 2023-01-01 、 2023-01-01T00:00:00 、 2023-01-01T00:00:00Z 、 2023-01-01
00:00:00 等。
动态字典参数
如果需要接收灵活的键值对数据：
from fastapi import FastAPI, Body
from datetime import datetime
app = FastAPI()
@app.post("/date-range")
def date_range(start_date: datetime = Body(...), end_date: datetime =
Body(...)):
duration = end_date - start_date
return {
"start_date": start_date.isoformat(),
"end_date": end_date.isoformat(),
"days": duration.days,
}
{
"start_date": "2023-01-01T00:00:00",
"end_date": "2023-12-31T23:59:59"
}
{
"start_date": "2023-01-01T00:00:00",
"end_date": "2023-12-31T23:59:59",
"days": 364
}

---

<!-- p.7 -->

代码解释：
Dict[str, Any] 允许接收键为字符串、值可以为任意类型的数据
适用于接收前端动态生成的表单数据或不确定结构的配置
请求示例：
响应示例：
字段验证器
使用 Field 配合 Pydantic 模型，可以为请求体中的字段添加丰富的验证规则：
from fastapi import FastAPI, Body
from typing import Dict, Any
app = FastAPI()
@app.post("/dynamic-data")
def dynamic_data(data: Dict[str, Any] = Body(...)):
return {
"keys": list(data.keys()),
"values": data,
"count": len(data),
}
{
"name": "张三",
"age": 25,
"is_vip": true,
"metadata": {
"source": "web",
"version": "1.0"
}
}
{
"keys": ["name", "age", "is_vip", "metadata"],
"values": {
"name": "张三",
"age": 25,
"is_vip": true,
"metadata": {
"source": "web",
"version": "1.0"
}
},
"count": 4
}
from fastapi import FastAPI

---

<!-- p.8 -->

参数 说明 示例
min_length 最小长度（字符串） min_length=3
max_length 最大长度（字符串） max_length=20
ge 最小值（数字） ge=0
le 最大值（数字） le=150
pattern 正则表达式 pattern=r"^[a-zA-Z]+$"
请求示例：
响应示例：
常用验证参数
from pydantic import BaseModel, Field, field_validator
import re
app = FastAPI()
class RegisterRequest(BaseModel):
username: str = Field(..., min_length=3, max_length=20,
pattern=re.compile(r"^[a-zA-Z0-9_]+$"))
email: str = Field(..., description="电子邮箱")
password: str = Field(..., min_length=8, description="密码")
age: int = Field(18, ge=0, le=150, description="年龄")
@field_validator("email")
@classmethod
def validate_email(cls, v: str) -> str:
if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", v):
raise ValueError("邮箱格式不正确")
return v
@app.post("/register")
def register(request: RegisterRequest):
return {"message": "注册成功", "username": request.username}
{
"username": "john_doe",
"email": "john@example.com",
"password": "securepass123",
"age": 25
}
{
"message": "注册成功",
"username": "john_doe"
}

---

<!-- p.9 -->

参数 说明 示例
default 默认值 Field(default=18)
description 字段描述（用于文档） description="用户名"
场景 推荐方式 原因
复杂数据结构 Pydantic 模型 类型安全、自动验证、代码清晰
简单几个字段 Body(...) + 类型注解 简洁直观
需要别名 Body(..., alias="...") 兼容不同前端字段名
需要嵌入字段 Body(..., embed=True) 适配特定 API 规范
动态字段 Dict[str, Any] 灵活处理不确定结构
代码解释：
... （Ellipsis）表示必填，等价于 Field(...) 不传 default 参数
ge （greater than or equal）和 le （less than or equal）是数字类型的边界验证
field_validator 用于自定义字段级别的验证逻辑
Body 与 Pydantic 模型的选择
总结
1. 优先使用 Pydantic 模型：对于结构化的请求体数据，Pydantic 模型提供了更好的类型安全、验证
和文档支持。
2. Body 的适用场景：
需要设置别名（ alias ）
需要精细的字段验证
需要嵌入单个字段（ embed=True ）
处理动态字典数据
3. 简化写法：对于多个简单类型的请求体参数，推荐用 Pydantic 模型；若仅需单个请求体参数，需
显式用 Body(...) 声明（否则会被解析为查询参数）；对于 Pydantic 模型参数，可直接用类型
注解，无需包裹 Body 。
4. 使用 Field 增强验证： Field 可以为 Pydantic 模型的字段添加描述、验证规则等元数据。
