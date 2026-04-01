import atexit
import json
import logging
import os
import queue
import re
import tarfile
import tempfile
import threading
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SensitiveDataMasker:
    """
    敏感数据脱敏器
    用于检测和隐藏日志中的敏感信息（如手机号、身份证号、邮箱）。
    """
    def __init__(self) -> None:
        # 定义脱敏规则和对应的处理函数
        self.patterns = [
            (re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)"), self._mask_phone),
            (re.compile(r"(?<!\w)(\d{17}[\dXx]|\d{15})(?!\w)"), self._mask_id_card),
            (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), self._mask_email),
        ]

    def _mask_phone(self, value: str) -> str:
        """隐藏手机号中间四位"""
        return f"{value[:3]}****{value[-4:]}"

    def _mask_id_card(self, value: str) -> str:
        """隐藏身份证号中间部分"""
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}********{value[-4:]}"

    def _mask_email(self, value: str) -> str:
        """隐藏邮箱用户名部分"""
        name, domain = value.split("@", maxsplit=1)
        if len(name) <= 2:
            masked = "*" * len(name)
        else:
            masked = f"{name[0]}***{name[-1]}"
        return f"{masked}@{domain}"

    def mask(self, data: Any) -> Any:
        """
        递归地对数据进行脱敏处理。
        支持字典、列表和字符串类型。
        
        Args:
            data (Any): 需要脱敏的数据。
            
        Returns:
            Any: 脱敏后的数据。
        """
        if isinstance(data, dict):
            return {key: self.mask(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self.mask(item) for item in data]
        if isinstance(data, str):
            masked = data
            for pattern, handler in self.patterns:
                masked = pattern.sub(lambda match: handler(match.group(0)), masked)
            return masked
        return data


@dataclass
class UploadResult:
    """
    日志上传结果数据类
    """
    uploaded_files: int      # 上传的文件数量
    uploaded_bytes: int      # 上传的字节数
    deleted_files: int       # 删除的文件数量
    request_status_code: int # 请求状态码
    response_body: str       # 响应体内容


class AsyncConversationLogger:
    """
    异步会话日志记录器
    使用队列和后台线程异步写入日志，避免阻塞主线程。
    支持日志分片、自动刷盘和敏感数据脱敏。
    """
    def __init__(
        self,
        base_dir: Path | None = None,
        queue_size: int = 1000,
        flush_interval_seconds: int = 5,
        ring_buffer_size: int = 2000,
    ) -> None:
        """
        初始化日志记录器。

        Args:
            base_dir (Path | None): 日志存储的基础目录。
            queue_size (int): 内存队列大小。
            flush_interval_seconds (int): 自动刷盘间隔时间（秒）。
            ring_buffer_size (int): 环形缓冲区大小（用于降级）。
        """
        self.base_dir = base_dir or Path(__file__).resolve().parents[1] / "logs" / "conversation"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.flush_interval_seconds = flush_interval_seconds
        self.masker = SensitiveDataMasker()
        self.buffer_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=queue_size)
        self.ring_buffer: deque[dict[str, Any]] = deque(maxlen=ring_buffer_size)
        self.stop_event = threading.Event()
        
        # 启动后台刷盘线程
        self.flush_thread = threading.Thread(target=self._flush_loop, daemon=True, name="conversation-log-flusher")
        self.flush_thread.start()
        
        # 注册程序退出时的清理函数
        atexit.register(self.shutdown)

    def log(self, payload: dict[str, Any]) -> None:
        """
        记录一条日志。
        会对日志进行脱敏并放入队列。

        Args:
            payload (dict[str, Any]): 日志内容。
        """
        try:
            sanitized = self.masker.mask(payload)
            self.buffer_queue.put_nowait(sanitized)
        except queue.Full:
            # 如果队列满了，放入环形缓冲区作为降级方案
            self.ring_buffer.append(sanitized)
        except Exception as exc:
            logger.error("会话日志入队失败: %s", exc)

    def _flush_loop(self) -> None:
        """
        后台刷盘循环。
        定期从队列中取出日志并写入磁盘。
        """
        local_batch: list[dict[str, Any]] = []
        while not self.stop_event.is_set():
            try:
                # 阻塞等待日志，超时时间为刷盘间隔
                item = self.buffer_queue.get(timeout=self.flush_interval_seconds)
                local_batch.append(item)
                # 尽可能多地取出队列中的日志
                self._drain_queue(local_batch)
            except queue.Empty:
                pass
            
            if local_batch:
                self._flush_batch(local_batch)
                local_batch.clear()

    def _drain_queue(self, batch: list[dict[str, Any]]) -> None:
        """
        从队列中取出所有立即可用的日志放入批次中。
        """
        while True:
            try:
                batch.append(self.buffer_queue.get_nowait())
            except queue.Empty:
                return

    def _resolve_target_file(self, item: dict[str, Any]) -> Path:
        """
        根据日志内容确定目标文件路径。
        按日期分目录，按 Session ID 分文件。
        """
        today_dir = self.base_dir / datetime.now().strftime("%Y-%m-%d")
        today_dir.mkdir(parents=True, exist_ok=True)
        session_id = item.get("sessionId", "unknown-session")
        target = today_dir / f"{session_id}.jsonl"
        
        # 确保文件权限安全 (600)
        if not target.exists():
            fd = os.open(target, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
            os.close(fd)
            os.chmod(target, 0o600)
        return target

    def _flush_batch(self, batch: list[dict[str, Any]]) -> None:
        """
        将一批日志写入磁盘。
        会先处理环形缓冲区中的积压日志。
        """
        try:
            grouped: dict[Path, list[dict[str, Any]]] = {}
            # 先处理积压的日志
            while self.ring_buffer:
                cached = self.ring_buffer.popleft()
                target = self._resolve_target_file(cached)
                grouped.setdefault(target, []).append(cached)
            
            # 再处理当前批次的日志
            for item in batch:
                target = self._resolve_target_file(item)
                grouped.setdefault(target, []).append(item)
            
            # 按文件批量写入
            for file_path, payloads in grouped.items():
                with open(file_path, "a", encoding="utf-8") as fp:
                    for payload in payloads:
                        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.error("会话日志刷盘失败，已降级到环形缓存: %s", exc)
            # 写入失败时回退到环形缓冲区
            for item in batch:
                self.ring_buffer.append(item)

    def shutdown(self) -> None:
        """
        关闭日志记录器。
        停止后台线程并强制刷新剩余日志。
        """
        if self.stop_event.is_set():
            return
        self.stop_event.set()
        self.flush_thread.join(timeout=3)
        pending: list[dict[str, Any]] = []
        self._drain_queue(pending)
        if pending:
            self._flush_batch(pending)

    def list_files_by_date_range(self, start_date: date, end_date: date) -> list[Path]:
        """
        列出指定日期范围内的所有日志文件。
        """
        results: list[Path] = []
        for child in sorted(self.base_dir.iterdir()):
            if not child.is_dir():
                continue
            try:
                day_value = datetime.strptime(child.name, "%Y-%m-%d").date()
            except ValueError:
                continue
            if start_date <= day_value <= end_date:
                results.extend(sorted(child.glob("*.jsonl")))
        return results

    def upload_logs(
        self,
        start_date: date,
        end_date: date,
        upload_url: str,
        delete_after_upload: bool,
        timeout_seconds: int = 30,
    ) -> UploadResult:
        """
        打包并上传指定日期范围内的日志文件。
        
        Args:
            start_date (date): 开始日期。
            end_date (date): 结束日期。
            upload_url (str): 上传目标 URL。
            delete_after_upload (bool): 上传成功后是否删除本地文件。
            timeout_seconds (int): 上传超时时间。
            
        Returns:
            UploadResult: 上传结果统计。
        """
        files = self.list_files_by_date_range(start_date, end_date)
        if not files:
            return UploadResult(0, 0, 0, 204, "no files")
            
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as temp_file:
            archive_path = Path(temp_file.name)
            
        try:
            # 创建 tar.gz 压缩包
            with tarfile.open(archive_path, mode="w:gz") as tar:
                for file_path in files:
                    arcname = file_path.relative_to(self.base_dir)
                    tar.add(file_path, arcname=str(arcname))
            
            archive_size = archive_path.stat().st_size
            
            # 上传文件
            with open(archive_path, "rb") as fp:
                response = httpx.post(
                    upload_url,
                    files={"file": ("agent-conversation-logs.tar.gz", fp, "application/gzip")},
                    data={
                        "startDate": start_date.isoformat(),
                        "endDate": end_date.isoformat(),
                        "fileCount": str(len(files)),
                    },
                    timeout=timeout_seconds,
                )
            
            deleted = 0
            # 上传成功后删除文件
            if response.is_success and delete_after_upload:
                for file_path in files:
                    file_path.unlink(missing_ok=True)
                    deleted += 1
                self._cleanup_empty_dirs()
                
            return UploadResult(
                uploaded_files=len(files),
                uploaded_bytes=archive_size,
                deleted_files=deleted,
                request_status_code=response.status_code,
                response_body=response.text[:2000],
            )
        finally:
            archive_path.unlink(missing_ok=True)

    def _cleanup_empty_dirs(self) -> None:
        """清理空目录"""
        for day_dir in self.base_dir.iterdir():
            if day_dir.is_dir() and not any(day_dir.iterdir()):
                day_dir.rmdir()


# 全局单例实例
conversation_logger = AsyncConversationLogger()
