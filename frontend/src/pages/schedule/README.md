# Schedule (日程管理)

## 1. 页面功能描述
Schedule 页面用于展示、创建、更新和删除用户的日程安排及提醒事项。支持按时间、状态对日程进行筛选和分类查看。

## 2. 组件结构图
- `index.vue` (主页面，展示日程列表或日历视图)
  - `components/ScheduleForm.vue` (日程创建和编辑表单)
  - 列表/日历展示组件 (基于 Arco Design 渲染)

## 3. 数据流向说明
1. 进入页面后调用 `getSchedules` 拉取当前用户的日程数据。
2. 点击新建/编辑时弹出 `ScheduleForm.vue`，接收用户输入的标题、时间、重复规则等。
3. 表单提交后调用 `createSchedule` 或 `updateSchedule`，成功后重新刷新列表。
4. 提供快速完成或删除按钮，调用 `deleteSchedule` 后在前端直接移除或重新拉取数据。

## 4. 依赖模块
- **API 接口**: `src/api/schedule.js` (getSchedules, createSchedule, updateSchedule, deleteSchedule, getScheduleReminders)
- **工具库**: `dayjs` (用于复杂的日期时间格式化和计算)
- **状态管理**: `src/store/loading.js` (统一管理列表加载和提交表单的 loading)

## 5. 功能扩展指导
- **视图切换**: 当前可能是列表视图，可引入 FullCalendar 风格的日历视图组件以支持按月/周查看。
- **提醒机制**: 可以结合 WebSocket 或 SSE，将 `getScheduleReminders` 的数据用于全局消息通知推送。
