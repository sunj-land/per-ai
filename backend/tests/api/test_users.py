import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.user import User, Role, UserRoleLink

def test_read_roles(authenticated_client: TestClient):
    response = authenticated_client.get("/api/v1/users/roles")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["name"] == "admin"

def test_read_users(authenticated_client: TestClient, mock_user: User):
    response = authenticated_client.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["items"][0]["username"] == mock_user.username

def test_read_users_with_query(authenticated_client: TestClient, mock_user: User):
    response = authenticated_client.get("/api/v1/users/?query=testuser")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1

def test_create_user(authenticated_client: TestClient, session: Session):
    response = authenticated_client.post(
        "/api/v1/users/",
        json={
            "username": "createduser",
            "email": "created@example.com",
            "password": "Password123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "createduser"
    assert "id" in data

    # Verify in DB
    db_user = session.exec(select(User).where(User.username == "createduser")).first()
    assert db_user is not None

def test_create_user_duplicate(authenticated_client: TestClient, mock_user: User):
    response = authenticated_client.post(
        "/api/v1/users/",
        json={
            "username": mock_user.username,
            "email": "another@example.com",
            "password": "Password123!"
        }
    )
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_read_user(authenticated_client: TestClient, mock_user: User):
    response = authenticated_client.get(f"/api/v1/users/{mock_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == mock_user.username

def test_read_user_not_found(authenticated_client: TestClient):
    response = authenticated_client.get("/api/v1/users/9999")
    assert response.status_code == 404

def test_update_user(authenticated_client: TestClient, mock_user: User, session: Session):
    response = authenticated_client.put(
        f"/api/v1/users/{mock_user.id}",
        json={
            "email": "updated@example.com",
            "password": "NewPassword123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "updated@example.com"

    session.refresh(mock_user)
    assert mock_user.email == "updated@example.com"

def test_update_user_not_found(authenticated_client: TestClient):
    response = authenticated_client.put(
        "/api/v1/users/9999",
        json={"email": "updated@example.com"}
    )
    assert response.status_code == 404

def test_delete_user(authenticated_client: TestClient, session: Session):
    # Create a user to delete (ID should not be 1)
    user_to_delete = User(
        username="todelete",
        email="todelete@example.com",
        hashed_password="hash"
    )
    session.add(user_to_delete)
    session.commit()
    session.refresh(user_to_delete)

    response = authenticated_client.delete(f"/api/v1/users/{user_to_delete.id}")
    assert response.status_code == 200

    deleted = session.get(User, user_to_delete.id)
    assert deleted is None

def test_delete_super_admin(authenticated_client: TestClient, session: Session):
    # Ensure a user with ID 1 exists
    admin_user = session.get(User, 1)
    if not admin_user:
        admin_user = User(
            id=1,
            username="superadmin",
            email="super@example.com",
            hashed_password="hash"
        )
        session.add(admin_user)
        session.commit()

    response = authenticated_client.delete("/api/v1/users/1")
    assert response.status_code == 403
    assert "Cannot delete super admin" in response.json()["detail"]

def test_delete_users_batch(authenticated_client: TestClient, session: Session):
    u1 = User(username="batch1", email="b1@example.com", hashed_password="h")
    u2 = User(username="batch2", email="b2@example.com", hashed_password="h")
    session.add_all([u1, u2])
    session.commit()
    
    response = authenticated_client.delete(f"/api/v1/users/?user_ids={u1.id}&user_ids={u2.id}")
    assert response.status_code == 200

    assert session.get(User, u1.id) is None
    assert session.get(User, u2.id) is None
