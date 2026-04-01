# Channel (频道与消息通道)

## 1. 页面功能描述
Channel 模块主要用于管理不同消息分发通道（如 QQBot、Webhook、微信等）。允许用户浏览频道列表、查看消息发送历史、并支持手动触发消息发送测试。

## 2. 组件结构图
- `index.vue` (频道列表主页)
  - `components/operate-modal.vue` (新增/编辑频道的表单弹窗)
  - `components/send-modal.vue` (主动推送消息的测试弹窗)
  - `components/history-drawer.vue` (查看该频道的消息历史记录)

## 3. 数据流向说明
1. `index.vue` 调用 `getChannels` 拉取已配置的通道列表进行表格展示。
2. 点击新增/编辑，打开 `operate-modal.vue`，收集配置参数后调用 `createChannel` / `updateChannel`。
3. 若需测试通道连通性，通过 `send-modal.vue` 输入测试内容，调用 `sendMessage` 进行发送。
4. 查看历史时，通过 `history-drawer.vue` 传入频道 ID，分页拉取 `getChannelMessages` 的数据。

## 4. 依赖模块
- **API 接口**: `src/api/channel.js` (负责所有的 CRUD 及消息历史请求)
- **UI 组件**: `@arco-design/web-vue` (Table, Modal, Drawer, Form)

## 5. 功能扩展指导
- **支持更多通道类型**: 若需新增如钉钉、飞书等，只需在 `operate-modal.vue` 中扩展表单字段，并在对应通道枚举中注册。
- **实时消息监控**: `history-drawer.vue` 目前是主动拉取，可考虑通过 WebSocket 订阅实时查看通道的进出消息流水。
