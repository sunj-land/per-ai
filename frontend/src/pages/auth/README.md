# Auth (身份认证模块)

## 1. 页面功能描述
Auth 模块提供用户登录、忘记密码以及重置密码的完整身份认证流程。包含清晰的表单校验及错误提示，确保系统访问的安全性。

## 2. 组件结构图
- `Login.vue` (登录页面)
- `ForgotPassword.vue` (发送重置邮件页面)
- `ResetPassword.vue` (根据 token 重置密码页面)

## 3. 数据流向说明
1. 用户在 `Login.vue` 输入账号密码，点击登录。
2. 触发 `login` 接口，使用 `x-www-form-urlencoded` 格式传递凭证。
3. 成功后获取 `access_token` 并存储在 `localStorage` 或全局状态中，随后路由跳转至系统首页或来源页。
4. `ForgotPassword` 收集邮箱后发送重置链接，`ResetPassword` 接收 url 中的 token 参数并结合新密码提交重置请求。

## 4. 依赖模块
- **API 接口**: `src/api/auth.js` (login, register, forgotPassword, resetPassword, getMe)
- **状态管理**: `src/store/auth.js` (保存当前登录用户信息和 token)
- **路由**: `vue-router` (控制登录后跳转以及未授权重定向拦截)

## 5. 功能扩展指导
- **新增第三方登录**: 可在 `Login.vue` 底部添加第三方登录（如 GitHub/Google）的按钮，并在 `auth.js` 中增加相应的 OAuth 回调处理接口。
- **登录方式扩展**: 若增加验证码或手机号登录，需扩展 `Login.vue` 中的表单结构并在对应 API 增加参数字段。
