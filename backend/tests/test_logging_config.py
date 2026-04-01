import errno
import logging
import os
import tempfile
import time
import unittest
from pathlib import Path

from app.core.logging_config import (
    DynamicLogLevelFilter,
    DualRotatingDailyFileHandler,
    JsonFormatter,
)


class FakeBrokenStream:
    def write(self, *_args, **_kwargs):
        raise OSError(errno.ENOSPC, "No space left on device")

    def flush(self):
        return None

    def close(self):
        return None


class LoggingConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_handler(self, filename: str = "application.log", max_bytes: int = 256):
        handler = DualRotatingDailyFileHandler(
            base_dir=self.log_root,
            filename=filename,
            max_bytes=max_bytes,
            retention_days=30,
        )
        handler.setFormatter(JsonFormatter())
        return handler

    def test_should_split_by_size_and_date_directory(self):
        logger = logging.getLogger("test.size.rotation")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        handler = self._create_handler(max_bytes=180)
        logger.addHandler(handler)

        for _ in range(30):
            logger.info("x" * 80)

        day_dir = self.log_root / time.strftime("%Y-%m-%d")
        self.assertTrue(day_dir.exists())
        self.assertTrue((day_dir / "application.log").exists())
        rotated_files = list(day_dir.glob("application.log.*"))
        self.assertTrue(len(rotated_files) >= 1)
        handler.close()

    def test_should_create_log_file_with_600_permission(self):
        handler = self._create_handler(filename="error.log")
        target = self.log_root / time.strftime("%Y-%m-%d") / "error.log"
        mode = os.stat(target).st_mode & 0o777
        self.assertEqual(mode, 0o600)
        handler.close()

    def test_should_degrade_when_disk_is_full(self):
        handler = self._create_handler(filename="access.log")
        if handler.stream:
            handler.stream.close()
        handler._ensure_stream = lambda: None
        handler.stream = FakeBrokenStream()
        record = logging.LogRecord(
            name="test.degrade",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="degrade message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)
        self.assertTrue(handler.degraded)
        handler.close()

    def test_should_apply_dynamic_log_level_without_restart(self):
        filter_instance = DynamicLogLevelFilter()
        old_level = os.getenv("LOG_LEVEL")

        os.environ["LOG_LEVEL"] = "ERROR"
        info_record = logging.LogRecord("test", logging.INFO, __file__, 1, "info", (), None)
        self.assertFalse(filter_instance.filter(info_record))

        os.environ["LOG_LEVEL"] = "TRACE"
        trace_record = logging.LogRecord("test", 5, __file__, 1, "trace", (), None)
        self.assertTrue(filter_instance.filter(trace_record))

        if old_level is None:
            os.environ.pop("LOG_LEVEL", None)
        else:
            os.environ["LOG_LEVEL"] = old_level


if __name__ == "__main__":
    unittest.main()
