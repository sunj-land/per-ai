# SkillHub Skill 管理接口工具实施计划

## 一、Summary
- 目标：在现有 `agent-center` 基础上，新增一套完整的 SkillHub 搜索/安装/管理能力，覆盖后端 API、数据库持久化、前端管理页增强、实时进度（SSE）、审计日志、幂等控制与测试交付。
- 范围：按你的决策执行——SkillHub 数据源采用“HTTP Registry + 本地索引双模式兼容”；进度同步采用 SSE；统一返回格式改造范围为 `agent-center` 全量接口；冲突策略为“自动升级”；覆盖率口径为“仅 Skill 模块”。
- 交付：后端接口源码、数据库初始化脚本、前端页面源码、API 文档、测试报告（Skill 模块覆盖率≥90%）。

## 二、Current State Analysis

### 2.1 后端现状
- `backend/app/api/agent_center.py` 已有基础 Skill 接口：`/skills`、`/skills/create`、`/skills/install`（URL 安装）等，但无 SkillHub 搜索、版本管理、依赖解析、冲突检测、卸载/更新、安装记录查询。
- `backend/app/services/skill_service.py` 仅支持从 URL 下载 Python 文件并动态加载，安装流程没有任务化进度、没有依赖图与冲突治理、原子性不足（文件与 DB 事务边界分离）。
- `backend/app/models/agent_store.py` 中 `skill_store` 字段较简化，缺少版本、作者、依赖关系、安装历史、状态追踪、幂等键等结构化字段。
- 当前 `agent-center` 接口返回格式不统一（直接返回模型或默认错误），尚未统一为 `code/msg/data`。

### 2.2 前端现状
- `frontend/packages/web/src/pages/agent-center/SkillList.vue` 仅支持本地同步、创建、URL 安装；无分类过滤、高亮、安装记录列表、卸载/更新入口、实时安装日志。
- `frontend/packages/web/src/api/agent-center.js` 没有 SkillHub 搜索/安装任务进度/SSE 订阅/安装记录相关 API 封装。
- `frontend/packages/web/ARCHITECTURE.md` 当前为空，未记录 Agent/Skill 页面能力设计。

### 2.3 架构文档现状
- 根文档 `ARCHITECTURE.md` 已覆盖主要系统模块，但未包含 SkillHub 管理链路、安装事务、SSE 进度流、幂等与审计设计。

## 三、Proposed Changes

### 3.1 数据模型与数据库（直接调整现有模型）

#### 3.1.1 修改现有模型文件
- 文件：`backend/app/models/agent_store.py`
- 变更：
  - 扩展 `SkillModel` 字段：`version`、`author`、`tags`、`source_type`、`source_url`、`install_dir`、`install_status`、`last_install_at`、`last_error`、`dependency_snapshot`、`idempotency_key`、`is_deleted` 等。
  - 保留兼容字段（如 `name/description/file_path/status`），避免破坏现有读取逻辑。
- 原因：直接使用既有模型满足“直接调整现有模型”的决策，并承载版本管理与状态追踪。

#### 3.1.2 新增安装记录表与依赖关系表
- 文件：`backend/app/models/agent_store.py`（同文件新增模型）
- 新增：
  - `SkillInstallRecordModel`：记录安装/更新/卸载操作（操作人、时间、结果、日志摘要、目标版本、耗时）。
  - `SkillDependencyModel`：记录 skill 与依赖的解析结果（依赖名、约束、实际安装版本、来源）。
- 原因：满足安装历史追踪、依赖可视化、审计与排障。

#### 3.1.3 数据库初始化脚本
- 文件：`backend/scripts/init_skill_schema.sql`（新增）
- 内容：创建/补齐 skill 相关字段及新表结构（适配 SQLite）。
- 原因：满足“数据库初始化脚本”交付要求，并支持环境初始化。

### 3.2 后端服务层：SkillHub 搜索、安装编排、事务原子性

#### 3.2.1 SkillHub 客户端与索引抽象
- 文件：`backend/app/services/skillhub_client.py`（新增）
- 能力：
  - 双模式检索：HTTP Registry 查询 + 本地索引回退。
  - 支持按名称/标签/版本搜索，返回统一 DTO。
- 原因：将外部源与业务编排解耦，便于测试与扩展。

#### 3.2.2 安装编排服务
- 文件：`backend/app/services/skill_service.py`（重构）
- 变更：
  - 新增安装任务化流程：解析请求 → 幂等检查 → 查询可用版本 → 依赖解析 → 冲突检测（自动升级策略）→ 文件准备 → DB 写入 → 完成/回滚。
  - 安装目标固定 `项目根目录/skills`，自动创建并校验目录结构（`skills/<skill_name>/<version>/...`）。
  - 失败自动回滚：回滚 DB 事务并清理安装文件（临时目录+原子替换方案）。
  - 记录安装日志到安装记录表，并写入结构化日志。
- 原因：满足原子性、可追踪性与稳定性要求。

#### 3.2.3 进度实时同步（SSE）
- 文件：`backend/app/services/skill_install_progress_service.py`（新增）
- 能力：
  - 维护安装任务状态机（pending/running/success/failed）。
  - 提供事件流（步骤、百分比、日志）供 SSE 输出。
- 原因：支撑前端实时进度与日志展示。

### 3.3 后端 API：AgentCenter 全量统一 REST 返回

#### 3.3.1 新增统一响应模型
- 文件：`backend/app/api/agent_center.py`（改造）
- 变更：
  - 所有 `agent-center` 路由统一返回 `{"code": int, "msg": str, "data": any}`。
  - 保留 HTTP 状态码语义，同时统一业务响应体。
