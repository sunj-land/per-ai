import json
import os
import re
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import logging

try:
    import yaml
except Exception:
    yaml = None

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:
    FileSystemEventHandler = object
    Observer = None


class DuplicateIdConflictError(Exception):
    def __init__(self, conflicts: List[Dict[str, Any]]):
        self.conflicts = conflicts
        super().__init__("duplicate id conflicts detected")


class FileParseError(Exception):
    def __init__(self, errors: List[Dict[str, str]]):
        self.errors = errors
        super().__init__("file parse failed")


class DataPathNotFoundError(Exception):
    def __init__(self, data_type: str, path: str):
        self.data_type = data_type
        self.path = path
        super().__init__(f"{data_type} data path not found: {path}")


class ReadWriteLock:
    def __init__(self) -> None:
        self._readers = 0
        self._writer = False
        self._condition = threading.Condition()

    @contextmanager
    def read_lock(self):
        with self._condition:
            while self._writer:
                self._condition.wait()
            self._readers += 1
        try:
            yield
        finally:
            with self._condition:
                self._readers -= 1
                if self._readers == 0:
                    self._condition.notify_all()

    @contextmanager
    def write_lock(self):
        with self._condition:
            while self._writer or self._readers > 0:
                self._condition.wait()
            self._writer = True
        try:
            yield
        finally:
            with self._condition:
                self._writer = False
                self._condition.notify_all()


class _CatalogWatchHandler(FileSystemEventHandler):
    def __init__(self, service: "AgentCenterCatalogService"):
        self.service = service
        super().__init__()

    def on_any_event(self, _event):
        self.service.refresh_all()


