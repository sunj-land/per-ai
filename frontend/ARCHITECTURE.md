# Frontend Web Architecture

## Overview
- **技术栈**：Vue 3 + Vite + Arco Design + TailwindCSS + Pinia。
- **项目定位**：作为一个综合性 AI 前端中台，集成了 Agent 技能管理、实时聊天、频道管理、日程安排和向量知识库等核心模块。
- **架构调整**：
  - 各个主页面模块下已增加独立的 `README.md`，用于详细说明该模块的功能、组件结构、数据流向及扩展建议。
  - 清理了未使用的组件（如 `HelloWorld.vue`）和冗余状态模块（如 `counter.js`）。

## Directory Structure
- `src/api/`：统一的接口请求层，封装了基于 Axios 的网络请求与数据解包（包含详细的 JSDoc 注释）。
- `src/components/`：全局共享的公共组件（卡片、聊天消息、布局等）。
- `src/pages/`：业务页面入口，按模块划分（agent-center, auth, channel, plan, rss, schedule 等）。
- `src/store/`：基于 Pinia 的全局状态管理，管理登录状态、全局 Loading 和聊天会话。
- `src/utils/`：工具函数，如 Axios 的 request 拦截器封装。

## Agent Center
- 页面入口：`src/pages/agent-center/index.vue`
- 子模块：
  - `AgentList.vue`：展示 Agent 卡片与流程图查看入口。
  - `SkillList.vue`：Skill 管理主页面，包含搜索、安装、安装记录与运维操作。
  - `SkillDetail.vue`：技能文档编辑与预览。

## Skill Management UI
- API 层：`src/api/agent-center.js`
  - 统一解包后端 `code/msg/data`。
  - 提供 SkillHub 搜索、安装、安装进度 SSE、安装记录、卸载、升级接口封装。
- 页面能力：
  - 实时搜索（模糊匹配）
  - 标签过滤与关键词高亮
  - Hub 结果安装
  - 安装记录列表
  - 卸载与升级操作
  - 安装进度实时反馈（SSE）

## Data Flow (Core)
1. 用户操作触发对应页面的 `handleXXX` 方法。
2. 页面调用 `src/api` 中的请求函数。
3. 涉及流式响应（如 Chat 或 Install SSE），在 Store 或组件中建立连接，实时更新本地 state 并在界面渲染。
4. 全局通过 `loadingStore` 统管异步请求状态，展示 Skeleton 或 Spin 动画。
