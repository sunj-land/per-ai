# Vector (知识库向量管理)

## 1. 页面功能描述
Vector Admin 页面用于管理系统的向量知识库（RAG 底层）。支持查看当前的向量集合（Collections）、上传文档解析并存入向量库、以及执行向量的语义检索测试。

## 2. 组件结构图
- `VectorAdmin.vue` (知识库管理的统一后台面板)
  - 集合列表视图
  - 语料上传与切分配置面板
  - 检索测试沙盒

## 3. 数据流向说明
1. 初始化调用 `getCollections` 或类似接口展示当前存在的向量数据库集合。
2. 用户上传 PDF/TXT 等文档，后端执行 Embedding 并存入向量库，前端通过轮询或长连接监控状态。
3. 在测试沙盒中输入 Query，调用 `searchVector` 接口返回 Top-K 匹配的相关文档片段，以便验证 Embedding 效果。

## 4. 依赖模块
- **API 接口**: `src/api/vector.js` (处理集合、文档向量化和搜索查询)
- **UI 组件**: `@arco-design/web-vue` (Upload 组件, Table, Card 等)

## 5. 功能扩展指导
- **切分策略可视化**: 上传文档时，可以增加让用户选择 chunk_size, overlap 等参数的表单。
- **可视化图表**: 可以通过引入 ECharts 或二维投影库，对高维向量进行降维聚类可视化展示。
