# 前端 Loading 状态管理与体验优化方案

## 1. 背景与目标
在前端项目中，异步操作（如 API 请求、文件上传/下载、复杂计算等）会导致用户界面的短暂延迟或卡顿。为了提供流畅、一致且友好的用户体验，本项目实现了一套统一的 Loading 状态管理方案。

**主要目标：**
- **统一管理**：集中管理全局和局部的加载状态，避免代码冗余。
- **防止闪烁**：实现优先级管理与最小加载时间（如 300ms），避免请求过快返回导致的 UI 闪烁。
- **请求取消**：支持用户主动或在页面切换时取消未完成的请求。
- **多形态展示**：支持全屏加载、局部遮罩加载、骨架屏等多种形态。
- **错误与超时处理**：在请求失败或超时时提供友好的反馈。

## 2. 技术架构与规范

### 2.1 状态管理 (Pinia)
使用 Pinia 建立全局的 `useLoadingStore` (`src/store/loading.js`)，核心功能包括：
- `globalLoading`：布尔值，控制全屏级 Loading。
- `localLoadings`：Map/Object，通过唯一键值（Key）管理细粒度的局部 Loading。
- `activeRequests`：Map，存储当前活跃请求的 `AbortController`，用于取消请求。

### 2.2 请求拦截器 (Axios)
在统一的请求工具 `src/utils/request.js` 中：
- **请求拦截**：自动读取配置中的 `loading` 字段。如果为 `true` 则触发全局 Loading，如果为字符串则作为 Key 触发局部 Loading，并注入 `AbortSignal`。
- **响应拦截**：在请求成功、失败或超时时，自动关闭对应的 Loading 状态。

### 2.3 可复用组件 (`src/components/loading/`)
1. **GlobalLoading.vue**：挂载于 `App.vue` 的全屏遮罩层。
2. **BlockLoading.vue**：使用 Arco Design 的 `<a-spin>` 封装，支持包裹任意组件，提供局部遮罩。
3. **SkeletonLoading.vue**：骨架屏组件，用于首次数据加载时提供更好的感知性能。

## 3. 使用示例与最佳实践

### 3.1 默认全局 Loading
默认情况下，所有 API 请求如果未特别指定，可能不触发或触发默认的全局 Loading（取决于 Axios 配置）。推荐显式配置。

```javascript
// 触发全局 Loading
await request.get('/api/data', { loading: true });

// 禁用所有 Loading
await request.get('/api/data', { loading: false });
```

### 3.2 局部 Loading（推荐）
对于特定的页面模块（如表格、按钮、弹窗），推荐使用字符串标识符作为局部 Loading 的 Key。

**API 定义：**
```javascript
// src/api/user.js
export const getUserList = (params, config = {}) => {
  return request.get('/v1/users', {
    params,
    loading: 'user-list', // 唯一 Key
    ...config
  });
};
```

**组件使用：**
```vue
<template>
  <a-table
    :data="users"
    :loading="loadingStore.isLoading('user-list')"
  />
</template>

<script setup>
import { useLoadingStore } from '@/store/loading';
const loadingStore = useLoadingStore();
</script>
```

### 3.3 骨架屏应用
适用于列表首次加载或复杂页面结构的占位。

```vue
<template>
  <SkeletonLoading :loading="isLoading" :rows="3" animated>
    <div class="content">真实内容...</div>
  </SkeletonLoading>
</template>
```

### 3.4 手动控制 Loading
在非 Axios 请求（如 WebSocket、文件读取、AI 流式输出）中，可以手动调用 Store 方法。

**Chat 流式响应示例：**
```javascript
const loadingStore = useLoadingStore();

// 开始流式响应状态
loadingStore.startLoading('chat-sending');

try {
  await sendMessageStream(..., (data) => {
    // 处理流式数据...
  });
} finally {
  // 结束流式响应状态
  loadingStore.stopLoading('chat-sending');
}
```

### 3.5 取消请求
在组件卸载时或用户主动点击取消时，终止所有相关请求。

```javascript
// 在组件卸载时取消所有进行中的请求
onUnmounted(() => {
  loadingStore.cancelAll();
});
```

## 4. 优化效果与测试

- **防止闪烁 (Anti-flicker)**: `useLoadingStore` 内部设置了 300ms 的最小加载时间阈值。如果请求在 100ms 内完成，Loading 将维持至少 300ms，避免 UI 短暂闪烁。
- **并发请求管理**: 同一个 Key 的多次请求会正确更新引用计数或覆盖请求状态，确保组件不会在其中一个请求返回时错误地提前关闭 Loading。
- **请求取消与组件卸载**: 配合 Vue Router 的导航守卫或组件的 `onUnmounted` 生命周期，可调用 `loadingStore.cancelAll()` 或通过 Axios 传递的 `AbortController` 取消进行中的请求。
- **单元测试**: 使用 Vitest 对 `loading.test.js` 进行了充分测试，验证了状态切换、防闪烁延迟和请求取消功能。
- **UX 测试**: 确保动画帧率达到 60fps，骨架屏在弱网环境下提供一致的占位反馈。

## 4. 性能与 UX 测试指标

1. **流畅度**：基于 Arco Design 的 CSS 动画，确保 Loading 动画帧率达到 60fps。
2. **防闪烁**：请求响应时间 < 300ms 时，Loading 状态会延迟关闭，保证用户能看清加载动画，不产生视觉突跳。
3. **超时机制**：Axios 默认超时时间配置为 30s（部分特殊接口可覆盖），超时后自动抛出错误并关闭 Loading。
4. **离线提示**：在 Axios 拦截器中捕获网络错误，弹出 "网络错误，请检查您的连接" 提示。

## 5. 项目扫描与改造记录
本项目已全面扫描并改造了以下核心模块，均已接入统一的 Loading 状态管理：
- **认证模块 (Auth)**：登录、登出、密码重置。
- **消息中心 (Message Center)**：AI 总结、消息列表查询。
- **卡片中心 (Card Center)**：卡片列表加载、保存、发布。
- **附件管理 (Attachment)**：文件上传、列表刷新。
- **任务与计划 (Task & Plan)**：任务看板、列表、计划保存。
- **RSS & 向量库 (RSS & Vector)**：文章列表、向量数据同步。
- **Agent 中心 (SkillHub)**：技能列表、同步、搜索。
- **聊天模块 (Chat)**：会话列表、创建会话、消息流式响应。
- **频道管理 (Channel)**：频道列表、操作日志。
- **用户资料 (User Profile)**：个人信息加载、更新。

## 6. 代码规范要求
- **禁止在组件内使用 `const loading = ref(false)`** 除非是极个别脱离 API 的纯本地同步状态。
- **API 方法必须接受 `config = {}`** 并在 request 中透传，以便组件层面覆盖 Loading 配置。
- Loading Key 的命名规范为：`模块名-动作`，例如 `user-list`, `card-publish`, `attachment-upload`。
