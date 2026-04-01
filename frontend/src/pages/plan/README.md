# Plan (计划管理)

## 1. 页面功能描述
Plan 模块用于展示用户的目标与计划。支持通过自然语言一键生成智能计划（由大模型支持），或手动创建、查看计划的仪表盘，方便进行长期任务跟踪。

## 2. 组件结构图
- `PlanDashboard.vue` (主面板，展示所有计划进度和概览)
- `PlanCreate.vue` (计划生成与创建页面)

## 3. 数据流向说明
1. `PlanDashboard.vue` 初始化时调用 `listPlans` 拉取所有计划记录，并在界面中展示统计数据（如已完成、进行中）。
2. 在 `PlanCreate.vue` 中，用户输入自然语言目标，点击生成，调用 `generatePlan` 接口（通常为长耗时请求）。
3. 得到 AI 拆解的计划详情后，用户可以进行二次修改确认，最后调用 `createPlan` 保存到数据库，随后跳转回 Dashboard。

## 4. 依赖模块
- **API 接口**: `src/api/plan.js` (generatePlan, createPlan, listPlans, getPlan)
- **状态管理**: 可能与 `task` (具体任务) 的状态产生联动。
- **UI 库**: 基于 Arco Design 的表单和数据统计图表。

## 5. 功能扩展指导
- **甘特图展示**: 可以在 `PlanDashboard` 增加 Gantt 图视图展示各个子计划的依赖和排期。
- **流式生成**: 目前 `generatePlan` 可能为一次性返回长文本，可升级为 SSE 流式输出，让计划生成过程在前端逐字打字机显示。
