# FastAPI的Redis缓存

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\18FastAPI的Redis缓存\FastAPI的Redis缓存.pdf`
> **页数**：11（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 7,894 字符，其中汉字 1,878 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

存储 读取速度 说明
传统数据库 10-50 毫秒 从磁盘读取
Redis 0.1-1 毫秒 从内存读取，快 50-100 倍
FastAPI 的 Redis 缓存
本节介绍如何在 FastAPI 中使用 Redis 做缓存。
Redis 为何重要？
Redis 是一个"超级快的内存数据库"，用来缓存数据，让你的应用响应更快。
速度对比：
类比：
Redis 数据结构
Redis 有 5 种存储数据的方式，叫"数据结构"。
1. 字符串（String）—— 最常用
就像普通的键值对，一个 key 对应一个 value。
图书馆找书：
- 传统方式：去书架上找（数据库，从磁盘读取）
- 用缓存：提前把书放在桌上（Redis，从内存读取）
显然，桌上的书更快找到。
import redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
# 存数据
r.set('name', '张三')
r.set('age', 25)
# 取数据
name = r.get('name') # '张三'
age = r.get('age') # '25'
# 设置带过期时间（秒）
r.setex('token', 3600, 'abc123') # 存 token，1小时后自动消失
# 批量操作
r.mset({'city': '北京', 'job': '程序员'})
cities = r.mget(['city', 'job']) # ['北京', '程序员']

---

<!-- p.2 -->

场景 示例
存储用户 Token setex('token:user123', 3600, token值)
存储临时验证码 setex('code:phone123', 300, '123456')
页面缓存 setex('page:home', 60, html内容)
场景 示例
用户信息 user:1001 存用户 ID=100 的信息
商品信息 product:2001 存商品 ID=2001 的信息
使用场景：
2. 哈希（Hash）—— 存对象
适合存"用户信息"、"商品信息"这样的对象。
Redis Key 命名规范（全局通用）：
1. 格式： 业务名:模块名:标识:属性 （全小写，用冒号分隔）
示例： ecommerce:item:1001:stock （电商-商品-1001-库存）、 user:session:12345
（用户-会话-12345）
2. 避免特殊字符：不用空格、换行、中文（如需用中文，确保编码为 UTF-8）
3. 长度控制：Key 不宜过长（如超过100字符），否则占用内存且降低查询效率
4. 统一前缀：同业务模块用统一前缀，便于批量操作/删除（如 ecommerce:* ）
使用场景：
# 计数器
r.set('count', 10)
r.incr('count') # 11（自动 +1）
r.incrby('count', 5) # 16（增加 5）
# 存一个用户对象
r.hset('user:1001', mapping={
'name': '张三',
'email': 'zhangsan@example.com',
'age': '25'
})
# 取单个字段
r.hget('user:1001', 'name') # '张三'
# 取所有字段
r.hgetall('user:1001')
# {'name': '张三', 'email': 'zhangsan@example.com', 'age': '25'}
# 删除字段
r.hdel('user:1001', 'age')

---

<!-- p.3 -->

场景 示例
最近浏览 lpush('history:user123', '商品ID')
任务队列 lpush('queue:tasks', '任务内容')
场景 示例
文章标签 sadd('tags:article:1', 'Python', 'FastAPI')
用户好友 sadd('friends:user123', 'user456', 'user789')
3. 列表（List）—— 排队
按顺序排列的列表，适合"任务队列"、"最近浏览记录"。
使用场景：
4. 集合（Set）—— 去重
元素唯一，插入重复元素时会被自动忽略，天然具备去重特性，适合"标签"、"好友列表"。
使用场景：
5. 有序集合（Sorted Set）—— 排行榜
每个元素带分数，按分数排序，适合"排行榜"、"评分系统"。
# 从左边插入（左=列表头部，后插入的元素更靠前）
r.lpush('tasks', '任务3', '任务2') # 结果：['任务2', '任务3']
# 从右边插入（右=列表尾部）
r.rpush('tasks', '任务4') # 结果：['任务2', '任务3', '任务4']
# 查看列表
r.lrange('tasks', 0, -1) # ['任务2', '任务3', '任务4']
# 取出元素
r.lpop('tasks') # '任务2'（从左边弹出）
r.rpop('tasks') # '任务4'（从右边弹出）
# 添加标签
r.sadd('tags:article:1', 'Python', 'FastAPI', 'Redis')
# 查看所有标签
r.smembers('tags:article:1') # {'Python', 'FastAPI', 'Redis'}
# 检查是否包含
r.sismember('tags:article:1', 'Python') # True

---

<!-- p.4 -->

场景 示例
游戏排行榜 zadd('rank:game1', {'玩家A': 5000})
商品评分 zadd('rating:product1', {'用户A': 5})
使用场景：
FastAPI 集成 Redis
第一步：安装依赖
第二步：连接配置
第三步：创建 Redis 连接
# 添加排行榜数据
r.zadd('leaderboard', {'张三': 100, '李四': 90, '王五': 95})
# 查看排名（从高到低）
r.zrevrange('leaderboard', 0, -1, withscores=True)
# [('张三', 100.0), ('王五', 95.0), ('李四', 90.0)]
# 查看某人排名
r.zrevrank('leaderboard', '张三') # 0（第1名）
pip install redis fastapi uvicorn
# config.py
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
redis_host: str = "localhost"
redis_port: int = 6379
redis_db: int = 0
model_config = {"env_file": ".env"}
# database.py
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
settings = Settings()
# 方式1：直接连接
# 配置连接池（生产环境必备）
pool = ConnectionPool(
host=settings.redis_host,
port=settings.redis_port,
db=settings.redis_db,

---

<!-- p.5 -->

注意：使用 redis.asyncio （异步版本），可以提高并发性能。
第四步：在应用中使用
decode_responses=True,
max_connections=100, # 最大连接数，根据业务调整
socket_timeout=5, # 连接超时
socket_keepalive=True
)
r = redis.Redis(
host=settings.redis_host,
port=settings.redis_port,
db=settings.redis_db,
decode_responses=True
)
# 方式2：从 URL 连接
async def init_redis():
try:
url = f"redis://{settings.redis_host}:
{settings.redis_port}/{settings.redis_db}"
pool = ConnectionPool.from_url(
url,
encoding="utf-8",
decode_responses=True,
max_connections=100
)
r = redis.from_url(url, encoding="utf-8", decode_responses=True)
await r.ping() # 校验连接
return r
except Exception as e:
raise RuntimeError(f"Redis 连接失败: {e}") from e
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
import redis.asyncio as redis
from database import init_redis
settings = Settings()
# 生命周期管理（启动/关闭时连接/断开）
@asynccontextmanager
async def lifespan(app: FastAPI):
app.state.redis = await init_redis()
yield
await app.state.redis.close()
app = FastAPI(lifespan=lifespan)
# 数据模型
class Item(BaseModel):
name: str

---

<!-- p.6 -->

场景 过期时间建议 说明
验证码 5-10 分钟 短时效，防止恶意利用
商品 / 用户缓存 1-24 小时 平衡新鲜度和缓存命中率
Token 1-7 天 结合刷新令牌机制
空值标记（防穿透） 1-5 分钟 短时效，避免长期缓存空值
缓存查询流程：
过期时间设置建议
更新数据时清除缓存
1. 推荐策略：先更新数据库 → 再删除缓存（避免并发下数据不一致）
反例：先删缓存 → 再更库，若更库前有请求查缓存，会缓存旧值；
2. 不推荐“直接更新缓存”：高并发下易导致缓存值覆盖混乱；
3. 特殊场景（如高频更新）：可延迟双删（更库后删缓存 → 等待 1 秒 → 再删一次），解决并发更新
问题。
price: float
# 缓存查询示例
@app.get("/items/{item_id}")
async def get_item(item_id: int):
redis = app.state.redis
cache_key = f"item:{item_id}"
# 第1步：查缓存
cached = await redis.get(cache_key)
if cached:
return {"source": "cache", "data": cached}
# 第2步：缓存没命中，查数据库
# （这里简化处理，实际项目中应该查真实数据库）
item_data = {"id": item_id, "name": f"商品{item_id}", "price": 99.99}
# 第3步：写入缓存，设置60秒过期
await redis.setex(cache_key, 60, str(item_data))
return {"source": "database", "data": item_data}
请求 → 查缓存 → 命中 → 直接返回
↓
未命中
↓
查数据库 → 返回数据
↓
写入缓存（带过期时间）

---

<!-- p.7 -->

生产环境 Redis 配置建议
1. 开启持久化：
RDB：定期快照（适合备份，如每小时快照）；
AOF：日志追加（适合数据可靠性，每秒刷盘）；
推荐：RDB + AOF 混合持久化。
2. 配置内存淘汰策略：
推荐 volatile-lru （只淘汰带过期时间的 Key，按 LRU 算法），避免 Redis 占满内存。
3. 集群部署：
高并发场景用 Redis 集群/哨兵，避免单点故障。
缓存常见问题
问题 1：缓存穿透
问题：查询不存在的数据，每次都穿透到数据库，恶意请求会打垮数据库。
举例：
解决方案：用特殊标记 "NULL" 记录"查不到"。
@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
redis = app.state.redis
# 更新数据库（省略）
# 清除旧缓存，防止数据不一致
cache_key = f"item:{item_id}"
await redis.delete(cache_key)
return {"message": "更新成功"}
用户查询 ID=9999 的商品（不存在）
↓
缓存查不到
↓
去数据库查
↓
数据库也查不到，返回空
↓
用户反复查询，数据库压力山大
async def get_item(item_id: int):
cache_key = f"item:{item_id}"
cached = await redis.get(cache_key)
if cached == "NULL":
return None # 之前查过，确实不存在

---

<!-- p.8 -->

问题 2：缓存雪崩
问题：缓存雪崩指大量缓存 Key 同时过期，或 Redis 服务整体宕机，导致原本由缓存承接的大量请求瞬
间全部穿透到数据库，超出数据库的承载能力，最终引发数据库崩溃的现象。
举例：
解决方案：过期时间加随机偏移量。
if cached:
return eval(cached)
# 查数据库
item = await db.get_item(item_id)
if not item:
# 查不到也存进去，过期时间短一点
await redis.setex(cache_key, 60, "NULL")
else:
await redis.setex(cache_key, 3600, str(item))
return item
缓存都设置1小时后过期
↓
1小时后，所有缓存同时失效
↓
大量请求同时查数据库
↓
数据库崩溃
import random
def get_with_cache(item_id: int):
base_expiry = 3600 # 1小时
# 随机加减10%，避免同时失效
expiry = base_expiry + random.randint(-360, 360)
cache_key = f"item:{item_id}"
cached = redis.get(cache_key)
if cached:
return eval(cached)
item = await db.get_item(item_id)
if item:
redis.setex(cache_key, expiry, str(item))
return item

---

<!-- p.9 -->

问题 3：缓存击穿
问题：热点数据过期瞬间，大量并发同时查数据库。
举例：
解决方案：分布式双重检查锁（第一层查缓存→加锁→第二层查缓存→查库，仅让一个请求查库，其余
请求等待 / 重试）
某商品太热门，10000人同时访问
↓
缓存刚好过期
↓
10000人同时查数据库
↓
数据库被打垮
import asyncio
async def get_item_with_lock(item_id: int):
cache_key = f"item:{item_id}"
# 第1层检查：看缓存有没有
cached = await redis.get(cache_key)
if cached:
return json.loads(cached)
# 没缓存，尝试加锁（只让一个人查库）
lock_key = f"lock:{cache_key}"
# 分布式锁的超时时间（ex=5）需根据实际查库 + 写缓存的耗时调整（建议比最大耗时多 2-3
秒），
# 避免锁提前释放导致多请求穿透到数据库。
lock_acquired = await redis.set(lock_key, "1", ex=5, nx=True)
if lock_acquired:
try:
cached = await redis.get(cache_key)
if cached:
return json.loads(cached)
item = await db.get_item(item_id)
await redis.setex(cache_key, 3600, json.dumps(item))
finally:
await redis.delete(lock_key) # 无论是否异常，都释放锁
return item
else:
# 循环重试，而非递归
for _ in range(5): # 限制重试次数
await asyncio.sleep(0.1)
cached = await redis.get(cache_key)
if cached:
return json.loads(cached)
raise Exception("获取数据超时")

---

<!-- p.10 -->

数据结构 特点 适用场景
String 简单键值对 Token、验证码、页面缓存
Hash 存对象 用户信息、商品信息
List 有顺序、可排队 任务队列、最近浏览
Set 不重复 标签、好友列表
Sorted Set 带分数的排名 排行榜、评分系统
要点 说明
先查缓存 命中则直接返回，不查库
设置过期时间 平衡内存使用和数据新鲜度
更新时清缓存 防止数据不一致
处理三个问题 穿透（空值标记）、雪崩（随机过期）、击穿（双检锁）
总结
Redis 数据结构速查
缓存最佳实践
缓存查询代码模板
async def get_data(key: str):
# 1. 查缓存
cached = await redis.get(key)
if cached:
return eval(cached)
# 2. 查数据库
data = db.query(key)
# 3. 写入缓存（带过期时间）
await redis.setex(key, 3600, str(data))
return data
