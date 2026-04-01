# Agent Center (智能体与技能管理)

## 1. 页面功能描述
Agent Center 页面是智能体与技能的统一管理入口。提供展示系统中的 Agent 卡片、技能列表，支持技能的在线搜索、一键安装、同步、升级及卸载等全生命周期管理，并包含安装记录的可视化展示。

## 2. 组件结构图
- `index.vue` (主页面入口，包含 Tab 切换)
  - `AgentList.vue` (展示所有 Agent 信息)
  - `SkillList.vue` (技能列表与安装管理)
    - `SkillDetail.vue` (技能的 Markdown 详情及编辑)
  - Modal 组件 (创建/安装弹窗)
  - Drawer 组件 (抽屉式展示详情)

## 3. 数据流向说明
1. 页面初始化加载 `getAgentList` 和 `getSkillList` 获取本地数据。
2. 用户触发搜索请求时，调用 `searchSkillHub` 查询线上 Hub 的技能。
3. 用户触发安装/更新时，调用相应接口，并建立 SSE 连接 (`streamInstallProgress`)，实时在 UI 上展示进度，完成后重新加载列表。

## 4. 依赖模块
- **API 接口**: `src/api/agent-center.js` (包括 getAgentList, getSkillList, installSkillFromHub, streamInstallProgress 等)
- **状态管理**: `src/store/loading.js` (处理各个操作按钮的 loading 状态)
- **UI 组件**: `@arco-design/web-vue` (Table, Tabs, Modal, Drawer, Form)

## 5. 功能扩展指导
- **新增 Agent 属性**: 若需在 `AgentList` 增加属性展示，需修改对应 table 的 columns，并同步调整后端的 API 字段。
- **自定义安装流程**: 当前支持通过 Hub 和 URL 安装，可扩展支持本地文件上传安装，需在 `installSkill` 的接口中增加文件流处理逻辑。
