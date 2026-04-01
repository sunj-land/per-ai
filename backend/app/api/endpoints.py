# endpoints.py: API 路由定义
# 该文件定义了所有 API 路由，并将其组织成一个 APIRouter。

from fastapi import APIRouter

# 创建一个 API 路由实例
router = APIRouter()

# 示例路由：获取用户信息
@router.get("/users/me", tags=["Users"])
async def read_current_user():
    """
    获取当前用户信息。
    这是一个示例路由，实际应用中需要实现认证逻辑。
    """
    return {"username": "fakecurrentuser"}


# 示例路由：获取项目列表
@router.get("/projects", tags=["Projects"])
async def read_projects():
    """
    获取项目列表。
    这是一个示例路由，实际应用中需要从数据库中获取数据。
    """
    return [{"name": "项目A"}, {"name": "项目B"}]
