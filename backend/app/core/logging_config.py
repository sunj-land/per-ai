import contextvars
import errno
import json
import logging
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid

TRACE_LEVEL_NUM = 5
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")

TRACE_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


def _trace(self: logging.Logger, message: str, *args: Any, **kwargs: Any) -> None:
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self._log(TRACE_LEVEL_NUM, message, args, **kwargs)


if not hasattr(logging.Logger, "trace"):
    setattr(logging.Logger, "trace", _trace)


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        token = TRACE_ID_CONTEXT.set(trace_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            TRACE_ID_CONTEXT.reset(token)


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = TRACE_ID_CONTEXT.get("-")
        record.class_name = record.name
        return True


class DynamicLogLevelFilter(logging.Filter):
    _level_map = {
        "TRACE": TRACE_LEVEL_NUM,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    def filter(self, record: logging.LogRecord) -> bool:
        configured = os.getenv("LOG_LEVEL", "INFO").upper()
        threshold = self._level_map.get(configured, logging.INFO)
        return record.levelno >= threshold


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(UTC).isoformat()
        payload = {
            "timestamp": timestamp,
            "level": record.levelname,
            "traceId": getattr(record, "trace_id", "-"),
            "thread": record.threadName,
            "className": getattr(record, "class_name", record.name),
            "message": record.getMessage(),
            "exception": None,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class DualRotatingDailyFileHandler(logging.Handler):
    def __init__(self, base_dir: Path, filename: str, max_bytes: int, retention_days: int) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.filename = filename
        self.max_bytes = max_bytes
        self.retention_days = retention_days
        self.current_date = ""
        self.current_path: Path | None = None
        self.stream = None
        self.degraded = False
        self.createLock()
        self._open_stream()

    def _resolve_log_path(self) -> Path:
        day_dir = datetime.now().strftime("%Y-%m-%d")
        return self.base_dir / day_dir / self.filename

    def _open_stream(self) -> None:
        target = self._resolve_log_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        self._cleanup_expired_dirs()
        if self.stream:
            self.stream.close()
        file_descriptor = os.open(target, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        os.chmod(target, 0o600)
        self.stream = os.fdopen(file_descriptor, "a", encoding="utf-8", buffering=1)
        self.current_path = target
        self.current_date = target.parent.name

    def _cleanup_expired_dirs(self) -> None:
        if not self.base_dir.exists():
            return
        threshold = datetime.now().date() - timedelta(days=self.retention_days)
        for child in self.base_dir.iterdir():
            if not child.is_dir():
                continue
            try:
                dir_date = datetime.strptime(child.name, "%Y-%m-%d").date()
            except ValueError:
                continue
            if dir_date < threshold:
                shutil.rmtree(child, ignore_errors=True)

    def _rotate_size(self) -> None:
        if not self.current_path or not self.current_path.exists():
            return
        if self.stream:
            self.stream.close()
        max_index = 0
        for sibling in self.current_path.parent.glob(f"{self.filename}.*"):
            suffix = sibling.name.rsplit(".", maxsplit=1)[-1]
            if suffix.isdigit():
                max_index = max(max_index, int(suffix))
        for index in range(max_index, 0, -1):
            src = self.current_path.parent / f"{self.filename}.{index}"
            dst = self.current_path.parent / f"{self.filename}.{index + 1}"
            if src.exists():
                src.rename(dst)
        rotated = self.current_path.parent / f"{self.filename}.1"
        self.current_path.rename(rotated)
        self._open_stream()

    def _ensure_stream(self) -> None:
        target = self._resolve_log_path()
        date_changed = self.current_date != target.parent.name
        if date_changed or self.stream is None or self.current_path != target:
            self._open_stream()
            return
        if self.current_path and self.current_path.exists():
            current_size = self.current_path.stat().st_size
            if current_size >= self.max_bytes:
                self._rotate_size()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self.acquire()
            try:
                self._ensure_stream()
                if self.stream is None:
                    return
                self.stream.write(f"{message}\n")
                self.stream.flush()
                self.degraded = False
            finally:
                self.release()
        except OSError as exc:
            if exc.errno in {errno.ENOSPC, errno.EDQUOT}:
                if not self.degraded:
                    self.degraded = True
                    logging.getLogger(__name__).error(
                        "日志写盘失败，触发降级输出: %s",
                        str(exc),
                    )
                try:
                    print(message, flush=True)
                except Exception:
                    pass
            else:
                raise
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        self.acquire()
        try:
            if self.stream:
                self.stream.close()
                self.stream = None
        finally:
            self.release()
        super().close()


def _is_container_environment() -> bool:
    return Path("/.dockerenv").exists() or bool(os.getenv("KUBERNETES_SERVICE_HOST"))


def configure_logging(log_dir: str | Path | None = None) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.filters.clear()
    root.setLevel(TRACE_LEVEL_NUM)

    base_dir = Path(log_dir) if log_dir else Path(__file__).resolve().parents[2] / "logs"
    base_dir.mkdir(parents=True, exist_ok=True)

    formatter = JsonFormatter()
    trace_filter = TraceIdFilter()
    level_filter = DynamicLogLevelFilter()

    file_kwargs = {
        "base_dir": base_dir,
        "max_bytes": 50 * 1024 * 1024,
        "retention_days": 30,
    }

    application_handler = DualRotatingDailyFileHandler(filename="application.log", **file_kwargs)
    application_handler.setLevel(TRACE_LEVEL_NUM)
    application_handler.setFormatter(formatter)
    application_handler.addFilter(trace_filter)
    application_handler.addFilter(level_filter)

    error_handler = DualRotatingDailyFileHandler(filename="error.log", **file_kwargs)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(trace_filter)
    error_handler.addFilter(level_filter)

    access_handler = DualRotatingDailyFileHandler(filename="access.log", **file_kwargs)
    access_handler.setLevel(TRACE_LEVEL_NUM)
    access_handler.setFormatter(formatter)
    access_handler.addFilter(trace_filter)
    access_handler.addFilter(level_filter)

    root.addHandler(application_handler)
    root.addHandler(error_handler)

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.setLevel(TRACE_LEVEL_NUM)
    access_logger.addHandler(access_handler)
    access_logger.propagate = False

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.setLevel(TRACE_LEVEL_NUM)

    if _is_container_environment():
        console_handler = logging.StreamHandler()
        console_handler.setLevel(TRACE_LEVEL_NUM)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(trace_filter)
        console_handler.addFilter(level_filter)
        root.addHandler(console_handler)
        access_logger.addHandler(console_handler)
        uvicorn_error_logger.addHandler(console_handler)
