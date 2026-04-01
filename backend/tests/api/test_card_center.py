import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.card import Card, CardVersion
from unittest.mock import patch, AsyncMock, mock_open
import os

def test_create_card(client: TestClient):
    response = client.post(
        "/api/v1/cards/",
        json={"name": "test_card", "description": "A test card", "status": "draft"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "test_card"

def test_create_card_duplicate(client: TestClient, session: Session):
    c = Card(name="dup_card", description="desc", status="draft")
    session.add(c)
    session.commit()

    response = client.post(
        "/api/v1/cards/",
        json={"name": "dup_card", "description": "desc", "status": "draft"}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_list_cards(client: TestClient, session: Session):
    c = Card(name="list_card", description="desc", status="draft")
    session.add(c)
    session.commit()

    response = client.get("/api/v1/cards/")
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_get_card(client: TestClient, session: Session):
    c = Card(name="get_card", description="desc", status="draft")
    session.add(c)
    session.commit()
    session.refresh(c)

    response = client.get(f"/api/v1/cards/{c.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "get_card"

def test_get_card_not_found(client: TestClient):
    response = client.get("/api/v1/cards/9999")
    assert response.status_code == 404

def test_update_card(client: TestClient, session: Session):
    c = Card(name="upd_card", description="desc", status="draft")
    session.add(c)
    session.commit()
    session.refresh(c)

    response = client.put(f"/api/v1/cards/{c.id}", json={"status": "published"})
    assert response.status_code == 200
    assert response.json()["status"] == "published"

def test_delete_card(client: TestClient, session: Session):
    c = Card(name="del_card", description="desc", status="draft")
    session.add(c)
    session.commit()
    session.refresh(c)

    response = client.delete(f"/api/v1/cards/{c.id}")
    assert response.status_code == 200
    assert session.get(Card, c.id) is None

@patch("app.api.card_center.CardService.create_version")
def test_create_version(mock_create_v, client: TestClient, session: Session):
    c = Card(name="ver_card", description="desc", status="draft")
    session.add(c)
    session.commit()
    session.refresh(c)
    
    mock_create_v.return_value = CardVersion(card_id=c.id, version=1, code="<div>test</div>", changelog="init")

    response = client.post(
        f"/api/v1/cards/{c.id}/versions",
        json={"code": "<div>test</div>", "changelog": "init", "version": 1, "card_id": c.id}
    )
    assert response.status_code == 200
    assert response.json()["changelog"] == "init"

def test_get_versions(client: TestClient, session: Session):
    c = Card(name="v_list_card", description="desc", status="draft")
    session.add(c)
    session.commit()
    session.refresh(c)

    v = CardVersion(card_id=c.id, version=1, code="...", changelog=".")
    session.add(v)
    session.commit()

    response = client.get(f"/api/v1/cards/{c.id}/versions")
    assert response.status_code == 200
    assert len(response.json()) >= 1

@patch("app.api.card_center.ai_service.generate_card_code", new_callable=AsyncMock)
def test_generate_card(mock_gen, client: TestClient):
    mock_gen.return_value = "<div>ai</div>"
    response = client.post("/api/v1/cards/generate?prompt=test")
    assert response.status_code == 200
    assert response.json()["code"] == "<div>ai</div>"

@patch("builtins.open", new_callable=mock_open)
@patch("os.makedirs")
def test_publish_card(mock_makedirs, mock_open_file, client: TestClient, session: Session):
    c = Card(name="pub_card", description="desc", status="draft")
    session.add(c)
    session.commit()
    session.refresh(c)

    v = CardVersion(card_id=c.id, version=1, code="<template></template>", changelog="init")
    session.add(v)
    session.commit()

    response = client.post(f"/api/v1/cards/{c.id}/publish/1")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    
    session.refresh(c)
    assert c.status == "published"