class AgentCenterCatalogService:
    _instance: Optional["AgentCenterCatalogService"] = None
    _allowed_extensions = {
        ".json",
        ".yaml",
        ".yml",
        ".js",
        ".cjs",
        ".mjs",
        ".ts",
        ".py",
        ".md",
    }
    _ignore_dirs = {"__pycache__", ".git", ".idea", ".vscode", "node_modules", ".tmp"}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._lock = ReadWriteLock()
        self._cache: Dict[str, List[Dict[str, Any]]] = {"agents": [], "skills": []}
        self._parse_errors: Dict[str, List[Dict[str, str]]] = {"agents": [], "skills": []}
        self._snapshot: Dict[str, Tuple[str, ...]] = {"agents": tuple(), "skills": tuple()}
        self._observer = None
        self._poll_thread = None
        self._poll_stop_event = threading.Event()
        self._started = False
        self._paths = self._resolve_paths()
        self._logger = self._build_error_logger()
        self._refresh_guard = threading.Lock()

    def _build_error_logger(self) -> logging.Logger:
        logger = logging.getLogger("agent_center_error_logger")
        if logger.handlers:
            return logger
        project_root = Path(__file__).resolve().parents[3]
        logs_dir = project_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            filename=str(logs_dir / "agent-center-error.log"),
            when="D",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)
        logger.propagate = False
        return logger

    def _resolve_paths(self) -> Dict[str, str]:
        project_root = Path(__file__).resolve().parents[3]
        default_skill_path = str(project_root / "agents" / "skills")
        default_agent_path = str(project_root / "agents" / "agents")
        return {
            "skills": os.getenv("SKILL_DATA_PATH", default_skill_path),
            "agents": os.getenv("AGENT_DATA_PATH", default_agent_path),
        }

    def initialize(self) -> None:
        with self._lock.write_lock():
            if self._started:
                return
            self._paths = self._resolve_paths()
            self._reload_locked("agents")
            self._reload_locked("skills")
            self._start_watchers_locked()
            self._started = True

    def shutdown(self) -> None:
        with self._lock.write_lock():
            if self._observer is not None:
                self._observer.stop()
                self._observer.join(timeout=2)
                self._observer = None
            if self._poll_thread is not None:
                self._poll_stop_event.set()
                self._poll_thread.join(timeout=2)
                self._poll_thread = None
                self._poll_stop_event = threading.Event()
            self._started = False

    def refresh_all(self) -> None:
        with self._refresh_guard:
            with self._lock.write_lock():
                self._paths = self._resolve_paths()
                self._reload_locked("agents")
                self._reload_locked("skills")

    def refresh(self, data_type: str) -> None:
        with self._refresh_guard:
            with self._lock.write_lock():
                self._paths = self._resolve_paths()
                self._reload_locked(data_type)

    def log_internal_error(self, message: str, exc: Exception) -> None:
        self._logger.error(message, exc_info=exc)

    def get_items(
        self, data_type: str, page: Optional[int] = None, size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        self.initialize()
        with self._lock.read_lock():
            errors = list(self._parse_errors.get(data_type, []))
            items = list(self._cache.get(data_type, []))
        if errors:
            raise FileParseError(errors)
        if page is None or size is None:
            return items
        start = max(page - 1, 0) * size
        end = start + size
        return items[start:end]

    def _reload_locked(self, data_type: str) -> None:
        root_path = self._paths[data_type]
        if not os.path.exists(root_path):
            self._cache[data_type] = []
            self._parse_errors[data_type] = [
                {"file": root_path, "error": "data path not found"}
            ]
            self._snapshot[data_type] = tuple()
            raise DataPathNotFoundError(data_type, root_path)
        files = self._scan_files(root_path)
        parsed_items: List[Dict[str, Any]] = []
        parse_errors: List[Dict[str, str]] = []
        id_files_map: Dict[str, List[str]] = {}
        for file_path in files:
            try:
                item = self._build_item(data_type=data_type, root_path=root_path, file_path=file_path)
                parsed_items.append(item)
                id_files_map.setdefault(item["id"], []).append(file_path)
            except FileParseError as exc:
                parse_errors.extend(exc.errors)
            except Exception as exc:
                parse_errors.append({"file": file_path, "error": str(exc)})
        conflicts = []
        for item_id, related_files in id_files_map.items():
            if len(related_files) > 1:
                conflicts.append({"id": item_id, "files": related_files})
        if conflicts:
            self._parse_errors[data_type] = []
            self._cache[data_type] = []
            raise DuplicateIdConflictError(conflicts)
        if parse_errors:
            self._parse_errors[data_type] = parse_errors
            self._cache[data_type] = []
            raise FileParseError(parse_errors)
        parsed_items.sort(key=lambda item: item["name"])
        self._cache[data_type] = parsed_items
        self._parse_errors[data_type] = []
        self._snapshot[data_type] = tuple(
            sorted(
                f"{path}:{os.path.getmtime(path)}:{os.path.getsize(path)}" for path in files
            )
        )

    def _scan_files(self, root_path: str) -> List[str]:
        files: List[str] = []
        for current_root, dir_names, file_names in os.walk(root_path):
            dir_names[:] = [
                name
                for name in dir_names
                if name not in self._ignore_dirs and not name.startswith(".")
            ]
            for file_name in file_names:
                if file_name.startswith("."):
                    continue
                ext = os.path.splitext(file_name)[1].lower()
                if ext not in self._allowed_extensions:
                    continue
                files.append(os.path.join(current_root, file_name))
        return files

    def _load_structured_data(self, file_path: str) -> Dict[str, Any]:
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                return payload if isinstance(payload, dict) else {}
            if ext in {".yaml", ".yml"}:
                if yaml is None:
                    raise ValueError("yaml parser unavailable, install PyYAML")
                with open(file_path, "r", encoding="utf-8") as f:
                    payload = yaml.safe_load(f)
                return payload if isinstance(payload, dict) else {}
            return {}
        except Exception as exc:
            raise FileParseError([{"file": file_path, "error": str(exc)}]) from exc

    def _extract_markdown_name_desc(self, file_path: str) -> Tuple[str, str]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            raise FileParseError([{"file": file_path, "error": str(exc)}]) from exc
        lines = [line.strip() for line in content.splitlines()]
        title = ""
        description = ""
        for line in lines:
            if not title and line.startswith("#"):
                title = line.lstrip("#").strip()
                continue
            if line:
                description = line
                break
        return title, description

    def _extract_enabled(self, payload: Dict[str, Any]) -> bool:
        if "enabled" in payload:
            return bool(payload["enabled"])
        status = str(payload.get("status", "active")).lower()
        return status not in {"inactive", "disabled", "false"}

    def _sanitize_name(self, raw: str) -> str:
        name = (raw or "").strip()
        return name or "unknown"

    def _build_item(self, data_type: str, root_path: str, file_path: str) -> Dict[str, Any]:
        ext = os.path.splitext(file_path)[1].lower()
        relative_path = os.path.relpath(file_path, root_path).replace("\\", "/")
        file_stat = os.stat(file_path)
        created_at = datetime.fromtimestamp(file_stat.st_ctime).isoformat()
        updated_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        payload: Dict[str, Any] = {}
        markdown_title = ""
        markdown_description = ""
        if ext in {".json", ".yaml", ".yml"}:
            payload = self._load_structured_data(file_path)
        if ext == ".md":
            markdown_title, markdown_description = self._extract_markdown_name_desc(file_path)
        raw_name = (
            payload.get("name")
            or markdown_title
            or Path(file_path).stem
        )
        raw_description = (
            payload.get("description")
            or markdown_description
            or f"{data_type} file from {relative_path}"
        )
        item_id = payload.get("id")
        if not item_id:
            stable_key = f"{data_type}:{relative_path}"
            item_id = stable_key
        version = str(payload.get("version", "0.1.0"))
        enabled = self._extract_enabled(payload)
        item = {
            "id": str(item_id),
            "name": self._sanitize_name(str(raw_name)),
            "description": str(raw_description),
            "version": version,
            "enabled": enabled,
            "createdAt": created_at,
            "updatedAt": updated_at,
            "sourcePath": file_path,
        }
        if data_type == "agents":
            item["type"] = str(payload.get("type", "standard"))
            item["status"] = "active" if enabled else "inactive"
        if data_type == "skills":
            tags = payload.get("tags", [])
            item["tags"] = tags if isinstance(tags, list) else []
            item["install_status"] = str(payload.get("install_status", "installed"))
        return item

    def _start_watchers_locked(self) -> None:
        if Observer is not None and FileSystemEventHandler is not None:
            observer = Observer()
            handler = _CatalogWatchHandler(self)
            for path in self._paths.values():
                if os.path.exists(path):
                    observer.schedule(handler, path, recursive=True)
            observer.daemon = True
            observer.start()
            self._observer = observer
            return
        self._poll_stop_event.clear()
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()
        self._poll_thread = thread

    def _poll_loop(self) -> None:
        while not self._poll_stop_event.is_set():
            try:
                changed = False
                with self._lock.read_lock():
                    current_paths = dict(self._paths)
                    old_snapshot = dict(self._snapshot)
                for data_type, path in current_paths.items():
                    if not os.path.exists(path):
                        new_snapshot = tuple()
                    else:
                        files = self._scan_files(path)
                        new_snapshot = tuple(
                            sorted(
                                f"{f}:{os.path.getmtime(f)}:{os.path.getsize(f)}"
                                for f in files
                            )
                        )
                    if new_snapshot != old_snapshot.get(data_type, tuple()):
                        changed = True
                        break
                if changed:
                    self.refresh_all()
            except Exception as exc:
                self._logger.error("agent-center poll watcher failed", exc_info=exc)
            time.sleep(1.5)


agent_center_catalog_service = AgentCenterCatalogService()
