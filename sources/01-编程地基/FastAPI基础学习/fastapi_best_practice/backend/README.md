# backend

基于 FastAPI + Vue3 的内容发布站点。

## 技术栈

### 后端
- **FastAPI** - 高性能 Web 框架
- **SQLAlchemy** - ORM
- **Pydantic v2** - 请求/响应数据校验

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
│   │   ├── user_api.py               # 用户 API
│   │   ├── book_api.py               # 书籍 API
│   │   ├── health_api.py             # 健康检查
│   │   └── router.py                 # 路由注册
│   ├── services/                      # Service 业务层
│   │   ├── user_service.py
│   │   └── book_service.py
│   ├── dao/                          # DAO 数据访问层
│   │   ├── user_dao.py
│   │   └── book_dao.py
│   ├── models/                       # ORM 模型
│   │   ├── user.py
│   │   └── book.py
│   ├── schemas/                      # Pydantic Schema（req/res）
│   │   ├── req/
│   │   └── res/
│   ├── config/                       # 配置（db/redis/app）
│   ├── common/                       # Result/response_code 等
│   └── dependencies/                # 依赖注入
│       ├── api_dp/                   # API 层依赖（调用 service_dp）
│       │   ├── user_api_dp.py
│       │   └── book_api_dp.py
│       └── service_dp/               # Service 层依赖
│           ├── user_service_dp.py
│           └── book_service_dp.py
│
├── scripts/                           # 运维脚本（使用 backend/.venv 启动 main.py）
│   ├── start.sh                      # 启动（写 run/app.pid，日志 logs/app.log）
│   ├── stop.sh                       # 停止（按 pid 停止）
│   ├── restart.sh                    # 重启
│   └── log.sh                        # 查看日志
│
├── logs/                              # 日志目录（start.sh 写入 logs/app.log）
├── main.py                            # 入口（可直接 python main.py）
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


## API 概览

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 否 |
| POST | `/api/users` | 创建用户 | 否 |
| GET | `/api/users` | 用户列表 | 否 |
| POST | `/api/users/{user_id}/books` | 为用户创建书籍 | 否 |
| GET | `/api/books` | 书籍列表 | 否 |
