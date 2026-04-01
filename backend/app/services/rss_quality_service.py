from __future__ import annotations

import asyncio
import html
import logging
import math
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup
from sqlmodel import Session, select

from app.core.database import engine
from app.models.rss import RSSArticle, RSSFeed
from app.models.rss_quality import (
    DIMENSION_KEYS,
    RSSQualityBatchScoreRequest,
    RSSQualityResultQuery,
    RSSQualityRule,
    RSSQualityRuleUpdate,
    RSSQualityScoreLog,
    RSSQualityScoreResult,
)

logger = logging.getLogger(__name__)

DEFAULT_RSS_QUALITY_CONFIG: Dict[str, Any] = {
    "name": "RSS 默认评分规则",
    "weights": {
        "originality": 0.24,
        "information_value": 0.24,
        "writing_quality": 0.18,
        "interaction_potential": 0.17,
        "timeliness": 0.17,
    },
    "thresholds": {
        "excellent": 85,
        "good": 70,
        "review": 55,
    },
    "settings": {
        "originality": {
            "comparison_window": 25,
            "shingle_size": 3,
        },
        "information_value": {
            "min_content_chars": 280,
            "industry_keywords": {
                "ai": ["ai", "大模型", "llm", "机器学习", "agent", "deepseek", "openai"],
                "tech": ["cloud", "saas", "developer", "api", "芯片", "编程", "软件"],
                "finance": ["finance", "fintech", "投资", "市场", "股票", "资金", "经济"],
                "media": ["marketing", "增长", "媒体", "广告", "品牌", "传播", "内容"],
                "commerce": ["电商", "零售", "消费", "供应链", "物流", "订单", "转化"],
            },
        },
        "writing_quality": {
            "ideal_paragraph_min": 3,
            "ideal_paragraph_max": 8,
            "max_sentence_chars": 160,
        },
        "interaction_potential": {
            "power_words": [
                "how",
                "why",
                "best",
                "guide",
                "增长",
                "趋势",
                "深度",
                "实战",
                "完整",
                "揭秘",
            ],
            "hot_topics": [
                "ai",
                "agent",
                "automation",
                "growth",
                "seo",
                "大模型",
                "出海",
                "创业",
                "效率",
                "产品",
            ],
        },
        "timeliness": {
            "fresh_hours": 48,
            "decay_days": 21,
            "freshness_keywords": [
                "today",
                "latest",
                "breaking",
                "new",
                "今日",
                "最新",
                "刚刚",
                "本周",
                "今年",
                "趋势",
            ],
        },
    },
}

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "your",
    "into",
    "have",
    "will",
    "about",
    "what",
    "when",
    "where",
    "while",
    "一个",
    "我们",
    "你们",
    "他们",
    "以及",
    "因为",
    "所以",
    "如何",
    "什么",
    "文章",
    "内容",
    "进行",
    "可以",
    "已经",
    "通过",
    "更多",
    "如果",
    "这些",
}


