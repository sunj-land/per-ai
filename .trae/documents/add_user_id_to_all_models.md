# 为所有数据结构表增加用户ID关联

## 1. 总结 (Summary)
随着系统中用户管理功能的引入，为了实现多用户的数据隔离和归属管理，本计划将对所有业务相关的数据表（包括顶级表和子表）统一增加 `user_id` 字段。同时，编写并执行一个 Python 迁移脚本，为所有的历史数据填充 `admin` 用户的 ID（`id=1`），保证现有历史数据在迁移后仍能正常使用。

## 2. 现状分析 (Current State Analysis)
- 当前项目数据库采用 SQLModel 和 SQLite。
- 虽然已有 `user` 表（且存在 `id=1` 的 `admin` 用户），但多数业务表（如 `Task`, `RSS`, `Channel`, `Chat`, `Agent` 等）缺失用户关联字段。
- 部分表已经存在表示用户关联的字段但命名不统一（例如 `attachment` 表中的 `uploader_id`，`card` 表中的 `creator_id`）。
- 历史数据直接挂在全局，未隔离。系统目前通过手写 Python/SQL 脚本进行轻量级的数据迁移，未使用 Alembic 等自动化迁移工具。

## 3. 拟议变更 (Proposed Changes)

### 3.1 修改数据模型 (`backend/app/models/*.py`)
在以下模型的 Base 类或主类中添加 `user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="所属用户ID")`：
- **`task.py`**: `TaskBase`, `TaskLog`
- **`rss.py`**: `RSSGroupBase`, `RSSFeedBase`, `RSSArticleBase`
- **`channel.py`**: `ChannelBase`, `ChannelMessageBase`
- **`chat.py`**: `ChatSessionBase`, `ChatMessageBase`
- **`agent_store.py`**: `AgentModelBase`, `SkillModelBase`, `SkillInstallRecordModel`, `SkillDependencyModel`
- **`note.py`**: `ArticleNoteBase`, `ArticleSummaryBase`
- **`user_profile.py`**: `UserProfile`, `UserProfileHistory`
- **`content.py`**: `ContentRepoBase`
- **`plan.py`**: `PlanMilestoneBase`, `PlanTaskBase`（注：`PlanHeader` 已有 `user_id`，子表也按要求添加）

针对已有类似字段的模型进行**重命名**替换：
- **`attachment.py`**: 将 `AttachmentBase` 和相关类中的 `uploader_id` 重命名为 `user_id`。
- **`card.py`**: 将 `Card`（及可能涉及到的 Base）中的 `creator_id` 重命名为 `user_id`，并在 `CardVersionBase` 中添加 `user_id`。

### 3.2 编写并执行迁移脚本 (`backend/scripts/migrate_user_id.py`)
创建一个独立的 Python 脚本，主要功能：
1. **检查 Admin 用户**：查询 `user` 表中 `id=1` 的用户是否存在。
2. **统一重命名字段**：使用 `ALTER TABLE ... RENAME COLUMN ... TO ...` 将 `attachment` 表的 `uploader_id` 和 `card` 表的 `creator_id` 重命名为 `user_id`。
3. **新增 `user_id` 字段**：遍历上述所有目标表，检查是否存在 `user_id`，若不存在则执行 `ALTER TABLE {table_name} ADD COLUMN user_id INTEGER REFERENCES user(id)`。
4. **刷新历史数据**：对所有涉及的表执行 `UPDATE {table_name} SET user_id = 1 WHERE user_id IS NULL`。

## 4. 假设与决策 (Assumptions & Decisions)
- **子表添加**：根据确认，为所有独立业务表及其子表（例如 `ChatMessage`, `PlanTask` 等）统一添加 `user_id` 字段，以实现更严格的权限查询和未来可能的解耦。
- **字段重命名**：为保持字段命名规范一致，现有业务表中的 `uploader_id` 和 `creator_id` 统一更名为 `user_id`。
- **数据迁移策略**：SQLite 3.25.0+ 已支持 `RENAME COLUMN`，这极大地简化了字段重命名的迁移步骤，我们直接采用 SQL `ALTER TABLE` 语句实现。
- **关联表 (Link Tables)**：对于纯粹多对多的关联表（如 `RSSFeedGroupLink`），本身仅负责映射关系，不需要额外添加 `user_id`，因为其关联的主体已经具备该字段。

## 5. 验证步骤 (Verification Steps)
1. 运行 `python backend/scripts/migrate_user_id.py` 并观察输出日志，确保所有目标表均处理成功。
2. 使用 `sqlite3 data/database.db ".schema"` 抽查如 `task`、`chatsession` 等表结构，确认 `user_id` 字段成功添加；检查 `attachment` 和 `card` 表，确认旧字段已被重命名。
3. 在 SQLite 中执行 `SELECT count(*) FROM task WHERE user_id IS NULL;` 等查询，确保历史数据的 `user_id` 均已被刷为 1（或非 NULL）。
4. 启动后端服务 `python main.py`，确认无任何因模型与数据库结构不匹配而导致的启动错误。