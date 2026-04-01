import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool
from app.main import app
from app.core.database import get_session
from app.core.auth import get_current_active_user
from app.models.user import User, UserStatus, Role, UserRoleLink

# 使用内存数据库
sqlite_url = "sqlite:///:memory:"
engine = create_engine(
    sqlite_url, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
        
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="mock_user")
def mock_user_fixture(session: Session):
    role = Role(name="admin", description="System Admin")
    session.add(role)
    session.commit()
    session.refresh(role)

    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password="hashedpassword",
        status=UserStatus.ACTIVE,
        role_id=role.id
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    link = UserRoleLink(user_id=user.id, role_id=role.id)
    session.add(link)
    session.commit()
    
    return user

@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(client: TestClient, mock_user: User):
    def get_current_active_user_override():
        return mock_user
    def get_current_user_override():
        return mock_user
    
    app.dependency_overrides[get_current_active_user] = get_current_active_user_override
    from app.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = get_current_user_override
    yield client
