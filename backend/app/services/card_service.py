from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from app.models.card import Card, CardCreate, CardUpdate, CardVersion, CardVersionCreate, CardStatus

class CardService:
    """
    卡片服务类，负责处理卡片实体及版本的核心业务逻辑。
    涵盖卡片的增删改查（CRUD）以及多版本管理。
    """

    def __init__(self, session: Session):
        """
        初始化卡片服务。

        :param session: 数据库会话实例，用于执行后续的数据库操作。
        """
        self.session = session

    def create_card(self, card: CardCreate) -> Card:
        """
        创建新卡片并保存到数据库。

        :param card: 包含新卡片信息的 DTO。
        :return: 保存后的卡片数据库模型实例。
        """
        # 将传入的数据结构转换为数据库模型
        db_card = Card.from_orm(card)
        self.session.add(db_card)
        # 提交事务以保存数据
        self.session.commit()
        # 刷新实例以获取数据库生成的 ID 等默认字段
        self.session.refresh(db_card)
        return db_card

    def get_card(self, card_id: int) -> Optional[Card]:
        """
        根据 ID 获取指定的卡片记录。

        :param card_id: 要查找的卡片 ID。
        :return: 对应的卡片记录，如果不存在则返回 None。
        """
        return self.session.get(Card, card_id)

    def get_card_by_name(self, name: str) -> Optional[Card]:
        """
        根据名称精确查询卡片。通常用于验证重名情况。

        :param name: 要查找的卡片名称。
        :return: 找到的卡片实例，未找到返回 None。
        """
        statement = select(Card).where(Card.name == name)
        result = self.session.exec(statement)
        return result.first()

    def list_cards(self, skip: int = 0, limit: int = 100) -> List[Card]:
        """
        分页获取所有卡片列表。

        :param skip: 结果集的起始偏移量。
        :param limit: 单次返回的最大记录数。
        :return: 满足条件的卡片列表。
        """
        statement = select(Card).offset(skip).limit(limit)
        return self.session.exec(statement).all()

    def update_card(self, card_id: int, card_update: CardUpdate) -> Optional[Card]:
        """
        更新现有卡片的信息。

        :param card_id: 需要更新的卡片 ID。
        :param card_update: 包含要更新字段的数据结构。
        :return: 更新后的卡片实例，若卡片不存在则返回 None。
        """
        db_card = self.session.get(Card, card_id)
        if not db_card:
            return None

        # 仅提取已设置的字段，避免覆盖未提供的原有值
        card_data = card_update.dict(exclude_unset=True)
        for key, value in card_data.items():
            setattr(db_card, key, value)

        # 更新时间戳
        db_card.updated_at = datetime.utcnow()
        self.session.add(db_card)
        self.session.commit()
        self.session.refresh(db_card)
        return db_card

    def delete_card(self, card_id: int) -> bool:
        """
        删除指定的卡片记录。

        :param card_id: 需要删除的卡片 ID。
        :return: 布尔值，删除成功返回 True，记录不存在返回 False。
        """
        db_card = self.session.get(Card, card_id)
        if not db_card:
            return False
        self.session.delete(db_card)
        self.session.commit()
        return True

    def create_version(self, card_id: int, version_data: CardVersionCreate) -> Optional[CardVersion]:
        """
        为指定卡片创建一个新的代码版本，并同步更新主卡片的当前版本号。

        :param card_id: 关联的卡片 ID。
        :param version_data: 新版本的数据内容。
        :return: 新创建的版本实例，若关联的主卡片不存在返回 None。
        """
        db_card = self.session.get(Card, card_id)
        if not db_card:
            return None

        # Pydantic v2 support
        db_version = CardVersion(**version_data.model_dump())
        db_version.card_id = card_id

        # 同步更新主表版本号及修改时间
        db_card.version = version_data.version
        db_card.updated_at = datetime.utcnow()

        self.session.add(db_version)
        self.session.add(db_card)
        self.session.commit()
        self.session.refresh(db_version)
        return db_version

    def get_versions(self, card_id: int) -> List[CardVersion]:
        """
        获取指定卡片的所有历史版本，按版本号降序排列。

        :param card_id: 目标卡片 ID。
        :return: 该卡片的版本列表。
        """
        statement = select(CardVersion).where(CardVersion.card_id == card_id).order_by(CardVersion.version.desc())
        return self.session.exec(statement).all()

    def get_latest_version(self, card_id: int) -> Optional[CardVersion]:
        """
        获取指定卡片的最新版本信息。

        :param card_id: 目标卡片 ID。
        :return: 最新版本的实例，若不存在返回 None。
        """
        statement = select(CardVersion).where(CardVersion.card_id == card_id).order_by(CardVersion.version.desc())
        result = self.session.exec(statement)
        return result.first()
