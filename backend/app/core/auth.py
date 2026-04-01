from datetime import datetime, timedelta
from typing import Optional, Union, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.user import User, UserStatus
import re

# Configuration
SECRET_KEY = "YOUR_SECRET_KEY_CHANGE_ME_IN_PROD" # TODO: Load from env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days
REFRESH_TOKEN_EXPIRE_DAYS = 30 # 30 days

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password_strength(password: str) -> bool:
    """
    验证密码强度：至少8位，包含大小写字母、数字、特殊字符
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_type: str = payload.get("type")
        if token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.status != UserStatus.ACTIVE:
        # Check if user is locked
        if current_user.status == UserStatus.LOCKED:
             if current_user.locked_until and current_user.locked_until > datetime.utcnow():
                 raise HTTPException(status_code=400, detail=f"Account locked until {current_user.locked_until}")
        elif current_user.status == UserStatus.DISABLED:
            raise HTTPException(status_code=400, detail="Inactive user")

    return current_user

def check_permissions(required_permissions: List[str]):
    """
    权限检查依赖
    """
    async def permission_checker(current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
        # Super admin bypass
        # assuming 'admin' role has all permissions or check explicit permission
        # For simplicity, let's fetch user roles and their permissions

        # Load roles (SQLModel relationships are lazy by default unless joined)
        # We need to make sure roles are loaded. current_user might not have them loaded if not joined.
        # But we can access current_user.roles if lazy loading works or we re-fetch.

        # Since get_current_user doesn't do join, accessing .roles triggers a DB query if session is active.
        # However, FastAPI dependency injection session scope might be tricky.
        # Let's assume lazy loading works with the injected session.

        user_permissions = set()
        for role in current_user.roles:
            if role.name == "admin": # System Admin has all permissions
                return current_user
            if role.permissions:
                # Role permissions are stored as list of strings in JSON
                user_permissions.update(role.permissions)

        for perm in required_permissions:
            if perm not in user_permissions:
                 raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user

    return permission_checker
