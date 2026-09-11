# FastAPI使用sqlAIchemy连接数据库

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\17FastAPI使用sqlAIchemy连接数据库\FastAPI使用sqlAIchemy连接数据库.pdf`
> **页数**：24（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 22,115 字符，其中汉字 4,860 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 使用 SQLAlchemy 连接数据库
在 FastAPI 中，对象关系映射（ORM）框架用于简化与数据库的交互。ORM 提供了一种将数据库表与
Python 类进行映射的方法，使得开发者可以通过操作对象来与数据库进行交互，而不需要直接编写
SQL 语句。FastAPI 支持多种 ORM 框架，其中最常用的是 SQLAlchemy 和 Tortoise ORM。
在传统的关系型数据库中，数据是以表格的形式存储，而在面向对象编程中，数据是以对象的形式表
示。ORM 技术允许开发人员通过定义对象类来描述数据库表，然后由 ORM 工具自动创建和管理数据库
表和对象之间的映射关系。这样开发人员可以使用面向对象的方式来处理数据，而无须直接编写 SQL 查
询语句。
ORM 优势如下：
简化开发：ORM 可以减少编写和维护 SQL 查询语言的工作量。
提高可维护性：通过将数据库模式与代码分离，可以更轻松地进行数据库结构的更改，而不影响应
用程序的其余部分。
跨数据库平台：ORM 提供了一种抽象层，使得应用程序可以在不同的数据库系统之间切换，而无
须改变大部分代码。
面向对象特性：开发人员可以使用面向对象编程的概念，如继承、多态和封装来处理数据。
性能优化：部分 ORM 工具提供可选的性能优化能力（如延迟加载、批量处理），但需合理配置，
否则可能引入 N+1 查询等性能问题。
安装
FastAPI 与 SQLAlchemy 配合使用时，需要安装两个部分：SQLAlchemy 核心库和具体数据库的异步驱
动。
安装 SQLAlchemy 核心库
SQLAlchemy 本身是同步的， sqlalchemy[asyncio] 会同时安装 sqlalchemy 核心包以及异步所需的
额外依赖。通过 create_async_engine 和 AsyncSession 实现异步数据库操作。
SQLAlchemy 核心库 负责 ORM 语法、模型定义、会话管理
+
具体数据库的异步驱动 负责与数据库通信，将 SQL 指令发送到数据库
pip install sqlalchemy[asyncio]

---

<!-- p.2 -->

数据库 驱动包 连接字符串前缀
MySQL aiomysql 或 asyncmy
mysql+aiomysql:// 或
mysql+asyncmy://
PostgreSQL asyncpg postgresql+asyncpg://
SQLite
aiosqlite （仅 Python 原生可
用）
sqlite+aiosqlite://
安装数据库异步驱动
不同的数据库需要不同的异步驱动，以下是常用驱动对比：
注意：驱动只需要安装对应数据库的即可。例如只用 MySQL，则只需安装
sqlalchemy[asyncio] + aiomysql ，不需要安装其他驱动。
完整安装示例（以 MySQL 为例）
本教程后续示例均以 MySQL + aiomysql 为基础，驱动更换时仅需修改连接字符串和安装的包。
建库与建表
建库
作用：在 MySQL 数据库中创建一个新的数据库，作为存放所有数据表的容器。
解释： create database 是 MySQL 的 DDL（数据定义语言）命令，用于创建一个新的数据库实例。
fastapi_first 是数据库名称，应与代码中的配置保持一致。
查看创建的数据库：
解释： show databases; 用于列出 MySQL 服务器中所有已存在的数据库，用于确认 fastapi_first
是否创建成功。
# MySQL 异步驱动（二选一）
pip install aiomysql # 纯 Python 实现，依赖少
pip install asyncmy # 基于 PyMySQL，性能更好
# PostgreSQL
pip install asyncpg
# SQLite
pip install aiosqlite
pip install sqlalchemy[asyncio] aiomysql
create database fastapi_first
show databases;

---

<!-- p.3 -->

建表
建表过程分为以下三个步骤：
1. 创建数据库引擎
2. 定义模型类
3. 启动应用时建表
创建数据库引擎
使用 create_async_engine 创建异步引擎：
作用：数据库引擎是应用程序与 MySQL 数据库之间的桥梁，负责管理连接池、处理 SQL 语句发送和结
果接收。 create_async_engine 创建的是异步引擎，可以配合 FastAPI 的异步特性使用。
连接 URL 各部分解释：
from sqlalchemy.ext.asyncio import create_async_engine
# mysql数据库(mysql)+驱动(aiomysql)://用户名(root):密码(123456)@域名(localhost):数据库
端口(3306)/数据库名称(FastAPI_first)?charset=utf8
ASYNC_DATABASE_URL = "mysql+aiomysql://root:123456@localhost:3306/FastAPI_first?
charset=utf8mb4"
async_engine = create_async_engine(
ASYNC_DATABASE_URL,
echo=True, # 可选，输出 SQL 日志
pool_size=10, # 设置连接池活跃的连接数
max_overflow=20 # 允许额外的连接数
)

---

<!-- p.4 -->

部分 含义
mysql+aiomysql:// 数据库类型（mysql）+ 异步驱动（aiomysql）
root:123456 MySQL 用户名和密码
localhost:3306 数据库主机地址和端口
FastAPI_first 数据库名称
?charset=utf8mb4 字符集设置，防止中文乱码
参数 作用
echo=True
开启后会在控制台打印所有执行的 SQL 语句，便于调试和查看 ORM 生成
的 SQL
pool_size=10 连接池中始终保持 10 个活跃连接，避免频繁创建销毁连接的性能开销
max_overflow=20 当 pool_size 不够用时，允许临时创建最多 20 个额外连接应对高峰
参数说明：
定义模型类
定义模型类分为以下两个步骤：
1. 基类：继承 DeclarativeBase
2. 数据库表对应的模型类：定义数据库表的结构
作用：模型类是用 Python 类来描述数据库表结构的一种方式。通过定义模型类，SQLAlchemy 可以自
动生成建表 SQL、进行 CRUD 操作，而不需要直接写 SQL 语句。
from datetime import datetime
from sqlalchemy import DateTime, func, String, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
# 2. 定义模型类： 基类 + 表对应的模型类
# 基类：创建时间、更新时间；书籍表：id、书名、作者、价格、出版社
class Base(DeclarativeBase):
create_time: Mapped[datetime] = mapped_column(DateTime,
insert_default=func.now(), default=func.now, comment="创建时间")
update_time: Mapped[datetime] = mapped_column(DateTime,
insert_default=func.now(), default=func.now, onupdate=func.now(), comment="修改时
间")
class Book(Base):
__tablename__ = "book"
id: Mapped[int] = mapped_column(primary_key=True, comment="书籍id")
bookname: Mapped[str] = mapped_column(String(255), comment="书名")
author: Mapped[str] = mapped_column(String(255), comment="作者")
price: Mapped[float] = mapped_column(Float, comment="价格")
publisher: Mapped[str] = mapped_column(String(255), comment="出版社")

---

<!-- p.5 -->

参数 作用
Mapped[类型] Python 类型提示，声明字段的 Python 数据类型
mapped_column(...) 配置列的各项属性
primary_key=True 标记该字段为主键
String(255) VARCHAR(255)，最大 255 字符的字符串
Float 浮点数类型，存储价格
insert_default=func.now() 插入数据时自动使用当前时间作为默认值
onupdate=func.now() 更新数据时自动刷新为当前时间
comment="..." 字段注释，便于理解字段含义
基类 Base 的作用：所有模型类都需要继承 DeclarativeBase 派生的基类。基类中可以定义公共字
段，如 create_time 和 update_time ，这些字段会自动添加到所有继承它的子表中。
模型类 Book 的作用：对应数据库中的 book 表，每个属性对应表中的一列。
字段参数说明：
启动应用时建表
启动应用时建表分为以下两个步骤：
1. 从连接池获取异步连接，开启事务，执行 ORM 操作
2. FastAPI 应用启动时，创建数据库表
作用：通过 FastAPI 的生命周期钩子，在应用启动时自动检查并创建数据库表，确保数据库结构与应用
代码中的模型类定义保持一致。
lifespan 解释：
from contextlib import asynccontextmanager
from fastapi import FastAPI
app = FastAPI()
# 定义启动和关闭事件
@asynccontextmanager
async def lifespan(app: FastAPI):
# 启动时：创建数据库表
async with async_engine.begin() as conn:
await conn.run_sync(Base.metadata.create_all)
yield # 应用运行中
# 关闭时：销毁数据库引擎
await async_engine.dispose()
app = FastAPI(lifespan=lifespan)

---

<!-- p.6 -->

阶
段
代码 说明
启
动
async_engine.begin() 从连接池获取异步连接，开启事务
启
动
conn.run_sync(Base.metadata.create_all)
扫描所有模型类，生成并执行建表
SQL
关
闭
await async_engine.dispose() 关闭数据库引擎，释放所有连接
lifespan 替代了废弃的 @app.on_event ，在同一处同时管理启动和关闭逻辑。
SQLAlchemy 使用 ORM
核心概念
核心：创建依赖项，使用 Depends 注入到处理函数。
作用：ORM（Object Relational Mapping，对象关系映射）允许开发者用 Python 对象操作数据库，而
不需要写 SQL 语句。FastAPI 的依赖注入系统可以自动管理数据库会话的生命周期。
创建依赖项
作用：依赖项是一个可调用的函数，FastAPI 会自动调用它并把返回值注入到路由处理函数的参数中。
通过依赖注入，可以统一管理数据库会话的创建、提交和关闭，避免重复代码。
代码解释：
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
# 需求：查询功能的接口，查询图书 → 依赖注入：创建依赖项获取数据库会话 + Depends 注入路由处理函
数
AsyncSessionLocal = async_sessionmaker(
bind=async_engine, # 绑定数据库引擎
class_=AsyncSession, # 指定会话类
expire_on_commit=False # 提交后会话不过期，不会重新查询数据库
)
# 依赖项
async def get_database():
async with AsyncSessionLocal() as session:
try:
yield session # 返回数据库会话给路由处理函数
await session.commit() # 提交事务
except Exception:
await session.rollback() # 有异常，回滚
raise
finally:
await session.close() # 关闭会话

---

<!-- p.7 -->

代码 作用
async_sessionmaker 会话工厂类，用于批量创建数据库会话实例
bind=async_engine 将会话工厂绑定到之前创建的数据库引擎
class_=AsyncSession 指定使用异步会话类
expire_on_commit=False
提交事务后，已加载的 ORM 对象属性仍可访问（不会自动过
期），访问属性时不会触发额外的数据库查询；默认 True 时，提
交后访问属性会重新查询数据库。
yield session
将 session 临时交给路由函数使用，执行完后自动继续执行 yield
之后的代码
commit() 路由函数正常执行完毕后，提交事务，保存所有数据库修改
rollback() 发生异常时回滚，撤销所有未提交的修改
close() 无论如何都会执行，关闭会话，归还连接到连接池
代码 作用
db: AsyncSession =
Depends(get_database)
声明参数 db ，类型为 AsyncSession ，值来自
get_database() 依赖项
db.execute(select(Book))
执行查询， select(Book) 生成 SELECT * FROM book
SQL
result.scalars().all() 从查询结果中提取所有行，转为 Python 对象列表
return book FastAPI 自动将返回的 Python 对象序列化为 JSON 响应
使用时注入
使用时注入（不止放到路由函数，还可以是DAO、Service层）：
作用：通过 FastAPI 的 Depends 依赖注入系统，将数据库会话自动注入到路由处理函数中，无需手动
创建和关闭会话。
代码解释：
完整请求流程：
1. 请求到达路由 → FastAPI 调用 get_database() 创建会话
2. get_database() 中的 yield 将 session 传递给路由函数使用
3. 路由函数使用 db 执行数据库查询
@app.get("/book/books")
async def get_book_list(db: AsyncSession = Depends(get_database)):
# 查询
result = await db.execute(select(Book))
book = result.scalars().all()
return book

---

<!-- p.8 -->

方法 说明
scalars().all() 获取所有记录，返回列表
scalars().first() 获取第一条记录，没有则返回 None
scalar_one_or_none() 获取唯一记录（预期结果最多 1 条），不存在返回 None
scalar() 获取聚合计算后的单个标量值（如 count、avg 的结果）
类型 示例 说明
比较判断 Book.id == book_id 等于、大于，小于等
模糊查询 Book.author.like("曹%") 使用通配符匹配
与查询 & 多个条件同时满足
或查询 \| 满足任一条件即可
4. 路由函数执行完毕 → 自动 commit() 提交事务
5. finally 块确保无论成功与否都 close() 关闭会话
操作数据 - 查询（重点）
核心语句
查询使用 select() 构造器，返回结果对象：
解释：
select(Book) ：构造一条查询语句，告诉 SQLAlchemy "我要查 Book 表"。
await db.execute(...) ：异步执行这条查询语句， db 是通过 Depends(get_database) 注入
的 AsyncSession 会话对象。
返回的 result 是一个结果集对象，还不是 Python 数据，需要进一步提取。
使用 scalars() 提取数据（从结果集中取出实际的模型对象）：
为什么用 scalars() ？

execute() 返回的结果包含行数据（Row）和元数据。 scalars() 告诉 SQLAlchemy "我只想要
每一行的第一列"，也就是 ORM 模型对象，省去手动转换的麻烦。
查询条件
where() 中可以传入多个条件，用逗号分隔，效果相当于用 AND 连接。
常见条件类型：
result = await db.execute(select(Book)) # 查询 Book 表所有记录
select(模型类).where( 条件, 条件2, ... )

---

<!-- p.9 -->

类型 示例 说明
非查询 ~ 取反
包含查询 in_() 字段值在列表中
通配符 含义 示例 匹配示例
% 匹配零个、一个或多个字符 "曹%" 曹操、曹雪芹、曹
_ 匹配任意单个字符 "曹__" 曹操、曹雪芹（3个字）
比较判断
解释：
select(Book) 指定要查询 Book 模型对应的表。
.where(Book.id == book_id) 添加过滤条件——只返回 id 等于路径参数 book_id 的那一条
记录。
.scalar_one_or_none() 从结果中取出 ORM 对象。由于查询的是主键 id，结果最多只有一条记
录，用此方法最合适。如果查不到返回 None，FastAPI 会自动序列化为 JSON null 返回给前端。
解释：
Book.price >= 200 表示"价格大于等于 200"的过滤条件。
.scalars().all() 取出所有满足条件的记录，返回一个列表。
模糊查询
模糊查询使用 like() ，通配符规则如下：
解释：
"曹%" 表示"以'曹'开头的任意字符串"，也就是查询所有姓曹的作者。
like() 在 SQL 中对应 LIKE 关键字。
@app.get("/book/get_book/{book_id}")
async def get_book(book_id: int, db: AsyncSession = Depends(get_database)):
result = await db.execute(select(Book).where(Book.id == book_id))
return result.scalar_one_or_none()
@app.get("/book/search_book")
async def search_book(db: AsyncSession = Depends(get_database)):
result = await db.execute(select(Book).where(Book.price >= 200))
return result.scalars().all()
@app.get("/book/get_books")
async def get_books(db: AsyncSession = Depends(get_database)):
result = await db.execute(select(Book).where(Book.author.like("曹%")))
return result.scalars().all()

---

<!-- p.10 -->

方法 说明
count 统计行数量
avg 求平均值
max 求最大值
min 求最小值
sum 求和
与非查询
使用 & （与）、 | （或）、 ~ （非）组合多个查询条件：
解释：
& 表示 AND，两个条件必须同时满足——既要作者姓曹，并且价格大于 100。
注意每个条件要用括号括起来，避免运算符优先级问题。
SQL 等价于： WHERE author LIKE '曹%' AND price > 100
包含查询
使用 in_() 查询字段值是否在指定列表中：
解释：
in_() 在 SQL 中对应 IN 关键字。
查询 id 为 1、3、5、7 的书籍记录。
SQL 等价于： WHERE id IN (1, 3, 5, 7)
聚合查询
聚合函数通过 func 模块调用，常见方法如下：
使用方式： select(func.方法(模型类.属性))
@app.get("/book/get_books")
async def get_books(db: AsyncSession = Depends(get_database)):
result = await db.execute(
select(Book).where((Book.author.like("曹%")) & (Book.price > 100))
)
return result.scalars().all()
@app.get("/book/search_book")
async def search_book(db: AsyncSession = Depends(get_database)):
id_list = [1, 3, 5, 7]
result = await db.execute(select(Book).where(Book.id.in_(id_list)))
return result.scalars().all()

---

<!-- p.11 -->

方法 说明
offset(n) 跳过前 n 条记录
limit(n) 最多返回 n 条记录
解释：
func.avg(Book.price) 构造一条 SQL 聚合语句： SELECT AVG(price) FROM book 。
func 是 SQLAlchemy 提供的一个命名空间，用来调用数据库内置函数（如 count、sum、avg
等）。
.scalar() 用于取出聚合结果（单个值），这里返回的是所有书籍的平均价格。
如果数据库中没有记录，返回 None。
分页查询
使用 select().offset().limit() 实现分页：
公式： offset 值 = (当前页码 - 1) * limit 每页数量
@app.get("/book/count")
async def get_count(db: AsyncSession = Depends(get_database)):
result = await db.execute(select(func.avg(Book.price)))
return result.scalar()
from pydantic import BaseModel
# 定义分页响应模型
class PaginationResponse(BaseModel):
items: List[BookResponse]
total: int
page: int
page_size: int
total_pages: int
@app.get("/book/get_book_list", response_model=PaginationResponse)
async def get_book_list(
page: int = 1,
page_size: int = 3,
db: AsyncSession = Depends(get_database)
):

---

<!-- p.12 -->

解释：
page ：当前页码，从 1 开始。
page_size ：每页显示多少条记录，默认 3。
skip = (page - 1) * page_size ：计算需要跳过的记录数。
第 1 页：skip = 0 → 从第 1 条开始取
第 2 页：skip = 3 → 从第 4 条开始取
第 3 页：skip = 6 → 从第 7 条开始取
stmt 是构造好的查询语句，先 .offset() 跳过，再 .limit() 取数量。
.scalars().all() 取出结果列表返回给前端。
操作数据 - 新增
核心步骤
核心步骤：定义 ORM 对象 -> 添加对象到事务： add(对象) -> commit 提交到数据库
示例代码
page = max(page, 1)
page_size = max(page_size, 1)
skip = (page - 1) * page_size
# 查询总条数
total_stmt = select(func.count(Book.id))
total = await db.scalar(total_stmt)
total_pages = (total + page_size - 1) // page_size # 向上取整
# 查询当前页数据
data_stmt = select(Book).offset(skip).limit(page_size)
result = await db.execute(data_stmt)
books = result.scalars().all()
return {
"items": books,
"total": total,
"page": page,
"page_size": page_size,
"total_pages": total_pages
}
from pydantic import BaseModel
class BookBase(BaseModel):
bookname: str
author: str
price: float
publisher: str

---

<!-- p.13 -->

解释：
1. 定义 Pydantic 模型： BookBase
BookBase 用来验证前端传入的 JSON 请求体，确保字段类型和必填性正确。
如果前端传了非法数据（如 price 传了字符串），FastAPI 会自动返回 422 错误，不会进入业务代
码。
2. 创建 ORM 对象： Book(**book.model_dump())
book.model_dump() 将 Pydantic 对象转成字典： {"bookname": "...", "author": "...",
...} 。
Book(**字典) 用字典解包方式传给 Book 模型的构造函数，创建一条 ORM 记录对象（此时还在
内存中，未写入数据库）。
3. 添加到会话： db.add(book_obj)
add() 只是把对象放入 SQLAlchemy 的会话（session）管理区，生成对应的 INSERT SQL 语句，
但此时还没有真正执行。
4. 提交事务： await db.commit()
commit() 真正将 pending（待执行）的 SQL 发送到数据库执行。执行成功后，数据库中就新增
了一条记录。
5. 返回结果
这里直接返回原始的 book （Pydantic 对象），也可以返回 book_obj （ORM 对象）。Pydantic
配置了 from_attributes=True 后会自动从 ORM 对象中取值进行序列化。
操作数据 - 更新
核心步骤
核心步骤：查询 get -> 属性重新赋值 -> commit 提交到数据库
示例代码
@app.post("/book/add_book")
async def add_book(book: BookBase, db: AsyncSession = Depends(get_database)):
book_obj = Book(**book.model_dump())
db.add(book_obj)
await db.commit()
return book
class BookUpdate(BaseModel):
bookname: str
author: str
price: float
publisher: str
@app.put("/book/update_book/{book_id}")
async def update_book(
book_id: int,

---

<!-- p.14 -->

解释：
1. 根据主键查询： await db.get(Book, book_id)
db.get(Book, book_id) 是根据主键查询的单条记录方法，等价于
select(Book).where(Book.id == book_id) 。
找到返回 ORM 对象，找不到返回 None 。
2. 异常处理：查不到时返回 404
if db_book is None 时抛出 HTTPException(status_code=404) ，让前端知道资源不存在。
3. 直接修改属性赋值
SQLAlchemy 的核心特性：ORM 对象是动态追踪的。直接对 db_book.bookname =
data.bookname 赋值，SQLAlchemy 会自动标记这个字段为"已修改"，生成 UPDATE SQL，不需
要手动拼装 SQL。
4. 提交事务： await db.commit()
commit 时，SQLAlchemy 会自动对比修改前后的差异，只 UPDATE 真正改过的字段（脏检查机
制）。
操作数据 - 删除
核心步骤
核心步骤： get 查询对象 -> delete 删除 -> commit 提交到数据库
示例代码
data: BookUpdate,
db: AsyncSession = Depends(get_database)
):
db_book = await db.get(Book, book_id)
if db_book is None:
raise HTTPException(status_code=404, detail="查无此书")
db_book.bookname = data.bookname
db_book.author = data.author
db_book.price = data.price
db_book.publisher = data.publisher
await db.commit()
return db_book
@app.delete("/book/delete_book/{book_id}")
async def delete_book(book_id: int, db: AsyncSession = Depends(get_database)):
db_book = await db.get(Book, book_id)
if db_book is None:
raise HTTPException(status_code=404, detail="查无此书")
await db.delete(db_book)
await db.commit()
return {"message": "删除成功"}

---

<!-- p.15 -->

解释：
1. 根据主键查询： await db.get(Book, book_id)
先查这条记录是否存在，避免误删。如果不存在，返回 404。
2. 标记删除： await db.delete(db_book)
delete() 是"标记式"删除——将对象标记为待删除状态，生成 DELETE SQL，但此时还没有真正
删除。
3. 提交事务： await db.commit()
commit 后，DELETE 语句发送到数据库，物理删除该行记录。
4. 返回响应
删除成功后返回 JSON 消息。HTTP 状态码默认 200，也可以改为 status_code=204 表示"无内
容"。
最佳实践
项目结构
本项目采用标准的分层架构，将路由层、数据访问层（DAO）和模型层分离，便于维护和测试。
config/database.py（异步数据库配置）
核心配置文件，负责创建异步数据库引擎和会话工厂：
code/17/
├── main.py # FastAPI 应用入口
├── config/
│ ├── __init__.py # 配置模块导出
│ ├── database.py # 异步数据库引擎与会话配置
│ └── settings.py # 项目配置（引用 database.py 中的 URL）
├── models/
│ ├── __init__.py # 模型模块导出
│ └── models.py # ORM 模型定义（Book 表 + Base 基类）
├── schemas/
│ ├── __init__.py # Schema 模块导出
│ └── schemas.py # Pydantic 请求/响应模型
├── routers/
│ ├── __init__.py # 路由模块导出
│ └── book_router.py # 书籍 CRUD 路由
├── dao/
│ ├── __init__.py # DAO 模块导出
│ └── book_dao.py # 数据访问层（BookDAO 类）
└── dependencies/
└── __init__.py # 依赖注入说明
"""
数据库配置模块
负责创建数据库引擎、连接配置
"""

---

<!-- p.16 -->

config/settings.py（项目配置）
统一管理项目配置，引用 database.py 中的 URL：
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession,
async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
# 数据库连接 URL
# mysql+aiomysql://用户名:密码@主机:端口/数据库名?charset=utf8
ASYNC_DATABASE_URL = "mysql+aiomysql://root:123456@localhost:3306/fastapi_first?
charset=utf8"
# 创建异步数据库引擎
async_engine = create_async_engine(
ASYNC_DATABASE_URL,
echo=True, # 开启后输出 SQL 日志，方便调试
pool_size=10, # 连接池保持的活跃连接数
max_overflow=20, # 允许的额外连接数
pool_recycle=3600, # 1小时回收一次连接，避免MySQL关闭空闲连接
pool_pre_ping=True # 执行SQL前检测连接是否有效，无效则重新创建
)
# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
bind=async_engine, # 绑定数据库引擎
class_=AsyncSession, # 指定会话类
expire_on_commit=False, # 提交后不销毁对象
)
# 创建依赖项：获取数据库会话
async def get_database():
"""
FastAPI 依赖项：管理数据库会话的生命周期
- yield 前：创建会话
- yield：将会话传递给路由函数
- yield 后（正常）：提交事务
- yield 后（异常）：回滚事务
- finally：关闭会话
"""
async with AsyncSessionLocal() as session:
try:
yield session # 返回会话给路由函数使用
await session.commit() # 正常结束时提交事务
except Exception:
await session.rollback() # 发生异常时回滚
raise
finally:
await session.close() # 无论如何都关闭会话

---

<!-- p.17 -->

models/models.py（ORM 模型定义）
使用 SQLAlchemy 2.0 新版写法，定义基类和 Book 模型：
"""
项目配置文件
"""
from .database import ASYNC_DATABASE_URL
# 数据库配置
DATABASE_URL = ASYNC_DATABASE_URL
"""
模型类模块
定义数据库表结构
"""
from datetime import datetime
from sqlalchemy import String, Float, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
# 基类：所有模型类都继承此类
class Base(DeclarativeBase):
"""基类：包含公共字段"""
create_time: Mapped[datetime] = mapped_column(
DateTime,
insert_default=func.now(),
default=func.now,
comment="创建时间"
)
update_time: Mapped[datetime] = mapped_column(
DateTime,
insert_default=func.now(),
default=func.now,
onupdate=func.now(),
comment="修改时间"
)
# 书籍模型类
class Book(Base):
"""书籍表模型"""
__tablename__ = "book"
id: Mapped[int] = mapped_column(primary_key=True, comment="书籍id")
bookname: Mapped[str] = mapped_column(String(255), nullable=False,
comment="书名")
author: Mapped[str] = mapped_column(String(255), nullable=False, comment="作
者")
# 价格非负约束
price: Mapped[float] = mapped_column(Float, nullable=False, comment="价格")

---

<!-- p.18 -->

schemas/schemas.py（Pydantic 数据模型）
定义请求/响应的数据结构：
publisher: Mapped[str] = mapped_column(String(255), nullable=False,
comment="出版社")
# 业务约束：价格大于等于0
__table_args__ = (
CheckConstraint("price >= 0", name="check_price_non_negative"),
)
"""
Pydantic Schema 模块
定义请求/响应数据模型
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
# 书籍基础 Schema
class BookBase(BaseModel):
"""书籍基础字段"""
bookname: str
author: str
price: float
publisher: str
# 创建书籍 Schema
class BookCreate(BookBase):
"""创建书籍时的请求体"""
pass
# 更新书籍 Schema
class BookUpdate(BaseModel):
"""更新书籍时的请求体（全部字段可选）"""
bookname: str | None = None
author: str | None = None
price: float | None = None
publisher: str | None = None
# 书籍响应 Schema
class BookResponse(BookBase):
"""书籍响应模型"""
id: int
create_time: datetime
update_time: datetime
model_config = ConfigDict(from_attributes=True) # 从 ORM 对象转换

---

<!-- p.19 -->

dao/book_dao.py（数据访问层）
封装数据库的增删改查操作，提供面向对象的 DAO 接口：
"""
DAO 层：数据访问对象
封装数据库的增删改查操作
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.models import Book
from typing import Optional
class BookDAO:
"""书籍数据访问对象"""
def __init__(self, session: AsyncSession):
self.session = session
async def create(self, book_data: dict) -> Book:
"""创建书籍"""
book = Book(**book_data)
self.session.add(book)
# 先 flush 拿到自增 ID，commit 由依赖项统一处理
await self.session.flush() # 刷新获取自增 id
# 仅需 flush 即可获取自增字段，refresh 可省略（commit 后自动同步）
return book
async def get_by_id(self, book_id: int) -> Optional[Book]:
"""根据 ID 查询书籍"""
result = await self.session.execute(
select(Book).where(Book.id == book_id)
)
return result.scalars().first()
async def get_all(self) -> list[Book]:
"""查询所有书籍"""
result = await self.session.execute(select(Book))
return list(result.scalars().all())
async def update(self, book_id: int, update_data: dict) -> Optional[Book]:
"""更新书籍"""
book = await self.get_by_id(book_id)
if not book:
return None
for key, value in update_data.items():
if value is not None:
setattr(book, key, value)
await self.session.flush()
await self.session.refresh(book)
return book
async def delete(self, book_id: int) -> bool:

---

<!-- p.20 -->

routers/book_router.py（路由层）
定义书籍的 CRUD 接口，通过依赖注入获取 DAO 实例：
"""删除书籍"""
book = await self.get_by_id(book_id)
if not book:
return False
await self.session.delete(book)
return True
"""
书籍路由模块
定义书籍的增删改查接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from config.database import get_database
from dao.book_dao import BookDAO
from schemas.schemas import BookCreate, BookUpdate, BookResponse
router = APIRouter(prefix="/books", tags=["书籍管理"])
def get_book_dao(session: AsyncSession = Depends(get_database)) -> BookDAO:
"""获取 BookDAO 实例"""
return BookDAO(session)
@router.post("/", response_model=BookResponse,
status_code=status.HTTP_201_CREATED)
async def create_book(
book_data: BookCreate,
dao: BookDAO = Depends(get_book_dao)
):
"""创建书籍"""
book = await dao.create(book_data.model_dump())
return book
@router.get("/", response_model=List[BookResponse])
async def get_books(dao: BookDAO = Depends(get_book_dao)):
"""查询所有书籍"""
books = await dao.get_all()
return books
@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
book_id: int,
dao: BookDAO = Depends(get_book_dao)
):

---

<!-- p.21 -->

dependencies/init.py（依赖注入说明）
"""根据 ID 查询书籍"""
book = await dao.get_by_id(book_id)
if not book:
raise HTTPException(
status_code=status.HTTP_404_NOT_FOUND,
detail=f"书籍 id={book_id} 不存在"
)
return book
@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
book_id: int,
book_data: BookUpdate,
dao: BookDAO = Depends(get_book_dao)
):
"""更新书籍"""
book = await dao.update(book_id, book_data.model_dump(exclude_unset=True))
if not book:
raise HTTPException(
status_code=status.HTTP_404_NOT_FOUND,
detail=f"书籍 id={book_id} 不存在"
)
return book
@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
book_id: int,
dao: BookDAO = Depends(get_book_dao)
):
"""删除书籍"""
success = await dao.delete(book_id)
if not success:
raise HTTPException(
status_code=status.HTTP_404_NOT_FOUND,
detail=f"书籍 id={book_id} 不存在"
)
"""
依赖项模块
提供 FastAPI 依赖注入函数
"""
# 注意：get_database 在 config.database 中定义
# 其他模块请直接从 config.database 导入

---

<!-- p.22 -->

main.py（应用入口）
使用 lifespan 方式管理应用生命周期，完成启动和关闭时的数据库初始化和清理工作：
"""
FastAPI 应用入口
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from config.database import async_engine
from models.models import Base
from routers import book_router
# 定义启动和关闭事件
@asynccontextmanager
async def lifespan(app: FastAPI):
"""应用生命周期管理"""
# 启动时：创建数据库表
async with async_engine.begin() as conn:
await conn.run_sync(Base.metadata.create_all)
print("✅ 数据库表创建成功")
yield # 应用运行中
# 关闭时：销毁数据库引擎
await async_engine.dispose()
print("✅ 数据库连接已关闭")
# 创建 FastAPI 应用
app = FastAPI(
title="FastAPI + SQLAlchemy 连接 MySQL 示例",
description="演示 FastAPI 与 SQLAlchemy 的异步集成",
version="1.0.0",
lifespan=lifespan,
)
# 注册路由
app.include_router(book_router)
@app.get("/", tags=["首页"])
async def root():
"""首页"""
return {"message": "FastAPI 连接 MySQL 数据库成功！"}
if __name__ == "__main__":
import uvicorn
uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

---

<!-- p.23 -->

层级 目录/文件 职责
路由层（Route） routers/ 接收 HTTP 请求，调用 DAO，返回响应
数据访问层（DAO） dao/ 封装 SQL 操作，负责增删改查
模型层（Model） models/ 定义数据库表结构（ORM）
数据库准备
在使用本项目前，需要先在 MySQL 中创建对应的数据库：
依赖安装
启动项目
服务启动后访问 http://127.0.0.1:8000/docs 打开 Swagger UI 进行接口测试。
架构说明
三层架构
依赖注入流程
get_database() ：通过 FastAPI Depends 注入，管理会话生命周期（自动提交/回滚/关闭）。
get_book_dao() ：通过 FastAPI Depends 注入，创建 BookDAO 实例并传入会话。
CREATE DATABASE fastapi_first DEFAULT CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci;
pip install fastapi uvicorn sqlalchemy aiomysql pydantic
python main.py
请求 → get_database() → AsyncSession → BookDAO → 数据库
