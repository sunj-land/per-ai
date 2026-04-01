from datetime import datetime, timedelta

from sqlmodel import Session

from app.models.rss import RSSArticle, RSSFeed
import app.services.rss_quality_service as rss_quality_service_module


def _create_feed_and_articles(session: Session) -> dict[str, int]:
    feed = RSSFeed(
        url="https://example.com/rss.xml",
        title="AI Weekly",
        description="AI feed",
    )
    session.add(feed)
    session.commit()
    session.refresh(feed)

    now = datetime.utcnow()
    article_one = RSSArticle(
        feed_id=feed.id,
        title="2026 AI Agent 增长趋势完整指南",
        link="https://example.com/articles/1",
        summary="聚焦大模型、自动化与增长策略。",
        content="""
        <p>最新 AI Agent 市场正在快速演进。</p>
        <p>本文将拆解产品策略、自动化工作流与增长模型。</p>
        <p>我们还会分析 API 生态、开发者工具与商业化机会。</p>
        """,
        published_at=now - timedelta(hours=6),
        content_hash="hash-article-1",
    )
    article_two = RSSArticle(
        feed_id=feed.id,
        title="AI Agent 增长趋势完整指南",
        link="https://example.com/articles/2",
        summary="和上一篇高度相似的内容。",
        content="""
        <p>最新 AI Agent 市场正在快速演进。</p>
        <p>本文将拆解产品策略、自动化工作流与增长模型。</p>
        <p>我们还会分析 API 生态、开发者工具与商业化机会。</p>
        """,
        published_at=now - timedelta(days=18),
        content_hash="hash-article-1",
    )
    session.add(article_one)
    session.add(article_two)
    session.commit()
    session.refresh(article_one)
    session.refresh(article_two)
    return {
        "feed_id": feed.id,
        "article_one_id": article_one.id,
        "article_two_id": article_two.id,
    }


def test_rss_quality_config_update_and_default(client, session: Session, monkeypatch):
    monkeypatch.setattr(rss_quality_service_module, "engine", session.bind)
    response = client.get("/api/v1/agent-center/rss-quality/config")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert set(body["data"]["weights"].keys()) == {
        "originality",
        "information_value",
        "writing_quality",
        "interaction_potential",
        "timeliness",
    }

    update_response = client.put(
        "/api/v1/agent-center/rss-quality/config",
        json={
            "name": "运营评分规则",
            "weights": {
                "originality": 0.3,
                "information_value": 0.25,
                "writing_quality": 0.15,
                "interaction_potential": 0.15,
                "timeliness": 0.15,
            },
            "thresholds": {
                "excellent": 90,
                "good": 75,
                "review": 60,
            },
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["name"] == "运营评分规则"
    assert updated["thresholds"]["excellent"] == 90
    assert updated["weights"]["originality"] == 0.3

    default_response = client.get("/api/v1/agent-center/rss-quality/config/default")
    assert default_response.status_code == 200
    assert default_response.json()["data"]["name"] == "RSS 默认评分规则"


def test_rss_quality_batch_scoring_result_filter_and_logs(client, session: Session, monkeypatch):
    monkeypatch.setattr(rss_quality_service_module, "engine", session.bind)
    seed = _create_feed_and_articles(session)

    score_response = client.post(
        "/api/v1/agent-center/rss-quality/score",
        json={
            "feed_id": seed["feed_id"],
            "limit": 10,
            "concurrency": 2,
        },
    )
    assert score_response.status_code == 200
    score_body = score_response.json()
    assert score_body["code"] == 0
    data = score_body["data"]
    assert data["summary"]["total"] == 2
    assert len(data["results"]) == 2
    assert all(0 <= item["overallScore"] <= 100 for item in data["results"])

    batch_id = data["batchId"]
    results_response = client.get(
        "/api/v1/agent-center/rss-quality/results",
        params={"batch_id": batch_id, "min_score": 0, "max_score": 100, "limit": 10},
    )
    assert results_response.status_code == 200
    results = results_response.json()["data"]
    assert len(results) == 2
    assert results[0]["batchId"] == batch_id
    assert "report" in results[0]

    filtered_response = client.get(
        "/api/v1/agent-center/rss-quality/results",
        params={"min_score": 70, "limit": 10},
    )
    assert filtered_response.status_code == 200
    filtered_results = filtered_response.json()["data"]
    assert all(item["overallScore"] >= 70 for item in filtered_results)

    log_response = client.get(
        "/api/v1/agent-center/rss-quality/logs",
        params={"batch_id": batch_id, "limit": 20},
    )
    assert log_response.status_code == 200
    logs = log_response.json()["data"]
    assert len(logs) >= 4
    assert all(log["batchId"] == batch_id for log in logs)
