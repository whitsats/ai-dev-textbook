# FastAPI中如何进行单元测试

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\23FastAPI中如何进行单元测试\FastAPI中如何进行单元测试.pdf`
> **页数**：16（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 13,176 字符，其中汉字 1,817 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

对比项 没有测试 有测试
修改代码 提心吊胆，怕改坏 运行测试，立刻知道结果
重构代码 不敢动，怕出问题 放心重构，测试会报错
上线部署 赌运气 有信心
FastAPI 中如何进行单元测试
单元测试是保证代码质量的重要手段。本节介绍 FastAPI 项目中如何编写、运行测试。
什么是单元测试？
单元测试是对代码的最小功能单元进行验证。想象工厂质检员——每生产一个零件都要检测是否合格。
单元测试就是代码的质检员。
快速开始
安装测试依赖
最简单的测试
运行测试：
pip install pytest pytest-asyncio httpx
# tests/test_example.py
from fastapi.testclient import TestClient
from fastapi import FastAPI
# 创建测试用的 app
app = FastAPI()
@app.get("/hello")
async def hello():
return {"message": "Hello, World!"}
# 创建测试客户端（它会帮我们发请求）
client = TestClient(app)
def test_hello():
"""测试 hello 接口返回正确的内容"""
response = client.get("/hello")
assert response.status_code == 200 # 检查状态码
assert response.json() == {"message": "Hello, World!"} # 检查响应体

---

<!-- p.2 -->

输出示例：
-v 参数显示详细信息，可以看到每个测试的名称和结果。
TestClient 详解
TestClient 是 FastAPI 自带的测试工具，模拟浏览器或前端发请求。
工作原理
支持的请求方法
检查响应内容
pytest tests/test_example.py -v
tests/test_example.py::test_hello PASSED
# TestClient 做了三件事：
# 1. 构造符合 HTTP 规范的请求参数（模拟 GET /hello）；
# 2. 直接调用 FastAPI 应用的路由匹配和处理逻辑（不启动真实 HTTP 服务器）；
# 3. 将处理结果封装为标准的响应对象（包含状态码、响应体、响应头等）。
from fastapi.testclient import TestClient
client = TestClient(app)
response = client.get("/items/1") # 模拟 GET 请求
# 等价于：curl http://localhost:8000/items/1
# GET 请求（查询数据）
client.get("/items")
# POST 请求（创建数据）
client.post("/items", json={"name": "电脑"})
# PUT 请求（更新全部数据）
client.put("/items/1", json={"name": "新电脑", "price": 5999})
# PATCH 请求（部分更新）
client.patch("/items/1", json={"price": 4999})
# DELETE 请求（删除数据）
client.delete("/items/1")
def test_item_response():
response = client.get("/items/1")
# 1. 检查状态码
assert response.status_code == 200
# 2. 检查 JSON 响应体

---

<!-- p.3 -->

测试带参数的场景
测试路径参数
测试查询参数
data = response.json()
assert data["id"] == 1
assert data["name"] == "电脑"
assert "price" in data # 字段存在即可，不关心值
# 3. 检查响应头
assert response.headers["content-type"] == "application/json"
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
app = FastAPI()
items = {
1: {"id": 1, "name": "电脑", "price": 5999},
2: {"id": 2, "name": "手机", "price": 3999}
}
@app.get("/items/{item_id}")
async def get_item(item_id: int):
if item_id not in items:
raise HTTPException(status_code=404, detail="商品不存在")
return items[item_id]
client = TestClient(app)
def test_get_exist_item():
"""测试获取已存在的商品"""
response = client.get("/items/1")
assert response.status_code == 200
assert response.json()["name"] == "电脑"
def test_get_not_exist_item():
"""测试获取不存在的商品"""
response = client.get("/items/999")
assert response.status_code == 404
assert "不存在" in response.json()["detail"]
from typing import Optional
app = FastAPI()
products = [

---

<!-- p.4 -->

测试请求体（POST/PUT）
{"id": 1, "name": "电脑", "category": "电子产品", "price": 5999},
{"id": 2, "name": "水杯", "category": "生活用品", "price": 29},
{"id": 3, "name": "键盘", "category": "电子产品", "price": 299},
]
@app.get("/products")
async def list_products(
category: Optional[str] = None,
min_price: Optional[int] = None
):
result = products
# 按分类过滤
if category:
result = [p for p in result if p["category"] == category]
# 按最低价过滤
if min_price is not None:
result = [p for p in result if p["price"] >= min_price]
return result
client = TestClient(app)
def test_filter_by_category():
"""测试按分类过滤"""
response = client.get("/products?category=电子产品")
data = response.json()
assert len(data) == 2
assert all(p["category"] == "电子产品" for p in data)
def test_filter_by_price():
"""测试按价格过滤"""
response = client.get("/products?min_price=100")
data = response.json()
assert len(data) == 2 # 电脑 5999 和键盘 299
assert all(p["price"] >= 100 for p in data)
def test_no_filter():
"""测试不过滤，返回全部"""
response = client.get("/products")
assert len(response.json()) == 3
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.testclient import TestClient
app = FastAPI()

---

<!-- p.5 -->

使用 pytest fixtures
Fixture 是 pytest 的核心功能，用于共享测试数据和setup/teardown逻辑。
class ItemCreate(BaseModel):
name: str
price: float
class Item(BaseModel):
id: int
name: str
price: float
@pytest.fixture
def reset_item_db():
"""每个测试重置数据和 ID"""
app.state.items_db = []
app.state.next_id = 1
yield
@app.post("/items", response_model=Item)
async def create_item(item: ItemCreate):
# 从 app.state 读取，而非全局变量
new_item = Item(
id=app.state.next_id,
**item.model_dump()
)
app.state.items_db.append(new_item)
app.state.next_id += 1
return new_item
client = TestClient(app)
def test_create_item():
"""测试创建商品"""
response = client.post("/items", json={"name": "耳机", "price": 199.5})
assert response.status_code == 200
data = response.json()
assert data["name"] == "耳机"
assert data["price"] == 199.5
assert "id" in data # 自动生成了 ID
def test_create_item_validation_error():
"""测试参数验证失败"""
response = client.post("/items", json={"name": "耳机"}) # 缺少 price
assert response.status_code == 422 # FastAPI 自动返回 422

---

<!-- p.6 -->

基本 fixture
Fixture 命名最佳实践
小写+下划线命名（如 client / test_items / db_session ），避免驼峰或缩写；
语义化命名：让读者一眼看懂用途（如 reset_item_db 而非 fix_db ）；
避免重复命名：不同作用的 fixture 不要重名（如区分 db_engine （会话级）和 db_session
（函数级））。
带数据的 fixture
# tests/conftest.py
# conftest.py 是 pytest 的配置文件，放在 tests/ 目录下
# 里面的 fixture 可以被所有测试文件使用
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from main import app # 导入你的 FastAPI app
@pytest.fixture
def client():
"""每个测试都会获得一个新的 TestClient"""
return TestClient(app)
# tests/test_items.py
# 现在可以省略创建 app 和 client 的代码
def test_get_item(client):
response = client.get("/items/1")
assert response.status_code == 200
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from main import app
# 创建测试用的数据（不影响真实数据库）
@pytest.fixture
def test_items():
return [
{"id": 1, "name": "电脑", "price": 5999},
{"id": 2, "name": "手机", "price": 3999},
]
@pytest.fixture
def client(test_items):
"""创建客户端并预先插入测试数据"""
# 模拟数据插入（补充：接口需读取 app.state.test_items）

---

<!-- p.7 -->

scope 值 含义 使用场景
function （默认） 每个测试函数执行一次 大多数情况
class 每个测试类执行一次 一组测试共享数据
module 每个模块（文件）执行一次 模块级别的共享资源
session 整个测试过程只执行一次 数据库引擎等昂贵资源
Session 级 fixture（整个测试过程只创建一次）
测试依赖注入（Mock 外部依赖）
测试时需要隔离外部依赖（如数据库、第三方 API），用 Mock 替代。
使用 app.dependency_overrides
app.state.test_items = test_items
# 补充：给 app 临时注册接口（示例）
@app.get("/test-items")
async def get_test_items():
return app.state.test_items
return TestClient(app)
# tests/conftest.py
import pytest
@pytest.fixture(scope="session")
def db_engine():
"""整个测试会话只创建一个数据库引擎"""
from sqlalchemy import create_engine
engine = create_engine("sqlite:///:memory:")
# 创建表...
yield engine
# 清理工作...
@pytest.fixture(scope="function")
def db_session(db_engine):
"""每个测试函数获得一个新的数据库会话"""
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=db_engine)
session = Session()
yield session
session.rollback() # 测试结束后回滚，保持数据干净
session.close()
# main.py
from fastapi import FastAPI, Depends
from pydantic import BaseModel

---

<!-- p.8 -->

app = FastAPI()
# 定义数据库操作的依赖（接口）
def get_db():
"""真实环境：连接真实数据库"""
db = Database()
try:
yield db
finally:
db.close()
class Item(BaseModel):
name: str
price: float
@app.post("/items")
async def create_item(item: Item, db=Depends(get_db)):
return db.create_item(item)
@app.get("/items")
async def list_items(db=Depends(get_db)):
return db.list_items()
# tests/test_items.py
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app, get_db
# 创建 Mock 数据库
def mock_db():
mock = MagicMock()
mock.list_items.return_value = [
{"id": 1, "name": "电脑", "price": 5999}
]
mock.create_item.return_value = {"id": 2, "name": "手机", "price": 3999}
return mock
def test_list_items():
"""测试列表接口，使用 Mock 数据库"""
app.dependency_overrides[get_db] = mock_db
client = TestClient(app)
response = client.get("/items")
assert response.status_code == 200
assert len(response.json()) == 1
# 清理：移除 Mock，恢复原样

---

<!-- p.9 -->

更好的方式：使用 fixture 自动清理
优势：无需手动调用 app.dependency_overrides.clear() ，避免漏清理导致测试污染，同时减少重
复代码。
app.dependency_overrides.clear()
def test_create_item():
"""测试创建接口"""
app.dependency_overrides[get_db] = mock_db
client = TestClient(app)
response = client.post("/items", json={"name": "手机", "price": 3999})
assert response.status_code == 200
assert response.json()["id"] == 2
app.dependency_overrides.clear()
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from main import app, get_db
@pytest.fixture
def client():
return TestClient(app)
@pytest.fixture
def mock_db():
"""创建 Mock 数据库"""
mock = MagicMock()
mock.list_items.return_value = []
return mock
@pytest.fixture
def override_dependencies(mock_db, client):
"""自动注入 Mock 并在测试后清理"""
app.dependency_overrides[get_db] = lambda: mock_db
yield mock_db
app.dependency_overrides.clear() # 测试结束后清理

---

<!-- p.10 -->

测试异步接口
如果使用 async def 定义的接口，有两种测试方式。
方式一：使用 pytest-asyncio （推荐）
方式二：使用 TestClient（同步方式）
推荐：
单接口功能测试：使用 TestClient （同步调用，代码更简洁）；
# tests/test_items.py
def test_list_items(client, override_dependencies):
"""直接使用注入的 Mock"""
mock_db = override_dependencies
mock_db.list_items.return_value = [
{"id": 1, "name": "电脑", "price": 5999}
]
response = client.get("/items")
assert response.status_code == 200
pip install pytest-asyncio
# tests/conftest.py
import pytest
# 启用 asyncio 模式
pytest_plugins = ('pytest_asyncio',)
# tests/test_async.py
import pytest
from httpx import AsyncClient
from main import app
@pytest.mark.asyncio
async def test_async_endpoint():
"""异步测试：使用 AsyncClient"""
async with AsyncClient(app=app, base_url="http://test") as ac:
response = await ac.get("/items")
assert response.status_code == 200
# TestClient 内部会自动处理异步，可以不用 async/await
def test_sync_call_async():
client = TestClient(app)
response = client.get("/items")
assert response.status_code == 200

---

<!-- p.11 -->

并发/异步流程测试（如异步数据库操作、多请求并行）：使用 AsyncClient （真正的异步调用，
能覆盖并发场景）；
注意： TestClient 内部会通过 asyncio.run 同步执行异步接口，无法测试并发逻辑，仅适合单
接口功能验证。
测试异常处理
测试 HTTPException
测试自定义异常处理器
from fastapi import HTTPException
app = FastAPI()
FAKE_DB = {1: "alice", 2: "bob"}
@app.get("/users/{user_id}")
async def get_user(user_id: int):
if user_id not in FAKE_DB:
raise HTTPException(status_code=404, detail="用户不存在")
return {"user_id": user_id, "name": FAKE_DB[user_id]}
client = TestClient(app)
def test_user_not_found():
"""测试用户不存在时返回 404"""
response = client.get("/users/999")
assert response.status_code == 404
assert "不存在" in response.json()["detail"]
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
app = FastAPI()
# 定义自定义异常
class AppError(Exception):
def __init__(self, message: str, code: str):
self.message = message
self.code = code
# 注册全局异常处理器
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
return JSONResponse(
status_code=400,
content={

---

<!-- p.12 -->

测试组织结构
推荐的项目结构：
测试命名规范：
"error": exc.code,
"message": exc.message,
"path": str(request.url)
}
)
@app.get("/error")
async def trigger_error():
raise AppError(message="业务错误", code="BIZ_ERROR")
client = TestClient(app)
def test_custom_error():
"""测试自定义异常被正确处理"""
response = client.get("/error")
assert response.status_code == 400
data = response.json()
assert data["error"] == "BIZ_ERROR"
assert data["message"] == "业务错误"
project/
├── main.py # FastAPI 入口
├── models.py # 数据模型
├── schemas.py # Pydantic 模型
├── routers/ # 路由
│ ├── __init__.py
│ ├── items.py
│ └── users.py
├── services/ # 业务逻辑
│ ├── __init__.py
│ ├── item_service.py
│ └── user_service.py
├── tests/ # 测试目录
│ ├── __init__.py
│ ├── conftest.py # pytest 配置和共享 fixtures
│ ├── test_items.py # items 路由测试
│ └── test_users.py # users 路由测试

---

<!-- p.13 -->

运行测试
基本命令
pytest.ini 配置
# 文件名：test_xxx.py
# 函数名：test_xxx_yyy()
def test_get_item_success():
"""描述：获取商品成功"""
pass
def test_get_item_not_found():
"""描述：获取不存在的商品"""
pass
# 运行所有测试
pytest
# 运行指定文件
pytest tests/test_items.py
# 运行指定测试函数
pytest tests/test_items.py::test_get_item_success
# 失败的测试重试 3 次（解决偶发失败）
pytest --reruns 3 --reruns-delay 1
# 显示详细信息
pytest -v
# 显示打印内容（调试用）
pytest -s
# 显示失败的具体位置
pytest -vv
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short

---

<!-- p.14 -->

测试覆盖率
常见问题
问题 1：测试通过但实际运行失败
原因：测试环境和生产环境不一致（如 Mock 过度）
解决：保持测试逻辑与真实逻辑一致，定期运行集成测试
问题 2：测试数据库状态污染
原因：测试修改了数据，影响后续测试
解决：每个测试前重置数据库，或使用事务回滚
问题 3：异步测试报错
报错： Scope mismatch in config
解决：确保 pytest.ini 中配置了 asyncio_mode = auto
问题 4：fixture 之间传递数据
pip install pytest-cov
# 生成覆盖率报告（排除 tests 目录，只统计业务代码）
pytest --cov=main --cov=routers --cov=services --cov-exclude=tests/ --cov-
report=html
# 设置覆盖率阈值（低于 80% 则测试失败）
pytest --cov=main --cov-fail-under=80
# 生成简洁的终端报告（无需打开 HTML）
pytest --cov=main --cov-report=term-missing
@pytest.fixture
def clean_db():
"""每个测试前清空数据库"""
db.delete_all() # 清空所有数据
yield db
[pytest]
asyncio_mode = auto

---

<!-- p.15 -->

测试最佳实践
1. 每个测试只验证一件事：保持测试简洁，失败时能快速定位问题
2. 测试名称描述清晰： test_create_user_success 比 test_1 好
3. Arrange-Act-Assert 模式：
4. 避免重复创建 app：在 fixture 中创建一次，所有测试复用
5. Mock 外部依赖：数据库、API 等使用 Mock，不依赖外部环境
6. 测试边界情况：不仅要测正常流程，还要测异常流程
@pytest.fixture
def user_id():
"""创建用户，返回 ID"""
# 创建用户...
return created_id
def test_get_user(user_id):
"""使用上一个 fixture 创建的用户 ID"""
response = client.get(f"/users/{user_id}")
assert response.status_code == 200
def test_create_item_success():
# Arrange：准备数据
item_data = {"name": "电脑", "price": 5999}
# Act：执行操作
response = client.post("/items", json=item_data)
# Assert：验证结果
assert response.status_code == 200
assert response.json()["name"] == "电脑"
def test_edge_cases():
"""边界情况测试"""
# 空列表
assert client.get("/items").json() == []
# 负数 ID
assert client.get("/items/-1").status_code == 404
# 超大数值
assert client.get("/items/999999999").status_code == 404
