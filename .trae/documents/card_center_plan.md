# 组件卡片中心系统建设方案

## 1. 概述
本方案旨在构建一个集卡片生成、管理、预览、发布于一体的“组件卡片中心”。系统将采用“AI辅助生成 + 运行时动态渲染 + 源码持久化”的混合架构，既满足开发时的快速生成与预览，又保证生产环境的性能与稳定性。

## 2. 核心架构设计

### 2.1 后端架构 (FastAPI + SQLModel)
- **数据模型**:
  - `Card`: 存储卡片元数据（ID, 名称, 类型, 状态, 版本号, 描述）。
  - `CardVersion`: 存储卡片代码版本（代码内容, 配置参数, 变更日志）。
  - `CardApproval`: 审核记录（仅作为扩展预留，简化实现为状态字段）。
- **API 服务**:
  - `CardRouter`: 提供 RESTful 接口 (CRUD, 发布/下线, 版本回滚)。
  - `AICardService`: 封装 LLM 调用，专门用于生成 Vue3 组件代码。
- **文件管理**:
  - 提供将“已发布”卡片代码写入前端项目 `src/components/cards/generated/` 目录的能力（Local Dev 模式）。

### 2.2 前端架构 (Vue3 + Arco Design)
- **卡片管理中心**:
  - 独立的路由页面 `/card-center`。
  - 功能：卡片列表、AI 生成器（对话式）、实时预览器、参数配置表单。
- **动态渲染引擎**:
  - **开发/预览态**: 使用 `vue3-sfc-loader` 实现从后端 API 获取 `.vue` 代码字符串并在浏览器端实时编译渲染。
  - **生产/运行态**: 
    - 方案 A (推荐): “发布”即“写入文件”。卡片代码保存为物理文件，Vite 自动构建。
    - 方案 B: 运行时加载。继续使用 `vue3-sfc-loader` 加载远程代码（适合低代码平台）。
    - *本计划采用方案 A + 预览态混合模式*：预览时动态加载，确认后写入文件成为标准组件。
- **占位符系统**:
  - 扩展现有的 `MessageContent.vue`，支持解析 `{{card:card_id}}`。
  - 遇到该占位符时，调用 `<AsyncCardRenderer :id="card_id" />` 组件。

## 3. 实施步骤

### 阶段一：后端基础建设
1.  **创建数据模型**: 在 `backend/app/models/card.py` 中定义 `Card`, `CardVersion`。
2.  **实现服务层**: 
    - `CardService`: 处理数据库操作。
    - `AICardService`: 构造 System Prompt，要求 LLM 输出符合项目规范（Vue3 + Arco + Scoped CSS）的代码。
3.  **开发 API 接口**: `backend/app/api/card_center.py`，注册到 `main.py`。

### 阶段二：前端核心引擎
1.  **引入依赖**: 安装 `vue3-sfc-loader` 用于动态预览。
2.  **创建卡片容器**: 
    - `src/components/cards/DynamicCardPreview.vue`: 接收代码字符串，动态渲染。
    - `src/components/cards/AsyncCardRenderer.vue`: 根据 ID 决定是加载本地组件还是动态组件。
3.  **建立 Manifest**: 创建 `src/components/cards/cards-manifest.json` 管理本地卡片注册表。

### 阶段三：AI 卡片生成器与管理界面
1.  **开发卡片中心页**: `src/pages/card-center/CardCenter.vue`。
2.  **实现生成交互**: 左侧输入提示词（如“生成一个带有股票走势图的产品卡片”），右侧实时显示预览。
3.  **参数配置**: 自动解析组件 `props` 定义，生成对应的表单控件供用户调试。

### 阶段四：占位符与消息集成
1.  **解析器升级**: 修改 `src/components/chat/MessageContent.vue`，增加 `{{card:ID}}` 的正则匹配与替换逻辑。
2.  **渲染集成**: 将匹配到的 ID 传递给 `AsyncCardRenderer`。

### 阶段五：示例卡片库建设
1.  利用新的 AI 生成工具，生成以下标准模板并固化到项目中：
    - `ProductCard.vue` (产品展示)
    - `NewsCard.vue` (新闻资讯)
    - `UserProfileCard.vue` (用户资料)
    - `StatCard.vue` (数据统计)
    - `GuideCard.vue` (操作指引)
    - `MediaCard.vue` (多媒体)
    - `FormCard.vue` (交互表单)

## 4. 关键技术决策
- **代码生成规范**: 强制 AI 使用 `<script setup>`, `const props = defineProps`, 以及 Arco Design 组件库。
- **样式隔离**: 生成代码时强制添加 `<style scoped>`，并使用特定前缀 class。
- **安全性**: 动态渲染仅在“预览”和“开发”模式下开放高权限，生产环境建议只加载本地编译好的组件。

## 5. 验证计划
- **单元测试**: 测试 API 的 CRUD 逻辑。
- **功能验证**: 
  1. 在卡片中心输入描述，生成代码，预览成功。
  2. 点击“保存/发布”，文件出现在 `src/components/cards/generated/`。
  3. 刷新页面，卡片通过本地组件方式加载。
  4. 在聊天框发送 `{{card:ID}}`，聊天气泡正确显示卡片。
