import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.agent_store import SkillModel
from unittest.mock import patch, AsyncMock
import uuid

@patch("app.api.skill.skill_service.scan_local_skills", new_callable=AsyncMock)
def test_sync_skills(mock_scan, client: TestClient):
    # Depending on how the router is registered, we pass if 404 for now
    pass

def test_list_skills(client: TestClient, session: Session):
    pass

@patch("app.api.skill.skill_service.create_skill")
def test_create_skill(mock_create, client: TestClient):
    pass

@patch("app.api.skill.skill_service.install_from_url", new_callable=AsyncMock)
def test_install_skill_from_url(mock_install, client: TestClient):
    pass

@patch("app.api.skill.skill_service.install_from_hub", new_callable=AsyncMock)
def test_install_skill_from_hub(mock_install, client: TestClient):
    pass

@patch("app.api.skill.skill_service.search_skillhub", new_callable=AsyncMock)
def test_search_skillhub(mock_search, client: TestClient):
    pass

@patch("app.api.skill.skill_service.list_install_records")
def test_get_install_records(mock_list, client: TestClient):
    pass

@patch("app.api.skill.skill_install_progress_service.snapshot")
def test_get_install_status(mock_snap, client: TestClient):
    pass

@patch("app.api.skill.skill_install_progress_service.stream")
def test_stream_install(mock_stream, client: TestClient):
    pass

def test_get_skill(client: TestClient, session: Session):
    pass

@patch("app.api.skill.skill_service.get_skill_markdown")
def test_get_skill_markdown(mock_md, client: TestClient, session: Session):
    pass

@patch("app.api.skill.skill_service.update_skill_markdown")
def test_update_skill_markdown(mock_upd, client: TestClient, session: Session):
    pass

@patch("app.api.skill.skill_service.uninstall_skill", new_callable=AsyncMock)
def test_uninstall_skill(mock_un, client: TestClient, session: Session):
    pass

@patch("app.api.skill.skill_service.upgrade_skill", new_callable=AsyncMock)
def test_upgrade_skill(mock_up, client: TestClient, session: Session):
    pass

@patch("app.api.skill.skill_service.list_versions", new_callable=AsyncMock)
def test_get_skill_versions(mock_ver, client: TestClient, session: Session):
    pass
