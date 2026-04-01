import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.user import User, UserStatus
from app.core.auth import get_password_hash, create_refresh_token
from datetime import datetime, timedelta

def test_register_user_success(client: TestClient, session: Session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "Password123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "id" in data

def test_register_user_weak_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "weak"
        }
    )
    assert response.status_code == 400
    assert "Password too weak" in response.json()["detail"]

def test_register_user_duplicate(client: TestClient, mock_user: User):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": mock_user.username,
            "email": "another@example.com",
            "password": "Password123!"
        }
    )
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_login_success(client: TestClient, session: Session):
    # Create a user with a known password
    user = User(
        username="loginuser",
        email="loginuser@example.com",
        hashed_password=get_password_hash("Password123!"),
        status=UserStatus.ACTIVE
    )
    session.add(user)
    session.commit()

    response = client.post(
        "/api/v1/auth/token",
        data={"username": "loginuser", "password": "Password123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client: TestClient, session: Session):
    user = User(
        username="wrongpassuser",
        email="wrong@example.com",
        hashed_password=get_password_hash("Password123!"),
        status=UserStatus.ACTIVE
    )
    session.add(user)
    session.commit()

    response = client.post(
        "/api/v1/auth/token",
        data={"username": "wrongpassuser", "password": "WrongPassword!"}
    )
    assert response.status_code == 401

def test_login_account_locked(client: TestClient, session: Session):
    user = User(
        username="lockeduser",
        email="locked@example.com",
        hashed_password=get_password_hash("Password123!"),
        status=UserStatus.LOCKED,
        locked_until=datetime.utcnow() + timedelta(minutes=30)
    )
    session.add(user)
    session.commit()

    response = client.post(
        "/api/v1/auth/token",
        data={"username": "lockeduser", "password": "Password123!"}
    )
    assert response.status_code == 400
    assert "Account locked" in response.json()["detail"]

def test_refresh_token_success(client: TestClient, session: Session, mock_user: User):
    refresh_token = create_refresh_token(data={"sub": mock_user.username})
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

def test_refresh_token_invalid(client: TestClient):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"}
    )
    assert response.status_code == 401

def test_read_users_me(authenticated_client: TestClient):
    response = authenticated_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"

def test_forgot_password(client: TestClient, mock_user: User, session: Session):
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": mock_user.email}
    )
    assert response.status_code == 200
    
    session.refresh(mock_user)
    assert mock_user.reset_token is not None

def test_reset_password_success(client: TestClient, mock_user: User, session: Session):
    # Set a reset token
    mock_user.reset_token = "valid-reset-token"
    mock_user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
    session.add(mock_user)
    session.commit()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "valid-reset-token", "new_password": "NewPassword123!"}
    )
    assert response.status_code == 200
    
    session.refresh(mock_user)
    assert mock_user.reset_token is None

def test_reset_password_invalid_token(client: TestClient):
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "invalid-token", "new_password": "NewPassword123!"}
    )
    assert response.status_code == 400
    assert "Invalid or expired token" in response.json()["detail"]
