# UserProfile 表结构迁移说明

## 迁移概述

本次迁移对 UserProfile 和 UserProfileHistory 表进行了重大结构变更，以支持多用户环境和版本管理功能。

## 变更内容

### 1. UserProfile 表变更

**新增字段：**
- `user_id` (Integer, ForeignKey, Unique, Indexed): 关联的用户ID，外键指向 user 表，唯一约束保证一对一关系

**变更原因：**
- 原设计缺少用户关联，无法支持多用户环境
- 添加 user_id 后，每个用户可以拥有独立的配置

### 2. UserProfileHistory 表变更

**新增字段：**
- `user_id` (Integer, ForeignKey, Indexed): 关联的用户ID，外键指向 user 表
- `version` (Integer, Default=1): 版本号，每次更新递增，用于追踪变更顺序
- `change_reason` (String, Optional): 变更原因说明

**移除字段：**
- `profile_id`: 移除旧的关联方式，改用 user_id 直接关联用户

**变更原因：**
- 移除 profile_id 简化了关联关系
- 添加 version 字段支持版本回溯功能
- 添加 change_reason 字段记录变更原因

## 数据迁移策略

### 1. UserProfile 数据迁移

**策略：**
- 将所有旧的 UserProfile 记录关联到第一个用户（通常是管理员）
- 如果系统中有多个用户，需要手动调整数据归属

**SQL 逻辑：**
```sql
-- 添加 user_id 列
ALTER TABLE user_profile ADD COLUMN user_id INTEGER;

-- 关联到第一个用户
UPDATE user_profile SET user_id = (SELECT id FROM user LIMIT 1) WHERE user_id IS NULL;

-- 创建外键和索引
CREATE UNIQUE INDEX ix_user_profile_user_id ON user_profile(user_id);
```

### 2. UserProfileHistory 数据迁移

**策略：**
- 根据 profile_id 查找对应的 user_id
- 为历史记录分配版本号（按创建时间排序）
- 删除没有关联用户的孤立记录

**SQL 逻辑：**
```sql
-- 添加新字段
ALTER TABLE user_profile_history ADD COLUMN user_id INTEGER;
ALTER TABLE user_profile_history ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE user_profile_history ADD COLUMN change_reason VARCHAR(255);

-- 根据 profile_id 查找 user_id
UPDATE user_profile_history
SET user_id = (
    SELECT up.user_id 
    FROM user_profile up 
    WHERE up.id = user_profile_history.profile_id
)
WHERE profile_id IS NOT NULL;

-- 分配版本号
UPDATE user_profile_history
SET version = (
    SELECT COUNT(*)
    FROM user_profile_history h2
    WHERE h2.user_id = user_profile_history.user_id
    AND h2.created_at <= user_profile_history.created_at
)
WHERE user_id IS NOT NULL;

-- 删除旧字段
ALTER TABLE user_profile_history DROP COLUMN profile_id;
```

## 迁移步骤

### 1. 备份数据库

```bash
# 备份 SQLite 数据库
cp data/database.db data/database.db.backup
```

### 2. 运行迁移脚本

```bash
# 进入 backend 目录
cd backend

# 运行 Alembic 迁移
alembic upgrade head
```

### 3. 验证迁移结果

```bash
# 检查表结构
sqlite3 data/database.db "PRAGMA table_info(user_profile);"
sqlite3 data/database.db "PRAGMA table_info(user_profile_history);"

# 检查数据完整性
sqlite3 data/database.db "SELECT COUNT(*) FROM user_profile WHERE user_id IS NULL;"
sqlite3 data/database.db "SELECT COUNT(*) FROM user_profile_history WHERE user_id IS NULL;"
```

## 回滚方案

如果迁移出现问题，可以执行回滚：

```bash
# 回滚到迁移前版本
alembic downgrade -1
```

**回滚操作：**
1. 恢复 UserProfileHistory 的 profile_id 字段
2. 根据 user_id 查找对应的 profile_id
3. 删除新增的字段（user_id, version, change_reason）
4. 恢复 UserProfile 表结构

## API 变更说明

### 1. 认证要求

所有 UserProfile 相关接口现在都需要用户认证：
- 必须在请求头中携带有效的 JWT token
- 接口会自动从 token 中获取当前用户信息

**示例：**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/user_profile/
```

### 2. 新增接口

**版本回溯接口：**
```http
POST /api/v1/user_profile/rollback/{version}
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "change_reason": "回溯原因说明"
}
```

### 3. 接口响应变更

**UserProfile 响应：**
```json
{
  "id": 1,
  "user_id": 1,
  "identity": "用户身份设定",
  "rules": "个性化规则",
  "created_at": "2026-04-02T00:00:00",
  "updated_at": "2026-04-02T00:00:00"
}
```

**UserProfileHistory 响应：**
```json
{
  "id": 1,
  "user_id": 1,
  "identity": "历史版本身份设定",
  "rules": "历史版本规则",
  "version": 1,
  "change_reason": "变更原因",
  "created_at": "2026-04-02T00:00:00"
}
```

## 功能增强

### 1. 版本管理

- 每次更新配置时自动保存历史版本
- 版本号自动递增，便于追踪变更顺序
- 支持查看历史版本列表

### 2. 版本回溯

- 可以回溯到任意历史版本
- 回溯前自动备份当前配置
- 记录回溯原因，便于审计

### 3. 多用户支持

- 每个用户拥有独立的配置
- 配置变更历史按用户隔离
- 支持用户级别的权限控制

## 注意事项

1. **数据归属：** 迁移后，所有旧数据会关联到第一个用户。如果需要调整，请手动更新数据库。

2. **认证要求：** 所有接口现在都需要认证，请确保前端正确传递 JWT token。

3. **版本号管理：** 版本号从 1 开始递增，不会重复。删除历史记录不会影响版本号序列。

4. **性能优化：** 新增了多个索引，查询性能会更好，但写入性能可能略有下降（因为需要维护索引）。

5. **数据完整性：** 迁移脚本会自动清理孤立数据（没有关联用户的记录）。

## 测试验证

运行测试验证迁移是否成功：

```bash
# 运行 UserProfile 相关测试
pytest tests/api/test_user_profile.py -v

# 运行所有测试
pytest tests/ -v
```

## 常见问题

### Q1: 迁移后旧数据找不到？

**A:** 检查数据是否关联到了正确的用户：
```sql
SELECT * FROM user_profile WHERE user_id = YOUR_USER_ID;
```

### Q2: 接口返回 401 错误？

**A:** 确保请求头中包含有效的 JWT token：
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/user_profile/
```

### Q3: 版本回溯失败？

**A:** 检查目标版本是否存在：
```sql
SELECT * FROM user_profile_history WHERE user_id = YOUR_USER_ID AND version = TARGET_VERSION;
```

## 联系支持

如有问题，请联系开发团队或提交 Issue。
