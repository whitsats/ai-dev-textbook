# FastAPI应用配置信息读取

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\03FastAPI应用配置信息读取\FastAPI应用配置信息读取.pdf`
> **页数**：12（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 9,193 字符，其中汉字 1,338 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 应用配置信息读取
本文档介绍 FastAPI 应用中配置信息的读取与管理方式，包括 Pydantic Settings、环境变量、多
环境配置、敏感信息处理等核心内容。
为什么需要外部配置
在应用程序启动前，通常需要读取相关的配置参数，如应用密钥、数据库连接信息、第三方 API 密钥
等。这些配置参数一般不会硬编码到项目中，而是写入外部文件或环境变量中，以便根据不同环境（开
发、测试、生产）灵活调整。
在大型微服务架构中，还可以使用配置中心（如 Nacos、etcd 等）进行统一管理，实现不重新发布即可
变更配置。
Pydantic Settings 基础用法
FastAPI 官方推荐使用 Pydantic 的 BaseSettings 来管理配置，它支持环境变量、 .env 文件，并提供
强大的类型校验功能。
安装依赖
创建配置文件
注意： .env 文件不应提交到版本控制系统，应添加到 .gitignore 中。
pip install python-dotenv pydantic-settings
# 应用配置
DEBUG=true
TITLE="FastAPI 应用"
VERSION="1.0.0"
# 数据库配置
DATABASE_URL="postgresql://user:password@localhost:5432/mydb"
# 安全配置
SECRET_KEY="your-secret-key-here"
API_KEY="your-api-key-here"

---

<!-- p.2 -->

配置项 类型 默认值 说明
env_file
str |
None
None 环境变量文件路径
env_file_encoding str "utf-8" 文件编码格式
env prefix str ""
环境变量前缀，如 "APP_" ，字段
定义配置类
代码解释：
BaseSettings 是 Pydantic 提供的配置基类，自动读取环境变量和 .env 文件
model_config 字典配置 BaseSettings 的行为， env_file 指定环境变量文件的路径
case_sensitive=False 使环境变量不区分大小写（ DEBUG 和 debug 等效）
SecretStr 用于敏感字段，打印时自动掩码，防止敏感信息泄露
@lru_cache() 装饰器缓存配置实例，避免每次访问都重新读取和解析文件
get_settings() 函数返回全局单例配置对象
model_config 常用配置项
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
from functools import lru_cache
class Settings(BaseSettings):
# 应用配置
debug: bool = False
title: str = "FastAPI 应用"
version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$",
description="版本号")
# 数据库配置
database_url: str = Field(default="sqlite:///./app.db", description="数据库连
接")
database_password: SecretStr = Field(default=SecretStr(""), description="数据
库密码")
# 安全配置
secret_key: SecretStr = Field(default=SecretStr(""), description="应用密钥")
api_key: SecretStr = Field(default=SecretStr(""), description="API 密钥")
model_config = {
"env_file": ".env",
"env_file_encoding": "utf-8",
"case_sensitive": False,
}
@lru_cache()
def get_settings() -> Settings:
return Settings()

---

<!-- p.3 -->

配置项 类型 默认值 说明
env_prefix str
app_name 对应 APP_APP_NAME
case_sensitive bool False 是否区分大小写
extra str "ignore" 额外字段处理方式
参数 说明 示例
default 默认值 default=8000
description 字段描述 description="端口号"
ge 最小值（数字） ge=1
le 最大值（数字） le=65535
min_length 最小长度（字符串） min_length=8
max_length 最大长度（字符串） max_length=100
pattern 正则表达式 pattern=r"^\d+\.\d+$"
alias 字段别名 alias="apiKey"
在 FastAPI 中使用配置
代码解释：
get_settings() 获取全局单例配置对象，每次调用返回同一实例
配置对象直接提供类型安全的字段访问，无需手动转换类型
字段校验与验证器
Pydantic 提供了从单字段到对象级别的完整验证能力。
Field 验证参数
from fastapi import FastAPI
from settings import get_settings
app = FastAPI()
@app.get("/")
def root():
settings = get_settings()
return {
"title": settings.title,
"version": settings.version,
"debug": settings.debug,
}

---

<!-- p.4 -->

字段级验证器 field_validator
对象级验证器 model_validator
代码解释：
field_validator 验证单个字段的值，支持转换前后两个阶段（ mode="before" /
mode="after" ）
model_validator(mode="after") 在所有字段验证完成后执行，用于多个字段之间的关联校验
对象级验证常用于检查字段之间的依赖关系或业务规则约束
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
class Settings(BaseSettings):
port: int = Field(default=8000, ge=1, le=65535, description="服务端口")
version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
# 补充说明：Pydantic v2 语法，v1 需用 @validator 且无 mode 参数
@field_validator("version", mode="before")
@classmethod
def validate_version(cls, v: str) -> str:
# 完善校验逻辑：空值替换 + 格式校验兜底
if not v:
return "0.0.0"
if not cls.version.field_info.pattern.match(v):
raise ValueError(f"版本号 {v} 不符合 x.y.z 格式")
return v
model_config = {
"env_file": ".env",
}
from pydantic_settings import BaseSettings
from pydantic import model_validator
class Settings(BaseSettings):
database_url: str = ""
redis_url: str = ""
@model_validator(mode="after")
def check_urls(self):
if not self.database_url and not self.redis_url:
raise ValueError("至少需要配置 database_url 或 redis_url")
return self
model_config = {
"env_file": ".env",
}

---

<!-- p.5 -->

多环境配置与生产实践
在实际项目中，通常需要根据不同环境（开发、测试、生产）使用不同的配置。
环境感知配置
get_settings() 中使用 f".env.{env}" 动态拼接环境文件名， ENVIRONMENT 环境变量决定加载哪
套配置文件。同一套代码通过环境变量切换，无需修改代码。
对应多个 .env 文件：
.env.development ：
.env.production ：
使用方式
import os
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
debug: bool = False
database_url: str = "sqlite:///./default.db"
log_level: str = "INFO"
@property
def environment(self) -> str:
return os.getenv("ENVIRONMENT", "development")
# 移除 model_config 中的 env_file 静态配置
model_config = {
"env_file_encoding": "utf-8",
}
# 实例化时动态指定 env_file
def get_settings() -> Settings:
env = os.getenv("ENVIRONMENT", "development")
return Settings(_env_file=f".env.{env}")
DEBUG=true
DATABASE_URL="sqlite:///./dev.db"
LOG_LEVEL="DEBUG"
DEBUG=false
DATABASE_URL="postgresql://prod_user:prod_pass@db.example.com:5432/prod_db"
LOG_LEVEL="WARNING"
# 开发环境
ENVIRONMENT=development uvicorn main:app --reload
# 生产环境
ENVIRONMENT=production uvicorn main:app --host 0.0.0.0 --port 8000

---

<!-- p.6 -->

生产环境最佳实践
配置加载优先级
配置加载优先级（从高到低）：
1. 环境变量（直接设置的系统环境变量）
2. .env 文件
3. 代码默认值
代码解释：
生产环境中必须设置密钥，未设置时应主动抛出异常，而不是使用不安全的默认值
SecretStr 在打印或日志输出时自动掩码，防止敏感信息泄露
生产环境建议通过环境变量而非 .env 文件传入密钥
配置缓存优化
import os
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
class Settings(BaseSettings):
debug: bool = False
database_url: str = Field(default="sqlite:///./app.db", description="数据库连
接")
database_password: SecretStr = Field(default=SecretStr(""), description="数据
库密码")
secret_key: SecretStr = Field(default=SecretStr(""), description="应用密钥")
model_config = {
"env_file": ".env",
"case_sensitive": False,
}
def create_settings() -> Settings:
env = os.getenv("ENVIRONMENT", "development")
if env == "production":
if not os.getenv("SECRET_KEY"):
raise ValueError("生产环境必须设置 SECRET_KEY 环境变量")
return Settings()
# export DATABASE_PASSWORD="from_env"
# print(Settings().database_password) # from_env

---

<!-- p.7 -->

每次实例化 Settings 都会读取和解析配置文件，使用 @lru_cache 可以避免重复实例化：
带参数的缓存
如果需要根据环境变量动态加载配置， @lru_cache() 会根据函数参数自动生成缓存键，每个环境独立
缓存：
其他配置读取方式
from functools import lru_cache
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
debug: bool = False
title: str = "FastAPI"
version: str = "1.0.0"
model_config = {
"env_file": ".env",
}
@lru_cache()
def get_settings() -> Settings:
return Settings()
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
debug: bool = False
title: str = "FastAPI"
model_config = {
"env_file": ".env",
}
@lru_cache()
def cached_settings(env: str) -> Settings:
return Settings(_env_file=f".env.{env}")

---

<!-- p.8 -->

1. configparser（INI 文件）
config.ini 文件：
2. PyYAML（YAML 文件）
config.yaml 文件：
3. Python os 模块
import configparser
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')
debug = config.getboolean('DEFAULT', 'debug')
title = config.get('DEFAULT', 'title')
database_url = config.get('DATABASE', 'url')
[DEFAULT]
debug = true
title = FastAPI App
[DATABASE]
url = postgresql://user:pass@localhost/db
import yaml
with open('config.yaml', 'r', encoding='utf-8') as f:
config = yaml.safe_load(f)
debug = config.get('debug', False)
title = config.get('title', 'FastAPI')
debug: true
title: FastAPI App
database:
url: postgresql://user:pass@localhost/db
pool_size: 10
import os
debug = os.getenv('DEBUG', 'False').lower() == 'true'
title = os.getenv('TITLE', 'FastAPI')
database_url = os.environ.get('DATABASE_URL', '')
password = os.environ.get('DATABASE_PASSWORD', '')

---

<!-- p.9 -->

4. TOML 文件（Python 3.11+）
config.toml 文件：
完整项目示例
项目结构
config.py
import tomllib
with open('config.toml', 'rb') as f:
config = tomllib.load(f)
debug = config.get('debug', False)
title = config.get('title', 'FastAPI')
[app]
debug = true
title = "FastAPI App"
[database]
url = "postgresql://user:pass@localhost/db"
project/
├── .env # 环境变量配置
├── .env.example # 配置示例（不包含敏感信息）
├── .gitignore # 版本控制忽略
├── main.py # 应用入口
├── config.py # 配置模块
└── routers/
└── items.py # 示例路由
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
class Settings(BaseSettings):
app_name: str = Field(default="FastAPI App", description="应用名称")
debug: bool = Field(default=False, description="调试模式")
version: str = Field(default="1.0.0", description="版本号")
database_url: str = Field(default="sqlite:///./app.db", description="数据库连
接")
database_password: SecretStr = Field(default=SecretStr(""), description="数据
库密码")

---

<!-- p.10 -->

main.py
.env.example
secret_key: SecretStr = Field(default=SecretStr(""), description="应用密钥")
model_config = {
"env_file": ".env",
"env_file_encoding": "utf-8",
"case_sensitive": False,
}
@lru_cache()
def get_settings() -> Settings:
return Settings()
from fastapi import FastAPI
from config import get_settings
import uvicorn
app = FastAPI()
settings = get_settings()
@app.get("/")
def root():
return {
"app_name": settings.app_name,
"version": settings.version,
"debug": settings.debug,
}
if __name__ == "__main__":
uvicorn.run(
"main:app",
host="0.0.0.0",
port=8000,
reload=settings.debug,
)

---

<!-- p.11 -->

.gitignore
总结
1. 推荐方式：使用 pydantic-settings 管理配置，支持环境变量、类型校验和灵活配置
2. 缓存优化：使用 @lru_cache() 避免重复实例化配置对象
3. 敏感信息：使用 SecretStr 处理密码和密钥，避免明文泄露
4. 多环境：通过不同 .env 文件和 ENVIRONMENT 变量管理不同环境配置
5. 安全实践： .env 不提交到版本库，生产环境密钥从环境变量读取
# 复制此文件为 .env 并填写真实值
# 应用配置
DEBUG=false
APP_NAME="FastAPI 应用"
VERSION="1.0.0"
# 数据库配置
DATABASE_URL="postgresql://user:password@localhost:5432/mydb"
DATABASE_PASSWORD="your-password"
# 安全配置
SECRET_KEY="generate-a-secure-random-key-here"
# 环境变量文件
.env
# Python
__pycache__/
*.py[cod]
*.db
