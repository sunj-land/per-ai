import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class KnowledgeBaseTool:
    """
    特定系统的专业知识库检索工具（模拟实现）
    提供系统的常见问题解答、最佳实践和专业知识检索
    """
    
    def __init__(self):
        # 模拟的本地知识库数据
        self.mock_kb = [
            {
                "id": "kb_001",
                "title": "如何重置系统密码",
                "content": "重置系统密码请在登录页面点击'忘记密码'，然后按照注册邮箱收到的重置链接进行操作。如果无法收到邮件，请联系管理员。",
                "tags": ["account", "password", "troubleshoot"]
            },
            {
                "id": "kb_002",
                "title": "API 速率限制说明",
                "content": "标准用户的 API 调用速率限制为每分钟 60 次，每小时 1000 次。企业版用户无此限制。如果遇到 429 Too Many Requests 错误，请实现退避重试机制。",
                "tags": ["api", "rate_limit", "best_practice"]
            },
            {
                "id": "kb_003",
                "title": "系统部署最佳实践",
                "content": "部署系统时，建议使用 Docker 容器化部署，并通过 Kubernetes 进行编排。数据库请务必配置主从复制以保证高可用。",
                "tags": ["deployment", "best_practice", "architecture"]
            }
        ]
        
    def search(self, query: str, entities: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        根据查询词和提取的实体搜索知识库
        
        :param query: 搜索关键词
        :param entities: 相关的实体信息
        :return: 匹配的知识库条目列表
        """
        logger.info(f"KnowledgeBaseTool searching for: {query} with entities: {entities}")
        
        results = []
        # 简单的模拟搜索逻辑：如果查询词或实体在标题、内容或标签中出现，则返回该条目
        search_terms = [query.lower()]
        if entities:
            for v in entities.values():
                if isinstance(v, str):
                    search_terms.append(v.lower())
                elif isinstance(v, list):
                    search_terms.extend([str(item).lower() for item in v])
                    
        for entry in self.mock_kb:
            matched = False
            for term in search_terms:
                if (term in entry["title"].lower() or 
                    term in entry["content"].lower() or 
                    any(term in tag.lower() for tag in entry["tags"])):
                    matched = True
                    break
            if matched:
                results.append(entry)
                
        return results
