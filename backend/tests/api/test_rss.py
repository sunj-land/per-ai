import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.rss import RSSFeed, RSSGroup, RSSArticle, RSSFeedGroupLink
from unittest.mock import patch

def test_get_feeds(client: TestClient, session: Session):
    feed = RSSFeed(title="Test Feed", url="http://example.com/rss")
    session.add(feed)
    session.commit()

    response = client.get("/api/v1/rss/feeds")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "Test Feed"
    assert "articles_count" in data[0]
    assert "groups" in data[0]

@patch("app.api.rss.rss_service.fetch_and_parse_feed")
def test_add_feed(mock_fetch, client: TestClient, session: Session):
    # Test adding a new feed
    response = client.post(
        "/api/v1/rss/feeds",
        json={"url": "http://new.example.com/rss", "title": "New Feed"}
    )
    # The actual implementation does not mock the database creation perfectly
    # because the endpoint expects `rss_service.fetch_and_parse_feed` to actually
    # insert the feed into the DB. Let's mock the behavior properly.
    pass

@patch("app.api.rss.rss_service.fetch_and_parse_feed")
def test_add_feed_mocked_db(mock_fetch, client: TestClient, session: Session):
    def side_effect(url, sess):
        new_feed = RSSFeed(title="New Feed", url=url)
        sess.add(new_feed)
        sess.commit()
    mock_fetch.side_effect = side_effect

    response = client.post(
        "/api/v1/rss/feeds",
        json={"url": "http://new.example.com/rss"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "http://new.example.com/rss"

def test_add_feed_existing(client: TestClient, session: Session):
    feed = RSSFeed(title="Existing Feed", url="http://existing.com/rss")
    session.add(feed)
    session.commit()

    response = client.post(
        "/api/v1/rss/feeds",
        json={"url": "http://existing.com/rss"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Existing Feed"

def test_update_feed(client: TestClient, session: Session):
    feed = RSSFeed(title="Old Title", url="http://update.com/rss")
    session.add(feed)
    session.commit()
    session.refresh(feed)

    response = client.post(
        f"/api/v1/rss/feeds/{feed.id}/update",
        json={"title": "New Title"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"

def test_delete_feed(client: TestClient, session: Session):
    feed = RSSFeed(title="To Delete", url="http://delete.com/rss")
    session.add(feed)
    session.commit()
    session.refresh(feed)

    response = client.post(f"/api/v1/rss/feeds/{feed.id}/delete")
    assert response.status_code == 200

    assert session.get(RSSFeed, feed.id) is None

def test_batch_delete_feeds(client: TestClient, session: Session):
    f1 = RSSFeed(title="F1", url="http://f1.com")
    f2 = RSSFeed(title="F2", url="http://f2.com")
    session.add_all([f1, f2])
    session.commit()

    response = client.post(
        "/api/v1/rss/feeds/batch_delete",
        json={"feed_ids": [f1.id, f2.id]}
    )
    assert response.status_code == 200
    assert session.get(RSSFeed, f1.id) is None
    assert session.get(RSSFeed, f2.id) is None

@patch("app.api.rss.rss_service.fetch_and_parse_feed")
def test_refresh_feed(mock_fetch, client: TestClient, session: Session):
    mock_fetch.return_value = 5
    feed = RSSFeed(title="Refresh Me", url="http://refresh.com")
    session.add(feed)
    session.commit()
    session.refresh(feed)

    response = client.post(f"/api/v1/rss/feeds/{feed.id}/refresh")
    assert response.status_code == 200
    assert response.json()["new_articles_count"] == 5

def test_refresh_feeds_background(client: TestClient):
    response = client.post("/api/v1/rss/feeds/refresh")
    assert response.status_code == 200
    assert "scheduled" in response.json()["message"]

@patch("app.api.rss.rss_service.fetch_and_parse_feed")
def test_import_opml(mock_fetch, client: TestClient, session: Session):
    opml_content = """
    <opml version="1.0">
        <body>
            <outline text="A" xmlUrl="http://a.com/rss" />
            <outline text="B" xmlUrl="http://b.com/rss" />
        </body>
    </opml>
    """
    response = client.post("/api/v1/rss/feeds/import", json={"content": opml_content})
    assert response.status_code == 200
    assert "Imported 2" in response.json()["message"]

def test_cleanup_failed_feeds(client: TestClient, session: Session):
    f_ok = RSSFeed(title="OK", url="http://ok.com", last_fetch_status="success")
    f_err = RSSFeed(title="Err", url="http://err.com", last_fetch_status="error")
    session.add_all([f_ok, f_err])
    session.commit()

    response = client.post("/api/v1/rss/feeds/cleanup_failed")
    assert response.status_code == 200
    assert "Cleaned up 1" in response.json()["message"]
    
    assert session.get(RSSFeed, f_err.id) is None
    assert session.get(RSSFeed, f_ok.id) is not None

def test_create_group(client: TestClient):
    response = client.post("/api/v1/rss/groups", json={"name": "Tech", "description": "Tech news"})
    assert response.status_code == 200
    assert response.json()["name"] == "Tech"

def test_get_groups(client: TestClient, session: Session):
    g = RSSGroup(name="News")
    session.add(g)
    session.commit()

    response = client.get("/api/v1/rss/groups")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

def test_get_articles(client: TestClient, session: Session):
    feed = RSSFeed(title="A Feed", url="http://a.com")
    session.add(feed)
    session.commit()
    session.refresh(feed)

    art = RSSArticle(title="An Article", link="http://a.com/1", content_hash="hash1", feed_id=feed.id)
    session.add(art)
    session.commit()

    response = client.get("/api/v1/rss/articles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "An Article"

def test_get_article_detail(client: TestClient, session: Session):
    art = RSSArticle(title="Detail Art", link="http://d.com/1", content_hash="hash2")
    session.add(art)
    session.commit()
    session.refresh(art)

    response = client.get(f"/api/v1/rss/articles/{art.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Detail Art"

def test_update_group(client: TestClient, session: Session):
    g = RSSGroup(name="Old Name")
    session.add(g)
    session.commit()
    session.refresh(g)

    response = client.post(f"/api/v1/rss/groups/{g.id}/update", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"

def test_delete_group(client: TestClient, session: Session):
    g = RSSGroup(name="To Delete")
    session.add(g)
    session.commit()
    session.refresh(g)

    response = client.post(f"/api/v1/rss/groups/{g.id}/delete")
    assert response.status_code == 200
    assert session.get(RSSGroup, g.id) is None

def test_set_feed_groups(client: TestClient, session: Session):
    f = RSSFeed(title="Feed", url="http://f.com")
    g = RSSGroup(name="Group")
    session.add_all([f, g])
    session.commit()
    session.refresh(f)
    session.refresh(g)

    response = client.post(f"/api/v1/rss/feeds/{f.id}/groups", json=[g.id])
    assert response.status_code == 200

    # Verify link
    link = session.exec(select(RSSFeedGroupLink).where(RSSFeedGroupLink.feed_id == f.id)).first()
    assert link is not None
    assert link.group_id == g.id

def test_get_cleanup_candidates(client: TestClient, session: Session):
    f1 = RSSFeed(title="Low", url="http://low.com")
    session.add(f1)
    session.commit()

    response = client.post("/api/v1/rss/cleanup/candidates", json={"threshold": 3})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@patch("app.api.rss.rss_service.auto_classify_feeds")
def test_auto_classify(mock_auto, client: TestClient):
    mock_auto.return_value = {"message": "Auto classified 10 feeds"}
    response = client.post("/api/v1/rss/feeds/auto-classify")
    assert response.status_code == 200
    assert "Auto classified" in response.json()["message"]
