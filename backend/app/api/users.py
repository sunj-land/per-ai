from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from app.core.database import get_session
from app.core.auth import get_current_active_user, check_permissions, get_password_hash
from app.models.user import User, UserRead, UserUpdate, Role, UserRoleLink, UserCreate, UserListResponse, UserStatus

router = APIRouter()

@router.get("/roles", response_model=List[Role], dependencies=[Depends(check_permissions(["user:list"]))], summary="获取角色列表")
async def read_roles(session: Session = Depends(get_session)):
    """
    获取系统中所有的角色记录。
    需要用户具有 `user:list` 权限。

    Args:
        session (Session): 数据库会话。

    Returns:
        List[Role]: 包含所有角色的列表。
    """
    roles = session.exec(select(Role)).all()
    return roles

@router.get("", response_model=UserListResponse, dependencies=[Depends(check_permissions(["user:list"]))], summary="获取用户列表")
async def read_users(
    skip: int = Query(0, description="分页偏移量"),
    limit: int = Query(100, description="每页最大记录数"),
    query: Optional[str] = Query(None, description="搜索关键字（匹配用户名、邮箱或手机号）"),
    status: Optional[UserStatus] = Query(None, description="按用户状态过滤"),
    session: Session = Depends(get_session)
):
    """
    分页获取用户列表，支持按关键字和状态进行过滤。
    需要用户具有 `user:list` 权限。

    业务逻辑：
    1. 构建基础查询语句。
    2. 如果提供了关键字，则在用户名、邮箱和手机号中进行模糊匹配。
    3. 如果提供了状态，则按指定状态进行精确过滤。
    4. 执行 Count 查询以获取总记录数。
    5. 应用分页并使用 `selectinload` 预加载用户的关联角色。

    Args:
        skip (int, optional): 分页偏移量。
        limit (int, optional): 返回限制数量。
        query (Optional[str], optional): 模糊搜索关键字。
        status (Optional[UserStatus], optional): 指定的用户状态。
        session (Session): 数据库会话。

    Returns:
        UserListResponse: 包含用户项列表及总数的响应模型。
    """
    base_statement = select(User)

    if query:
        base_statement = base_statement.where(
            (User.username.contains(query)) |
            (User.email.contains(query)) |
            (User.phone.contains(query))
        )

    if status:
        base_statement = base_statement.where(User.status == status)

    # Count total efficiently / 高效计算总数
    count_statement = select(func.count()).select_from(base_statement.subquery())
    total = session.exec(count_statement).one()

    # Pagination with eager loading / 使用预加载进行分页查询
    statement = base_statement.options(selectinload(User.roles)).offset(skip).limit(limit)
    users = session.exec(statement).all()

    return UserListResponse(items=users, total=total)

@router.post("", response_model=UserRead, dependencies=[Depends(check_permissions(["user:create"]))], summary="创建新用户")
async def create_user(
    user: UserCreate,
    session: Session = Depends(get_session)
):
    """
    创建一个新的用户账号。
    需要用户具有 `user:create` 权限。

    业务逻辑：
    1. 检查用户名是否已存在，存在则抛出 400 错误。
    2. 对传入的明文密码进行哈希加密处理。
    3. 提取请求体中的 `role_ids` 并构建 User 对象进行保存。
    4. 如果分配了角色，则更新 `role_id` 字段并创建多对多关联记录 (`UserRoleLink`)。

    Args:
        user (UserCreate): 包含用户名、密码及角色等信息的数据模型。
        session (Session): 数据库会话。

    Returns:
        UserRead: 创建成功后的用户详细信息。

    Raises:
        HTTPException: 用户名已注册时抛出 400 错误。
    """
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)

    # Create User object manually to handle extra fields in UserCreate
    # 手动创建 User 对象以处理 UserCreate 中不需要直接存入 User 表的字段
    user_data = user.dict(exclude_unset=True)
    user_data.pop("password", None)
    role_ids = user_data.pop("role_ids", [])

    user_data["hashed_password"] = hashed_password
    db_user = User(**user_data)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    # Assign roles / 分配角色
    if role_ids:
        # Update legacy role_id with the first role / 为向后兼容更新旧的 role_id 字段
        db_user.role_id = role_ids[0]
        session.add(db_user)

        for rid in role_ids:
            link = UserRoleLink(user_id=db_user.id, role_id=rid)
            session.add(link)
        session.commit()
        session.refresh(db_user)

    return db_user

