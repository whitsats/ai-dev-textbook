# FastAPI的JWT详解

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\19FastAPI的认证与授权（集合）\FastAPI的JWT详解\FastAPI的JWT详解.pdf`
> **页数**：13（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 13,368 字符，其中汉字 2,347 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

字段 含义 作用
alg Algorithm，签名算法 告诉验证方用什么算法来验证签名，常用值： HS256 、 RS256
typ Type，令牌类型 固定值 JWT ，表明这是一个 JWT，不是其他类型的令牌
类型 说明 举例
Registered
Claims
JWT 官方定义好的标准字段，全世界
通用
sub （用户ID）、 exp （过期时
间）
Private Claims 你和前端约定好的自定义字段
name （用户名）、 role （角
FastAPI 的 JWT 详解
什么是 JWT
JWT（JSON Web Token，RFC 7519）是一种开放标准，用于在各方之间安全地传输信息，通过数字签
名验证真实性和完整性，常用于身份验证和授权。
JWT 与 OAuth2 的关系：OAuth2 是一套授权框架（定义了多种授权流程，如密码模式、授权码模式，
解决 “如何安全获取访问令牌” 的问题），JWT 是一种令牌格式标准（定义令牌的结构和验证方式），两
者可协作 ——OAuth2 流程中发放的令牌常采用 JWT 格式。
JWT 的优势
无状态：令牌自身包含用户身份、过期时间等所有验证信息，服务器无需存储会话数据（减轻数据
库压力）；注：若需令牌撤销，仍需结合黑名单等有状态机制
跨域：可以在不同域之间传输，适合微服务架构
安全：通过数字签名验证信息的真实性和完整性
灵活：可以包含任意的 JSON 数据
JWT 的结构
JWT 由三部分组成，用点号（.）分隔： xxxxx.yyyyy.zzzzz → Header.Payload.Signature
Header（头部）
经过 Base64URL 编码，包含两个固定字段：
Payload（载荷）
Payload 就像一张临时身份证上的信息页，里面记录了"这张证是谁的"、"什么时候有效"等关键信息。
Payload 由多个声明（Claims）组成，你可以把声明理解为"数据字段"。
声明分为三类（先记住前两个即可，Public Claims 很少用到）：
{"alg": "HS256", "typ": "JWT"}

---

<!-- p.2 -->

类型 说明 举例
Private Claims 你和前端约定好的自定义字段
色）
Public Claims 需要向 IANA 注册的公共声明 很少用到，了解即可
声明 含义 通俗理解 是否常用
sub Subject（主题） 这张令牌属于谁 ⭐ 必须
exp Expiration Time（过期时间） 令牌什么时候失效 ⭐ 必须
iat Issued At（签发时间） 令牌什么时候发的 常用
iss Issuer（发行者） 谁签发了这张令牌 常用
aud Audience（受众） 这张令牌给谁用 较少
nbf Not Before（生效时间） 令牌什么时候开始有效 较少
jti JWT ID（唯一标识） 令牌的身份证号，防重复 较少
一个真实的 Payload 长这样：
7 个标准声明详解：
Signature（签名）
签名是 JWT 的安全保障机制，它的核心作用是：防止内容被篡改。
为什么需要签名？
想象这样一个场景：
用户把 JWT 中的 role 从 "user" 改成了 "admin"
如果没有签名验证，服务端会傻傻地相信这个被改过的 JWT
有了签名，改动后的签名就"对不上号"，服务器一眼就能发现数据被动过手脚
签名是怎么生成的？（大白话版）
{
"sub": "1001", // 用户的ID（相当于身份证号）
"name": "张三", // 用户自己取的名字
"role": "admin", // 用户的角色权限
"iat": 1516239022, // 这张"证"什么时候发的
"exp": 1717242622 // 这张"证"什么时候过期
}
第一步：把 Header 和 Payload 分别转成 Base64 字符串
第二步：把两个字符串用 "." 拼接起来
第三步：用"密钥"对这个拼接串进行加密，得到签名

---

<!-- p.3 -->

对应到代码就是：
一句话总结：签名就像"防伪水印"，只要 JWT 内容被改过，水印就对不上，服务器就会拒绝这个请求。
可以用在线工具 jwt.io 解码查看具体内容。
JWT 的签名算法
签名的作用是防篡改：如果有人改了 JWT 中的内容（比如把 role 改成 admin），签名就会变化，服务
器验证签名时就能发现。
HS256（对称算法，最常用）
签名和验证使用同一个密钥。该密钥仅由生成 / 验证令牌的服务端持有（客户端不接触），适用于单体
应用或可信内部服务。
场景：单体应用或内部服务，所有人都用同一个密钥，简单高效。
import hmac
import hashlib
import base64
# 假设这是 Header 和 Payload 转成的字符串
header = "eyJhbGciOiJIUzI1NiJ9" # {"alg":"HS256"}
payload = "eyJzdWIiOiIxMjM0NTY3ODkwIn0" # {"sub":"1234567890"}
# 用 "." 拼接
data = header + "." + payload
# 用密钥进行加密，生成签名
secret = "我的密钥是秘密".encode('utf-8') # 需编码为字节
signature = hmac.new(secret, data.encode('utf-8'), hashlib.sha256).digest()
signature_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
# Base64URL 编码
# 最终的 JWT = Header + "." + Payload + "." + Signature
jwt_token = f"{header}.{payload}.{signature_b64}"
print("最终JWT:", jwt_token)
import jwt
secret = "同一个密钥，发的人和收的人都知道"
# 发的人：用密钥签名
token = jwt.encode({"sub": "user123"}, secret, algorithm="HS256")
# 收的人：用同一个密钥验证
payload = jwt.decode(token, secret, algorithms=["HS256"])

---

<!-- p.4 -->

对比项 HS256 RS256
密钥 签名和验证用同一个 签名用私钥，验证用公钥
密钥分发 所有参与方共享同一个密钥 只需分发公钥，私钥不用传
性能 快 慢
适用场景 单机、内部系统 微服务、开放平台
包名 作用 类比
python-jose[cryptography] JWT 的生成和验证 相当于"制作和检验身份证"的工具
passlib[bcrypt] 用户密码的加密存储 相当于"把密码锁进保险箱"的工具
python-multipart FastAPI 解析表单数据 处理登录请求时需要用到
RS256（非对称算法）
签名用私钥，验证用公钥。私钥只有服务端知道，公钥可以发给任何客户端。
场景：微服务、开放 API。多服务之间不需要共享私钥，只需分发公钥。
对比
安装依赖
接下来的代码演示需要用到以下库：
在 FastAPI 中使用 JWT
接下来我们一步步实现一个完整的登录认证功能。先从最简单的开始。
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
# 生成密钥对
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048,
backend=default_backend())
public_key = private_key.public_key()
# 服务端用私钥签名
token = jwt.encode({"sub": "user123"}, private_key, algorithm="RS256")
# 客户端用公钥验证（公钥可以公开）
payload = jwt.decode(token, public_key, algorithms=["RS256"])
pip install "python-jose[cryptography]" "passlib[bcrypt]" python-multipart

---

<!-- p.5 -->

操作 明文密码 哈希后
注册 "123456" "$2b$12$EixZaYVK1..."
登录验证 "123456" 自动比对，返回 True/False
第一步：生成和验证 JWT（最小示例）
这是 JWT 最核心的操作：生成和验证。 先掌握这个，再往下看。
运行结果示例：
关键点：
jwt.encode() = 生成 JWT，用密钥签名
jwt.decode() = 验证 JWT，检查签名是否正确
sub = 存用户 ID，这是约定俗成的字段名
第二步：密码哈希（为什么要哈希？）
背景：如果数据库里存的是明文密码（ password: "123456" ），万一数据库泄露，所有用户的密码就
暴露了。
解决：用哈希处理密码，存进数据库的是一串乱码。
import jwt
from datetime import datetime, timedelta
# 1. 准备密钥（相当于"签名笔"）
secret = "这是我设置的秘密密钥"
# 2. 准备载荷（你想存什么信息？这里存了用户ID）
payload = {
"sub": "user123", # sub = 用户ID
"name": "张三",
"exp": datetime.utcnow() + timedelta(hours=1) # 1小时后过期
}
# 3. 生成 JWT（用密钥"签名"）
token = jwt.encode(payload, secret, algorithm="HS256")
print("生成的Token:", token)
# 4. 验证 JWT（用同一把"钥匙"来检验）
try:
decoded = jwt.decode(token, secret, algorithms=["HS256"])
print("验证成功:", decoded) # {'sub': 'user123', 'name': '张三', 'exp': ...}
except jwt.ExpiredSignatureError:
print("Token 已过期")
except jwt.InvalidTokenError:
print("Token 无效或被篡改")
生成的Token: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIiwiZ...
验证成功: {'sub': 'user123', 'name': '张三', 'exp': 1717242622}

---

<!-- p.6 -->

第三步：封装成函数（方便复用）
把 JWT 生成和密码验证封装成函数，后面会反复用到。
from passlib.context import CryptContext
# 配置使用 bcrypt 算法（目前最安全的哈希算法）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# 注册时：把密码变成哈希
password = "123456"
hashed = pwd_context.hash(password)
print("哈希后:", hashed) # $2b$12$EixZaYVK1fsbw1ZfbX...
# 登录时：验证密码是否匹配
is_correct = pwd_context.verify("123456", hashed) # True
is_wrong = pwd_context.verify("000000", hashed) # False
print("密码正确?", is_correct)
print("密码错误?", is_wrong)
from datetime import datetime, timedelta
from jose import jwt, JWTError
# ============ 配置 ============
SECRET_KEY = "change-this-in-production" # 密钥，生产环境要从环境变量读取
ALGORITHM = "HS256" # 算法
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Token 有效期
# ============ 密码工具 ============
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def verify_password(plain_password: str, hashed_password: str) -> bool:
"""验证密码是否正确"""
return pwd_context.verify(plain_password, hashed_password)
def get_password_hash(password: str) -> str:
"""把密码哈希（注册时用）"""
return pwd_context.hash(password)
# ============ JWT 工具 ============
def create_access_token(data: dict) -> str:
"""
生成 JWT
data: 要存入 Token 的数据，通常是 {"sub": "用户名"}
"""
to_encode = data.copy()
expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
to_encode.update({
"exp": expire, # 过期时间（必须）
"iat": datetime.utcnow() # 签发时间
})
return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

---

<!-- p.7 -->

第四步：完整的登录认证示例
现在把上面的内容整合起来，实现一个完整的 FastAPI 登录认证系统。
def verify_token(token: str) -> dict | None:
"""验证 Token，返回 payload；失败返回 None"""
try:
return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
except JWTError:
return None
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
app = FastAPI()
# ============ OAuth2 配置 ============
# 自动从请求头提取 Token，格式：Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
# ============ 模拟数据库（生产用真实数据库）==========
fake_users_db = {
"admin": {
"username": "admin",
"password":
"$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW" # 密码是 "secret"
}
}
def authenticate_user(username: str, password: str):
"""验证用户名和密码"""
user = fake_users_db.get(username)
if not user:
return None
if not verify_password(password, user["password"]):
return None
return user
async def get_current_user(token: str = Depends(oauth2_scheme)):
"""
依赖项：从 Token 中获取当前用户
每个需要登录才能访问的接口都用 Depends(get_current_user)
"""
payload = verify_token(token)
if payload is None:
raise HTTPException(
status_code=status.HTTP_401_UNAUTHORIZED,
detail="Token 无效或已过期",
headers={"WWW-Authenticate": "Bearer"}
)
username = payload.get("sub")
if username is None:
raise HTTPException(status_code=401, detail="无效的 Token")

---

<!-- p.8 -->

请求流程图
完整实现示例
上面是简化版，实际项目中会把各模块分文件存放。下面是整合在一起的完整版本：
return username
# ============ 路由 ============
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
"""
登录接口
前端发送：username=admin&password=secret
返回：access_token
"""
user = authenticate_user(form_data.username, form_data.password)
if not user:
raise HTTPException(
status_code=status.HTTP_401_UNAUTHORIZED,
detail="用户名或密码错误"
)
# 生成 Token
access_token = create_access_token(data={"sub": user["username"]})
return {"access_token": access_token, "token_type": "bearer"}
@app.get("/profile")
async def get_profile(username: str = Depends(get_current_user)):
"""
获取个人信息（需要登录）
调用方式：请求头加 Authorization: Bearer <token>
"""
return {"username": username, "message": "这是你的个人信息"}
1. 登录获取 Token
POST /login
Body: username=admin&password=secret
↓
返回: {"access_token": "eyJhbGc...", "token_type": "bearer"}
2. 访问需要登录的接口
GET /profile
Headers: Authorization: Bearer eyJhbGc...
↓
返回: {"username": "admin", "message": "这是你的个人信息"}
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError

---

<!-- p.9 -->

from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from typing import Optional
from pydantic_settings import BaseSettings
# ============ 配置 ============
class Settings(BaseSettings):
SECRET_KEY: str = "change-this-in-production"
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
model_config = {"env_file": ".env"}
settings = Settings()
# ============ 密码哈希 ============
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def verify_password(plain: str, hashed: str) -> bool:
return pwd_context.verify(plain, hashed)
def get_password_hash(password: str) -> str:
return pwd_context.hash(password)
# ============ 令牌创建与验证 ============
def create_access_token(data: dict, expires_delta: timedelta | None = None) ->
str:
to_encode = data.copy()
expire = datetime.utcnow() + (expires_delta or
timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type":
"access"})
return jwt.encode(to_encode, settings.SECRET_KEY,
algorithm=settings.ALGORITHM)
def verify_token(token: str) -> dict | None:
try:
return jwt.decode(token, settings.SECRET_KEY, algorithms=
[settings.ALGORITHM])
except JWTError:
return None
# ============ Pydantic 模型 ============
class Token(BaseModel):
access_token: str
token_type: str = "bearer"
class User(BaseModel):
username: str
email: EmailStr
full_name: str | None = None
class UserCreate(User):
password: str
# ============ 模拟数据库 ============

---

<!-- p.10 -->

fake_users_db = {
"johndoe": {
"username": "johndoe",
"full_name": "John Doe",
"email": "johndoe@example.com",
"hashed_password":
"$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW", # secret
}
}
def get_user(username: str):
if username in fake_users_db:
return User(**fake_users_db[username])
return None
def authenticate_user(username: str, password: str):
user_dict = fake_users_db.get(username)
if not user_dict:
return None
if not verify_password(password, user_dict["hashed_password"]):
return None
return User(**user_dict)
# ============ 认证依赖 ============
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
credentials = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
payload = verify_token(token)
if payload is None:
raise credentials
username = payload.get("sub")
token_type = payload.get("type")
if username is None or token_type != "access":
raise credentials
user = get_user(username)
if user is None:
raise credentials
return user
# ============ 路由 ============
app = FastAPI()
@app.post("/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
user = authenticate_user(form_data.username, form_data.password)
if not user:
raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
access_token = create_access_token(data={"sub": user.username})
return {"access_token": access_token, "token_type": "bearer"}
@app.post("/auth/register")
async def register(user: UserCreate):

---

<!-- p.11 -->

问题 说明 解决
JWT 泄漏 令牌被攻击者获取 HTTPS + 合理过期时间 + 敏感操作重新验证密码
算法篡改 攻击者将算法改为 none 指定 algorithms 列表
重放攻击 重复使用同一个有效令牌 使用 jti 配合黑名单
核心流程：
刷新令牌机制
访问令牌有效期短（如 30 分钟），刷新令牌有效期长（如 7 天）。这样设计的好处：安全性更高（被
盗窗口有限）、用户体验好（无需频繁登录）、可随时撤销。
常见安全问题
if user.username in fake_users_db:
raise HTTPException(status_code=400, detail="Username already exists")
fake_users_db[user.username] = {
"username": user.username,
"email": user.email,
"full_name": user.full_name,
"hashed_password": get_password_hash(user.password),
}
return {"message": "User created successfully"}
@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
return current_user
@app.get("/users/me/items")
async def read_own_items(current_user: User = Depends(get_current_user)):
return [{"item_id": "Item1", "name": "示例物品", "owner":
current_user.username}]
用户登录 → /auth/token 验证用户名密码 → 返回 access_token
↓
后续请求 Authorization: Bearer <token>
↓
OAuth2PasswordBearer 自动提取令牌 → get_current_user 验证签名和过期时间
↓
返回当前用户信息
用户登录 → 获取 access_token + refresh_token
↓
access_token 过期 → 使用 refresh_token 换取新的 access_token
↓
refresh_token 也过期 → 重新登录

---

<!-- p.12 -->

序号 要点 说明
1 JWT 结构 Header.Payload.Signature 三部分
2 签名算法 HS256 对称算法简单高效，RS256 非对称适合分布式
3 无状态认证 服务器不存储会话，减少数据库压力
4 刷新机制 访问令牌短期 + 刷新令牌长期，兼顾安全与体验
5 安全措施 HTTPS、强密钥、设置过期时间、不存敏感信息
操作 方法
生成令牌 jwt.encode(payload, secret, algorithm)
验证令牌 jwt.decode(token, secret, algorithms)
验证密码 pwd_context.verify(plain, hashed)
哈希密码 pwd_context.hash(password)
核心要点
常用方法
