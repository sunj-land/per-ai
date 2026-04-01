from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, SQLModel

DIMENSION_KEYS = (
    "originality",
    "information_value",
    "writing_quality",
    "interaction_potential",
    "timeliness",
)


class RSSQualityRuleBase(SQLModel):
    """RSS 文章质量评分规则基础模型。"""

    name: str = Field(default="default", description="评分规则名称")
    is_active: bool = Field(default=True, description="是否为当前生效规则")
    weights: Dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="评分维度权重配置",
    )
    thresholds: Dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="评分阈值配置",
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="评分算法附加配置",
    )


class RSSQualityRule(RSSQualityRuleBase, table=True):
    """RSS 文章质量评分规则表。"""

    __tablename__ = "rss_quality_rule"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="评分规则主键",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="规则创建时间",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="规则更新时间",
    )


class RSSQualityRuleUpdate(SQLModel):
    """评分规则更新请求模型。"""

    name: Optional[str] = Field(default=None, description="规则名称")
    weights: Dict[str, float] = Field(
        default_factory=dict,
        description="维度权重配置",
    )
    thresholds: Dict[str, float] = Field(
        default_factory=dict,
        description="评分阈值配置",
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="附加评分设置",
    )


class RSSQualityScoreResult(SQLModel, table=True):
    """RSS 文章质量评分结果表。"""

    __tablename__ = "rss_quality_score_result"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="评分结果主键",
    )
    batch_id: str = Field(index=True, description="批量评分任务编号")
    article_id: int = Field(index=True, description="关联 RSS 文章 ID")
    feed_id: Optional[int] = Field(default=None, index=True, description="关联 RSS 源 ID")
    article_title: str = Field(default="", description="文章标题快照")
    article_link: str = Field(default="", description="文章链接快照")
    feed_title: Optional[str] = Field(default=None, description="订阅源标题快照")
    published_at: Optional[datetime] = Field(default=None, description="文章发布时间快照")
    status: str = Field(default="success", index=True, description="评分状态")
    grade: str = Field(default="review", description="评分等级")
    overall_score: float = Field(default=0, index=True, description="综合质量评分")
    originality_score: float = Field(default=0, description="内容原创性评分")
    information_value_score: float = Field(default=0, description="信息价值度评分")
    writing_quality_score: float = Field(default=0, description="写作质量评分")
    interaction_potential_score: float = Field(default=0, description="用户互动潜力评分")
    timeliness_score: float = Field(default=0, description="时效性评分")
    weights: Dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="评分时使用的权重快照",
    )
    report: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="详细评分报告",
    )
    config_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="评分配置快照",
    )
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="失败时的错误信息",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
        description="结果创建时间",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="结果更新时间",
    )


class RSSQualityScoreLog(SQLModel, table=True):
    """RSS 文章质量评分日志表。"""

    __tablename__ = "rss_quality_score_log"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="日志主键",
    )
    batch_id: str = Field(index=True, description="批量评分任务编号")
    article_id: Optional[int] = Field(default=None, index=True, description="关联文章 ID")
    level: str = Field(default="info", description="日志级别")
    message: str = Field(description="日志消息")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="日志上下文",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
        description="日志创建时间",
    )


class RSSQualityBatchScoreRequest(SQLModel):
    """批量评分请求模型。"""

    feed_id: Optional[int] = Field(default=None, description="待评分 RSS 源 ID")
    article_ids: List[int] = Field(default_factory=list, description="指定待评分文章 ID 列表")
    limit: int = Field(default=20, ge=1, le=200, description="批量评分文章数量上限")
    concurrency: int = Field(default=5, ge=1, le=20, description="批量并发评分数量")
    weights: Dict[str, float] = Field(default_factory=dict, description="临时覆盖权重")
    thresholds: Dict[str, float] = Field(default_factory=dict, description="临时覆盖阈值")
    settings: Dict[str, Any] = Field(default_factory=dict, description="临时覆盖算法设置")


class RSSQualityResultQuery(SQLModel):
    """评分结果查询条件模型。"""

    min_score: Optional[float] = Field(default=None, ge=0, le=100, description="最低分")
    max_score: Optional[float] = Field(default=None, ge=0, le=100, description="最高分")
    feed_id: Optional[int] = Field(default=None, description="RSS 源 ID")
    batch_id: Optional[str] = Field(default=None, description="批量任务编号")
    status: Optional[str] = Field(default=None, description="评分状态")
    limit: int = Field(default=50, ge=1, le=200, description="返回数量")