class RSSQualityService:
    """RSS 文章质量评分服务。"""

    def get_default_config(self) -> Dict[str, Any]:
        """返回默认评分配置。"""

        return self._clone_payload(DEFAULT_RSS_QUALITY_CONFIG)

    def get_active_rule(self, session: Session) -> RSSQualityRule:
        """获取当前生效评分规则。"""

        rule = session.exec(
            select(RSSQualityRule)
            .where(RSSQualityRule.is_active == True)  # noqa: E712
            .order_by(RSSQualityRule.updated_at.desc())
        ).first()
        if rule:
            return rule

        default_config = self.get_default_config()
        rule = RSSQualityRule(
            name=default_config["name"],
            is_active=True,
            weights=default_config["weights"],
            thresholds=default_config["thresholds"],
            settings=default_config["settings"],
        )
        session.add(rule)
        session.commit()
        session.refresh(rule)
        return rule

    def update_rule(self, session: Session, payload: RSSQualityRuleUpdate) -> RSSQualityRule:
        """更新当前评分规则。"""

        rule = self.get_active_rule(session)
        merged_config = self.merge_config(
            self.serialize_rule(rule),
            {
                "name": payload.name or rule.name,
                "weights": payload.weights,
                "thresholds": payload.thresholds,
                "settings": payload.settings,
            },
        )
        rule.name = merged_config["name"]
        rule.weights = merged_config["weights"]
        rule.thresholds = merged_config["thresholds"]
        rule.settings = merged_config["settings"]
        rule.updated_at = datetime.utcnow()
        session.add(rule)
        session.commit()
        session.refresh(rule)
        return rule

    def serialize_rule(self, rule: RSSQualityRule) -> Dict[str, Any]:
        """序列化评分规则。"""

        return {
            "id": str(rule.id),
            "name": rule.name,
            "weights": self._normalize_weights(rule.weights),
            "thresholds": self._normalize_thresholds(rule.thresholds),
            "settings": self._merge_dict(self.get_default_config()["settings"], rule.settings or {}),
            "updatedAt": rule.updated_at.isoformat(),
            "createdAt": rule.created_at.isoformat(),
        }

    def merge_config(self, base_config: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """合并评分配置并输出规范化结果。"""

        merged = self.get_default_config()
        merged["name"] = overrides.get("name") or base_config.get("name") or merged["name"]
        merged["weights"] = self._normalize_weights(
            self._merge_dict(base_config.get("weights", {}), overrides.get("weights", {}))
        )
        merged["thresholds"] = self._normalize_thresholds(
            self._merge_dict(base_config.get("thresholds", {}), overrides.get("thresholds", {}))
        )
        merged["settings"] = self._merge_dict(
            self._merge_dict(self.get_default_config()["settings"], base_config.get("settings", {})),
            overrides.get("settings", {}),
        )
        return merged

    async def score_articles(self, payload: RSSQualityBatchScoreRequest) -> Dict[str, Any]:
        """批量并发评分指定 RSS 文章。"""

        with Session(engine) as session:
            active_rule = self.serialize_rule(self.get_active_rule(session))
            effective_config = self.merge_config(
                active_rule,
                {
                    "weights": payload.weights,
                    "thresholds": payload.thresholds,
                    "settings": payload.settings,
                },
            )
            articles = self._resolve_articles(session, payload)

        batch_id = f"rss-quality-{uuid.uuid4().hex[:12]}"
        if not articles:
            return {
                "batchId": batch_id,
                "config": effective_config,
                "summary": {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "averageScore": 0,
                },
                "results": [],
            }

        await self._write_log(
            batch_id=batch_id,
            article_id=None,
            level="info",
            message="batch scoring started",
            context={
                "articleIds": [article.id for article in articles],
                "concurrency": payload.concurrency,
            },
        )

        semaphore = asyncio.Semaphore(payload.concurrency)

        async def _run(article_id: int) -> Dict[str, Any]:
            async with semaphore:
                return await asyncio.to_thread(self._score_single_article, article_id, batch_id, effective_config)

        results = await asyncio.gather(*[_run(article.id) for article in articles])
        success_results = [result for result in results if result["status"] == "success"]
        failed_results = [result for result in results if result["status"] != "success"]
        average_score = round(
            sum(item["overallScore"] for item in success_results) / len(success_results),
            2,
        ) if success_results else 0

        await self._write_log(
            batch_id=batch_id,
            article_id=None,
            level="info",
            message="batch scoring finished",
            context={
                "total": len(results),
                "success": len(success_results),
                "failed": len(failed_results),
                "averageScore": average_score,
            },
        )

        return {
            "batchId": batch_id,
            "config": effective_config,
            "summary": {
                "total": len(results),
                "success": len(success_results),
                "failed": len(failed_results),
                "averageScore": average_score,
            },
            "results": results,
        }

    def list_results(self, session: Session, query: RSSQualityResultQuery) -> List[Dict[str, Any]]:
        """查询评分结果列表。"""

        statement = select(RSSQualityScoreResult).order_by(RSSQualityScoreResult.created_at.desc())
        if query.min_score is not None:
            statement = statement.where(RSSQualityScoreResult.overall_score >= query.min_score)
        if query.max_score is not None:
            statement = statement.where(RSSQualityScoreResult.overall_score <= query.max_score)
        if query.feed_id is not None:
            statement = statement.where(RSSQualityScoreResult.feed_id == query.feed_id)
        if query.batch_id:
            statement = statement.where(RSSQualityScoreResult.batch_id == query.batch_id)
        if query.status:
            statement = statement.where(RSSQualityScoreResult.status == query.status)
        statement = statement.limit(query.limit)
        results = session.exec(statement).all()
        return [self._serialize_result(result) for result in results]

    def list_logs(
        self,
        session: Session,
        batch_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """查询评分日志列表。"""

        statement = select(RSSQualityScoreLog).order_by(RSSQualityScoreLog.created_at.desc()).limit(limit)
        if batch_id:
            statement = statement.where(RSSQualityScoreLog.batch_id == batch_id)
        logs = session.exec(statement).all()
        return [
            {
                "id": str(item.id),
                "batchId": item.batch_id,
                "articleId": item.article_id,
                "level": item.level,
                "message": item.message,
                "context": item.context or {},
                "createdAt": item.created_at.isoformat(),
            }
            for item in logs
        ]

    def _resolve_articles(self, session: Session, payload: RSSQualityBatchScoreRequest) -> List[RSSArticle]:
        """根据请求参数解析待评分文章。"""

        if payload.article_ids:
            unique_ids = list(dict.fromkeys(payload.article_ids))
            return session.exec(
                select(RSSArticle)
                .where(RSSArticle.id.in_(unique_ids))
                .order_by(RSSArticle.published_at.desc())
            ).all()

        statement = select(RSSArticle).order_by(RSSArticle.published_at.desc())
        if payload.feed_id is not None:
            statement = statement.where(RSSArticle.feed_id == payload.feed_id)
        return session.exec(statement.limit(payload.limit)).all()

    def _score_single_article(self, article_id: int, batch_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """对单篇文章执行评分并持久化结果。"""

        with Session(engine) as session:
            article = session.get(RSSArticle, article_id)
            if not article:
                message = f"article {article_id} not found"
                self._persist_log(session, batch_id, article_id, "error", message, {})
                session.commit()
                return {
                    "articleId": article_id,
                    "status": "error",
                    "overallScore": 0,
                    "errorMessage": message,
                }

            feed = session.get(RSSFeed, article.feed_id) if article.feed_id else None
            self._persist_log(
                session,
                batch_id,
                article_id,
                "info",
                "article scoring started",
                {"title": article.title},
            )

            try:
                report = self._build_report(session, article, feed, config)
                result = RSSQualityScoreResult(
                    batch_id=batch_id,
                    article_id=article.id,
                    feed_id=article.feed_id,
                    article_title=article.title,
                    article_link=article.link,
                    feed_title=feed.title if feed else None,
                    published_at=article.published_at,
                    status="success",
                    grade=report["grade"],
                    overall_score=report["overallScore"],
                    originality_score=report["dimensions"]["originality"]["score"],
                    information_value_score=report["dimensions"]["information_value"]["score"],
                    writing_quality_score=report["dimensions"]["writing_quality"]["score"],
                    interaction_potential_score=report["dimensions"]["interaction_potential"]["score"],
                    timeliness_score=report["dimensions"]["timeliness"]["score"],
                    weights=config["weights"],
                    report=report,
                    config_snapshot=config,
                    updated_at=datetime.utcnow(),
                )
                session.add(result)
                self._persist_log(
                    session,
                    batch_id,
                    article_id,
                    "info",
                    "article scoring finished",
                    {
                        "overallScore": report["overallScore"],
                        "grade": report["grade"],
                    },
                )
                session.commit()
                return self._serialize_result(result)
            except Exception as exc:
                logger.exception("rss quality scoring failed for article=%s", article_id)
                result = RSSQualityScoreResult(
                    batch_id=batch_id,
                    article_id=article.id,
                    feed_id=article.feed_id,
                    article_title=article.title,
                    article_link=article.link,
                    feed_title=feed.title if feed else None,
                    published_at=article.published_at,
                    status="error",
                    grade="error",
                    overall_score=0,
                    originality_score=0,
                    information_value_score=0,
                    writing_quality_score=0,
                    interaction_potential_score=0,
                    timeliness_score=0,
                    weights=config["weights"],
                    report={},
                    config_snapshot=config,
                    error_message=str(exc),
                    updated_at=datetime.utcnow(),
                )
                session.add(result)
                self._persist_log(
                    session,
                    batch_id,
                    article_id,
                    "error",
                    "article scoring failed",
                    {"error": str(exc)},
                )
                session.commit()
                return self._serialize_result(result)

    async def _write_log(
        self,
        batch_id: str,
        article_id: Optional[int],
        level: str,
        message: str,
        context: Dict[str, Any],
    ) -> None:
        """异步写入批量评分日志。"""

        await asyncio.to_thread(self._write_log_sync, batch_id, article_id, level, message, context)

    def _write_log_sync(
        self,
        batch_id: str,
        article_id: Optional[int],
        level: str,
        message: str,
        context: Dict[str, Any],
    ) -> None:
        """同步写入批量评分日志。"""

        with Session(engine) as session:
            self._persist_log(session, batch_id, article_id, level, message, context)
            session.commit()

    def _persist_log(
        self,
        session: Session,
        batch_id: str,
        article_id: Optional[int],
        level: str,
        message: str,
        context: Dict[str, Any],
    ) -> None:
        """在当前会话中写入评分日志。"""

        session.add(
            RSSQualityScoreLog(
                batch_id=batch_id,
                article_id=article_id,
                level=level,
                message=message,
                context=context,
            )
        )

    def _build_report(
        self,
        session: Session,
        article: RSSArticle,
        feed: Optional[RSSFeed],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """构建单篇文章评分报告。"""

        text = self._compose_text(article)
        dimensions = {
            "originality": self._score_originality(session, article, text, config),
            "information_value": self._score_information_value(article, text, feed, config),
            "writing_quality": self._score_writing_quality(article, text, config),
            "interaction_potential": self._score_interaction_potential(article, text, config),
            "timeliness": self._score_timeliness(article, text, config),
        }
        weights = config["weights"]
        overall_score = round(
            sum(dimensions[key]["score"] * weights[key] for key in DIMENSION_KEYS),
            2,
        )
        grade = self._resolve_grade(overall_score, config["thresholds"])
        return {
            "articleId": article.id,
            "title": article.title,
            "link": article.link,
            "feedId": article.feed_id,
            "feedTitle": feed.title if feed else None,
            "publishedAt": article.published_at.isoformat() if article.published_at else None,
            "overallScore": overall_score,
            "grade": grade,
            "weights": weights,
            "thresholds": config["thresholds"],
            "dimensions": dimensions,
            "generatedAt": datetime.utcnow().isoformat(),
        }

    def _score_originality(
        self,
        session: Session,
        article: RSSArticle,
        text: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """计算原创性评分。"""

        settings = config["settings"]["originality"]
        comparison_window = int(settings.get("comparison_window", 25))
        shingle_size = max(int(settings.get("shingle_size", 3)), 2)

        candidates = session.exec(
            select(RSSArticle)
            .where(RSSArticle.id != article.id)
            .order_by(RSSArticle.published_at.desc())
            .limit(comparison_window)
        ).all()
        exact_duplicates = [
            candidate.id for candidate in candidates if candidate.content_hash == article.content_hash
        ]
        base_tokens = self._tokenize(text)
        base_shingles = self._build_shingles(base_tokens, shingle_size)
        max_similarity = 0.0

        for candidate in candidates:
            candidate_text = self._compose_text(candidate)
            candidate_shingles = self._build_shingles(self._tokenize(candidate_text), shingle_size)
            similarity = self._jaccard_similarity(base_shingles, candidate_shingles)
            max_similarity = max(max_similarity, similarity)

        if not candidates and text:
            score = 92.0
        else:
            score = max(0.0, 100 - len(exact_duplicates) * 35 - max_similarity * 70)

        reasons = [
            f"检测到 {len(exact_duplicates)} 篇内容哈希完全一致文章",
            f"最近样本最高相似度为 {round(max_similarity * 100, 2)}%",
        ]
        if score >= 80:
            reasons.append("未发现高风险重复内容，原创性表现较好")
        elif score < 60:
            reasons.append("存在较明显重复风险，建议重新审查内容来源")

        return {
            "score": round(score, 2),
            "weight": config["weights"]["originality"],
            "reasons": reasons,
            "metrics": {
                "comparisonWindow": len(candidates),
                "exactDuplicateCount": len(exact_duplicates),
                "maxSimilarityRatio": round(max_similarity, 4),
            },
        }

    def _score_information_value(
        self,
        article: RSSArticle,
        text: str,
        feed: Optional[RSSFeed],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """计算信息价值度评分。"""

        settings = config["settings"]["information_value"]
        tokens = [token for token in self._tokenize(text) if token not in STOPWORDS]
        counter = Counter(tokens)
        keyword_items = counter.most_common(8)
        keyword_weight_score = min(
            100.0,
            sum(freq * min(len(word), 10) for word, freq in keyword_items) * 2.4,
        )

        lowered_text = text.lower()
        industry_scores: Dict[str, int] = {}
        for industry, keywords in settings.get("industry_keywords", {}).items():
            industry_scores[industry] = sum(1 for keyword in keywords if keyword.lower() in lowered_text)
        dominant_industry = max(industry_scores, key=industry_scores.get) if industry_scores else "general"
        industry_score = min(
            100.0,
            max(industry_scores.values(), default=0) * 20 + len([value for value in industry_scores.values() if value > 0]) * 6,
        )

        content_chars = len(text)
        min_content_chars = int(settings.get("min_content_chars", 280))
        depth_ratio = min(content_chars / max(min_content_chars, 1), 1.5)
        depth_score = min(100.0, 55 + depth_ratio * 30)

        final_score = keyword_weight_score * 0.45 + industry_score * 0.35 + depth_score * 0.20
        reasons = [
            f"高权重关键词数量 {len(keyword_items)}，头部关键词为 {', '.join(word for word, _ in keyword_items[:5]) or '无'}",
            f"行业相关性最高的领域为 {dominant_industry}，匹配命中 {max(industry_scores.values(), default=0)} 次",
            f"正文长度约 {content_chars} 字符，信息承载量 {'充足' if depth_score >= 75 else '一般'}",
        ]
        if feed and feed.title:
            reasons.append(f"来源订阅源为 {feed.title}")

        return {
            "score": round(min(final_score, 100.0), 2),
            "weight": config["weights"]["information_value"],
            "reasons": reasons,
            "metrics": {
                "contentChars": content_chars,
                "keywordWeightScore": round(keyword_weight_score, 2),
                "industryScore": round(industry_score, 2),
                "depthScore": round(depth_score, 2),
                "dominantIndustry": dominant_industry,
                "topKeywords": [word for word, _ in keyword_items],
            },
        }

    def _score_writing_quality(
        self,
        article: RSSArticle,
        text: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """计算写作质量评分。"""

        settings = config["settings"]["writing_quality"]
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
        sentences = [item.strip() for item in re.split(r"[。！？!?\.]+", text) if item.strip()]
        weird_char_ratio = len(re.findall(r"[^\w\s\u4e00-\u9fff，。！？；：、“”‘’（）()《》【】,.!?;:'\"/%+-]", text)) / max(len(text), 1)
        repeated_punctuation = len(re.findall(r"[!?！？。,.，]{3,}", text))
        unmatched_pairs = abs(text.count("(") - text.count(")")) + abs(text.count("“") - text.count("”"))
        max_sentence_chars = int(settings.get("max_sentence_chars", 160))
        long_sentences = len([sentence for sentence in sentences if len(sentence) > max_sentence_chars])

        grammar_penalty = repeated_punctuation * 8 + unmatched_pairs * 6 + long_sentences * 4 + weird_char_ratio * 100
        grammar_score = max(0.0, 100 - grammar_penalty)

        ideal_min = int(settings.get("ideal_paragraph_min", 3))
        ideal_max = int(settings.get("ideal_paragraph_max", 8))
        paragraph_count = len(paragraphs)
        if ideal_min <= paragraph_count <= ideal_max:
            paragraph_score = 92.0
        else:
            gap = min(abs(paragraph_count - ideal_min), abs(paragraph_count - ideal_max))
            paragraph_score = max(40.0, 92 - gap * 12)

        sentence_density_score = 85.0 if 3 <= len(sentences) <= 28 else max(45.0, 85 - abs(len(sentences) - 12) * 2.5)
        final_score = grammar_score * 0.55 + paragraph_score * 0.30 + sentence_density_score * 0.15
        reasons = [
            f"段落数为 {paragraph_count}，结构 {'较为合理' if paragraph_score >= 80 else '需要优化'}",
            f"检测到异常标点 {repeated_punctuation} 处、超长句 {long_sentences} 句",
            f"估算异常字符占比 {round(weird_char_ratio * 100, 2)}%",
        ]
        if not article.summary:
            reasons.append("缺少摘要字段，阅读导览性偏弱")

        return {
            "score": round(min(final_score, 100.0), 2),
            "weight": config["weights"]["writing_quality"],
            "reasons": reasons,
            "metrics": {
                "paragraphCount": paragraph_count,
                "sentenceCount": len(sentences),
                "grammarPenalty": round(grammar_penalty, 2),
                "repeatedPunctuation": repeated_punctuation,
                "longSentenceCount": long_sentences,
                "weirdCharRatio": round(weird_char_ratio, 4),
            },
        }

    def _score_interaction_potential(
        self,
        article: RSSArticle,
        text: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """计算互动潜力评分。"""

        settings = config["settings"]["interaction_potential"]
        title = (article.title or "").strip()
        title_length = len(title)
        ideal_title_score = 88.0 if 12 <= title_length <= 28 else max(45.0, 88 - abs(title_length - 18) * 3)
        lowered_title = title.lower()
        power_hits = sum(1 for word in settings.get("power_words", []) if word.lower() in lowered_title)
        numeric_bonus = 8 if re.search(r"\d", title) else 0
        question_bonus = 6 if "?" in title or "？" in title else 0
        title_score = min(100.0, ideal_title_score + power_hits * 8 + numeric_bonus + question_bonus)

        lowered_text = text.lower()
        hot_hits = sum(1 for keyword in settings.get("hot_topics", []) if keyword.lower() in lowered_text)
        hot_topic_score = min(100.0, 45 + hot_hits * 12)

        final_score = title_score * 0.60 + hot_topic_score * 0.40
        reasons = [
            f"标题长度为 {title_length}，标题吸引力基础分 {round(ideal_title_score, 2)}",
            f"标题触发强势词 {power_hits} 次，热点话题命中 {hot_hits} 次",
        ]
        if title_score >= 80:
            reasons.append("标题具备较强点击动机")
        elif title_score < 60:
            reasons.append("标题表达偏平，建议增强利益点或问题意识")

        return {
            "score": round(min(final_score, 100.0), 2),
            "weight": config["weights"]["interaction_potential"],
            "reasons": reasons,
            "metrics": {
                "titleLength": title_length,
                "powerHits": power_hits,
                "hotTopicHits": hot_hits,
                "titleScore": round(title_score, 2),
                "hotTopicScore": round(hot_topic_score, 2),
            },
        }

    def _score_timeliness(
        self,
        article: RSSArticle,
        text: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """计算时效性评分。"""

        settings = config["settings"]["timeliness"]
        fresh_hours = float(settings.get("fresh_hours", 48))
        decay_days = max(float(settings.get("decay_days", 21)), 1.0)
        freshness_keywords = settings.get("freshness_keywords", [])

        if article.published_at:
            now = datetime.now(timezone.utc)
            published_at = article.published_at
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            age_hours = max((now - published_at).total_seconds() / 3600, 0)
            if age_hours <= fresh_hours:
                age_score = 100.0
            else:
                age_score = max(20.0, 100.0 * math.exp(-(age_hours - fresh_hours) / (24 * decay_days)))
        else:
            age_hours = None
            age_score = 52.0

        lowered_text = text.lower()
        keyword_hits = sum(1 for keyword in freshness_keywords if keyword.lower() in lowered_text)
        year_bonus = 10 if str(datetime.utcnow().year) in lowered_text else 0
        freshness_content_score = min(100.0, 48 + keyword_hits * 10 + year_bonus)
        final_score = age_score * 0.80 + freshness_content_score * 0.20
        reasons = [
            f"发布时间距今约 {round(age_hours, 2)} 小时" if age_hours is not None else "未提供发布时间，时效性按中位值估算",
            f"新鲜度关键词命中 {keyword_hits} 次，内容新鲜度辅助分 {round(freshness_content_score, 2)}",
        ]

        return {
            "score": round(min(final_score, 100.0), 2),
            "weight": config["weights"]["timeliness"],
            "reasons": reasons,
            "metrics": {
                "ageHours": round(age_hours, 2) if age_hours is not None else None,
                "ageScore": round(age_score, 2),
                "keywordHits": keyword_hits,
                "freshnessContentScore": round(freshness_content_score, 2),
            },
        }

    def _serialize_result(self, result: RSSQualityScoreResult) -> Dict[str, Any]:
        """序列化评分结果。"""

        return {
            "id": str(result.id),
            "batchId": result.batch_id,
            "articleId": result.article_id,
            "feedId": result.feed_id,
            "articleTitle": result.article_title,
            "articleLink": result.article_link,
            "feedTitle": result.feed_title,
            "publishedAt": result.published_at.isoformat() if result.published_at else None,
            "status": result.status,
            "grade": result.grade,
            "overallScore": round(result.overall_score, 2),
            "dimensions": {
                "originality": round(result.originality_score, 2),
                "information_value": round(result.information_value_score, 2),
                "writing_quality": round(result.writing_quality_score, 2),
                "interaction_potential": round(result.interaction_potential_score, 2),
                "timeliness": round(result.timeliness_score, 2),
            },
            "weights": result.weights or {},
            "report": result.report or {},
            "configSnapshot": result.config_snapshot or {},
            "errorMessage": result.error_message,
            "createdAt": result.created_at.isoformat(),
            "updatedAt": result.updated_at.isoformat(),
        }

    def _resolve_grade(self, overall_score: float, thresholds: Dict[str, float]) -> str:
        """根据阈值计算评分等级。"""

        excellent = thresholds.get("excellent", 85)
        good = thresholds.get("good", 70)
        review = thresholds.get("review", 55)
        if overall_score >= excellent:
            return "excellent"
        if overall_score >= good:
            return "good"
        if overall_score >= review:
            return "review"
        return "low"

    def _compose_text(self, article: RSSArticle) -> str:
        """拼装文章用于评分的文本。"""

        parts = [article.title or "", article.summary or "", article.content or ""]
        text = "\n\n".join(part for part in parts if part)
        return self._strip_html(text)

    def _strip_html(self, raw_text: str) -> str:
        """移除 HTML 标签并解码实体。"""

        if not raw_text:
            return ""
        soup = BeautifulSoup(raw_text, "html.parser")
        text = soup.get_text("\n")
        text = html.unescape(text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    def _tokenize(self, text: str) -> List[str]:
        """对文本进行轻量分词。"""

        if not text:
            return []
        return [
            token.lower()
            for token in re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_\-]{1,}", text)
        ]

    def _build_shingles(self, tokens: List[str], shingle_size: int) -> set[str]:
        """构建词元切片集合。"""

        if len(tokens) < shingle_size:
            return {" ".join(tokens)} if tokens else set()
        return {
            " ".join(tokens[index : index + shingle_size])
            for index in range(len(tokens) - shingle_size + 1)
        }

    def _jaccard_similarity(self, left: Iterable[str], right: Iterable[str]) -> float:
        """计算 Jaccard 相似度。"""

        left_set = set(left)
        right_set = set(right)
        if not left_set or not right_set:
            return 0.0
        intersection = len(left_set & right_set)
        union = len(left_set | right_set)
        return intersection / union if union else 0.0

    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """标准化维度权重。"""

        merged_weights = {
            key: float(weights.get(key, DEFAULT_RSS_QUALITY_CONFIG["weights"][key]))
            for key in DIMENSION_KEYS
        }
        total = sum(max(value, 0.0) for value in merged_weights.values())
        if total <= 0:
            return self._clone_payload(DEFAULT_RSS_QUALITY_CONFIG["weights"])
        return {
            key: round(max(value, 0.0) / total, 4)
            for key, value in merged_weights.items()
        }

    def _normalize_thresholds(self, thresholds: Dict[str, float]) -> Dict[str, float]:
        """标准化评分阈值。"""

        default_thresholds = DEFAULT_RSS_QUALITY_CONFIG["thresholds"]
        merged = {
            "excellent": float(thresholds.get("excellent", default_thresholds["excellent"])),
            "good": float(thresholds.get("good", default_thresholds["good"])),
            "review": float(thresholds.get("review", default_thresholds["review"])),
        }
        merged["excellent"] = min(max(merged["excellent"], 0), 100)
        merged["good"] = min(max(merged["good"], 0), merged["excellent"])
        merged["review"] = min(max(merged["review"], 0), merged["good"])
        return merged

    def _merge_dict(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """递归合并字典配置。"""

        result = self._clone_payload(base)
        for key, value in (override or {}).items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self._merge_dict(result[key], value)
            else:
                result[key] = value
        return result

    def _clone_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """复制配置对象。"""

        if isinstance(payload, dict):
            return {key: self._clone_payload(value) if isinstance(value, dict) else list(value) if isinstance(value, list) else value for key, value in payload.items()}
        return payload


rss_quality_service = RSSQualityService()

