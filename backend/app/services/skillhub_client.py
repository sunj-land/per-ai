import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class SkillHubClient:
    def __init__(self):
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backend_dir = os.path.dirname(os.path.dirname(app_dir))
        self.project_root = os.path.dirname(backend_dir)
        self.skills_dir = os.path.join(self.project_root, "skills")
        self.registry_url = os.getenv("SKILLHUB_REGISTRY_URL", "").strip()
        self.local_index_path = os.getenv(
            "SKILLHUB_LOCAL_INDEX",
            os.path.join(self.skills_dir, "skillhub-index.json"),
        )

    async def search(
        self,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        version: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        records = []
        remote_error: Optional[str] = None

        if self.registry_url:
            try:
                records = await self._search_remote(name=name, tags=tags, version=version)
            except Exception as exc:
                remote_error = str(exc)
                logger.warning("SkillHub remote search failed, fallback to local index: %s", exc)

        if not records:
            records = self._search_local(name=name, tags=tags, version=version)
            if remote_error:
                for item in records:
                    item["fallback_reason"] = remote_error

        return records

    async def get_skill_package(self, name: str, version: Optional[str] = None) -> Dict[str, Any]:
        records = await self.search(name=name, version=version)
        exact = [item for item in records if item.get("name") == name]
        if not exact:
            raise ValueError(f"Skill {name} not found in registry/local index")

        selected = self._pick_version(exact, version)
        return selected

    async def _search_remote(
        self,
        name: Optional[str],
        tags: Optional[List[str]],
        version: Optional[str],
    ) -> List[Dict[str, Any]]:
        query_params: Dict[str, Any] = {}
        if name:
            query_params["name"] = name
        if tags:
            query_params["tags"] = ",".join(tags)
        if version:
            query_params["version"] = version

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(self.registry_url, params=query_params)
            resp.raise_for_status()
            payload = resp.json()

        if isinstance(payload, dict):
            data = payload.get("data", payload.get("items", []))
        elif isinstance(payload, list):
            data = payload
        else:
            data = []

        if not isinstance(data, list):
            return []

        return [self._normalize_record(item, source="registry") for item in data if isinstance(item, dict)]

    def _search_local(
        self,
        name: Optional[str],
        tags: Optional[List[str]],
        version: Optional[str],
    ) -> List[Dict[str, Any]]:
        data = self._load_local_index()
        result: List[Dict[str, Any]] = []
        tag_set = {tag.lower() for tag in (tags or []) if tag}

        for item in data:
            record = self._normalize_record(item, source="local")
            if name and name.lower() not in record["name"].lower():
                continue
            if version and record.get("version") != version:
                continue
            if tag_set:
                item_tags = {tag.lower() for tag in record.get("tags", [])}
                if not item_tags.intersection(tag_set):
                    continue
            result.append(record)
        return result

    def _load_local_index(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.local_index_path):
            try:
                with open(self.local_index_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    payload = payload.get("skills", [])
                if isinstance(payload, list):
                    return [item for item in payload if isinstance(item, dict)]
            except Exception as exc:
                logger.warning("Failed to load local skillhub index %s: %s", self.local_index_path, exc)

        generated: List[Dict[str, Any]] = []
        if not os.path.exists(self.skills_dir):
            return generated

        for entry in os.scandir(self.skills_dir):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            manifest_path = os.path.join(entry.path, "skill.json")
            readme_path = os.path.join(entry.path, "SKILL.md")
            item: Dict[str, Any] = {
                "name": entry.name,
                "version": "0.1.0",
                "tags": [],
                "author": "unknown",
                "description": "",
                "dependencies": [],
                "download_url": "",
            }
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    if isinstance(manifest, dict):
                        item.update(manifest)
                except Exception as exc:
                    logger.warning("Invalid manifest %s: %s", manifest_path, exc)
            elif os.path.exists(readme_path):
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        item["description"] = f.read(300)
                except Exception:
                    item["description"] = ""
            generated.append(item)

        return generated

    def _normalize_record(self, item: Dict[str, Any], source: str) -> Dict[str, Any]:
        return {
            "name": str(item.get("name", "")).strip(),
            "version": str(item.get("version", "0.1.0")).strip() or "0.1.0",
            "tags": item.get("tags", []) or [],
            "author": item.get("author") or "unknown",
            "description": item.get("description") or "",
            "dependencies": item.get("dependencies", []) or [],
            "download_url": item.get("download_url") or item.get("source_url") or "",
            "source_type": source,
            "raw": item,
        }

    def _pick_version(self, records: List[Dict[str, Any]], version: Optional[str]) -> Dict[str, Any]:
        if version:
            for item in records:
                if item.get("version") == version:
                    return item
            raise ValueError(f"Version {version} not found")
        return sorted(records, key=lambda x: self._version_tuple(x.get("version", "0.0.0")), reverse=True)[0]

    def _version_tuple(self, value: str):
        parts = []
        for part in str(value).split("."):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])


skillhub_client = SkillHubClient()