- 原因：满足“AgentCenter 全量统一返回格式”要求。

#### 3.3.2 新增 SkillHub 接口
- 文件：`backend/app/api/agent_center.py`（新增路由）
- 新增接口（RESTful）：
  - `GET /skills/hub/search`：按名称/标签/版本筛选。
  - `POST /skills/install`：按 skill 名称+版本安装（替代仅 URL 模式，保留兼容入口）。
  - `GET /skills/install/{task_id}/stream`：SSE 推送安装进度与日志。
  - `GET /skills/install-records`：安装记录分页查询。
  - `POST /skills/{skill_id}/uninstall`：卸载。
  - `POST /skills/{skill_id}/upgrade`：更新到指定版本/最新版本。
  - `GET /skills/{skill_id}/versions`：版本列表。
- 原因：完整覆盖搜索、安装、记录、生命周期管理。

#### 3.3.3 幂等与审计
- 文件：`backend/app/api/agent_center.py`、`backend/app/services/skill_service.py`
- 变更：
  - 基于请求体摘要 + 目标 skill/version + 操作类型生成幂等键，短窗口内避免重复安装。
  - 审计字段记录：用户、时间、操作、结果、失败原因。
- 原因：满足防重复安装与审计排障要求。

### 3.4 前端改造：Skill 管理页增强

#### 3.4.1 API 层增强
- 文件：`frontend/packages/web/src/api/agent-center.js`
- 新增封装：
  - `searchSkillHub(params)`
  - `installSkillFromHub(payload)`
  - `streamInstallProgress(taskId)`（SSE）
  - `getInstallRecords(params)`
  - `uninstallSkill(skillId)`
  - `upgradeSkill(skillId, payload)`
- 原因：为页面增强提供统一调用层。

#### 3.4.2 页面能力增强
- 文件：`frontend/packages/web/src/pages/agent-center/SkillList.vue`
- 变更：
  - 实时搜索框：支持模糊搜索、分类过滤、关键词高亮。
  - 一键下载/安装：触发后端安装任务并实时显示进度与日志。
  - 安装记录列表：展示状态、版本、时间、操作者；支持卸载/更新操作。
  - 异常处理：loading、错误提示、重试机制。
  - 响应式适配：桌面/移动端布局优化。
- 原因：满足前端交互与可运维性要求。

#### 3.4.3 页面拆分（若必要）
- 文件（新增，按复杂度决定）：
  - `frontend/packages/web/src/pages/agent-center/components/skill-install-progress.vue`
  - `frontend/packages/web/src/pages/agent-center/components/skill-install-records.vue`
- 原因：控制主页面复杂度并提升可维护性。

### 3.5 文档与架构同步
- 文件：
  - `ARCHITECTURE.md`（更新 root 架构文档，补充 SkillHub 管理链路）
  - `frontend/packages/web/ARCHITECTURE.md`（新增/补全前端技能管理架构说明）
  - `docs/api/README.md` 或新增 `docs/api/skillhub.md`（API 文档）
- 原因：满足“重大变更同步 ARCHITECTURE”与“API 文档交付”。

### 3.6 测试与报告

#### 3.6.1 后端测试
- 文件（新增）：
  - `backend/tests/test_skillhub_service.py`
  - `backend/tests/test_skillhub_api.py`
- 覆盖场景：
  - 搜索成功/空结果/数据源回退
  - 安装成功、依赖自动升级、冲突失败、网络异常、回滚验证
  - 幂等重复请求拦截
  - SSE 进度输出完整性

#### 3.6.2 前端测试
- 文件（新增）：
  - `frontend/packages/web/src/pages/agent-center/__tests__/SkillList.test.js`
  - 必要时补充 e2e 用例到 `frontend/packages/web/cypress/e2e/`
- 覆盖场景：
  - 搜索过滤与高亮
  - 安装流程状态变化、失败重试
  - 记录列表展示与操作回调

#### 3.6.3 测试报告
- 文件：`backend/tests/TEST_REPORT_SKILLHUB.md`（新增）
- 内容：覆盖率结果、关键用例结果、失败场景验证结论。

## 四、Assumptions & Decisions
- 已确认决策：
  - SkillHub：双模式兼容（HTTP Registry 优先，本地索引回退）。
  - 实时同步：SSE。
  - 统一返回：`agent-center` 全量接口统一 `code/msg/data`。
  - 数据库：直接调整现有模型。
  - 冲突策略：自动升级。
  - 覆盖率口径：仅 Skill 模块测试覆盖率 ≥90%。
- 关键假设：
  - 当前运行数据库为 SQLite，模型变更可通过启动初始化与脚本补齐。
  - 安装目标目录统一为项目根 `skills/`，与现有结构兼容。

## 五、Verification Steps
- 后端验证：
  - 启动后端并校验 `agent-center` 新旧接口返回体均符合 `code/msg/data`。
  - 验证 SkillHub 搜索、安装、卸载、升级、记录查询、版本查询接口。
  - 验证 SSE 安装进度事件连续性与失败日志可读性。
  - 注入异常（下载失败、依赖冲突、文件写入失败）并确认 DB/文件双回滚。
- 前端验证：
  - 页面搜索过滤/高亮、安装按钮、记录列表、卸载/更新交互链路。
  - 异常提示、重试、移动端布局展示。
  - 与 SSE 接口联调，确认实时进度与日志渲染。
- 测试验证：
  - 执行 Skill 模块后端+前端测试并统计覆盖率。
  - 输出测试报告，确认成功/失败/异常场景齐全且覆盖率达标。

