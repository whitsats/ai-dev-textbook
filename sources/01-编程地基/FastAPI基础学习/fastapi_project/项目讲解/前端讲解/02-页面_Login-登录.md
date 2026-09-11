# 页面讲解：Login 登录页（图形验证码 + 获取 token）

> 页面文件：`frontend/src/views/Login.vue`

## 1. 页面职责
Login 页面负责：
- 输入账号（邮箱/用户名）与密码
- 输入图形验证码
- 调用后端登录接口获取 token
- 登录成功后：
  - token 存入 localStorage
  - user_info 存入 localStorage
  - 跳转回首页

## 2. 路由入口
路由：`/login` -> `Login.vue`

常见跳转来源：
- 访问需要登录的页面（写文章/个人中心）时被路由守卫重定向到 login

## 3. 依赖与引用
- API：`login`、`getVcodeUrl` 来自 `@/api/user.js`
- token 存储：`setToken` 来自 `@/utils/auth.js`
- 路由：`useRouter`

## 4. 调用的后端接口
### 4.1 获取图形验证码
`getVcodeUrl()` 返回字符串：`/api/user/vcode?<timestamp>`
- Login 页面将其作为 `<img :src="vcodeUrl">`
- 点击验证码图片会刷新 URL，从而刷新验证码

后端对应：`GET /api/user/vcode`
- 返回图片二进制（image/jpeg）
- 同时通过 Set-Cookie 写入 `vcode`（有效 300s）

### 4.2 登录
`login(form)` -> `POST /api/user/login`

请求体：
- `username`
- `password`
- `vcode`（用户输入的验证码）

后端逻辑要点：
- 服务端读取 cookie 中的 `vcode` 并与用户输入对比
- 成功后返回 token

## 5. 页面状态与校验
核心状态：
- `form = { username, password, vcode }`
- `vcodeUrl`
- `loading`
- `error`

校验规则：
- username/password/vcode 任何一个为空，都提示“请填写完整信息”

## 6. 登录成功后的动作
`handleLogin()` 成功流程：
1. `setToken(res.data.token)` 存到 localStorage（key=`fastapi_token`）
2. `localStorage.setItem('user_info', ...)` 存储用户信息（user_id/username/nickname/picture）
3. `router.push('/')` 回首页

说明：
- axios 请求拦截器会从 localStorage 读取 token 并自动加到 `Authorization` 头
- 后续访问需要登录的 API 时会携带 Bearer token

## 7. 失败与异常处理
- 若 res.code != 200：
  - 展示 res.msg（或“登录失败”）
  - 刷新验证码
- 捕获异常：
  - 展示错误信息

## 8. 可优化点（仅文档说明）
- 当前路由守卫跳转 login 时会带 `redirect` 参数，但 Login 成功后默认跳转 `/`。
  - 可以增强为：如果存在 redirect，则跳回 redirect。
