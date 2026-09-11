# FastAPI的三层架构

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\24FastAPI的三层架构\FastAPI的三层架构.pdf`
> **页数**：13（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 13,562 字符，其中汉字 1,995 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

层次 职责 FastAPI 中的实现
表示层 处理用户请求和响应 路由（API 端点）
业务逻辑层 处理业务规则和逻辑 Service 层
数据访问层 数据的增删改查 DAO / Repository 层
FastAPI 三层架构
三层架构将应用分为表示层（API 路由）、业务逻辑层（Service）、数据访问层（DAO），各层职责单
一，层次间通过接口通信，便于维护、扩展和测试。
架构组成
项目结构
数据访问层（DAO）
DAO 层只负责与数据库交互，封装所有 CRUD 操作，是整个架构中最接近数据库的一层。
用户请求 → 表示层（路由）→ 业务逻辑层（Service）→ 数据访问层（DAO）→ 数据库
↓ ↓
返回响应 CRUD 操作
project/
├── main.py # 表示层：FastAPI 路由
├── models.py # 数据模型：SQLAlchemy ORM 实体
├── schemas.py # Pydantic 请求/响应模型
├── database.py # 数据库连接配置
├── dao/ # 数据访问层
│ └── user_dao.py
├── service/ # 业务逻辑层
│ └── user_service.py
└── tests/ # 测试
└── test_user.py
# dao/user_dao.py
from sqlalchemy.orm import Session
from models import User
class UserDAO:
def __init__(self, db: Session):
# 将数据库会话注入到 DAO 中，所有操作都在同一个会话中执行
self.db = db
def create(self, name: str, email: str, password: str) -> User:
# 构建用户对象（此时还在内存中，未写入数据库）
user = User(name=name, email=email, password=password)

---

<!-- p.2 -->

方法 作用
db.add(obj) 将对象加入会话，后续 commit 时写入数据库
db.commit() 提交事务，将所有更改（增/删/改）一次性写入数据库
db.refresh(obj)
从数据库重新读取对象，同步数据库生成的字段（如自增 ID、时间
戳）
db.query(Model) 构建查询起点
filter(...).first() 添加过滤条件，返回第一条记录，不存在则返回 None
db.delete(obj) 将对象标记为删除，commit 后生效
核心方法说明：
业务逻辑层（Service）
Service 层处理业务规则，调用 DAO 层，是业务逻辑的集中地。DAO 只做 CRUD，Service 做判断和流
程控制。
self.db.add(user) # 将对象标记为"待添加"，相当于 INSERT 准备阶段
self.db.commit() # 提交事务，将所有更改写入数据库
self.db.refresh(user) # 从数据库重新加载对象，获取自增 ID 等数据库生成的值
return user
def get_by_id(self, user_id: int) -> User | None:
# query() 构建查询，filter() 添加条件，first() 返回第一条结果或 None
return self.db.query(User).filter(User.id == user_id).first()
def get_by_email(self, email: str) -> User | None:
return self.db.query(User).filter(User.email == email).first()
def update(self, user: User) -> User:
# user 对象已修改（修改了属性），commit() 保存更改，refresh() 获取最新数据
self.db.commit()
self.db.refresh(user)
return user
def delete(self, user_id: int) -> User | None:
user = self.get_by_id(user_id) # 先查询是否存在
if user:
self.db.delete(user) # 标记为"待删除"
self.db.commit() # 提交事务执行删除
return user # 返回被删除的用户（或 None）
# service/user_service.py
from passlib.context import CryptContext
from dao.user_dao import UserDAO
from models import User
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

---

<!-- p.3 -->

业务规则设计思路：
class UserService:
def __init__(self, user_dao: UserDAO):
# 依赖注入：Service 不自己创建 DAO，由外部传入
self.user_dao = user_dao
def create_user(self, name: str, email: str, password: str) -> User:
# 业务规则：邮箱必须唯一，先查再创建
existing = self.user_dao.get_by_email(email)
if existing:
raise ValueError("邮箱已被注册") # 业务异常，不是系统错误
# 业务规则通过，调用 DAO 执行数据持久化
# 密码哈希
hashed_password = pwd_context.hash(password)
user = self.user_dao.create(name, email, hashed_password)
return user
def get_user(self, user_id: int) -> User:
user = self.user_dao.get_by_id(user_id)
if not user:
raise ValueError("用户不存在") # 找不到就抛异常，由上层决定如何响应
return user
def update_user(self, user_id: int, name: str, email: str) -> User:
# 业务规则：邮箱唯一性（排除自己）
existing = self.user_dao.get_by_email(email)
if existing and existing.id != user_id:
raise ValueError("邮箱已被其他用户使用")
user = self.user_dao.get_by_id(user_id)
if not user:
raise ValueError("用户不存在")
# 直接修改对象属性，ORM 会追踪变化，commit 时写入
user.name = name
user.email = email
return self.user_dao.update(user)
def delete_user(self, user_id: int) -> None:
user = self.user_dao.get_by_id(user_id)
if not user:
raise ValueError("用户不存在")
self.user_dao.delete(user_id)

---

<!-- p.4 -->

场景 规则 为什么
创建用
户
先查邮箱是否存在
避免重复注册，数据库 unique 约束是兜底，前端校验更友
好
获取用
户
查不到抛异常
让 API 层能区分"找不到"和"其他错误"，返回不同 HTTP 状
态码
更新用
户
邮箱唯一性要排除自
己
防止把自己的邮箱改成别人的邮箱
删除用
户
先检查存在性 避免静默失败，也便于区分"删了"和"本来就没有"
表示层（API 路由）
表示层负责接收 HTTP 请求、参数校验、调用 Service、构造响应。这一层不应该有业务逻辑。
数据模型定义
# models.py —— SQLAlchemy ORM 实体，对应数据库中的表
from sqlalchemy import Column, Integer, String
from database import Base
class User(Base):
__tablename__ = "users" # 表名
id = Column(Integer, primary_key=True, index=True) # 主键，自动递增
name = Column(String, nullable=False) # 必填字段
email = Column(String, unique=True, nullable=False, index=True) # 唯一索引，加
速查询
password = Column(String, nullable=False) # 存储哈希后的密码
# schemas.py —— Pydantic 模型，用于 API 的请求校验和响应序列化
from pydantic import BaseModel, EmailStr
class UserCreate(BaseModel):
"""创建用户的请求体"""
name: str # 普通字符串
email: EmailStr # 自动校验邮箱格式
password: str
class UserResponse(BaseModel):
"""用户响应模型，控制返回给客户端的字段"""
id: int
name: str
email: str
# 注意：没有 password 字段 —— API 绝不会返回密码
class Config:
from_attributes = True # 允许从 ORM 对象（SQLAlchemy）读取属性，而不只是字典

---

<!-- p.5 -->

API 路由实现
# database.py —— 数据库连接配置
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
# connect_args={"check_same_thread": False} 是 SQLite 特有设置，允许多线程访问同一文件
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=
{"check_same_thread": False})
# SessionLocal 配置说明：
# - autocommit=False：手动调用 commit() 才提交事务
# - autoflush=False：查询时不自动触发 flush（将内存中的更改写入数据库但不提交），避免未预期
的写入
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base() # 所有 ORM 模型的基类，用于生成表结构
# main.py —— FastAPI 应用入口
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from dao.user_dao import UserDAO
from service.user_service import UserService
from schemas import UserCreate, UserResponse
Base.metadata.create_all(bind=engine) # 启动时自动创建所有表（仅开发环境建议这样用）
app = FastAPI(title="三层架构示例")
# —— 数据库会话依赖（会话即用即关）——
def get_db():
db = SessionLocal() # 创建会话
try:
yield db # 将会话提供给路由函数使用
finally:
db.close() # 请求结束后自动关闭会话，释放连接
# —— 依赖注入工厂函数（每一层都通过 Depends 注入）——
def get_user_dao(db: Session = Depends(get_db)) -> UserDAO:
return UserDAO(db)
def get_user_service(dao: UserDAO = Depends(get_user_dao)) -> UserService:
return UserService(dao)
# —— CRUD 路由 ——
@app.post("/users", response_model=UserResponse,
status_code=status.HTTP_201_CREATED)

---

<!-- p.6 -->

注意：代码中异常的抛出只是举个简单的例子，实际业务需要按照可能出现的异常去抛出处理。
依赖注入链：
async def create_user(user_in: UserCreate, service: UserService =
Depends(get_user_service)):
"""创建用户：参数校验 → 调用 Service → 响应"""
try:
user = service.create_user(user_in.name, user_in.email,
user_in.password)
return user
except ValueError as e:
raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
detail=str(e))
@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, service: UserService =
Depends(get_user_service)):
try:
return service.get_user(user_id)
except ValueError as e:
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
detail=str(e))
@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_in: UserCreate, service: UserService =
Depends(get_user_service)):
try:
return service.update_user(user_id, user_in.name, user_in.email)
except ValueError as e:
raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
detail=str(e))
@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, service: UserService =
Depends(get_user_service)):
try:
service.delete_user(user_id)
except ValueError as e:
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
detail=str(e))

---

<!-- p.7 -->

组件 作用
Depends(get_db)
FastAPI 依赖注入系统，自动创建和关闭数据库会
话，无需手动管理连接
Base.metadata.create_all()
启动时根据 ORM 模型自动创建数据库表，开发环
境很方便
response_model=UserResponse
自动序列化响应对象，且过滤掉 UserResponse
中未定义的字段（如 password）
status_code=status.HTTP_201_CREATED 返回正确的 HTTP 状态码，符合 RESTful 规范
service: UserService = Depends(...)
整个依赖链通过一层层 Depends 自动串联，路由
代码保持简洁
HTTP_400 / HTTP_404
Service 抛出的 ValueError 在路由层捕获，转换
为对应的 HTTP 状态码
关键组件说明：
异步版本
对于高并发场景，使用异步数据库操作能显著提升性能，特别是在有大量 I/O 等待的场景下（如 Web 服
务）。
数据库配置：
请求进入
↓
get_db() 创建 Session
↓
get_user_dao(db) → UserDAO(db)
↓
get_user_service(dao) → UserService(dao)
↓
路由函数使用 service
↓
请求结束 → 依赖的 db.close() 自动执行
# database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession,
async_sessionmaker
# 异步引擎
ASYNC_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(
async_engine, class_=AsyncSession, expire_on_commit=False
)
# 异步依赖
async def get_async_db():
db = AsyncSessionLocal()

---

<!-- p.8 -->

dao层：
同步版 vs 异步版对比：
try:
yield db
finally:
await db.close()
# dao/user_dao.py（异步版本）
from sqlalchemy import select
from models import User
class UserDAO:
def __init__(self, db: AsyncSession):
self.db = db
async def create(self, name: str, email: str, password: str) -> User:
user = User(name=name, email=email, password=password)
self.db.add(user)
await self.db.commit() # 异步提交，不会阻塞事件循环
await self.db.refresh(user)
return user
async def update(self, user: User) -> User:
await self.db.commit()
await self.db.refresh(user)
return user
async def delete(self, user_id: int) -> User | None:
user = await self.get_by_id(user_id)
if user:
await self.db.delete(user)
await self.db.commit()
return user
async def get_by_id(self, user_id: int) -> User | None:
# 异步查询必须使用 select() 语句，不能用 query()
result = await self.db.execute(select(User).where(User.id == user_id))
return result.scalar_one_or_none() # 获取结果或 None
async def get_by_email(self, email: str) -> User | None:
result = await self.db.execute(select(User).where(User.email == email))
return result.scalar_one_or_none()

---

<!-- p.9 -->

操作 同步版 异步版
提交
事务
self.db.commit() await self.db.commit()
查询 self.db.query(User).filter(...).first()
await
self.db.execute(select(User).where(...))
获取
结果
直接返回 result.scalar_one_or_none()
适用
场景
简单脚本、CPU 密集型场景、低 I/O 等待的 Web
服务
I/O 密集型场景（如大量数据库查询 / 外部 API 调用）、
高并发 Web 服务
性能 受 GIL 限制，多线程提升有限 充分利用异步 I/O，单进程可处理大量并发连接
单元测试
三层架构的优势之一是各层可以独立测试，通过 Mock 隔离外部依赖，无需连接真实数据库。
Service 层测试
# tests/test_user_service.py
import pytest
from unittest.mock import Mock
from service.user_service import UserService
from models import User
@pytest.fixture
def mock_dao():
"""模拟 DAO，所有方法都是 Mock 对象"""
return Mock()
@pytest.fixture
def user_service(mock_dao):
"""注入 Mock DAO 创建 Service 实例"""
return UserService(mock_dao)
def test_create_user_success(user_service, mock_dao):
"""正常创建用户：邮箱不存在 → 创建成功"""
# 设置 Mock：get_by_email 返回 None（表示邮箱未注册）
mock_dao.get_by_email.return_value = None
# 设置 Mock：create 返回一个用户对象
mock_dao.create.return_value = User(id=1, name="Alice",
email="alice@example.com", password="pass")
# 执行
user = user_service.create_user("Alice", "alice@example.com", "pass")
# 断言：验证调用顺序和参数
mock_dao.get_by_email.assert_called_once_with("alice@example.com") # 确认先查
了邮箱
mock_dao.create.assert_called_once_with("Alice", "alice@example.com",
"pass") # 确认创建时参数正确
assert user.id == 1

---

<!-- p.10 -->

API 层测试
assert user.name == "Alice"
def test_create_user_email_exists(user_service, mock_dao):
"""重复邮箱：应抛出 ValueError，且不调用 create"""
# 设置 Mock：邮箱已被占用
mock_dao.get_by_email.return_value = User(id=1, name="Bob",
email="bob@example.com", password="pass")
# 断言：抛出业务异常
with pytest.raises(ValueError, match="邮箱已被注册"):
user_service.create_user("Bob", "bob@example.com", "pass")
# 关键断言：确保 DAO 的 create 方法从未被调用
mock_dao.create.assert_not_called()
def test_get_user_not_found(user_service, mock_dao):
"""用户不存在：应抛出 ValueError"""
mock_dao.get_by_id.return_value = None
with pytest.raises(ValueError, match="用户不存在"):
user_service.get_user(999)
# tests/test_user_api.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from main import app, get_db
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=
{"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False,
bind=engine)
def override_get_db():
"""覆盖依赖：使用测试数据库而非开发数据库"""
db = TestingSessionLocal()
try:
yield db
finally:
db.close()
app.dependency_overrides[get_db] = override_get_db
@pytest.fixture(autouse=True)
def setup_database():

---

<!-- p.11 -->

总结
"""每个测试前创建表，测试后清理"""
Base.metadata.create_all(bind=engine)
yield
Base.metadata.drop_all(bind=engine)
client = TestClient(app)
def test_create_and_get_user():
"""完整流程：创建用户 → 获取用户"""
# 创建用户
response = client.post("/users", json={"name": "Alice", "email":
"alice@example.com", "password": "pass"})
assert response.status_code == 201
user_data = response.json()
assert user_data["name"] == "Alice"
assert user_data["email"] == "alice@example.com"
assert "password" not in user_data # 敏感字段被 schemas 过滤，响应中不存在
# 获取用户
user_id = user_data["id"]
response = client.get(f"/users/{user_id}")
assert response.status_code == 200
assert response.json()["name"] == "Alice"
def test_create_user_duplicate_email():
"""重复邮箱：返回 400"""
client.post("/users", json={"name": "Alice", "email": "alice@example.com",
"password": "pass"})
response = client.post("/users", json={"name": "Bob", "email":
"alice@example.com", "password": "pass"})
assert response.status_code == 400
assert "邮箱已被注册" in response.json()["detail"]
def test_get_user_not_found():
"""用户不存在：返回 404"""
response = client.get("/users/9999")
assert response.status_code == 404
assert "用户不存在" in response.json()["detail"]
三层架构核心要点：
DAO 层 → 只做 CRUD，不包含任何业务逻辑，与数据库解耦
Service 层 → 处理业务规则（校验、权限、流程），调用 DAO，是业务核心
API 层 → 接收请求、参数校验、调用 Service、返回响应，不含业务逻辑
依赖注入 → 通过 Depends() 自动串联各层，代码简洁，单元测试友好
测试 → 各层独立测试，DAO/Service 用 Mock 隔离，API 用 TestClient 端到端测试

---

<!-- p.12 -->

各层职责边界总结：
┌─────────────────────────────────────────────┐
│ 表示层（路由） │
│ · 参数校验（Pydantic） │
│ · HTTP 状态码处理 │
│ · 调用 Service，捕获异常 │
│ · 绝对不写业务逻辑 │
└─────────────────┬───────────────────────────┘
│
▼
┌─────────────────────────────────────────────┐
│ 业务逻辑层（Service） │
│ · 业务规则校验（唯一性、存在性、权限） │
│ · 调用顺序控制 │
│ · 抛 ValueError 表示业务异常 │
└─────────────────┬───────────────────────────┘
│
▼
┌─────────────────────────────────────────────┐
│ 数据访问层（DAO） │
│ · 增删改查 │
│ · 事务管理 │
│ · 不做任何业务判断 │
└─────────────────────────────────────────────┘
