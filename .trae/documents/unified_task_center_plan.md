# 统一任务中心管理系统设计与实施计划

## 1. 概述 (Overview)
本计划旨在设计并开发一个统一的任务中心管理系统，用于集中管理各类自动化任务（如 RSS 爬取、脚本执行、Webhook 通知等）。系统将支持任务的全生命周期管理（增删改查、启停），并支持多种触发方式（定时、手动、API 调用）。

## 2. 现状分析 (Current State Analysis)
- **后端**：目前使用 `APScheduler` 在 `main.py` 中硬编码了 RSS 抓取任务（每 30 分钟一次）。缺乏动态管理能力，任务状态不可视，日志分散。
- **前端**：仅有 RSS 管理界面，无统一的任务管理视图。
- **需求**：
  - 支持任意脚本执行（Shell/Python）。
  - 支持 Webhook 调用（用于通知、n8n 集成）。
  - 支持学习目标的主动自动化检查。
  - 任务动态增删改查。
  - 任务执行日志记录。

## 3. 架构设计 (Architecture Design)

### 3.1 后端模型 (Backend Models)
新增 `backend/app/models/task.py`：
- **Task (任务定义)**
  - `id`: UUID
  - `name`: 任务名称
  - `description`: 任务描述
  - `type`: 任务类型 (`script`, `function`, `webhook`)
  - `payload`: 执行内容 (脚本路径 / 函数名 / URL)
  - `schedule_type`: 调度类型 (`cron`, `interval`, `date`)
  - `schedule_config`: 调度配置 (JSON, e.g., `{"minute": "30"}`)
  - `is_active`: 启用/禁用状态
  - `last_run_at`: 上次运行时间
  - `next_run_at`: 下次运行时间 (由调度器计算更新)
  - `created_at`, `updated_at`

- **TaskLog (任务日志)**
  - `id`: UUID
  - `task_id`: 关联任务 ID
  - `status`: 执行状态 (`success`, `failed`, `running`)
  - `output`: 执行输出/错误信息
  - `duration`: 执行耗时 (ms)
  - `created_at`: 开始时间

### 3.2 核心服务 (Core Service)
新增 `backend/app/services/task_service.py`：
- **TaskService 类**：
  - `initialize()`: 系统启动时从数据库加载所有激活任务到 `APScheduler`。
  - `create_task()`: 创建任务并添加到调度器。
  - `update_task()`: 更新任务信息并重启调度器中的对应任务。
  - `delete_task()`: 删除任务并从调度器移除。
  - `pause_task()` / `resume_task()`: 暂停/恢复任务。
  - `execute_task(task_id)`: 立即手动执行任务（支持异步）。
  - `_run_job(task_id)`: 实际执行逻辑（根据类型调用 subprocess / httpx / 内部函数），并记录日志。

### 3.3 API 接口 (API Endpoints)
新增 `backend/app/api/task.py`：
- `GET /api/v1/tasks`: 获取任务列表。
- `POST /api/v1/tasks`: 创建任务。
- `PUT /api/v1/tasks/{id}`: 更新任务。
- `DELETE /api/v1/tasks/{id}`: 删除任务。
- `POST /api/v1/tasks/{id}/run`: 手动触发任务。
- `POST /api/v1/tasks/{id}/pause`: 暂停任务。
- `POST /api/v1/tasks/{id}/resume`: 恢复任务。
- `GET /api/v1/tasks/{id}/logs`: 获取任务日志。

### 3.4 前端开发 (Frontend Development)
- **API 封装**: `frontend/packages/web/src/api/task.js`。
- **页面开发**: `frontend/packages/web/src/pages/task/TaskCenter.vue`。
  - 任务列表展示（卡片/表格）。
  - 任务状态开关。
  - “立即运行”按钮。
  - 查看日志弹窗。
  - 新建/编辑任务表单（支持 Cron 表达式生成器或简单配置）。
- **路由注册**: 在 `frontend/packages/web/src/router/index.js` 添加 `/task-center`。

## 4. 实施步骤 (Implementation Steps)

### 阶段一：后端核心实现 (Backend Core)
1.  [ ] 创建 `backend/app/models/task.py` 定义 `Task` 和 `TaskLog` 模型。
2.  [ ] 在 `backend/app/core/database.py` 中注册新模型（如果需要，虽然 SQLModel 通常自动发现，但需确认导入）。
3.  [ ] 创建 `backend/app/services/task_service.py` 实现调度逻辑和执行逻辑（subprocess, httpx）。
4.  [ ] 修改 `backend/app/main.py`，在 `lifespan` 中初始化 `TaskService`，替代硬编码的 RSS 任务（将 RSS 任务迁移为系统默认任务或保持共存但由 Service 管理）。
5.  [ ] 创建 `backend/app/api/task.py` 实现 CRUD 和控制接口。
6.  [ ] 在 `backend/app/main.py` 注册 `task` 路由。

### 阶段二：前端界面开发 (Frontend UI)
7.  [ ] 创建 `frontend/packages/web/src/api/task.js` 封装接口。
8.  [ ] 创建 `frontend/packages/web/src/pages/task/TaskCenter.vue` 实现管理界面。
9.  [ ] 更新 `frontend/packages/web/src/router/index.js` 添加路由。
10. [ ] 在侧边栏/导航栏添加“任务中心”入口。

### 阶段三：测试与验证 (Verification)
11. [ ] 验证脚本任务：创建一个简单的 Shell 脚本任务并执行，检查日志。
12. [ ] 验证 Webhook 任务：配置一个 Webhook（如测试 URL）并触发，检查请求。
13. [ ] 验证定时功能：设置一个短周期的任务，观察是否按时自动执行。
14. [ ] 验证启停功能：暂停任务，确认不再自动执行。

## 5. 假设与决策 (Assumptions & Decisions)
- **脚本安全**: 允许执行任意路径脚本，假设服务器环境受控，仅管理员可配置。
- **调度器**: 继续使用 `APScheduler` (`AsyncIOScheduler`)。
- **RSS 迁移**: 现有的 RSS 抓取逻辑将被封装为一个 `function` 类型的任务，初始数据迁移时可自动创建一个名为 "System RSS Fetch" 的任务。
- **学习目标**: 将作为一种特定类型的“任务”存在（例如每日提醒脚本），或者用户手动配置为 Webhook 提醒。

## 6. 验证步骤 (Verification Steps)
1.  启动后端服务，Swagger UI 应包含 `/api/v1/tasks` 相关接口。
2.  进入前端“任务中心”，应能看到任务列表（初始可能为空或包含默认 RSS 任务）。
3.  点击“新建任务”，创建一个类型为 `script` 的任务（例如 `echo "Hello World"`），保存。
4.  点击“立即运行”，稍后刷新日志，应看到 `Success` 状态和 `Hello World` 输出。
5.  设置 Cron 为每分钟执行 (`* * * * *`)，观察日志是否每分钟增加一条。
