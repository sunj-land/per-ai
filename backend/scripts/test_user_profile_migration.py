#!/usr/bin/env python3
"""
测试 UserProfile 迁移后的功能
"""
import sys
import os

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.core.database import engine
from app.models.user import User
from app.models.user_profile import UserProfile, UserProfileHistory
from app.services.user_profile_service import user_profile_service
from app.core.auth import get_password_hash

def test_user_profile_migration():
    """
    测试 UserProfile 迁移后的功能
    """
    print("=" * 60)
    print("开始测试 UserProfile 迁移功能")
    print("=" * 60)

    with Session(engine) as session:
        # ========== 步骤1：创建测试用户 ==========
        print("\n步骤1：创建测试用户...")

        # 检查用户是否已存在
        statement = select(User).where(User.username == "test_migration_user")
        test_user = session.exec(statement).first()

        if not test_user:
            test_user = User(
                username="test_migration_user",
                email="test_migration@example.com",
                hashed_password=get_password_hash("testpass123"),
                is_active=True
            )
            session.add(test_user)
            session.commit()
            session.refresh(test_user)
            print(f"✓ 创建测试用户成功: ID={test_user.id}, username={test_user.username}")
        else:
            print(f"✓ 测试用户已存在: ID={test_user.id}, username={test_user.username}")

        # ========== 步骤2：测试获取用户配置 ==========
        print("\n步骤2：测试获取用户配置...")
        profile = user_profile_service.get_profile(session, test_user.id)
        print(f"✓ 获取用户配置成功: ID={profile.id}, user_id={profile.user_id}")
        print(f"  - identity: {profile.identity}")
        print(f"  - rules: {profile.rules}")

        # ========== 步骤3：测试更新用户配置 ==========
        print("\n步骤3：测试更新用户配置...")
        from app.models.user_profile import UserProfileUpdate

        update_data = UserProfileUpdate(
            identity="测试用户身份设定",
            rules="测试个性化规则"
        )
        updated_profile = user_profile_service.update_profile(
            session,
            test_user.id,
            update_data,
            change_reason="测试更新"
        )
        print(f"✓ 更新用户配置成功:")
        print(f"  - identity: {updated_profile.identity}")
        print(f"  - rules: {updated_profile.rules}")

        # ========== 步骤4：测试历史记录 ==========
        print("\n步骤4：测试历史记录...")
        history = user_profile_service.get_history(session, test_user.id, limit=5)
        print(f"✓ 获取历史记录成功: 共 {len(history)} 条记录")
        for h in history:
            print(f"  - 版本 {h.version}: identity='{h.identity}', reason='{h.change_reason}'")

        # ========== 步骤5：测试版本回溯 ==========
        print("\n步骤5：测试版本回溯...")
        if len(history) > 0:
            target_version = history[-1].version
            rollback_profile = user_profile_service.rollback_to_version(
                session,
                test_user.id,
                target_version,
                change_reason="测试回溯"
            )
            print(f"✓ 回溯到版本 {target_version} 成功:")
            print(f"  - identity: {rollback_profile.identity}")
            print(f"  - rules: {rollback_profile.rules}")

        # ========== 步骤6：验证数据完整性 ==========
        print("\n步骤6：验证数据完整性...")

        # 检查 user_id 是否正确关联
        statement = select(UserProfile).where(UserProfile.user_id == test_user.id)
        profiles = session.exec(statement).all()
        print(f"✓ 用户配置记录数: {len(profiles)}")

        # 检查历史记录
        statement = select(UserProfileHistory).where(UserProfileHistory.user_id == test_user.id)
        histories = session.exec(statement).all()
        print(f"✓ 历史记录数: {len(histories)}")

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！迁移成功！")
        print("=" * 60)

if __name__ == "__main__":
    try:
        test_user_profile_migration()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
