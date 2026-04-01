# RSS 模块页面文档

本文档详细说明 RSS 模块下的各个页面的功能和实现。

## 目录结构

- `RSSFeeds.vue`: RSS 订阅源管理页面
- `RSSArticles.vue`: RSS 文章列表页面
- `ArticleDetail.vue`: RSS 文章详情页面

## 页面说明

### 1. RSSFeeds.vue (订阅源管理)

**功能：**
- **UI优化**：使用 `a-page-header` 作为页面头部，`a-card` 作为内容容器，提升视觉一致性。
- **UI优化**：引入 `dayjs` 进行相对时间格式化（如 "3小时前"），提升用户体验。
- **UI优化**：使用 `a-tag` 组件展示分组和更新状态。
- **响应式**：增加移动端适配（padding调整）。
- 展示当前所有已添加的 RSS 订阅源列表。
- 提供添加新 RSS 订阅源的功能（通过 URL）。
- **新增**：支持通过 OPML 文件批量导入订阅源。
- **新增**：支持批量删除选中的订阅源。
- **新增**：支持订阅源分组管理（添加时指定分组，列表中展示分组）。
- 提供手动触发全量刷新的功能。
- 每一个订阅源显示其标题、URL、文章数量、**分组**和最后更新时间。
- 提供跳转到该订阅源下文章列表的入口。

**核心逻辑：**
- 使用 `a-table` 展示数据，支持多选（`row-selection`）。
- `loadFeeds` 方法调用后端 `/feeds/query` POST 接口获取数据。
- `handleAddFeed` 方法调用 `/feeds` POST 接口添加新源。
- `handleImportOpml` 方法读取上传的 OPML 文件内容，调用 `/feeds/import-opml` 接口批量导入。
- `handleBatchDelete` 方法获取选中行 ID，调用 `/feeds/batch-delete` 接口批量删除。

### 2. RSSArticles.vue (文章列表)

**功能：**
- **UI优化**：列表项使用 `a-card` 和 `a-list-item` 组合，增加阴影和圆角。
- **UI优化**：使用 `a-avatar` 根据订阅源标题首字母生成彩色头像，增强识别度。
- **UI优化**：优化骨架屏（Skeleton）加载效果，更贴合实际内容布局。
- 展示 RSS 文章列表，按时间倒序排列。
- **更新**：支持无限滚动加载（Infinite Scroll），滚动到底部自动加载下一页。
- 支持按 `feed_id` 筛选特定订阅源的文章（通过路由参数控制）。
- 列表项展示更多元信息：作者、分类、来源、发布时间。
- 点击文章可跳转到详情页。

**核心逻辑：**
- 使用 `a-list` 展示文章摘要信息。
- 引入 `IntersectionObserver` 监听底部哨兵元素，触发自动加载。
- `loadArticles` 方法处理分页逻辑 (`offset`, `limit`) 和筛选逻辑 (`feed_id`)，接口改为 POST `/articles/query`。
- 维护 `page`, `hasMore`, `loadingMore` 状态以控制分页和骨架屏显示。

### 3. ArticleDetail.vue (文章详情)

**功能：**
- **UI优化**：使用 `a-page-header` 统一头部导航。
- **UI优化**：内容区域使用 `a-card` 包裹，提升阅读体验。
- **Markdown支持**：自动检测文章内容是否为 Markdown，若是则使用 `markdown-it` 渲染并应用 `github-markdown-css` 样式。
- **HTML样式优化**：针对原生 HTML 内容，通过 scoped CSS (`.prose`) 优化图片（自适应宽度）、表格、代码块、引用等标签的样式。
- 展示单篇文章的完整内容。
- **新增**：展示文章作者、分类信息。
- **新增**：支持音频/视频附件（Enclosure）的直接播放或下载。
- **更新**：Markdown/JSON 导出功能包含新增字段（作者、分类、附件）。
- 提供原文链接跳转。
- 提供返回上一页的按钮。

**核心逻辑：**
- 从路由参数 `id` 获取文章 ID。
- 调用 `/articles/{id}` POST 接口获取详情。
- 根据 `enclosure_type` 判断展示 `<audio>`, `<video>` 播放器或下载链接。
- `handleExport` 方法生成包含完整元数据的 Markdown/JSON 文件。
- `isMarkdownContent` 计算属性通过简单的启发式规则（不以 `<` 开头）判断内容类型。

## API 变更说明

- 所有涉及业务逻辑的数据获取接口（列表、详情、搜索）均已迁移为 **POST** 请求。
- 请求 Header 中统一携带 `Content-Type: application/json`。
- 错误处理增加了对 401/403/429/5xx 状态码的拦截与提示。

## 更新日志

- **2026-03-15**:
    - **Fix**: 修复 RSSFeeds 模板方法与脚本定义不一致导致的运行时告警（`handleModalOk`、`handleModalCancel`、`handleImportOpml`、`handleCleanupFailed`、`handleRefreshAll`、`openAddModal`、`rowSelection` 等）。
- **2026-03-14**: 
    - **UI重构**：全面接入 Arco Design 组件库，统一 RSS 模块 UI 风格。
    - **UI重构**：优化移动端响应式布局。
    - **Feature**：ArticleDetail 新增 Markdown 渲染支持及 HTML 样式美化。
    - 初始化 RSS 模块文档。
    - 完成三个核心页面的基础功能实现。
    - 添加详细的代码注释。
    - **Update**: 全面优化 HTTP 请求方式为 POST。
    - **Update**: RSSFeeds 新增 OPML 导入、批量删除、分组功能。
    - **Update**: RSSArticles 实现无限滚动与骨架屏。
    - **Update**: ArticleDetail 支持多媒体附件与丰富元数据展示。
