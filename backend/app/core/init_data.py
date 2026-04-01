import logging
from sqlmodel import Session, select
from app.models.user import User, Role, UserRoleLink, UserStatus
from app.core.auth import get_password_hash
import uuid

logger = logging.getLogger(__name__)

def init_db(session: Session) -> None:
    # ========== 步骤1：初始化角色 ==========
    roles_data = [
        {"name": "admin", "description": "System Administrator", "permissions": ["*"]},
        {"name": "user", "description": "Regular User", "permissions": ["read", "write"]},
        {"name": "guest", "description": "Guest User", "permissions": ["read"]}
    ]
    
    for role_data in roles_data:
        role = session.exec(select(Role).where(Role.name == role_data["name"])).first()
        if not role:
            role = Role(**role_data)
            session.add(role)
            session.commit()
            logger.info(f"Created role: {role_data['name']}")
            
    # Refresh roles to get IDs
    admin_role = session.exec(select(Role).where(Role.name == "admin")).first()
    user_role = session.exec(select(Role).where(Role.name == "user")).first()
    guest_role = session.exec(select(Role).where(Role.name == "guest")).first()

    # ========== 步骤2：初始化用户 ==========
    users_data = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "password": "Admin@123456",
            "role": admin_role,
            "full_name": "System Administrator"
        },
        {
            "username": "user",
            "email": "user@example.com",
            "password": "User@123456",
            "role": user_role,
            "full_name": "Regular User"
        },
        {
            "username": "guest",
            "email": "guest@example.com",
            "password": "Guest@123456",
            "role": guest_role,
            "full_name": "Guest User"
        }
    ]

    for user_data in users_data:
        user = session.exec(select(User).where(User.username == user_data["username"])).first()
        if not user:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                status=UserStatus.ACTIVE,
                salt=str(uuid.uuid4()),
                role_id=user_data["role"].id
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Create link
            link = UserRoleLink(user_id=user.id, role_id=user_data["role"].id)
            session.add(link)
            session.commit()
            
            logger.info(f"Created user: {user_data['username']}")
