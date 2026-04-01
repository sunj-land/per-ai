from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List, Optional
from app.core.database import get_session
from app.core.dependencies import get_ai_card_service
from app.models.card import Card, CardCreate, CardUpdate, CardVersion, CardVersionCreate
from app.services.card_service import CardService
import os

router = APIRouter()

@router.post("/", response_model=Card)
def create_card(card: CardCreate, session: Session = Depends(get_session)):
    """
    创建新卡片。

    :param card: 卡片创建请求数据。
    :param session: 数据库会话。
    :return: 创建成功的卡片信息。
    :raises HTTPException: 如果同名卡片已存在，抛出 400 错误。
    """
    service = CardService(session)
    # ========== 步骤1：检查是否重名 ==========
    existing = service.get_card_by_name(card.name)
    if existing:
        raise HTTPException(status_code=400, detail="Card with this name already exists")
    # ========== 步骤2：执行创建操作 ==========
    return service.create_card(card)

@router.get("/", response_model=List[Card])
def list_cards(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    """
    分页获取卡片列表。

    :param skip: 跳过的记录数，默认为 0。
    :param limit: 返回的最大记录数，默认为 100。
    :return: 卡片列表。
    """
    service = CardService(session)
    return service.list_cards(skip, limit)

@router.get("/{card_id}", response_model=Card)
def get_card(card_id: int, session: Session = Depends(get_session)):
    """
    根据 ID 获取单张卡片详情。

    :param card_id: 卡片 ID。
    :return: 对应的卡片对象。
    :raises HTTPException: 卡片不存在时抛出 404。
    """
    service = CardService(session)
    card = service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@router.put("/{card_id}", response_model=Card)
def update_card(card_id: int, card_update: CardUpdate, session: Session = Depends(get_session)):
    """
    更新指定卡片的基本信息。

    :param card_id: 卡片 ID。
    :param card_update: 需要更新的字段信息。
    :return: 更新后的卡片信息。
    :raises HTTPException: 卡片不存在时抛出 404。
    """
    service = CardService(session)
    card = service.update_card(card_id, card_update)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@router.delete("/{card_id}")
def delete_card(card_id: int, session: Session = Depends(get_session)):
    """
    删除指定卡片。

    :param card_id: 卡片 ID。
    :return: 包含成功标识的字典。
    :raises HTTPException: 卡片不存在时抛出 404。
    """
    service = CardService(session)
    success = service.delete_card(card_id)
    if not success:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"ok": True}

@router.post("/{card_id}/versions", response_model=CardVersion)
def create_version(card_id: int, version: CardVersionCreate, session: Session = Depends(get_session)):
    """
    为指定卡片创建新的代码版本。

    :param card_id: 卡片 ID。
    :param version: 版本信息，包含代码内容等。
    :return: 创建的新版本对象。
    :raises HTTPException: 关联的卡片不存在时抛出 404。
    """
    service = CardService(session)
    new_version = service.create_version(card_id, version)
    if not new_version:
        raise HTTPException(status_code=404, detail="Card not found")
    return new_version

@router.get("/{card_id}/versions", response_model=List[CardVersion])
def get_versions(card_id: int, session: Session = Depends(get_session)):
    """
    获取指定卡片的所有历史版本。

    :param card_id: 卡片 ID。
    :return: 卡片版本列表。
    """
    service = CardService(session)
    return service.get_versions(card_id)

@router.post("/generate")
async def generate_card(
    prompt: str,
    provider: str = "ollama",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    ai_svc=Depends(get_ai_card_service),
):
    """
    利用 AI 生成卡片的前端代码。

    :param prompt: 生成代码的提示词。
    :param provider: AI 模型提供商（如 ollama）。
    :param model: 具体模型名称。
    :param api_key: 可选的 API Key。
    :param base_url: 可选的 API Base URL。
    :return: 包含生成代码的字典。
    :raises HTTPException: 生成过程中出错时抛出 500。
    """
    # 构造模型配置参数，使用较低的温度以保证代码生成的稳定性
    model_config = {
        "provider": provider,
        "model_name": model,
        "api_key": api_key,
        "base_url": base_url,
        "temperature": 0.2
    }

    # 如果使用 ollama 且未指定模型，默认使用适用于代码生成的模型
    if provider == "ollama" and not model:
        model_config["model_name"] = "qwen2.5-coder:14b"

    try:
        code = await ai_svc.generate_card_code(prompt, model_config)
        return {"code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{card_id}/publish/{version}")
def publish_card(card_id: int, version: int, session: Session = Depends(get_session)):
    """
    发布指定卡片的特定版本，将卡片代码物理写入前端项目目录中。

    :param card_id: 卡片 ID。
    :param version: 要发布的版本号。
    :return: 发布结果，包括成功标识和物理文件路径。
    :raises HTTPException: 卡片或版本不存在，以及文件写入失败时抛出。
    """
    service = CardService(session)
    # ========== 步骤1：获取卡片信息 ==========
    card = service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # ========== 步骤2：查找目标版本 ==========
    versions = service.get_versions(card_id)
    target_version = next((v for v in versions if v.version == version), None)
    if not target_version:
        raise HTTPException(status_code=404, detail="Version not found")

    # ========== 步骤3：确定文件保存路径 ==========
    # 目标目录：frontend/packages/web/src/components/cards/generated/
    base_dir = os.path.abspath(os.path.join(os.getcwd(), "../frontend/packages/web/src/components/cards/generated"))
    os.makedirs(base_dir, exist_ok=True)

    # 拼接文件名，默认采用 卡片名.vue
    filename = f"{card.name}.vue"
    file_path = os.path.join(base_dir, filename)

    try:
        # ========== 步骤4：将代码写入文件 ==========
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(target_version.code)

        # ========== 步骤5：更新卡片状态为已发布 ==========
        service.update_card(card_id, CardUpdate(status="published"))

        return {"ok": True, "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")
