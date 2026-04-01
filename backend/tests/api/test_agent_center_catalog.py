import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.services.agent_center_catalog_service as catalog_module
from app.services.agent_center_catalog_service import (
    DataPathNotFoundError,
    FileParseError,
    _CatalogWatchHandler,
    agent_center_catalog_service,
)


@pytest.fixture(autouse=True)
def reset_agent_center_catalog_service():
    agent_center_catalog_service.shutdown()
    yield
    agent_center_catalog_service.shutdown()


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _setup_env(monkeypatch: pytest.MonkeyPatch, agent_dir: Path, skill_dir: Path):
    monkeypatch.setenv("AGENT_DATA_PATH", str(agent_dir))
    monkeypatch.setenv("SKILL_DATA_PATH", str(skill_dir))


def test_agent_center_list_success_with_required_fields(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    agent_dir = tmp_path / "agents"
    skill_dir = tmp_path / "skills"
    _write_json(
        agent_dir / "planner" / "agent.json",
        {
            "id": "agent-planner",
            "name": "PlannerAgent",
            "description": "plan tasks",
            "version": "1.0.0",
            "enabled": True,
        },
    )
    _write_json(
        skill_dir / "search" / "skill.json",
        {
            "id": "skill-search",
            "name": "SearchSkill",
            "description": "search docs",
            "version": "2.1.0",
            "enabled": True,
            "tags": ["search"],
        },
    )
    _setup_env(monkeypatch, agent_dir, skill_dir)

    sync_agents_resp = client.post("/api/v1/agent-center/agents/sync")
    assert sync_agents_resp.status_code == 200
    sync_skills_resp = client.post("/api/v1/agent-center/skills/sync")
    assert sync_skills_resp.status_code == 200

    agents_resp = client.get("/api/v1/agent-center/agents")
    skills_resp = client.get("/api/v1/agent-center/skills")
    assert agents_resp.status_code == 200
    assert skills_resp.status_code == 200

    agents_body = agents_resp.json()
    skills_body = skills_resp.json()
    assert agents_body["code"] == 0
    assert skills_body["code"] == 0
    assert len(agents_body["data"]) > 0
    assert len(skills_body["data"]) > 0

    for item in [agents_body["data"][0], skills_body["data"][0]]:
        assert "id" in item
        assert "name" in item
        assert "description" in item
        assert "version" in item
        assert "enabled" in item
        assert "createdAt" in item
        assert "updatedAt" in item

    paged_resp = client.get("/api/v1/agent-center/skills?page=1&size=1")
    assert paged_resp.status_code == 200
    assert len(paged_resp.json()["data"]) == 1


def test_agent_center_data_path_missing_returns_422(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    missing_agent_dir = tmp_path / "missing-agents"
    skill_dir = tmp_path / "skills"
    _write_json(skill_dir / "ok" / "skill.json", {"id": "s-1", "name": "skill-1"})
    _setup_env(monkeypatch, missing_agent_dir, skill_dir)

    response = client.get("/api/v1/agent-center/agents")
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 422
    assert body["msg"] == "agent data path not found"
    assert "path" in body["data"]


def test_agent_center_parse_error_returns_422(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    agent_dir = tmp_path / "agents"
    skill_dir = tmp_path / "skills"
    _write_json(agent_dir / "ok" / "agent.json", {"id": "a-1", "name": "agent-1"})
    broken = skill_dir / "broken" / "skill.json"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text('{"id":"broken","name":"bad",}', encoding="utf-8")
    _setup_env(monkeypatch, agent_dir, skill_dir)

    response = client.get("/api/v1/agent-center/skills")
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 422
    assert body["msg"] == "skill data parse failed"
    assert any("skill.json" in item["file"] for item in body["data"]["errors"])


def test_agent_center_duplicate_id_returns_400(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    agent_dir = tmp_path / "agents"
    skill_dir = tmp_path / "skills"
    _write_json(agent_dir / "a1" / "agent.json", {"id": "dup-id", "name": "A1"})
    _write_json(agent_dir / "a2" / "agent.json", {"id": "dup-id", "name": "A2"})
    _write_json(skill_dir / "s1" / "skill.json", {"id": "s-1", "name": "S1"})
    _setup_env(monkeypatch, agent_dir, skill_dir)

    response = client.get("/api/v1/agent-center/agents")
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 400
    assert body["msg"] == "duplicate agent id conflict"
    assert len(body["data"]["conflicts"]) == 1


def test_agent_center_concurrent_requests_are_safe(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    agent_dir = tmp_path / "agents"
    skill_dir = tmp_path / "skills"
    _write_json(agent_dir / "a1" / "agent.json", {"id": "a-1", "name": "A1"})
    _write_json(skill_dir / "s1" / "skill.json", {"id": "s-1", "name": "S1"})
    _setup_env(monkeypatch, agent_dir, skill_dir)

    def _fetch():
        response = client.get("/api/v1/agent-center/skills")
        assert response.status_code == 200
        assert response.json()["code"] == 0
        return len(response.json()["data"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _i: _fetch(), range(20)))
    assert all(length >= 1 for length in results)


def test_agent_center_cache_auto_refresh_on_file_change(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    agent_dir = tmp_path / "agents"
    skill_dir = tmp_path / "skills"
    _write_json(agent_dir / "a1" / "agent.json", {"id": "a-1", "name": "A1"})
    _write_json(skill_dir / "s1" / "skill.json", {"id": "s-1", "name": "S1"})
    _setup_env(monkeypatch, agent_dir, skill_dir)

    first = client.get("/api/v1/agent-center/skills")
    assert first.status_code == 200
    assert len(first.json()["data"]) == 1

    _write_json(skill_dir / "s2" / "skill.json", {"id": "s-2", "name": "S2"})

    updated_len = 0
    for _ in range(8):
        response = client.get("/api/v1/agent-center/skills")
        if response.status_code == 200:
            updated_len = len(response.json()["data"])
            if updated_len >= 2:
                break
        time.sleep(0.8)
    assert updated_len >= 2


def test_catalog_private_helpers_and_markdown_build(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    service = agent_center_catalog_service
    service.shutdown()
    agent_dir = tmp_path / "agents"
    skill_dir = tmp_path / "skills"
    _setup_env(monkeypatch, agent_dir, skill_dir)
    md_path = agent_dir / "writer" / "README.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("# WriterAgent\n\nAgent for writing", encoding="utf-8")

    title, desc = service._extract_markdown_name_desc(str(md_path))
    assert title == "WriterAgent"
    assert desc == "Agent for writing"

    item = service._build_item("agents", str(agent_dir), str(md_path))
    assert item["id"].startswith("agents:")
    assert item["name"] == "WriterAgent"
    assert item["enabled"] is True
    assert service._sanitize_name("  ") == "unknown"
    assert service._extract_enabled({"status": "disabled"}) is False


def test_catalog_path_missing_and_yaml_parser_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    service = agent_center_catalog_service
    service.shutdown()
    missing = tmp_path / "missing"
    _setup_env(monkeypatch, missing, missing)
    service._paths = {"agents": str(missing), "skills": str(missing)}
    with pytest.raises(DataPathNotFoundError):
        service._reload_locked("agents")

    yaml_path = tmp_path / "skills" / "bad.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text("name: a", encoding="utf-8")
    old_yaml = catalog_module.yaml
    monkeypatch.setattr(catalog_module, "yaml", None)
    with pytest.raises(FileParseError):
        service._load_structured_data(str(yaml_path))
    monkeypatch.setattr(catalog_module, "yaml", old_yaml)
    with pytest.raises(FileParseError):
        service._extract_markdown_name_desc(str(tmp_path / "not-exists.md"))


def test_catalog_watch_handler_and_poll_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    service = agent_center_catalog_service
    service.shutdown()
    calls = {"refresh": 0}

    def _mock_refresh_all():
        calls["refresh"] += 1

    service.refresh_all = _mock_refresh_all
    handler = _CatalogWatchHandler(service)
    handler.on_any_event(None)
    assert calls["refresh"] == 1

    monkeypatch.setattr(catalog_module, "Observer", None)
    service._paths = {"agents": str(tmp_path / "a"), "skills": str(tmp_path / "s")}
    service._start_watchers_locked()
    assert service._poll_thread is not None
    service._poll_stop_event.set()
    service._poll_thread.join(timeout=2)
    service._poll_thread = None


def test_catalog_poll_loop_triggers_refresh_and_handles_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    service = agent_center_catalog_service
    service.shutdown()
    agent_dir = tmp_path / "agents"
    skill_dir = tmp_path / "skills"
    _write_json(agent_dir / "a1" / "agent.json", {"id": "a-1", "name": "A1"})
    _write_json(skill_dir / "s1" / "skill.json", {"id": "s-1", "name": "S1"})
    service._paths = {"agents": str(agent_dir), "skills": str(skill_dir)}
    service._snapshot = {"agents": tuple(), "skills": tuple()}
    called = {"count": 0}

    def _refresh():
        called["count"] += 1
        raise RuntimeError("expected in test")

    service.refresh_all = _refresh

    def _sleep(_value):
        service._poll_stop_event.set()

    monkeypatch.setattr(catalog_module.time, "sleep", _sleep)
    service._poll_stop_event.clear()
    service._poll_loop()
    assert called["count"] >= 1
