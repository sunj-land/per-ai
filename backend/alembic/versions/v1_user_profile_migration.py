"""user_profile add user_id and version management

Revision ID: v1_user_profile_migration
Revises:
Create Date: 2026-04-02

处理 UserProfile 表结构变更：
1. 为 UserProfile 表添加 user_id 字段（外键关联 user 表）
2. 为 UserProfileHistory 表移除 profile_id 字段，添加 user_id、version、change_reason 字段
3. 迁移历史数据，确保数据完整性
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'v1_user_profile_migration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    升级数据库结构并迁移历史数据
    """
    conn = op.get_bind()

    # ========== 步骤0：检查并创建表（如果不存在） ==========
    # 检查 user_profile 表是否存在
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='user_profile'"))
    user_profile_exists = result.fetchone() is not None

    if not user_profile_exists:
        # 创建 user_profile 表（直接创建，不使用 batch mode）
        conn.execute(text("""
            CREATE TABLE user_profile (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                identity TEXT DEFAULT '',
                rules TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        """))

        # 创建唯一索引
        conn.execute(text("CREATE UNIQUE INDEX ix_user_profile_user_id ON user_profile(user_id)"))

    # 检查 user_profile_history 表是否存在
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='user_profile_history'"))
    history_exists = result.fetchone() is not None

    if not history_exists:
        # 创建 user_profile_history 表
        conn.execute(text("""
            CREATE TABLE user_profile_history (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                identity TEXT NOT NULL,
                rules TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                change_reason VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        """))

        # 创建索引
        conn.execute(text("CREATE INDEX ix_user_profile_history_user_id ON user_profile_history(user_id)"))

        # 迁移完成，直接返回
        return

    # ========== 步骤1：为 UserProfile 表添加 user_id 字段 ==========
    # 检查 user_id 列是否已存在
    result = conn.execute(text("PRAGMA table_info(user_profile)"))
    columns = [row[1] for row in result.fetchall()]

    if 'user_id' not in columns:
        # 使用 batch mode 添加 user_id 列
        with op.batch_alter_table('user_profile', schema=None) as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))

        # 创建唯一索引
        conn.execute(text("CREATE UNIQUE INDEX ix_user_profile_user_id ON user_profile(user_id)"))

    # ========== 步骤2：迁移 UserProfile 历史数据 ==========
    # 获取所有用户
    users_result = conn.execute(text("SELECT id FROM user"))
    user_ids = [row[0] for row in users_result.fetchall()]

    # 如果存在旧的 UserProfile 数据但没有 user_id，需要关联到用户
    # 策略：将所有旧数据关联到第一个用户（通常是管理员）
    if user_ids:
        first_user_id = user_ids[0]

        # 更新所有没有 user_id 的记录
        conn.execute(
            text("UPDATE user_profile SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": first_user_id}
        )

    # ========== 步骤3：修改 UserProfileHistory 表结构 ==========
    # 检查表是否存在
    result = conn.execute(text("PRAGMA table_info(user_profile_history)"))
    history_columns = [row[1] for row in result.fetchall()]

    if 'profile_id' in history_columns and 'user_id' not in history_columns:
        # 使用 batch mode 添加新字段
        with op.batch_alter_table('user_profile_history', schema=None) as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column('version', sa.Integer(), nullable=True, server_default='1'))
            batch_op.add_column(sa.Column('change_reason', sa.String(length=255), nullable=True))

        # 创建索引
        conn.execute(text("CREATE INDEX ix_user_profile_history_user_id ON user_profile_history(user_id)"))

        # ========== 步骤4：迁移 UserProfileHistory 历史数据 ==========
        # 根据 profile_id 查找对应的 user_id
        conn.execute(text("""
            UPDATE user_profile_history
            SET user_id = (
                SELECT up.user_id
                FROM user_profile up
                WHERE up.id = user_profile_history.profile_id
            )
            WHERE profile_id IS NOT NULL
        """))

        # 为历史记录分配版本号（按创建时间排序）
        conn.execute(text("""
            UPDATE user_profile_history
            SET version = (
                SELECT COUNT(*)
                FROM user_profile_history h2
                WHERE h2.user_id = user_profile_history.user_id
                AND h2.created_at <= user_profile_history.created_at
            )
            WHERE user_id IS NOT NULL
        """))

        # 删除旧的 profile_id 列
        with op.batch_alter_table('user_profile_history', schema=None) as batch_op:
            batch_op.drop_column('profile_id')

    # ========== 步骤5：清理孤立数据 ==========
    # 删除没有关联用户的 UserProfile 记录
    conn.execute(text("DELETE FROM user_profile WHERE user_id IS NULL"))

    # 删除没有关联用户的 UserProfileHistory 记录
    conn.execute(text("DELETE FROM user_profile_history WHERE user_id IS NULL"))


def downgrade() -> None:
    """
    回滚数据库结构变更
    """
    conn = op.get_bind()

    # ========== 步骤1：恢复 UserProfileHistory 表结构 ==========
    # 添加 profile_id 列
    with op.batch_alter_table('user_profile_history', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_id', sa.Integer(), nullable=True))

    # 根据 user_id 查找对应的 profile_id
    conn.execute(text("""
        UPDATE user_profile_history
        SET profile_id = (
            SELECT up.id
            FROM user_profile up
            WHERE up.user_id = user_profile_history.user_id
        )
        WHERE user_id IS NOT NULL
    """))

    # 删除新添加的字段
    conn.execute(text("DROP INDEX IF EXISTS ix_user_profile_history_user_id"))

    with op.batch_alter_table('user_profile_history', schema=None) as batch_op:
        batch_op.drop_column('change_reason')
        batch_op.drop_column('version')
        batch_op.drop_column('user_id')

    # ========== 步骤2：恢复 UserProfile 表结构 ==========
    conn.execute(text("DROP INDEX IF EXISTS ix_user_profile_user_id"))

    with op.batch_alter_table('user_profile', schema=None) as batch_op:
        batch_op.drop_column('user_id')
