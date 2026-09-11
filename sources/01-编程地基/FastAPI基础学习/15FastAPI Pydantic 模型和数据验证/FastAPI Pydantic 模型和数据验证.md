# FastAPI Pydantic 模型和数据验证

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\15FastAPI Pydantic 模型和数据验证\FastAPI Pydantic 模型和数据验证.pdf`
> **页数**：16（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 14,717 字符，其中汉字 1,356 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

配置参数 说明
str_strip_whitespace 自动去除字符串前后空格
from_attributes 支持从 ORM 模型转换
validate_assignment 对赋值操作进行验证
strict 严格类型检查，不允许自动转换
extra="forbid" 禁止传入未定义的字段
FastAPI Pydantic 模型和数据验证
Pydantic 是 FastAPI 的核心数据验证和序列化库。
定义模型
基础模型
所有字段默认必填，除非显式提供默认值。
模型配置（ConfigDict）
from pydantic import BaseModel
from typing import Optional
class Item(BaseModel):
name: str # 必填
price: float # 必填
description: Optional[str] = None # 可选，默认 None
tax: Optional[float] = None # 可选
from pydantic import BaseModel, ConfigDict
class Item(BaseModel):
name: str
price: float
model_config = ConfigDict(
str_strip_whitespace=True, # 自动去除字符串前后空格
from_attributes=True, # 支持从 ORM 模型转换
validate_assignment=True, # 赋值时自动验证
strict=True, # 严格类型检查（禁用自动转换）
extra="forbid", # 禁止传入未定义字段
)

---

<!-- p.2 -->

Field 参数 类型 说明
... （Ellipsis） - 必填字段
default 任意值 字段默认值
min_length / max_length int 字符串最小/最大长度
gt / lt / ge / le number 大于 / 小于 / 大于等于 / 小于等于
pattern str 正则表达式验证
description str OpenAPI 文档描述
字段验证（Field）
... （Ellipsis）表示必填字段。
使用模型
请求体验证（Request Body）
验证流程
from pydantic import BaseModel, Field
from typing import Optional
class Item(BaseModel):
name: str = Field(..., min_length=3, max_length=50, description="商品名称")
description: Optional[str] = Field(None, max_length=1000, description="商品描
述")
price: float = Field(..., gt=0, description="价格必须大于 0")
tax: Optional[float] = Field(None, ge=0, description="税率必须大于等于 0")
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional
app = FastAPI()
class Item(BaseModel):
name: str = Field(..., min_length=3, max_length=50)
description: Optional[str] = Field(None, max_length=1000)
price: float = Field(..., gt=0)
tax: Optional[float] = Field(None, ge=0)
@app.post("/items/")
def create_item(item: Item):
return {"item": item, "message": "商品创建成功"}

---

<!-- p.3 -->

类型 说明 示例
EmailStr 自动验证邮箱格式 "user@example.com"
HttpUrl 验证 URL（需包含协议） "https://example.com"
SecretStr 序列化时隐藏为 "********" "********"
IPvAnyAddress 验证 IP 地址 "192.168.1.1"
PaymentCardNumber Luhn 算法验证银行卡号 "4111111111111111"
请求示例
验证失败示例（422）
loc 指出错误字段位置， msg 是友好描述， type 可用于前端 i18n 国际化。
高级类型
客户端 JSON → FastAPI 按模型验证 → 通过 → 传递给路由函数
↓
失败 → 返回 422 错误
curl -X POST "http://127.0.0.1:8000/items/" \
-H "Content-Type: application/json" \
-d '{"name": "Python 书籍", "price": 99.9, "tax": 0.13}'
{
"detail": [
{"loc": ["body", "name"], "msg": "String should have at least 3 characters",
"type": "string_too_short"},
{"loc": ["body", "price"], "msg": "Input should be greater than 0", "type":
"greater_than"}
]
}
from pydantic import BaseModel, Field, EmailStr, HttpUrl, SecretStr
from typing import List
class User(BaseModel):
username: str = Field(..., pattern=r"^[a-zA-Z0-9_]+$", description="用户名")
email: EmailStr = Field(..., description="邮箱地址")
website: HttpUrl = Field(None, description="个人网站")
password: SecretStr = Field(..., description="密码")
tags: List[str] = Field(default_factory=list, description="标签列表")
age: int = Field(..., ge=18, le=120, description="年龄 18-120")

---

<!-- p.4 -->

查询参数和路径参数验证
Path 、 Query 、 Body 本质都是 Field 的快捷方式。
响应模型（response_model）
通过 response_model 过滤返回字段，防止敏感信息泄露：
响应中只包含 id 、 name 、 price ， internal_code 和 tax 字段被自动排除。
动态控制返回字段
from fastapi import FastAPI, Query, Path
from typing import Optional
app = FastAPI()
@app.get("/items/{item_id}")
def read_item(
item_id: int = Path(..., gt=0, description="商品ID"),
q: Optional[str] = Query(None, max_length=50),
price_min: float = Query(0, ge=0),
tags: list[str] = Query(default=[])
):
return {"item_id": item_id, "q": q, "price_min": price_min, "tags": tags}
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
app = FastAPI()
class ItemInternal(BaseModel):
id: int
name: str
price: float
tax: float
internal_code: str # 内部编码，不对外暴露
model_config = ConfigDict(from_attributes=True)
class ItemResponse(BaseModel):
id: int
name: str
price: float
model_config = ConfigDict(from_attributes=True)
@app.get("/items/{item_id}", response_model=ItemResponse)
def read_item(item_id: int):
db_item = ItemInternal(id=item_id, name="Python 书籍", price=99.9, tax=13.0,
internal_code="SKU-001")
return db_item # FastAPI 自动过滤 internal_code 和 tax

---

<!-- p.5 -->

数据转换和序列化
模型转换方法
序列化配置
# 排除某些字段
@app.get("/items/{item_id}", response_model_exclude={"tax"})
def read_item(item_id: int): ...
# 仅包含某些字段
@app.get("/items/{item_id}", response_model_include={"id", "name"})
def read_item(item_id: int): ...
from pydantic import BaseModel
class Item(BaseModel):
name: str
price: float
tax: float = None
# ① 从字典创建
item = Item(**{"name": "Python", "price": 99.9})
# ② 模型 → 字典
d = item.model_dump()
# ③ 模型 → JSON 字符串
j = item.model_dump_json()
# ④ JSON 字符串 → 模型
item = Item.model_validate_json('{"name": "Python", "price": 99.9}')
# ⑤ ORM 对象 → 模型（需 from_attributes=True）
# item = Item.model_validate(db_item)
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
class Item(BaseModel):
name: str = Field(..., alias="itemName")
description: Optional[str] = Field(None, alias="itemDesc")
price: float = Field(..., alias="itemPrice")
tax: Optional[float] = None
model_config = ConfigDict(by_alias=True, exclude_none=True)
item = Item(itemName="Python", itemPrice=99.9)

---

<!-- p.6 -->

exclude_none=True 排除所有值为 None 的字段， include 和 exclude 互补（不能同时用），
by_alias 使序列化时输出字段别名。
字段序列化器（field_serializer）
@field_serializer 在 model_dump() 时生效，不影响验证逻辑。
根模型（RootModel）
item.model_dump(exclude_none=True)
# {'name': 'Python', 'price': 99.9}
item.model_dump(by_alias=True)
# {'itemName': 'Python', 'itemDesc': None, 'itemPrice': 99.9}
item.model_dump(include={"name", "price"})
# {'name': 'Python', 'price': 99.9}
from pydantic import BaseModel, field_serializer
from datetime import datetime
class Product(BaseModel):
name: str
price: float
created_at: datetime
is_active: bool
@field_serializer("price")
def serialize_price(self, price: float) -> str:
return f"¥{price:.2f}"
@field_serializer("created_at")
def serialize_date(self, dt: datetime) -> str:
return dt.strftime("%Y-%m-%d %H:%M:%S")
product = Product(name="Python", price=99.9, created_at=datetime.now(),
is_active=True)
print(product.model_dump())
# {'name': 'Python', 'price': '¥99.90', 'created_at': '2026-04-01 10:30:00',
'is_active': True}
from fastapi import FastAPI
from pydantic import RootModel
app = FastAPI()
class ItemList(RootModel):
root: list[dict]
def get_count(self) -> int:

---

<!-- p.7 -->

根模型支持两种定义方式：显式定义 root 字段（可添加自定义方法），或使用泛型语法
RootModel[类型] （简化定义，等价于显式定义 root: 类型 ）。
自定义验证器
字段验证器（field_validator）
return len(self.root)
class StringList(RootModel[list[str]]):
pass
class ConfigMap(RootModel[dict[str, int]]):
pass
@app.get("/items/")
def get_items():
items = ItemList(root=[{"id": 1, "name": "Python"}])
return {"items": items.root, "count": items.get_count()}
@app.post("/strings/")
def create_strings(names: list[str]):
new_list = StringList(root=names)
return {"created": new_list.root}
from pydantic import BaseModel, field_validator
class User(BaseModel):
username: str
password: str
age: int
total: float
@field_validator("username")
@classmethod
def username_alphanumeric(cls, v: str) -> str:
if not v.replace("_", "").isalnum():
raise ValueError("用户名只能包含字母、数字和下划线")
return v
@field_validator("password")
@classmethod
def password_length(cls, v: str) -> str:
if len(v) < 8:
raise ValueError("密码至少 8 位")
return v
@field_validator("age")

---

<!-- p.8 -->

验证方法必须是 @classmethod ，参数为 cls 和字段值 v 。若需访问其他字段的已验证值，可
添加 values 参数（需确保字段顺序或设置 check_fields=True ）。
mode 参数（验证时机）
mode="before" 在 Pydantic 做类型转换之前执行，适合预处理外部输入。
模型验证器（model_validator）
用于跨字段验证（在所有字段验证之后执行）：
@classmethod
def age_valid(cls, v: int) -> int:
if not 0 < v < 150:
raise ValueError("年龄必须在 0-150 之间")
return v
@field_validator("total", check_fields=True)
@classmethod
def check_total_with_discount(cls, v: float, values) -> float:
discount = values.get("discount", 0.0)
if v < discount:
raise ValueError("总价不能小于折扣金额")
return v
from pydantic import BaseModel, field_validator
class Example(BaseModel):
price: float
# 默认（mode="after"）：类型转换之后验证
@field_validator("price")
@classmethod
def check_price(cls, v: float) -> float:
assert v > 0
return v
# mode="before"：类型转换之前验证，适合预处理字符串输入
@field_validator("price", mode="before")
@classmethod
def parse_price(cls, v):
if isinstance(v, str):
return float(v.replace("$", "").strip())
return v
from pydantic import BaseModel, model_validator
class Order(BaseModel):
items: list[str]
discount: float
total: float
# mode="before"：接收原始输入字典，返回处理后的字典

---

<!-- p.9 -->

mode 执行时机 适用场景
mode="before"
字段解析 / 验证前（接收原始输入
字典）
预处理原始数据（补全默认值、格式
转换）
mode="after"
所有字段验证之后（接收模型实
例）
跨字段验证
计算字段（computed_field）
@model_validator(mode="before")
@classmethod
def preprocess_input(cls, values):
# 预处理原始输入（比如补全默认值）
if "discount" not in values:
values["discount"] = 0.0
return values
# mode="after"：接收模型实例，返回实例
@model_validator(mode="after")
def check_total(self) -> "Order":
if self.total <= 0:
raise ValueError("总价必须大于 0")
return self
from pydantic import BaseModel, computed_field
class OrderItem(BaseModel):
price: float
quantity: int
tax_rate: float = 0.13
@computed_field
@property
def subtotal(self) -> float:
return self.price * self.quantity
@computed_field
@property
def tax_amount(self) -> float:
return self.subtotal * self.tax_rate
@computed_field
@property
def total(self) -> float:
return self.subtotal + self.tax_amount
order = OrderItem(price=99.9, quantity=2)
print(order.model_dump())
# {'price': 99.9, 'quantity': 2, 'tax_rate': 0.13, 'subtotal': 199.8,
'tax_amount': 25.974, 'total': 225.774}

---

<!-- p.10 -->

@computed_field 装饰的字段无默认值，其值由其他字段计算得出，序列化时自动包含。
高级用法
模型继承
子类继承父类所有字段和验证规则，可新增字段，也可覆盖父类字段定义。
嵌套模型
from pydantic import BaseModel, Field
class BaseItem(BaseModel):
name: str = Field(..., min_length=3, max_length=50)
price: float = Field(..., gt=0)
class ItemWithTax(BaseItem):
tax: float = Field(0.13, ge=0, le=1)
class DiscountedItem(BaseItem):
price: float = Field(..., gt=0) # 覆盖父类
discount: float = Field(0.0, ge=0, le=1)
@property
def discounted_price(self) -> float:
return self.price * (1 - self.discount)
from pydantic import BaseModel, Field
from typing import List, Optional
class Address(BaseModel):
street: str
city: str
country: str = "中国"
class Item(BaseModel):
name: str
price: float
class Order(BaseModel):
order_id: str = Field(..., min_length=8)
items: List[Item] = Field(..., min_length=1)
shipping_address: Address
notes: Optional[str] = None

---

<!-- p.11 -->

FastAPI 递归验证所有嵌套字段—— items 中每个 Item 都进行类型和验证检查， Address 也进行模
型验证。
别名（Alias）
字段名与外部数据不一致时，使用别名映射：
请求（使用 camelCase）
可辨识联合类型（Discriminated Union）
一个字段可以是多种不同模型时，用 discriminator 明确区分：
discriminator 参数指定一个字段（如 kind ），Pydantic 根据该字段值直接判断使用哪个模型，验
证效率更高，错误信息更准确。
from pydantic import BaseModel, Field, ConfigDict
class Item(BaseModel):
item_name: str = Field(..., alias="itemName")
item_price: float = Field(..., alias="itemPrice")
item_tax: float = Field(0.0, alias="itemTax")
model_config = ConfigDict(
populate_by_name=True, # 同时接受别名和原名
by_alias=True, # 序列化时输出别名
)
curl -X POST "http://127.0.0.1:8000/items/" \
-H "Content-Type: application/json" \
-d '{"itemName": "Python", "itemPrice": 99.9}'
from pydantic import BaseModel, Field
from typing import Union
class Cat(BaseModel):
kind: str = "cat"
name: str
meow_volume: int
class Dog(BaseModel):
kind: str = "dog"
name: str
bark_volume: int
class ZooRequest(BaseModel):
animal: Union[Cat, Dog] = Field(..., discriminator="kind")

---

<!-- p.12 -->

与其他组件配合
与 SQLAlchemy ORM 配合
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.exc import IntegrityError
Base = declarative_base()
class BookDB(Base):
__tablename__ = "books"
id = Column(Integer, primary_key=True)
title = Column(String(100), nullable=False)
price = Column(Float, nullable=False)
class BookCreate(BaseModel):
title: str = Field(..., min_length=1, max_length=100)
price: float = Field(..., gt=0)
class BookResponse(BaseModel):
id: int
title: str
price: float
model_config = ConfigDict(from_attributes=True)
app = FastAPI()
engine = create_engine("sqlite:///./books.db")
Base.metadata.create_all(bind=engine)
@app.post("/books/", response_model=BookResponse)
def create_book(book: BookCreate):
with Session(engine) as db:
try:
db_book = BookDB(**book.model_dump())
db.add(db_book)
db.commit()
db.refresh(db_book)
return db_book
except IntegrityError:
db.rollback()
raise HTTPException(status_code=400, detail="书籍标题已存在或数据无效")
@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int):

---

<!-- p.13 -->

关键配置： model_config = ConfigDict(from_attributes=True) 让 Pydantic 能从 ORM 对象创建
验证模型。
与 Depends 依赖注入配合
依赖项函数从 Query 参数构建 Pydantic 模型，路由中直接注入模型对象而非原始字典。
自定义验证错误响应
with Session(engine) as db:
book = db.get(BookDB, book_id)
if not book:
raise HTTPException(status_code=404, detail="书籍不存在")
return book
from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel, Field
app = FastAPI()
class Pagination(BaseModel):
page: int = Field(1, ge=1)
page_size: int = Field(10, ge=1, le=100)
def get_pagination(
page: int = Query(1, ge=1),
page_size: int = Query(10, ge=1, le=100)
) -> Pagination:
return Pagination(page=page, page_size=page_size)
@app.get("/items/")
def list_items(pagination: Pagination = Depends(get_pagination)):
offset = (pagination.page - 1) * pagination.page_size
return {"items": [f"item_{i}" for i in range(offset, offset +
pagination.page_size)], "total": 100}
@app.get("/users/")
def list_users(pagination: Pagination = Depends(get_pagination)):
offset = (pagination.page - 1) * pagination.page_size
return {"users": [f"user_{i}" for i in range(offset, offset +
pagination.page_size)]}
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
app = FastAPI()

---

<!-- p.14 -->

能力 方法
定义模型 class X(BaseModel)
字段验证 Field(...)
模型配置 ConfigDict(...)
字段验证器 @field_validator
模型验证器 @model_validator
计算字段 @computed_field
字段序列化器 @field_serializer
根模型 RootModel
能力 方法
模型 → 字典 item.model_dump()
模型 → JSON item.model_dump_json()
字典 模型
exc.errors() 返回 Pydantic 内部错误列表，可统一为项目自己的 API 响应格式。
方法速查
模型定义与验证
数据转换
class Item(BaseModel):
name: str = Field(..., min_length=3)
price: float = Field(..., gt=0)
@app.post("/items/")
def create_item(item: Item):
return {"message": "创建成功", "item": item}
@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
return JSONResponse(
status_code=422,
content={
"code": 422,
"message": "数据验证失败",
"errors": exc.errors()
}
)

---

<!-- p.15 -->

能力 方法
字典 → 模型 Item.model_validate()
JSON → 模型 Item.model_validate_json()
ORM → 模型 Item.model_validate()
场景 推荐配置
API 请求/响应模型 from_attributes=True
对外 API（严格模式） strict=True , extra="forbid"
内部数据处理 validate_assignment=True
处理前端数据 str_strip_whitespace=True
序列化选项
常用配置
item.model_dump(exclude_none=True) # 排除 None 值
item.model_dump(by_alias=True) # 使用别名输出
item.model_dump(include={"a", "b"}) # 仅包含指定字段
item.model_dump(exclude={"c"}) # 排除指定字段
