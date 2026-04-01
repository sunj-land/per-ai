from pydantic import BaseModel, Field
from typing import List, Optional

class IntentAnalysis(BaseModel):
    """
    用户意图分析模型
    """
    intent: str = Field(description="用户问题的核心意图分类，如：query_info, troubleshoot, unknown")
    entities: dict = Field(default_factory=dict, description="提取的实体信息，如模块名称、错误代码等")
    confidence: float = Field(ge=0.0, le=1.0, description="意图识别的置信度评分(0.0到1.0)")
    clarification_needed: bool = Field(default=False, description="是否需要用户补充信息以澄清问题")
    clarification_reason: Optional[str] = Field(default=None, description="如果需要澄清，说明需要什么补充信息")

class ExpertResponse(BaseModel):
    """
    专家回复模型
    """
    answer: str = Field(description="最终的解答文本")
    references: List[str] = Field(default_factory=list, description="参考的知识库条目或文档")
