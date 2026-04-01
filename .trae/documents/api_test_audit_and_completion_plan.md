# 后端 API 测试用例审计与补全计划 (Phase 1)

## 1. 总结 (Summary)
本项目后端（FastAPI + Python）位于 `backend/app/api` 目录下，共包含 20 个 API 路由文件，总计 138 个接口。通过审计发现，当前的测试脚本主要集中在服务层（Service）和集成测试，缺乏与 `api` 目录对应的 1:1 单元及集成测试映射。
为避免单次执行超时和超出上下文限制，本次计划**优先针对核心模块（Auth、Users、Chat）**进行 1:1 的测试用例补全，并使用现有的 `pytest` 和 `httpx` (TestClient) 框架。剩余模块将列入审计缺失清单，作为后续阶段的任务。

## 2. 现状分析 (Current State Analysis)
- **API 模块现状**：共有 `auth.py`, `users.py`, `chat.py`, `agent.py`, `rss.py` 等 20 个路由文件，138 个 Endpoints。
- **测试模块现状**：`backend/tests` 目录下仅有少量测试脚本（如 `test_agents_proxy.py`, `test_file_upload.py` 等），未严格按照 API 路由文件进行 `test_<module>.py` 的 1:1 映射。
- **冗余情况**：未发现映射到已删除 API 的冗余测试用例，现存测试多为合法且必要的 Service/Core 层测试，**无需清理删除**。
- **测试框架**：`pytest` 作为核心运行框架。

## 3. 审计报告 (Audit Report)
### 3.1 待补全测试清单（本次执行范围）
将为以下模块在 `backend/tests/api/` 下建立 1:1 测试映射：
1. **auth.py** (6个接口) -> `backend/tests/api/test_auth.py`
   - `/token` (正常登录、密码错误、账户锁定)
   - `/refresh` (正常刷新、无效Token)
   - `/register` (正常注册、邮箱/用户名冲突、弱密码拦截)
   - `/me` (正常获取、未认证拦截)
   - `/forgot-password` (正常流程)
   - `/reset-password` (正常重置、Token失效)
2. **users.py** (7个接口) -> `backend/tests/api/test_users.py`
   - 涵盖用户的 CRUD (创建、获取、更新、删除、批量删除) 以及权限角色查询。
3. **chat.py** (13个接口) -> `backend/tests/api/test_chat.py`
   - 涵盖会话管理 (创建、查询、更新、删除)
   - 消息交互 (发送、历史记录获取、反馈、收藏)
   - 其他 (SSE 事件订阅、模型列表、会话分享)

### 3.2 缺失清单（延后至后续阶段执行）
以下 17 个模块由于接口数量庞大（共计 112 个），将暂缓执行，并在后续单独作为批次处理：
`agent.py`, `agents.py`, `attachment.py`, `card_center.py`, `channel.py`, `content.py`, `endpoints.py`, `note.py`, `plan.py`, `progress.py`, `reminder.py`, `rss.py`, `schedule.py`, `schedule_ai.py`, `skill.py`, `task.py`, `user_profile.py`

### 3.3 删除清单
- **无**（现存的 8 个 `test_*.py` 脚本均为合法的集成层/服务层测试，暂无失效废弃的冗余 API 测试代码）。

## 4. 拟定变更与执行步骤 (Proposed Changes & Steps)
1. **环境准备与目录创建**：
   - 在 `backend/tests` 下创建 `api` 子目录，并添加 `__init__.py` 声明为测试包，建立清晰的 1:1 映射结构。
   - 编写或更新公用的 pytest fixtures（如获取 DB session、TestClient 初始化、Mock 当前用户等），可存放于 `backend/tests/conftest.py`。
2. **编写 `test_auth.py`**：
   - 使用 `@pytest.fixture` 创建临时测试数据库并初始化应用客户端。
   - 实现 Auth 模块 6 个接口的全覆盖（正常流程、错误异常、边界情况）。
3. **编写 `test_users.py`**：
   - 实现 Users 模块 7 个接口的全覆盖，包括超管禁止删除等特定业务逻辑的校验。
4. **编写 `test_chat.py`**：
   - 实现 Chat 模块 13 个接口的覆盖。
   - 针对流式响应 `/send` 和 SSE 端点，使用 mock 处理底层生成逻辑，验证接口封装与 HTTP 响应状态。
5. **本地 CI 验证**：
   - 在终端中运行 `cd backend && pytest tests/api/ -v`，验证新增测试全部通过。
   - 若项目已配置 pytest-cov，则附带运行覆盖率扫描以验证提升指标。

## 5. 假设与决策 (Assumptions & Decisions)
- **依赖隔离**：所有的 API 测试将使用基于 `sqlite:///:memory:` 的内存数据库（如 `test_file_upload.py` 中示范的模式），避免污染实际开发数据库。
- **依赖注入重写 (Dependency Override)**：通过 FastAPI 的 `app.dependency_overrides` 来 mock 数据库会话 (`get_session`) 和认证逻辑 (`get_current_active_user`)，从而提升测试稳定性与速度。

## 6. 验证标准 (Verification)
- 新增的三个测试文件必须成功运行，0 Failures。
- `pytest` 测试输出结果将被附在最终交付的回复中，证明测试用例可用且具备实际覆盖率。