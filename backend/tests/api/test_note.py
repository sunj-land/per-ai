import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.note import ArticleNote, ArticleSummary
from app.models.rss import RSSArticle, RSSFeed

@pytest.fixture(name="mock_article")
def mock_article_fixture(session: Session):
    feed = RSSFeed(title="Feed", url="http://f.com")
    session.add(feed)
    session.commit()
    session.refresh(feed)

    art = RSSArticle(title="Article", link="http://a.com/1", content_hash="h", feed_id=feed.id)
    session.add(art)
    session.commit()
    session.refresh(art)
    return art

def test_create_note(client: TestClient, session: Session, mock_article: RSSArticle):
    response = client.post(
        "/api/v1/note/notes",
        json={
            "article_id": mock_article.id,
            "selected_text": "hello",
            "start_offset": 0,
            "end_offset": 5,
            "color": "yellow",
            "content": "A note"
        }
    )
    assert response.status_code == 200
    assert response.json()["selected_text"] == "hello"

def test_get_notes_by_article(client: TestClient, session: Session, mock_article: RSSArticle):
    n = ArticleNote(
        article_id=mock_article.id,
        selected_text="txt",
        start_offset=1,
        end_offset=4,
        color="red"
    )
    session.add(n)
    session.commit()

    response = client.get(f"/api/v1/note/notes/article/{mock_article.id}")
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_update_note(client: TestClient, session: Session, mock_article: RSSArticle):
    n = ArticleNote(
        article_id=mock_article.id,
        selected_text="txt",
        start_offset=1,
        end_offset=4,
        color="red",
        content="old"
    )
    session.add(n)
    session.commit()
    session.refresh(n)

    response = client.put(f"/api/v1/note/notes/{n.id}", json={"content": "new"})
    assert response.status_code == 200
    assert response.json()["content"] == "new"

def test_update_note_post(client: TestClient, session: Session, mock_article: RSSArticle):
    n = ArticleNote(
        article_id=mock_article.id,
        selected_text="txt",
        start_offset=1,
        end_offset=4,
        color="red",
        content="old"
    )
    session.add(n)
    session.commit()
    session.refresh(n)

    response = client.post(f"/api/v1/note/notes/{n.id}/update", json={"content": "new_post"})
    assert response.status_code == 200
    assert response.json()["content"] == "new_post"

def test_delete_note(client: TestClient, session: Session, mock_article: RSSArticle):
    n = ArticleNote(article_id=mock_article.id, selected_text="t", start_offset=0, end_offset=1, color="red")
    session.add(n)
    session.commit()
    session.refresh(n)

    response = client.delete(f"/api/v1/note/notes/{n.id}")
    assert response.status_code == 200
    assert session.get(ArticleNote, n.id) is None

def test_delete_note_post(client: TestClient, session: Session, mock_article: RSSArticle):
    n = ArticleNote(article_id=mock_article.id, selected_text="t", start_offset=0, end_offset=1, color="red")
    session.add(n)
    session.commit()
    session.refresh(n)

    response = client.post(f"/api/v1/note/notes/{n.id}/delete")
    assert response.status_code == 200
    assert session.get(ArticleNote, n.id) is None

def test_create_summary(client: TestClient, session: Session, mock_article: RSSArticle):
    response = client.post(
        "/api/v1/note/summaries",
        json={"article_id": mock_article.id, "content": "sum", "is_draft": False}
    )
    assert response.status_code == 200
    assert response.json()["content"] == "sum"

def test_update_summary(client: TestClient, session: Session, mock_article: RSSArticle):
    s = ArticleSummary(article_id=mock_article.id, content="s1")
    session.add(s)
    session.commit()

    response = client.post(
        "/api/v1/note/summaries",
        json={"article_id": mock_article.id, "content": "s2", "is_draft": False}
    )
    assert response.status_code == 200
    assert response.json()["content"] == "s2"
    assert response.json()["version"] == 2

def test_get_summary_by_article(client: TestClient, session: Session, mock_article: RSSArticle):
    s = ArticleSummary(article_id=mock_article.id, content="sum")
    session.add(s)
    session.commit()

    response = client.get(f"/api/v1/note/summaries/article/{mock_article.id}")
    assert response.status_code == 200
    assert response.json()["content"] == "sum"

def test_delete_summary(client: TestClient, session: Session, mock_article: RSSArticle):
    s = ArticleSummary(article_id=mock_article.id, content="sum")
    session.add(s)
    session.commit()
    session.refresh(s)

    response = client.delete(f"/api/v1/note/summaries/{s.id}")
    assert response.status_code == 200
    assert session.get(ArticleSummary, s.id) is None
