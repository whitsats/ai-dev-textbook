# 页面讲解：Register 注册页（邮箱验证码 + 注册）

> 页面文件：`frontend/src/views/Register.vue`

## 1. 页面职责
Register 页面负责：
- 输入邮箱、密码、确认密码
- 发送邮箱验证码（倒计时 60s）
- 输入邮箱验证码并提交注册
- 注册成功后跳转到登录页

## 2. 路由入口
路由：`/register` -> `Register.vue`

## 3. 依赖与引用
- API：`sendEmailCode`、`register` 来自 `@/api/user.js`
- 路由：`useRouter`

## 4. 调用的后端接口
### 4.1 发送邮箱验证码
`sendEmailCode({ email })` -> `POST /api/user/ecode`

返回：
- 成功 code=200：前端提示“验证码已发送，请查收”并开始倒计时

说明：
- 后端当前实现会把验证码写入 Redis（key=`email:code:<email>`），过期 300s
- 开发环境下后端会直接把验证码返回在 data 里（方便调试），但前端仅提示“已发送”

### 4.2 提交注册
`register(form)` -> `POST /api/user/reg`

请求体：
- username（邮箱）
- password
- second_password
- ecode（邮箱验证码）

## 5. 页面状态与校验
核心状态：
- `form = { username, password, second_password, ecode }`
- `countdown`：倒计时秒数
- `loading`：注册中
- `error/successMsg`

校验规则：
- 发送验证码前：必须输入邮箱
- 提交注册前：
  - username/password/ecode 必填
  - password 与 second_password 必须一致

## 6. 倒计时逻辑
发送验证码成功后：
- `countdown = 60`
- `setInterval` 每秒减 1
- countdown <= 0 时清理定时器

按钮状态：
- countdown > 0 时禁用“发送验证码”按钮，并显示剩余秒数

## 7. 注册成功后的动作
`handleRegister()` 成功流程：
- 显示“注册成功，即将跳转登录...”
- 1.5s 后 `router.push('/login')`

说明：
- 当前实现注册成功后不自动登录（不写 token）

## 8. 常见问题
- “验证码已发送，但收不到邮件”？
  - 后端目前是开发模式：验证码主要用于测试流程，生产环境需要接入真实邮件发送。
- “倒计时结束前无法再次发送”？
  - 这是前端的防抖策略，避免频繁请求。
