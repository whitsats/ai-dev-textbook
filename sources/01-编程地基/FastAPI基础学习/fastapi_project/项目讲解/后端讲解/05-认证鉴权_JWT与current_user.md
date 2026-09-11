# 认证鉴权（JWT 与 current_user）

> 相关文件：
> - `backend/app/core/security.py`
> - `backend/app/dependencies/current_user.py`
> - `backend/app/api/user_api.py`

## 1. 为什么需要鉴权
项目中很多接口属于“登录用户私有操作”，比如：
- 发布/保存文章
- 上传文章头图
- 评论/回复
- 收藏/取消收藏
- 个人中心列表

这些操作需要知道当前用户是谁，因此需要 token。

## 2. JWT 的生成与校验
实现文件：`backend/app/core/security.py`

### 2.1 签发 token（create_access_token）
- 输入：payload dict
- 会自动加过期时间 `exp`
- 用 `settings.jwt_secret_key` 与 `settings.jwt_algorithm` 签名

本项目的 payload 关键字段：
- `sub`：用户 id（字符串）

### 2.2 解 token（decode_access_token）
- 若 token 无效或过期：返回 None

## 3. current_user 依赖怎么工作
实现文件：`backend/app/dependencies/current_user.py`

### 3.1 get_current_user（强制登录）
流程：
1. 从请求头读取 `Authorization`
2. 校验格式：必须是 `Bearer <token>`
3. `decode_access_token(token)` 获取 payload
4. 从 payload 读取 `sub` 得到 user_id
5. 创建 DB Session（SessionLocal），查询用户
6. 返回一个“脱敏后的用户 dict”

返回字段（给业务使用/给前端展示）：
- user_id/username/nickname/picture/job

### 3.2 get_current_user_optional（可选登录）
- 调用 get_current_user
- 若抛 `HTTPException` 则返回 None

适用场景：
- 页面既可以匿名访问，也可以登录访问
- 登录时返回更多信息（例如文章详情接口返回 is_favorite）

## 4. 登录接口与 token 的下发
登录 API：`backend/app/api/user_api.py` 的 `POST /api/user/login`

关键点：
- 先校验图形验证码：验证码存放在 cookie `vcode`
- service 校验用户名密码后返回 token
- API 层会把 token 写到 cookie `token`

## 5. 调用其它接口时 token 放哪里
> 注意：当前后端鉴权依赖读取的是 `Authorization` 请求头，而不是 cookie `token`。

因此前端调用需要：
- 在请求头携带：`Authorization: Bearer <token>`

如果前端只依赖 cookie 传递 token，那么需要在后端扩展 `get_current_user`：
- 同时支持从 cookie 读取 token

## 6. 常见问题
### 6.1 返回 401：未登录/Token 格式错误
- 没带 Authorization
- Authorization 不是 Bearer 格式
- token 已过期/无效

### 6.2 为什么 current_user 里自己创建 SessionLocal
`get_current_user` 使用 `SessionLocal()` 而不是 `Depends(get_db)` 的生成器形式，优点是依赖简单、容易复用；缺点是与其它 Depends 形式不完全一致。

如果后续希望统一风格，可以改造成：
- `get_current_user(db: Session = Depends(get_db), authorization: Optional[str]=Header(None))`

### 6.3 密码安全
- 存储：bcrypt hash（`hash_password`）
- 校验：bcrypt check（`verify_password`）
- 登录成功后返回 token，接口鉴权不再需要明文密码
