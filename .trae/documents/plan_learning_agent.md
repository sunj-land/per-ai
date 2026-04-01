# 智能学习规划 Agent 系统设计与实施计划

## 1. 系统概述
本项目旨在构建一套高可用、可扩展的智能学习规划 Agent 系统，核心功能包括自然语言目标分解、多级里程碑规划、子 Agent 内容动态生成、定时任务调度、学习进度追踪及自适应调整。系统采用前后端分离架构，后端基于 FastAPI + SQLite (WAL) + APScheduler，前端基于 Vue 3 + Arco Design，Agent 层独立部署并由后端调度。

## 2. 架构设计
### 2.1 后端架构 (Backend)
- **框架**: FastAPI (Python 3.12)
- **数据库**: SQLite (开启 WAL 模式，读写分离连接池)
- **认证**: OAuth2 (Password Flow) + JWT (RS256)
- **调度**: APScheduler (AsyncIOScheduler)
- **缓存**: Redis (用于热点元数据与分布式锁)
- **日志**: structlog (JSON 格式)
- **追踪**: OpenTelemetry (预留接入点)

### 2.2 Agent 架构 (Agents)
- **主 Agent**: `LearningPlanningAgent` (负责目标解析与规划生成)
- **子 Agent**: `ContentGenerationAgent` (负责具体内容生产，包含视频、练习、摘要等技能)
- **通信**: Backend 通过 HTTP/Internal API 调用 Agent 服务

### 2.3 前端架构 (Frontend)
- **框架**: Vue 3 + Vite
- **UI 组件**: Arco Design Vue
- **图表**: ECharts (用于进度雷达图与仪表盘)
- **交互**: 拖拽式规划预览、Markdown 渲染

## 3. 详细实施步骤

### 阶段一：后端基础建设 (Backend Foundation)
1.  **数据库模型设计 (`backend/app/models/`)**
    -   `User`: 用户基础信息 (id, username, password_hash, role, created_at)。
    -   `PlanHeader`: 学习计划主表 (plan_id, user_id, goal, deadline, status)。
    -   `PlanMilestone`: 里程碑 (milestone_id, plan_id, title, deadline)。
    -   `PlanTask`: 原子任务 (task_id, milestone_id, type, status, estimated_min)。
    -   `ContentRepo`: 内容仓库 (content_id, task_id, type, url, text, metadata)。
    -   `UserProgress`: 用户进度 (user_id, daily_study_time, completion_rate)。
    -   `EventLog`: 行为日志 (log_id, user_id, event_type, timestamp, metadata)。
    -   `UserReminder`: 提醒配置 (reminder_id, user_id, cron_expression, method)。
2.  **认证模块 (`backend/app/core/auth.py`, `api/auth.py`)**
    -   实现 OAuth2PasswordBearer 流程。
    -   集成 `passlib` 进行密码哈希。
    -   集成 `python-jose` 生成 JWT Token。
    -   实现 `get_current_user` 依赖注入。
3.  **通用服务 (`backend/app/services/`)**
    -   `BaseService`: 封装 CRUD 操作。
    -   `RedisService`: 封装缓存与分布式锁 (基于 `redis-py`)。

### 阶段二：Agent 核心逻辑 (Agent Core)
1.  **LearningPlanningAgent (`agents/instances/learning_planner.py`)**
    -   **GoalDecompositionSkill**: 调用 LLM 解析自然语言目标（提取类型、时间、现状）。
    -   **PlanGenerationSkill**: 基于知识图谱/Prompt 生成 JSON 规划（Milestones + Tasks）。
    -   **Schema**: 定义 `PlanSchema` (Pydantic)。
2.  **ContentGenerationAgent (`agents/instances/content_generator.py`)**
    -   **VideoSkill**: Mock 实现，返回随机视频 URL。
    -   **ExerciseSkill**: 调用 LLM 生成相关练习题。
    -   **SummarySkill**: 调用 LLM 生成知识点摘要。
3.  **Agent API (`agents/api/routers/`)**
    -   `/generate_plan`: 接收目标，返回 JSON。
    -   `/generate_content`: 接收任务元数据，返回 ContentPayload。

### 阶段三：业务逻辑与调度 (Business Logic & Scheduling)
1.  **计划管理服务 (`backend/app/services/plan_service.py`)**
    -   实现计划的创建、查询、状态更新。
    -   实现与 Agent 的交互逻辑（调用 Agent 生成规划）。
2.  **内容调度器 (`backend/app/services/scheduler_service.py`)**
    -   配置 APScheduler。
    -   **每日任务生成**: 每天 09:00 扫描 `PlanTask`，调用 `ContentGenerationAgent` 生成内容并存入 `ContentRepo`。
    -   **提醒推送**: 扫描 `UserReminder`，通过 `IPusher` 接口发送通知（实现 Mock/Log 推送）。
3.  **进度追踪服务 (`backend/app/services/progress_service.py`)**
    -   实现 `/progress/{user_id}` 接口，聚合 `EventLog` 数据。
    -   实现简单的 Bandit 算法（Epsilon-Greedy）调整任务难度系数。

### 阶段四：前端实现 (Frontend Implementation)
1.  **认证页面 (`frontend/src/views/login/`)**
    -   登录/注册表单，存储 JWT 到 LocalStorage。
2.  **规划中心 (`frontend/src/views/plan/`)**
    -   **创建页**: 输入目标，调用 API 生成预览，展示 JSON/树状图，确认后保存。
    -   **详情页**: 展示里程碑与任务进度。
3.  **学习仪表盘 (`frontend/src/views/dashboard/`)**
    -   展示每日学习时长、雷达图（基于 ECharts）。
4.  **Agent 可视化 (`frontend/src/views/agent/`)**
    -   展示 Agent 列表与状态。
    -   简单的 SVG 流程图展示 Agent 工作流。

### 阶段五：工程化与文档 (Engineering & Documentation)
1.  **日志与监控**
    -   配置 `structlog` 输出 JSON 日志。
    -   添加 `OpenTelemetry` 基础配置（代码层面）。
2.  **文档生成**
    -   使用 `erdiagram-mermaid` 生成 ER 图。
    -   生成 API 文档 (Swagger/Redoc)。

## 4. 关键技术决策
-   **数据库模式**: 使用 SQLite WAL 模式以支持高并发读写，未来可平滑迁移至 PostgreSQL。
-   **Agent 通信**: Backend 通过 HTTP 同步调用 Agent 生成规划（实时性要求高），通过 Scheduler 异步触发内容生成（耗时任务）。
-   **LLM 集成**: 复用现有的 `ChatService` 或 `ModelConfig` 统一管理 LLM 调用。
-   **Mock 策略**: 视频生成与外部推送采用 Mock 实现，确保系统核心逻辑可闭环测试。

## 5. 验证计划
1.  **单元测试**: 覆盖核心算法（难度调整）与工具类。
2.  **集成测试**: 模拟用户从“提交目标”到“生成规划”再到“每日任务推送”的全流程。
3.  **压力测试**: 使用 Locust 模拟 100+ 并发用户请求 API，验证 SQLite WAL 性能。
