# Card Center (卡片中心) 模块说明

## 模块概述
卡片中心是一个基于 Vue3 + JS 实现的个人日常生活聚合仪表盘（Dashboard）。支持多维度的信息展示（股价、新闻、天气、任务、待办等），并提供丰富的交互功能，如卡片的显隐控制、拖拽排序、自定义布局等。

## 页面结构
- **主页面**：`src/pages/card-center/CardCenter.vue`
- **卡片组件目录**：`src/pages/card-center/components/`
  - `stock-card.vue`: 股价趋势卡片
  - `news-card.vue`: 实时新闻卡片
  - `weather-card.vue`: 天气预报卡片
  - `task-card.vue`: 任务管理卡片
  - `reminder-card.vue`: 事项提醒卡片
  - `todo-card.vue`: 待办清单卡片

## 核心特性
1. **拖拽布局**：基于 `vuedraggable` 实现卡片的自由拖拽排序。
2. **个性化配置**：支持开关各个卡片的显示与隐藏，并将用户偏好的布局顺序与可见性持久化到 `localStorage` 中（Key: `card_center_layout`）。
3. **数据缓存机制**：为避免频繁调用模拟 API 造成性能损耗，各个卡片内置了带时效性的缓存机制（如股价缓存5分钟，天气缓存1小时）。
4. **响应式设计**：使用 CSS Grid 布局，自动适配屏幕宽度（桌面端多列，移动端单列）。

## 卡片组件 API 说明 (组件内部实现)

### 1. StockCard (股价趋势)
- **依赖**：`echarts`
- **数据结构**：
  - K线数据：`[开盘价, 收盘价, 最低价, 最高价]`
- **本地缓存 Key**：`stock_data_{stockCode}`
- **功能**：输入股票代码查询，展示最近4-8周的 K线折线图，支持 Echarts 内置的缩放和悬停 tooltip。

### 2. NewsCard (实时新闻)
- **本地缓存 Key**：`news_data_{category}`
- **功能**：支持“综合、财经、科技、体育”分类切换。列表展示标题、摘要、来源及时间，点击模拟新开页。

### 3. WeatherCard (天气预报)
- **本地缓存 Key**：`weather_data_{city}`
- **功能**：支持城市搜索。展示当前温度、湿度、风速、AQI 指数，以及未来 5 天的极值温度及天气图标。

### 4. TaskCard (任务管理)
- **本地缓存 Key**：`task_data`
- **数据模型**：
  ```javascript
  {
    id: Number,
    title: String,
    deadline: String, // YYYY-MM-DD
    priority: String, // 'high' | 'medium' | 'low'
    status: String // 'pending' | 'completed'
  }
  ```
- **功能**：提供新建、编辑、删除任务功能。顶部提供进度条和状态过滤（全部/待办/已完成）。

### 5. ReminderCard (提醒事项)
- **本地缓存 Key**：`reminder_data`
- **数据模型**：
  ```javascript
  {
    id: Number,
    title: String,
    time: String, // YYYY-MM-DD HH:mm
    priority: String,
    repeat: String, // 'none' | 'daily' | 'weekly' | 'monthly'
    completed: Boolean
  }
  ```
- **功能**：弹窗式创建提醒事项，内置定时器每分钟检测一次是否到期（误差 < 60s），到期时使用 `Message` 组件全局提示。

### 6. TodoCard (待办提醒)
- **本地缓存 Key**：`lite_todo_data`
- **数据模型**：
  ```javascript
  {
    id: Number,
    text: String,
    completed: Boolean
  }
  ```
- **功能**：轻量级待办，支持输入框回车快速添加，内部列表支持独立拖拽排序。

## 开发与扩展
如果需要新增卡片：
1. 在 `components/` 目录下创建新的 Vue 组件（如 `custom-card.vue`）。
2. 在 `CardCenter.vue` 中引入该组件。
3. 在 `defaultCards` 数组中注册该卡片的 `id`、`name` 和可见性状态。
4. 在 `getCardComponent` 映射方法中添加该卡片的引用。
