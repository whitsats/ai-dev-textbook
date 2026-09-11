# FastAPI的QAuth2详解

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\19FastAPI的认证与授权（集合）\FastAPI的QAuth2详解\FastAPI的QAuth2详解.pdf`
> **页数**：18（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 16,062 字符，其中汉字 2,928 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

对比项 OAuth2 JWT
本质 授权"流程"：怎么拿到访问权限 令牌"格式"：访问凭证长什么样
类比 酒店的"入住流程" 房卡"本身"
关系 OAuth2 定义了获取令牌的方法 JWT 是 OAuth2 中最常用的令牌格式之一
优势 说明 类比
安全 不需要把密码告诉第三方 不用把钥匙给物业，只需给临时门禁卡
灵活 支持多种授权方式 不同场景用不同方式开门
可控 可以限制第三方能访问什么 物业卡只能开楼门，不能开你家门
方便 用户只需登录一次 一次验证，多处通行
FastAPI 的 OAuth2 详解
什么是 OAuth2
OAuth2 是一种授权协议（RFC 6749），大白话就是："在不告诉别人密码的情况下，允许别人访问你的
东西"。
生活中的例子：
你去酒店住宿，把身份证给前台
前台登记后还你身份证，你并没有把身份证"送"给前台
前台只能在有效期内验证你是谁，不能用你的身份证做别的事
这就是 OAuth2 的核心理念：授权访问，而不是共享密码。
OAuth2 与 JWT 的关系
很多人以为 OAuth2 和 JWT 是"二选一"的关系，实际上它们解决的是不同问题：
一句话总结：
OAuth2 = "怎么拿到授权"
JWT = "授权凭证长什么样"
两者配合使用：OAuth2 负责"发卡"，JWT 就是那张"卡"。
OAuth2 的优势
OAuth2 的四个角色
OAuth2 就像一个快递系统，有四个关键角色：

---

<!-- p.2 -->

角色 说明 类比 示例
资源所有者 数据的主人 寄件人 普通用户
客户端 想访问数据的应用 收件人 第三方 App
授权服务器 验证身份、发通行证的 快递公司 FastAPI Auth Server
资源服务器 存储数据、提供数据的 仓库 FastAPI API Server
授权方式 适用场景 通俗理解
授权码 第三方网站登录（微信登录、Google 登录） 最安全，像"扫码授权"
密码授权 你自己的 App，用户直接给账号密码 像"直接给钥匙"
客户端凭证 服务之间互相调用（微服务） 像"员工卡"
隐式授权 已淘汰，用 PKCE 代替 不推荐
工作流程（类比快递）：
1. 你（资源所有者）想给某个 App 授权访问你的数据
2. App（客户端）去找授权服务器申请
3. 授权服务器问你要不要同意
4. 你同意后，授权服务器给 App 发一张"临时通行证"
5. App 拿着通行证去资源服务器取数据
OAuth2 的四种授权方式
OAuth2 根据不同场景，提供了 4 种"开门方式"：
一图理解四种授权方式
┌─────────────────────────────────────────────────────────────────┐
│ 授权码授权（第三方登录） │
│ 用户 → 扫码确认 → 返回授权码 → 用授权码换令牌（后端操作） │
│ ✅ 最安全，因为令牌不经过浏览器 │
├─────────────────────────────────────────────────────────────────┤
│ 密码授权（自家产品） │
│ 用户直接输入账号密码 → 返回令牌 │
│ ⚠️ 只适用于你完全信任的应用 │
├─────────────────────────────────────────────────────────────────┤
│ 客户端凭证（机器对机器） │
│ 服务 A 用密钥直接换令牌 → 返回令牌 │
│  没有用户参与，纯服务间通信 │
├─────────────────────────────────────────────────────────────────┤
│ 隐式授权（已淘汰） │
│ 用户 → 授权页 → 直接返回令牌 │
│ ❌ 不推荐，令牌暴露在 URL 中 │
└─────────────────────────────────────────────────────────────────┘

---

<!-- p.3 -->

你的情况 推荐方式
第三方网站想用微信登录 授权码授权
我自己开发的 App，让用户登录 密码授权（简化）/ 授权码 + PKCE（推荐）
后端服务 A 要调用后端服务 B 客户端凭证
微信小程序、手机 App 授权码 + PKCE
怎么选择授权方式？
授权码授权流程（第三方登录）
这是最安全的方式，适合"让用户用微信/Google 登录"这种场景。
流程图解
为什么要"用授权码换令牌"？为什么不直接返回令牌？
1. 用户点击"用微信登录"
↓
2. 网页跳转到微信授权页面
URL: https://api.weixin.qq.com/authorize?
response_type=code ← 告诉微信"我要授权码"
&client_id=你的应用ID
&redirect_uri=https://你的网站.com/callback ← 授权后跳回来
↓
3. 用户在微信页面点"确认登录"
↓
4. 微信跳转回你的网站，带上授权码
URL: https://你的网站.com/callback?code=XXXXXX ← 授权码在这里
↓
5. 你的后端服务器用授权码换令牌（这个过程在前端看不见！）
POST https://api.weixin.qq.com/sns/oauth2/access_token
参数: grant_type=authorization_code
code=XXXXXX
client_id=你的应用ID
client_secret=你的应用密钥 ← 这个只在后端用
↓
6. 微信返回 access_token
{
"access_token": "有用的令牌",
"refresh_token": "刷新令牌",
"expires_in": 7200
}

---

<!-- p.4 -->

直接返回令牌 用授权码换令牌
令牌暴露在浏览器 URL 中 令牌只在后端传输
可能被浏览器历史记录、日志记录 更安全
⚠️ 隐式授权（已淘汰） ✅ 授权码授权（推荐）
一句话：授权码授权把"令牌传输"这个步骤从"浏览器"转移到了"后端服务器"，更安全。
密码授权流程（自有产品登录）
什么时候用？ 你自己开发的 App，直接让用户输入账号密码。
一句话理解：用户在你的第一方 App 中输入账号密码，App 将密码提交给你的服务器，服务器验证后返
回令牌（客户端仅传输、不存储密码）
流程图解
密码授权的完整交互流程
下面是一个完整的"登录 → 获取 Token → 访问受保护接口"的步骤：
1. 用户在 App 输入账号密码
┌────────────────────────────────────────────┐
│ POST /token │
│ Content-Type: application/x-www-form-urlencoded│
│ │
│ grant_type=password │
│ &username=zhangsan │
│ &password=123456 │
└────────────────────────────────────────────┘
↓
2. 服务器验证账号密码
- 账号存在？
- 密码正确？
↓
3. 验证通过，返回令牌
{
"access_token": "eyJhbGci...",
"token_type": "bearer",
"expires_in": 1800
}
用户输入账号密码
↓
┌─────────────────────────────────────────────────────────┐
│ POST /token ← 登录接口 │
│ 发送: username=zhangsan&password=123456 │
└─────────────────────────────────────────────────────────┘
↓
服务器验证成功
↓

---

<!-- p.5 -->

场景 例子
微服务调用 订单服务调用库存服务
定时任务 备份脚本调用存储服务
运维脚本 部署脚本调用 CI/CD 服务
重要提醒：密码授权只适合"你自己开发的应用"，不要用于第三方应用！
客户端凭证授权（机器对机器）
什么时候用？ 服务 A 要调用服务 B，没有用户参与，纯机器之间的对话。
一句话理解：就像公司员工用工卡开门，不需要前台登记。
流程图解
┌─────────────────────────────────────────────────────────┐
│ 返回: access_token=eyJhbGci... │
│ 用户把这个 Token 存起来 │
└─────────────────────────────────────────────────────────┘
↓
以后访问需要登录的接口，带上 Token
┌─────────────────────────────────────────────────────────┐
│ GET /users/me │
│ Headers: Authorization: Bearer eyJhbGci... │
└─────────────────────────────────────────────────────────┘
↓
服务器验证 Token 有效，返回用户信息
1. 服务 A（内部）带着凭证去换令牌
┌────────────────────────────────────────────┐
│ POST /token │
│ Content-Type: application/x-www-form-urlencoded│
│ │
│ grant_type=client_credentials │
│ &client_id=order_service │
│ &client_secret=supersecret │
└────────────────────────────────────────────┘
↓
2. 服务器验证凭证
↓
3. 返回令牌
{
"access_token": "eyJhbGci...",
"token_type": "bearer",
"expires_in": 3600
}
↓
4. 服务 A 用令牌访问服务 B
┌────────────────────────────────────────────┐
│ GET /api/data │
│ Authorization: Bearer eyJhbGci... │

---

<!-- p.6 -->

Scope 能做什么 不能做什么
read 读取数据 写入、删除
write 读取 + 写入 删除
profile 读取用户名、头像等 读取邮箱
email 读取邮箱 修改邮箱
admin 管理员权限 无限制
包 作用
python-jose 生成和验证 JWT
passlib 密码加密
python-multipart 处理登录表单
pydantic-settings 读取配置文件
OAuth2 的作用域（Scopes）
什么是 Scope？
Scope（权限范围） 就像景区门票：买了"只逛景点"的票就不能进"剧场"，买了"全场通票"才能到处玩。
例子：
用户授权 App 读取他的基本信息（ profile ）
但不授权读取他的邮箱（ email ）
App 就只能获取名字、头像，无法获取邮箱
常用 Scope
在 FastAPI 中实现 OAuth2
接下来，我们一步步实现一个完整的登录认证系统。
安装依赖
└────────────────────────────────────────────┘
pip install "python-jose[cryptography]" "passlib[bcrypt]" python-multipart
pydantic-settings

---

<!-- p.7 -->

简化版：一步步实现
为了方便理解，我们从最简单的例子开始，一步步添加功能。
第一步：配置（config.py）
这段代码做了什么？
Settings 类从环境变量或 .env 文件读取配置
SECRET_KEY 是 JWT 的"签名笔"，必须保密
ALGORITHM 是签名算法，HS256 是最常用的
第二步：密码工具（auth/utils.py）
这段代码做了什么？
get_password_hash() ：把明文密码变成密文（不可逆）
verify_password() ：验证用户输入的密码是否正确
相同密码每次加密结果不同（因为有随机"盐"）
第三步：JWT 工具（auth/utils.py）
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
SECRET_KEY: str = "change-this-in-production" # JWT 签名密钥
ALGORITHM: str = "HS256" # 签名算法
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Token 有效期（分钟）
settings = Settings()
from passlib.context import CryptContext
# 使用 bcrypt 算法加密密码
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def verify_password(plain_password: str, hashed_password: str) -> bool:
"""验证密码是否正确"""
return pwd_context.verify(plain_password, hashed_password)
def get_password_hash(password: str) -> str:
"""把密码加密（注册时用）"""
return pwd_context.hash(password)
from datetime import datetime, timedelta
from jose import jwt
from config import settings
def create_access_token(data: dict) -> str:

---

<!-- p.8 -->

这段代码做了什么？
create_access_token() ：生成 Token，就像"制作房卡"
verify_token() ：验证 Token，就像"刷房卡开门"
第四步：认证依赖（auth/dependencies.py）
"""
生成 JWT Token
data: 要存进 Token 的数据（一般存用户ID）
"""
to_encode = data.copy()
# 设置过期时间
expire = datetime.utcnow() +
timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
# 把过期时间和签发时间塞进去
to_encode.update({
"exp": expire,
"iat": datetime.utcnow()
})
# 用密钥签名，生成 Token
return jwt.encode(to_encode, settings.SECRET_KEY,
algorithm=settings.ALGORITHM)
def verify_token(token: str) -> dict | None:
"""验证 Token，返回里面的数据；失败返回 None"""
try:
return jwt.decode(token, settings.SECRET_KEY, algorithms=
[settings.ALGORITHM])
except Exception:
return None
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from config import settings
from auth.utils import verify_token
# OAuth2 方案：自动从请求头提取 Bearer Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
# 模拟数据库（真实项目用数据库）
fake_users_db = {
"admin": {
"username": "admin",
"password":
"$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW", # 密码是 "secret"
}
}

---

<!-- p.9 -->

这段代码做了什么？
OAuth2PasswordBearer ：自动从请求头找 Authorization: Bearer xxx
get_current_user() ：验证 Token，返回用户名
Depends() ：FastAPI 的依赖注入，自动执行验证
第五步：路由（main.py）
def authenticate_user(username: str, password: str):
"""验证用户名和密码"""
user = fake_users_db.get(username)
if not user:
return None
if not verify_password(password, user["password"]):
return None
return user
async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
"""
依赖项：自动验证 Token 并返回当前用户
任何需要登录的接口都加上 Depends(get_current_user)
"""
credentials_exception = HTTPException(
status_code=status.HTTP_401_UNAUTHORIZED,
detail="Token 无效或已过期",
headers={"WWW-Authenticate": "Bearer"},
)
payload = verify_token(token)
if payload is None:
raise credentials_exception
username = payload.get("sub")
if username is None:
raise credentials_exception
return username
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from config import settings
from auth.utils import create_access_token, get_password_hash, verify_password
from auth.dependencies import authenticate_user, get_current_user
app = FastAPI()
# ============ 登录接口 ============
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
"""
用户登录，拿到 Token
请求方式：POST /login
参数：username=admin&password=secret（表单格式）

---

<!-- p.10 -->

这段代码做了什么？
/login ：接收用户名密码，返回 Token
/profile ：需要登录才能访问，验证 Token 后返回数据
Depends(get_current_user) ：自动验证 Token，没 Token 或 Token 无效就返回 401
完整流程图
完整实现示例（分文件结构）
如果你想用更规范的方式组织代码，可以按下面的文件结构来写：
"""
user = authenticate_user(form_data.username, form_data.password)
if not user:
raise HTTPException(
status_code=401,
detail="用户名或密码错误"
)
# 生成 Token
access_token = create_access_token(data={"sub": user["username"]})
return {"access_token": access_token, "token_type": "bearer"}
# ============ 需要登录才能访问的接口 ============
@app.get("/profile")
async def get_profile(username: str = Depends(get_current_user)):
"""
获取用户信息（需要登录）
请求方式：GET /profile
请求头：Authorization: Bearer <token>
"""
return {"username": username, "message": "这是你的个人信息"}
1. 登录获取 Token
POST /login
Body: username=admin&password=secret
↓
返回: {"access_token": "eyJhbGc...", "token_type": "bearer"}
2. 带着 Token 访问受保护接口
GET /profile
Headers: Authorization: Bearer eyJhbGc...
↓
返回: {"username": "admin", "message": "这是你的个人信息"}
3. Token 过期或无效
GET /profile
Headers: Authorization: Bearer 无效的token
↓
返回: 401 Unauthorized

---

<!-- p.11 -->

config.py
schemas.py
app/
├── main.py # 应用入口
├── config.py # 配置
├── schemas.py # 数据模型
├── auth/
│ ├── __init__.py
│ ├── utils.py # JWT、密码工具
│ └── dependencies.py # 认证依赖
└── routers/
└── items.py # 业务路由
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
SECRET_KEY: str = "change-this-in-production"
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
REFRESH_TOKEN_EXPIRE_DAYS: int = 7
model_config = {"env_file": ".env"}
settings = Settings()
from pydantic import BaseModel, EmailStr
from typing import Optional
class Token(BaseModel):
access_token: str
token_type: str = "bearer"
class UserBase(BaseModel):
username: str
email: EmailStr
full_name: Optional[str] = None
class UserCreate(UserBase):
password: str
class User(UserBase):
disabled: Optional[bool] = None
class UserInDB(User):
hashed_password: str

---

<!-- p.12 -->

auth/utils.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings
# 显式指定工作因子（12 是推荐值，越高越安全但越慢）
pwd_context = CryptContext(
schemes=["bcrypt"],
deprecated="auto",
bcrypt__rounds=12 # 工作因子，范围 4-31
)
def verify_password(plain_password: str, hashed_password: str) -> bool:
return pwd_context.verify(plain_password, hashed_password)
def get_password_hash(password: str) -> str:
return pwd_context.hash(password)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -
> str:
to_encode = data.copy()
expire = datetime.utcnow() + (expires_delta or
timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
to_encode.update({"exp": expire, "iat": datetime.utcnow()})
return jwt.encode(to_encode, settings.SECRET_KEY,
algorithm=settings.ALGORITHM)
def verify_token(token: str) -> Optional[dict]:
try:
payload = jwt.decode(
token,
settings.SECRET_KEY,
algorithms=[settings.ALGORITHM],
options={"verify_iat": True} # 显式校验签发时间
)
# 额外校验签发时间是否在合理范围（防止令牌提前签发）
iat = payload.get("iat")
if iat and datetime.utcfromtimestamp(iat) > datetime.utcnow():
return None
return payload
except jwt.ExpiredSignatureError:
# 令牌过期可单独捕获，便于前端区分
return None
except JWTError:
return None

---

<!-- p.13 -->

auth/dependencies.py
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from config import settings
from schemas import User, UserInDB
from auth.utils import verify_password, verify_token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
fake_users_db = {
"johndoe": {
"username": "johndoe",
"full_name": "John Doe",
"email": "johndoe@example.com",
"hashed_password":
"$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
"disabled": False,
}
}
def get_user(username: str):
if username in fake_users_db:
return UserInDB(**fake_users_db[username])
return None
def authenticate_user(username: str, password: str):
user = get_user(username)
if not user:
return None
if not verify_password(password, user.hashed_password):
return None
return user
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) ->
User:
credentials_exception = HTTPException(
status_code=status.HTTP_401_UNAUTHORIZED,
detail="无效的凭据",
headers={"WWW-Authenticate": "Bearer"},
)
payload = verify_token(token)
if payload is None:
raise credentials_exception
username = payload.get("sub")
if username is None:
raise credentials_exception
user = get_user(username)
if user is None:
raise credentials_exception
return user

---

<!-- p.14 -->

auth/routes.py
main.py
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from config import settings
from schemas import Token, User, UserCreate
from auth.utils import create_access_token, get_password_hash
from auth.dependencies import authenticate_user, get_current_user
from auth.dependencies import fake_users_db
router = APIRouter(prefix="/auth", tags=["认证"])
@router.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
user = authenticate_user(form_data.username, form_data.password)
if not user:
raise HTTPException(
status_code=status.HTTP_401_UNAUTHORIZED,
detail="用户名或密码错误",
headers={"WWW-Authenticate": "Bearer"},
)
access_token = create_access_token(data={"sub": user.username})
return {"access_token": access_token, "token_type": "bearer"}
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
if user.username in fake_users_db:
raise HTTPException(status_code=400, detail="用户名已存在")
fake_users_db[user.username] = {
"username": user.username,
"email": user.email,
"full_name": user.full_name,
"hashed_password": get_password_hash(user.password),
"disabled": False
}
return {"message": "注册成功"}
@router.get("/me", response_model=User)
async def read_users_me(current_user: Annotated[User,
Depends(get_current_user)]):
return current_user

---

<!-- p.15 -->

安全措施 说明
设置过期时间 访问令牌 15-30 分钟，刷新令牌 7-30 天
使用强密钥 secrets.token_urlsafe(32) 生成
传输加密 必须使用 HTTPS
OAuth2 的安全考虑
1. 使用 HTTPS
代码讲解：
listen 443 ssl ：监听 443 端口，启用 SSL/TLS
ssl_certificate ：SSL 证书路径
ssl_certificate_key ：SSL 私钥路径
proxy_pass ：反向代理到 FastAPI 应用
proxy_set_header ：传递原始请求头给后端
Host ：原始主机名
X-Real-IP ：客户端真实 IP
X-Forwarded-Proto ：原始协议（http/https）
Authorization ：认证头，确保 JWT 令牌传递给后端
2. 令牌安全
from fastapi import FastAPI
from auth.routes import router as auth_router
app = FastAPI(title="OAuth2 示例 API")
app.include_router(auth_router)
@app.get("/")
async def root():
return {"message": "OAuth2 示例 API"}
# Nginx 配置
server {
listen 443 ssl;
ssl_certificate /path/to/cert.pem;
ssl_certificate_key /path/to/key.pem;
location / {
proxy_pass http://127.0.0.1:8000;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-Proto $scheme;
# 传递认证头
proxy_set_header Authorization $http_authorization;
}
}

---

<!-- p.16 -->

安全措施 说明
传输加密 必须使用 HTTPS
不存储敏感信息 JWT payload 可被解码
安全措施 说明
短期有效 授权码有效期不超过 10 分钟
一次性使用 使用后立即失效
绑定 redirect_uri 只允许预设的回调地址
验证 state 防止 CSRF 攻击
风险 缓解措施
用户密码暴露给客户端 仅用于第一方应用
无法撤销单个应用的访问 需要修改用户密码
无法细粒度控制权限 使用 scopes
场景 授权类型 说明
第三方网站登录 授权码 最安全
自有前端 App 密码授权 用户直接提供凭证
微服务间调用 客户端凭证 服务对服务
移动端/SPA 授权码 + PKCE 更安全的选择
3. 授权码安全
4. 密码授权注意事项
密码授权虽然简单，但存在以下风险：
最佳实践：密码授权只用于：
1. 你自己开发的第一方应用
2. 用户明确信任的应用
3. 无法使用授权码的场景
总结
OAuth2 授权类型选择

---

<!-- p.17 -->

序号 要点 说明
1 角色分离 授权服务器和资源服务器可以是同一服务
2 令牌选择 JWT 是常用的令牌格式，可包含用户信息
3 作用域控制 使用 scopes 限制权限范围
4 安全传输 始终使用 HTTPS
5 密码授权限制 只用于第一方应用
组件 FastAPI 实现
密码授权 OAuth2PasswordBearer + OAuth2PasswordRequestForm
客户端凭证 OAuth2ClientCredentialsBearer
令牌验证 Depends(oauth2_scheme)
依赖注入 get_current_user() 自动验证
核心要点
OAuth2 与 FastAPI
FastAPI 提供了完整的 OAuth2 支持：
