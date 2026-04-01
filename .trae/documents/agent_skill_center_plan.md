# Agent 和 Skill 中心开发计划

## 1. 目标与范围
构建一个“Agent和Skill中心”，允许用户查看当前系统中可用的 Agent 和 Skill，并支持通过远程 URL 安装新的 Skill。
主要功能：
- **Agent 管理**：查看列表、查看工作流（Mermaid 可视化）。
- **Skill 管理**：查看列表、查看 Markdown 说明、通过 URL 安装/注册。
- **持久化**：使用数据库存储 Agent 和 Skill 的元数据。

## 2. 架构设计

### 2.1 数据库模型 (SQLModel)
在 `backend/app/models/` 下新增 `agent_store.py`（避免与 `agents/` 目录混淆）：
- **AgentModel**:
  - `id`: UUID (Primary Key)
  - `name`: String (Unique)
  - `description`: String
  - `type`: String (e.g., 'workflow', 'standard')
  - `status`: String ('active', 'inactive')
  - `config`: JSON (可选，存储配置)
  - `created_at`: DateTime
  - `updated_at`: DateTime

- **SkillModel**:
  - `id`: UUID (Primary Key)
  - `name`: String (Unique)
  - `description`: String (支持 Markdown)
  - `install_url`: String (安装来源 URL)
  - `file_path`: String (本地存储路径)
  - `status`: String ('active', 'error')
  - `input_schema`: JSON
  - `output_schema`: JSON
  - `created_at`: DateTime
  - `updated_at`: DateTime

### 2.2 后端服务
- **AgentService**:
  - `sync_agents()`: 启动时扫描 `agents/` 目录下的 `MasterAgent` 等，同步到数据库。
  - `get_agent_graph(agent_id)`: 获取 Agent 的 Mermaid 流程图定义。
- **SkillService**:
  - `install_skill(url)`: 下载 Python 文件 -> 存储到 `backend/app/custom_skills/` -> 动态加载 -> 解析元数据 -> 存入数据库。
  - `get_skill_markdown(skill_id)`: 获取 Skill 的详细说明（docstring 或专门的字段）。

### 2.3 API 接口
- `GET /api/v1/agents`: 获取 Agent 列表
- `GET /api/v1/agents/{id}`: 获取 Agent 详情（含 Mermaid）
- `GET /api/v1/skills`: 获取 Skill 列表
- `POST /api/v1/skills`: 注册 Skill (Body: `{url: "..."}`)
- `GET /api/v1/skills/{id}`: 获取 Skill 详情

### 2.4 前端页面 (Vue3 + Arco Design)
- **路由**: `/agent-center`
- **页面结构**:
  - `index.vue`: 包含两个 Tab (`Agents`, `Skills`)。
  - **Agent Tab**:
    - 卡片列表展示 Agent。
    - 点击卡片弹出详情抽屉，使用 `mermaid` 渲染工作流图。
  - **Skill Tab**:
    - 表格/卡片展示 Skill。
    - “安装 Skill” 按钮 -> 弹出模态框输入 URL。
    - 点击 Skill 查看详情抽屉，渲染 Markdown 说明。

## 3. 实施步骤

### Phase 1: 后端基础建设
1.  **创建数据模型**: 在 `backend/app/models/agent_store.py` 中定义 `AgentModel` 和 `SkillModel`。
2.  **更新数据库迁移**: 确保新表被创建（如果是自动建表则无需手动迁移，视项目配置而定）。
3.  **创建存储目录**: 创建 `backend/app/custom_skills/` 用于存放下载的 Skill。

### Phase 2: 后端逻辑实现
4.  **实现 SkillService**:
    - 编写文件下载逻辑。
    - 编写动态加载 Python 模块逻辑 (`importlib`)。
    - 编写元数据解析逻辑（从类中提取 name, description 等）。
5.  **实现 AgentService**:
    - 编写 `sync_agents`，将 `MasterAgent` 注册进数据库。
    - 编写 `get_graph_mermaid`，调用 `langgraph` 的绘图方法。
6.  **实现 API 路由**: 创建 `backend/app/api/v1/endpoints/agent_store.py`，暴露相关接口。
7.  **注册路由**: 在 `backend/app/main.py` 中注册新路由。

### Phase 3: 前端页面开发
8.  **封装 API**: 在 `frontend/src/api/agent-center.js` 中封装接口请求。
9.  **开发 Agent 列表页**: 实现展示和详情查看（集成 `mermaid`）。
10. **开发 Skill 列表页**: 实现展示、安装模态框、详情查看（Markdown 渲染）。
11. **路由配置**: 在 `frontend/src/router/index.js` 添加 `/agent-center`。

### Phase 4: 验证与集成
12. **验证 Agent 可视化**: 确保 `MasterAgent` 的图能正确生成 Mermaid 并在前端渲染。
13. **验证 Skill 安装**: 测试从 URL 下载简单的 Python Skill 文件并注册成功。
14. **集成测试**: 确保注册的 Skill/Agent 数据持久化正确。

## 4. 假设与依赖
- **假设**: 用户提供的 URL 指向直接可用的 Python 文件（`.py`），且该文件定义了一个兼容的 Skill 类。
- **依赖**: 
  - 后端：`langgraph` (已存在), `httpx` (用于下载), `importlib` (标准库)。
  - 前端：`mermaid` (需安装), `markdown-it` (已存在)。

## 5. 风险控制
- **安全风险**: 动态加载远程代码有执行恶意代码的风险。
  - *对策*: 添加显眼的警告信息，建议仅在开发环境或受信任网络中使用。
- **兼容性**: 远程 Skill 可能依赖缺失的库。
  - *对策*: 捕获加载错误，返回友好的错误信息，提示用户手动安装依赖或检查代码。
