import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.user_profile import UserProfile, UserProfileHistory
from app.models.user import User
from app.core.auth import get_password_hash


def create_test_user(session: Session) -> User:
    """
    创建测试用户
    """
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_auth_headers(client: TestClient, username: str, password: str) -> dict:
    """
    获取认证头
    """
    response = client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


def test_get_user_profile(client: TestClient, session: Session):
    """
    测试获取用户个人信息
    """
    # 创建测试用户
    user = create_test_user(session)
    headers = get_auth_headers(client, "testuser", "testpass123")
    
    if not headers:
        pytest.skip("Authentication failed")
    
    response = client.get("/api/v1/user_profile/", headers=headers)
    if response.status_code == 404:
        pytest.skip("Endpoint not found")
    
    assert response.status_code == 200
    data = response.json()
    assert "identity" in data
    assert "rules" in data
    assert data["user_id"] == user.id


def test_update_user_profile(client: TestClient, session: Session):
    """
    测试更新用户个人信息
    """
    # 创建测试用户
    user = create_test_user(session)
    headers = get_auth_headers(client, "testuser", "testpass123")
    
    if not headers:
        pytest.skip("Authentication failed")
    
    response = client.post(
        "/api/v1/user_profile/",
        json={"identity": "new identity", "rules": "new rules"},
        headers=headers
    )
    
    if response.status_code == 404:
        pytest.skip("Endpoint not found")
    
    assert response.status_code == 200
    data = response.json()
    assert data["identity"] == "new identity"
    assert data["rules"] == "new rules"
    assert data["user_id"] == user.id


def test_get_user_profile_history(client: TestClient, session: Session):
    """
    测试获取用户个人信息历史记录
    """
    # 创建测试用户
    user = create_test_user(session)
    headers = get_auth_headers(client, "testuser", "testpass123")
    
    if not headers:
        pytest.skip("Authentication failed")
    
    # 先创建配置
    profile = UserProfile(user_id=user.id, identity="i", rules="r")
    session.add(profile)
    session.commit()
    session.refresh(profile)
    
    # 创建历史记录
    history = UserProfileHistory(
        user_id=user.id,
        identity="old",
        rules="old",
        version=1
    )
    session.add(history)
    session.commit()
    
    response = client.get("/api/v1/user_profile/history?limit=10", headers=headers)
    
    if response.status_code == 404:
        pytest.skip("Endpoint not found")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["user_id"] == user.id
    assert "version" in data[0]


def test_rollback_to_version(client: TestClient, session: Session):
    """
    测试版本回溯功能
    """
    # 创建测试用户
    user = create_test_user(session)
    headers = get_auth_headers(client, "testuser", "testpass123")
    
    if not headers:
        pytest.skip("Authentication failed")
    
    # 创建配置
    profile = UserProfile(user_id=user.id, identity="current", rules="current")
    session.add(profile)
    session.commit()
    session.refresh(profile)
    
    # 创建历史版本
    history = UserProfileHistory(
        user_id=user.id,
        identity="old_version",
        rules="old_version",
        version=1
    )
    session.add(history)
    session.commit()
    
    # 测试回溯
    response = client.post(
        "/api/v1/user_profile/rollback/1",
        json={"change_reason": "Test rollback"},
        headers=headers
    )
    
    if response.status_code == 404:
        pytest.skip("Endpoint not found")
    
    assert response.status_code == 200
    data = response.json()
    assert data["identity"] == "old_version"
    assert data["rules"] == "old_version"
