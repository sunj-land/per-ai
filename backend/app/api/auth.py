from datetime import datetime, timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr

from app.core.database import get_session
from app.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    get_password_hash,
    verify_password,
    verify_password_strength,
    User,
    UserStatus,
    SECRET_KEY,
    ALGORITHM
)
from app.models.user import UserCreate, UserRead, Role, UserRoleLink, LoginLog, LoginStatus
from jose import jwt, JWTError
import uuid

router = APIRouter()

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session)
):
    """
    用户登录以获取访问令牌。

    :param request: HTTP 请求对象，用于获取客户端 IP 和 User-Agent。
    :param form_data: 包含用户名和密码的 OAuth2 表单数据。
    :param session: 数据库会话对象。
    :return: 包含访问令牌和刷新令牌的字典。
    :raises HTTPException: 当用户名或密码错误、或者账户被锁定时抛出异常。
    """
    # ========== 步骤1：查找用户 ==========
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()

    # 准备日志信息
    ip = request.client.host
    user_agent = request.headers.get("user-agent")

    # ========== 步骤2：检查用户是否存在 ==========
    if not user:
        # 为了防止用户名枚举攻击，这里可以记录尝试但模糊返回
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ========== 步骤3：检查锁定状态 ==========
    if user.status == UserStatus.LOCKED:
        if user.locked_until and user.locked_until > datetime.utcnow():
            # 记录失败日志
            log = LoginLog(user_id=user.id, ip_address=ip, status=LoginStatus.FAILURE, failure_reason="Account locked", user_agent=user_agent)
            session.add(log)
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account locked until {user.locked_until}"
            )
        else:
            # 自动解锁
            user.status = UserStatus.ACTIVE
            user.failed_login_count = 0
            user.locked_until = None
            session.add(user)
            session.commit()

    # ========== 步骤4：验证密码 ==========
    if not verify_password(form_data.password, user.hashed_password):
        # 增加失败次数
        user.failed_login_count += 1
        if user.failed_login_count >= 5:
            user.status = UserStatus.LOCKED
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            reason = "Max login attempts exceeded"
        else:
            reason = "Incorrect password"

        session.add(user)
        log = LoginLog(user_id=user.id, ip_address=ip, status=LoginStatus.FAILURE, failure_reason=reason, user_agent=user_agent)
        session.add(log)
        session.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ========== 步骤5：登录成功 ==========
    user.failed_login_count = 0
    user.locked_until = None
    session.add(user)

    log = LoginLog(user_id=user.id, ip_address=ip, status=LoginStatus.SUCCESS, user_agent=user_agent)
    session.add(log)
    session.commit()

    # ========== 步骤6：生成令牌 ==========
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str = Body(..., embed=True), session: Session = Depends(get_session)):
    """
    使用刷新令牌获取新的访问令牌。

    :param refresh_token: 请求体中嵌入的刷新令牌。
    :param session: 数据库会话对象。
    :return: 包含新访问令牌和新刷新令牌的字典。
    :raises HTTPException: 当令牌无效、过期或用户状态异常时抛出。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解析 JWT
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_type: str = payload.get("type")
        if token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise credentials_exception

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Inactive user")

    # 生成新访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    # 刷新令牌轮换 (为了更好的安全性，生成一个新的刷新令牌)
    new_refresh_token = create_refresh_token(
        data={"sub": user.username}
    )

    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

@router.post("/register", response_model=UserRead)
async def register_user(user: UserCreate, session: Session = Depends(get_session)):
    """
    注册新用户。

    :param user: 包含用户注册信息的 Pydantic 模型。
    :param session: 数据库会话对象。
    :return: 注册成功的用户对象。
    :raises HTTPException: 用户名/邮箱已存在或密码强度不足时抛出。
    """
    # ========== 步骤1：检查用户名/邮箱唯一性 ==========
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    if user.email:
        db_email = session.exec(select(User).where(User.email == user.email)).first()
        if db_email:
             raise HTTPException(status_code=400, detail="Email already registered")

    # ========== 步骤2：检查密码强度 ==========
    if not verify_password_strength(user.password):
        raise HTTPException(status_code=400, detail="Password too weak. Must be at least 8 chars, contain uppercase, lowercase, digit and special char.")

    # ========== 步骤3：创建用户 ==========
    hashed_password = get_password_hash(user.password)
    # 生成随机盐值 (虽然bcrypt不需要，但为了满足需求)
    salt = str(uuid.uuid4())

    db_user = User(
        username=user.username,
        hashed_password=hashed_password,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        salt=salt,
        status=UserStatus.ACTIVE
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    # ========== 步骤4：分配默认角色 (User) ==========
    # 查找默认角色 'user'
    default_role = session.exec(select(Role).where(Role.name == "user")).first()
    if not default_role:
        # 如果不存在则创建
        default_role = Role(name="user", description="Default user role")
        session.add(default_role)
        session.commit()
        session.refresh(default_role)

    # 建立关联
    user_role = UserRoleLink(user_id=db_user.id, role_id=default_role.id)
    session.add(user_role)
    session.commit()

    # 为了返回 UserRead 中的 roles，需要刷新
    session.refresh(db_user)
    return db_user

@router.get("/me", response_model=UserRead)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    """
    获取当前登录用户的个人信息。

    :param current_user: 通过依赖注入获取的当前激活用户对象。
    :return: 当前用户对象。
    """
    return current_user

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, session: Session = Depends(get_session)):
    """
    处理忘记密码请求，生成重置令牌。

    :param request: 包含用户邮箱的请求体。
    :param session: 数据库会话对象。
    :return: 确认信息（为防止枚举，无论邮箱是否存在均返回相同信息）。
    """
    # ========== 步骤1：查找用户 ==========
    user = session.exec(select(User).where(User.email == request.email)).first()
    if not user:
        # 为了安全，不提示用户不存在
        return {"message": "If email exists, a reset link has been sent."}

    # ========== 步骤2：生成重置令牌 ==========
    token = str(uuid.uuid4())
    user.reset_token = token
    user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
    session.add(user)
    session.commit()

    # ========== 步骤3：发送邮件 (模拟) ==========
    # TODO: 集成邮件服务
    print(f"========================================")
    print(f"Password reset for {user.email}: Token = {token}")
    print(f"========================================")

    return {"message": "If email exists, a reset link has been sent."}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, session: Session = Depends(get_session)):
    """
    根据重置令牌重置用户密码。

    :param request: 包含重置令牌和新密码的请求体。
    :param session: 数据库会话对象。
    :return: 成功提示信息。
    :raises HTTPException: 令牌无效/过期或新密码强度不足时抛出。
    """
    # ========== 步骤1：验证令牌 ==========
    statement = select(User).where(User.reset_token == request.token)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    # ========== 步骤2：验证新密码强度 ==========
    if not verify_password_strength(request.new_password):
        raise HTTPException(status_code=400, detail="Password too weak")

    # ========== 步骤3：更新密码 ==========
    user.hashed_password = get_password_hash(request.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    # 重置锁定状态
    user.status = UserStatus.ACTIVE
    user.failed_login_count = 0
    user.locked_until = None

    session.add(user)
    session.commit()

    return {"message": "Password updated successfully"}
