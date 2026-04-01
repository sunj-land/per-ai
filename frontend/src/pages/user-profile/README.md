# User Profile (个人中心)

## 1. 页面功能描述
User Profile 页面是当前登录用户的个人信息展示和编辑中心。用户可以在此查看基本信息、修改头像、修改密码以及进行系统偏好设置的调整。

## 2. 组件结构图
- `UserProfile.vue` (统一的个人中心页面)
  - 基本信息展示区块
  - 密码修改表单
  - 偏好设置选项卡

## 3. 数据流向说明
1. 初始化时，直接从 Pinia 的 `auth.js` store 获取已登录的 `user` 信息并回显。
2. 也可通过调用 `getMe` 或 `getUserProfile` (从 `user-profile.js`) 获取最新的扩展资料。
3. 用户提交修改（如修改昵称、密码等），调用对应的 `updateProfile` 或 `updatePassword` 接口。
4. 更新成功后，通过 `authStore.fetchUser()` 等方式刷新全局状态中的用户数据。

## 4. 依赖模块
- **API 接口**: `src/api/user-profile.js`, `src/api/auth.js`
- **状态管理**: `src/store/auth.js` (确保 Header 等其他组件同步更新头像/昵称)

## 5. 功能扩展指导
- **绑定第三方账号**: 可以在设置中扩展 OAuth 绑定列表（如关联 GitHub、Google）。
- **主题切换**: 若系统支持暗黑模式，可在此处扩展主题颜色、字体大小等本地设置的保存。
