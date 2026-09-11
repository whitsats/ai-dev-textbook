# backend

基于 FastAPI + Vue3 的内容发布站点。

## 技术栈

### 后端
- **FastAPI** - 高性能 Web 框架
- **SQLAlchemy** - ORM
- **Pydantic v2** - 请求/响应数据校验
- **python-jose** - JWT Token
- **bcrypt** - 密码哈希
- **Redis** - 邮箱验证码缓存

### 前端
- **Vue 3** + Composition API
- **Vite** - 构建工具
- **Vue Router 4** - 路由
- **Axios** - HTTP 客户端

## 项目结构

```
backend/
├── app/                              # 核心业务代码
│   ├── main.py                       # create_app + lifespan + 静态资源挂载
│   ├── api/                          # API 路由层
│   ├── services/                     # Service 业务层
│   ├── dao/                          # DAO 数据访问层
│   ├── models/                       # ORM 模型
│   ├── schemas/                      # Pydantic Schema（req/res）
│   ├── config/                       # 配置（db/redis/app）
│   ├── core/                         # 安全/JWT/验证码/图片等
│   ├── common/                       # Result/response_code 等
│   └── dependencies/                 # 依赖注入 current_user / api_dp / service_dp
│
├── scripts/                           # 运维脚本（使用 backend/.venv 启动 main.py）
│   ├── start.sh                      # 启动（写 run/app.pid，日志 logs/app.log）
│   ├── stop.sh                       # 停止（按 pid 停止）
│   ├── restart.sh                    # 重启
│   └── log.sh                        # 查看日志
│
├── resource/                          # 静态资源目录（/images -> resource/images）
├── logs/                              # 日志目录（start.sh 写入 logs/app.log）
├── run/                               # 运行时文件目录（pid 等）
├── main.py                            # 入口（可直接 python main.py）
├── shuiwenzhang.sql                   # 数据库初始化脚本（MySQL）
├── pyproject.toml                     # Python 依赖
└── .env.example                       # 环境变量示例
```

## 快速开始

### 1) 后端（推荐使用 backend/.venv）

进入后端目录：

```bash
cd backend
```

创建虚拟环境并安装依赖（任选其一）：

- 方式 A：使用 `uv`（如果你项目里使用 uv 管理依赖）

```bash
uv sync
```

- 方式 B：使用 pip（如果你使用 requirements/可编辑安装）

```bash
pip install -e .
```

复制环境变量文件并按需修改：

```bash
cp .env.example .env
```

启动后端（两种方式）：

- 方式 1：直接用 `.venv` 运行 `main.py`（最推荐，和 scripts 一致）

```bash
# Linux/Mac
./.venv/bin/python main.py

# Windows (PowerShell)
.\.venv\Scripts\python.exe main.py
```

- 方式 2：使用脚本（适合后台运行 + 写日志 + stop/restart）

```bash
./scripts/start.sh
./scripts/log.sh
./scripts/stop.sh
./scripts/restart.sh
```

默认：
- 后端端口：8000
- API 文档：http://localhost:8000/docs

### 2) 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认：http://localhost:5173

## 数据库

- MySQL 数据库：`shuiwenzhang`
- 初始化脚本：`backend/shuiwenzhang.sql`

> 注意：后端启动时会执行 `Base.metadata.create_all(bind=engine)`，但仍建议先用 SQL 脚本创建库与表并导入示例数据，便于联调。

## API 概览

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/` | 首页文章列表 | 否 |
| GET | `/api/article/detail?article_id=` | 文章详情 | 可选 |
| GET | `/api/article/new-page` | 新建文章页数据 | 是 |
| POST | `/api/article/save` | 保存/发布文章 | 是 |
| POST | `/api/article/upload` | 上传头图 | 是 |
| POST | `/api/favorite/update_status` | 收藏/取消 | 是 |
| POST | `/api/comment/add` | 添加评论 | 是 |
| POST | `/api/comment/reply` | 回复评论 | 是 |
| GET | `/api/personal/` | 个人中心 | 是 |
| POST | `/api/user/reg` | 注册 | 否 |
| POST | `/api/user/login` | 登录 | 否 |
| GET | `/api/user/vcode` | 图形验证码 | 否 |
| POST | `/api/user/ecode` | 发送邮箱验证码 | 否 |
