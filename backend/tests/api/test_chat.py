import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.chat import ChatSession, ChatMessage
import uuid
from unittest.mock import patch, MagicMock

def test_create_session(client: TestClient, session: Session):
    response = client.post("/api/v1/chat/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["title"] == "New Chat"

def test_get_sessions(client: TestClient, session: Session):
    # Create a session first
    sess = ChatSession(title="Test Session")
    session.add(sess)
    session.commit()

    response = client.get("/api/v1/chat/sessions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_get_qqbot_session(client: TestClient):
    response = client.get("/api/v1/chat/qqbot-session")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "QQBot 协同会话"

def test_get_messages(client: TestClient, session: Session):
    sess = ChatSession(title="Test Msg Session")
    session.add(sess)
    session.commit()
    session.refresh(sess)

    msg = ChatMessage(session_id=sess.id, role="user", content="Hello")
    session.add(msg)
    session.commit()

    response = client.get(f"/api/v1/chat/sessions/{sess.id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "Hello"

@patch("app.api.chat.chat_service.send_message")
def test_send_message(mock_send_message, client: TestClient, session: Session):
    sess = ChatSession(title="Send Session")
    session.add(sess)
    session.commit()
    session.refresh(sess)

    # Mock the generator
    async def mock_stream():
        yield b'{"content": "Hi"}\n'
    
    mock_send_message.return_value = mock_stream()

    response = client.post(
        f"/api/v1/chat/sessions/{sess.id}/send",
        json={"content": "Hi", "model_id": "test-model"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"
    assert "Hi" in response.text

@patch("app.api.chat.chat_service.subscribe")
def test_session_events(mock_subscribe, client: TestClient, session: Session):
    sess = ChatSession(title="Event Session")
    session.add(sess)
    session.commit()
    session.refresh(sess)

    import asyncio
    q = asyncio.Queue()
    q.put_nowait({"type": "test"})
    
    # We also need to put a sentinel to stop or we just read one item
    mock_subscribe.return_value = q

    # To prevent infinite loop in SSE test client, we can close it early or mock request.is_disconnected
    with patch("fastapi.Request.is_disconnected", side_effect=[False, True]):
        response = client.get(f"/api/v1/chat/sessions/{sess.id}/events")
        assert response.status_code == 200
        text = response.text
        assert "data: " in text
        assert "test" in text

@patch("app.api.chat.chat_service.get_enabled_models")
def test_list_models(mock_get_models, client: TestClient):
    mock_get_models.return_value = [{"id": "test-model", "name": "Test Model"}]
    response = client.get("/api/v1/chat/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "test-model"

def test_delete_session(client: TestClient, session: Session):
    sess = ChatSession(title="Delete Session")
    session.add(sess)
    session.commit()
    session.refresh(sess)

    response = client.delete(f"/api/v1/chat/sessions/{sess.id}")
    assert response.status_code == 200

    deleted = session.get(ChatSession, sess.id)
    assert deleted is None

def test_delete_session_not_found(client: TestClient):
    fake_id = uuid.uuid4()
    response = client.delete(f"/api/v1/chat/sessions/{fake_id}")
    assert response.status_code == 404

def test_update_session(client: TestClient, session: Session):
    sess = ChatSession(title="Old Title")
    session.add(sess)
    session.commit()
    session.refresh(sess)

    response = client.patch(
        f"/api/v1/chat/sessions/{sess.id}",
        json={"title": "New Title"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"

def test_update_feedback(client: TestClient, session: Session):
    sess = ChatSession(title="Feedback Session")
    session.add(sess)
    session.commit()
    session.refresh(sess)

    msg = ChatMessage(session_id=sess.id, role="user", content="Hello")
    session.add(msg)
    session.commit()
    session.refresh(msg)

    response = client.post(
        f"/api/v1/chat/messages/{msg.id}/feedback",
        json={"feedback": "like"}
    )
    assert response.status_code == 200
    
    session.refresh(msg)
    assert msg.feedback == "like"

def test_update_favorite(client: TestClient, session: Session):
    sess = ChatSession(title="Fav Session")
    session.add(sess)
    session.commit()
    session.refresh(sess)

    msg = ChatMessage(session_id=sess.id, role="user", content="Hello")
    session.add(msg)
    session.commit()
    session.refresh(msg)

    response = client.post(
        f"/api/v1/chat/messages/{msg.id}/favorite",
        json={"is_favorite": True}
    )
    assert response.status_code == 200
    
    session.refresh(msg)
    assert msg.is_favorite is True

def test_share_session(client: TestClient, session: Session):
    sess = ChatSession(title="Share Session")
    session.add(sess)
    session.commit()
    session.refresh(sess)

    response = client.post(f"/api/v1/chat/sessions/{sess.id}/share")
    assert response.status_code == 200
    assert "share_id" in response.json()

    share_id = response.json()["share_id"]
    
    # test get_shared_session
    response2 = client.get(f"/api/v1/chat/shared/{share_id}")
    assert response2.status_code == 200
    assert response2.json()["session"]["title"] == "Share Session"
