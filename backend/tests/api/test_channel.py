import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.channel import Channel, ChannelMessage
import uuid
from unittest.mock import patch, AsyncMock

# We need to use the real db logic or mock the channel_service since channel API uses channel_service internally
# Let's mock the channel_service methods to match what the endpoint expects.

@patch("app.api.channel.channel_service.create_channel")
def test_create_channel(mock_create, client: TestClient):
    mock_create.return_value = Channel(name="Test Channel", type="dingtalk", config={"webhook": "http://test"})
    response = client.post(
        "/api/v1/channels/",
        json={
            "name": "Test Channel",
            "type": "dingtalk",
            "config": {"webhook": "http://test"}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Channel"
    assert "id" in data

@patch("app.api.channel.channel_service.get_channels")
def test_get_channels(mock_get_all, client: TestClient):
    mock_get_all.return_value = [Channel(name="C1", type="dingtalk", config={})]
    response = client.get("/api/v1/channels/")
    assert response.status_code == 200
    assert len(response.json()) >= 1

@patch("app.api.channel.channel_service.get_channel")
def test_get_channel(mock_get, client: TestClient):
    ch_id = uuid.uuid4()
    mock_get.return_value = Channel(id=ch_id, name="C2", type="dingtalk", config={})
    response = client.get(f"/api/v1/channels/{str(ch_id)}")
    assert response.status_code == 200
    assert response.json()["name"] == "C2"

@patch("app.api.channel.channel_service.get_channel")
def test_get_channel_not_found(mock_get, client: TestClient):
    mock_get.return_value = None
    response = client.get(f"/api/v1/channels/{str(uuid.uuid4())}")
    assert response.status_code == 404

@patch("app.api.channel.channel_service.update_channel")
def test_update_channel(mock_update, client: TestClient):
    ch_id = uuid.uuid4()
    mock_update.return_value = Channel(id=ch_id, name="C3 Updated", type="dingtalk", config={})
    response = client.put(
        f"/api/v1/channels/{str(ch_id)}",
        json={"name": "C3 Updated"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "C3 Updated"

@patch("app.api.channel.channel_service.delete_channel")
def test_delete_channel(mock_delete, client: TestClient):
    mock_delete.return_value = True
    response = client.delete(f"/api/v1/channels/{str(uuid.uuid4())}")
    assert response.status_code == 200
    assert response.json() is True

@patch("app.api.channel.channel_service.get_messages")
def test_get_messages(mock_get_msgs, client: TestClient):
    ch_id = uuid.uuid4()
    mock_get_msgs.return_value = {
        "total": 1,
        "items": [ChannelMessage(channel_id=ch_id, content="hello", status="success")]
    }
    response = client.get("/api/v1/channels/messages")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) >= 1

@patch("app.api.channel.channel_service.get_channel_messages")
def test_get_channel_messages(mock_get_ch_msgs, client: TestClient):
    ch_id = uuid.uuid4()
    mock_get_ch_msgs.return_value = [ChannelMessage(channel_id=ch_id, content="test msg", status="success")]
    response = client.get(f"/api/v1/channels/{str(ch_id)}/messages")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["content"] == "test msg"

@patch("app.api.channel.channel_service.handle_webhook", new_callable=AsyncMock)
def test_handle_webhook(mock_handle, client: TestClient):
    mock_handle.return_value = {"status": "ok"}
    response = client.post(
        f"/api/v1/channels/{str(uuid.uuid4())}/webhook",
        json={"event": "ping"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("app.api.channel.channel_service.send_message", new_callable=AsyncMock)
def test_send_message(mock_send, client: TestClient, session: Session):
    ch = Channel(name="C7", type="dingtalk", config={})
    session.add(ch)
    session.commit()
    session.refresh(ch)

    mock_send.return_value = ChannelMessage(channel_id=ch.id, content="msg", status="success")

    response = client.post(
        f"/api/v1/channels/{str(ch.id)}/send",
        json={"content": "hello"}
    )
    assert response.status_code == 200
    assert response.json()["content"] == "msg"

@patch("app.api.channel.channel_service.broadcast", new_callable=AsyncMock)
def test_broadcast_message(mock_broadcast, client: TestClient):
    mock_broadcast.return_value = []
    response = client.post(
        "/api/v1/channels/broadcast",
        json={"content": "hello all"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)