@router.get("/{user_id}", response_model=UserRead, dependencies=[Depends(check_permissions(["*"]))], summary="获取用户详情")
async def read_user(user_id: int, session: Session = Depends(get_session)):
    """
    根据用户 ID 获取指定用户的详细信息。
    需要具备超级管理员 (`*`) 权限或其他相应权限（此处的权限依赖配置为 `*`）。

    Args:
        user_id (int): 目标用户的 ID。
        session (Session): 数据库会话。

    Returns:
        UserRead: 指定用户的详细信息。

    Raises:
        HTTPException: 用户不存在时抛出 404 错误。
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserRead, dependencies=[Depends(check_permissions(["user:update"]))], summary="更新用户")
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    session: Session = Depends(get_session)
):
    """
    更新指定用户的详细信息。
    需要具有 `user:update` 权限。

    业务逻辑：
    1. 查找指定用户，不存在则抛出 404。
    2. 如果更新内容中包含密码，则对其进行哈希加密后再保存。
    3. 如果包含角色更新 (`role_ids`)：
       - 更新向后兼容的 `role_id` 字段。
       - 清空原有的所有角色关联 (`UserRoleLink`)。
       - 重新建立新的角色关联。
    4. 更新其他常规字段并保存。

    Args:
        user_id (int): 要更新的用户 ID。
        user_update (UserUpdate): 包含要更新的数据。
        session (Session): 数据库会话。

    Returns:
        UserRead: 更新成功后的用户详细信息。

    Raises:
        HTTPException: 用户不存在时抛出 404 错误。
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = user_update.dict(exclude_unset=True)
    if "password" in user_data and user_data["password"]:
        user_data["hashed_password"] = get_password_hash(user_data["password"])
        del user_data["password"]

    # Handle role_ids if present in body / 处理请求体中可能存在的角色列表
    role_ids = user_data.pop("role_ids", None)

    for key, value in user_data.items():
        setattr(db_user, key, value)

    # Update roles if provided / 如果提供了新角色列表，进行更新
    if role_ids is not None:
        # Update legacy role_id / 更新向后兼容的 role_id 字段
        if role_ids:
            db_user.role_id = role_ids[0]
        else:
            db_user.role_id = None
        session.add(db_user)

        # Clear existing roles / 清除旧的关联
        links = session.exec(select(UserRoleLink).where(UserRoleLink.user_id == user_id)).all()
        for link in links:
            session.delete(link)

        # Add new roles / 添加新关联
        for rid in role_ids:
            link = UserRoleLink(user_id=user_id, role_id=rid)
            session.add(link)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@router.delete("/{user_id}", response_model=dict, dependencies=[Depends(check_permissions(["user:delete"]))], summary="删除用户")
async def delete_user(
    user_id: int,
    session: Session = Depends(get_session)
):
    """
    删除指定的单个用户记录。
    需要具备 `user:delete` 权限。

    业务逻辑：
    1. 查找要删除的用户。
    2. 检查是否为超级管理员（ID=1），如果是，则拒绝删除并抛出 403 错误。
    3. 执行删除并提交事务。

    Args:
        user_id (int): 待删除的用户 ID。
        session (Session): 数据库会话。

    Returns:
        dict: 包含成功信息的字典。

    Raises:
        HTTPException: 如果用户不存在抛出 404，如果尝试删除超级管理员则抛出 403 错误。
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting super admin or self (optional logic, good to have)
    # Here assuming user with id 1 is super admin / 假设 ID 为 1 的用户是超级管理员，防止被删除
    if db_user.id == 1:
         raise HTTPException(status_code=403, detail="Cannot delete super admin")

    session.delete(db_user)
    session.commit()
    return {"message": "User deleted successfully"}

@router.delete("", response_model=dict, dependencies=[Depends(check_permissions(["user:delete"]))], summary="批量删除用户")
async def delete_users_batch(
    user_ids: List[int] = Query(..., description="待删除的用户 ID 列表"),
    session: Session = Depends(get_session)
):
    """
    批量删除多个用户记录。
    需要具备 `user:delete` 权限。

    业务逻辑：
    1. 遍历提供的 `user_ids` 列表。
    2. 跳过超级管理员（ID=1）。
    3. 查找存在的用户并标记为删除。
    4. 统一提交事务完成删除。

    Args:
        user_ids (List[int]): 待删除的用户 ID 列表。
        session (Session): 数据库会话。

    Returns:
        dict: 包含成功信息的字典。
    """
    for user_id in user_ids:
        if user_id == 1:
            continue # Skip super admin / 跳过超级管理员
        db_user = session.get(User, user_id)
        if db_user:
            session.delete(db_user)

    session.commit()
    return {"message": "Users deleted successfully"}
