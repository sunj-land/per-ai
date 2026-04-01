import json
import tempfile
import time
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from core.conversation_logger import AsyncConversationLogger, SensitiveDataMasker


def test_sensitive_data_masker_should_hide_phone_id_and_email():
    masker = SensitiveDataMasker()
    payload = {
        "phone": "13800138000",
        "id_card": "11010519491231002X",
        "email": "abc@example.com",
        "nested": {"text": "联系我:13800138000, abc@example.com"},
    }

    masked = masker.mask(payload)
    assert masked["phone"] == "138****8000"
    assert masked["id_card"].startswith("1101")
    assert masked["email"] == "a***c@example.com"
    assert "****" in masked["nested"]["text"]


def test_conversation_logger_should_write_jsonl_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = AsyncConversationLogger(base_dir=Path(tmp_dir), flush_interval_seconds=1)
        logger.log(
            {
                "timestamp": "2026-01-01T00:00:00+00:00",
                "sessionId": "session-a",
                "userInput": "hello",
            }
        )
        time.sleep(1.3)
        logger.shutdown()

        day_dir = Path(tmp_dir) / date.today().strftime("%Y-%m-%d")
        target = day_dir / "session-a.jsonl"
        assert target.exists()
        with open(target, "r", encoding="utf-8") as fp:
            lines = [line.strip() for line in fp if line.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])["userInput"] == "hello"


def test_conversation_logger_should_use_ring_buffer_when_queue_is_full():
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = AsyncConversationLogger(
            base_dir=Path(tmp_dir),
            queue_size=1,
            flush_interval_seconds=5,
            ring_buffer_size=5,
        )
        logger.log({"sessionId": "s1", "userInput": "a"})
        logger.log({"sessionId": "s2", "userInput": "b"})
        assert len(logger.ring_buffer) >= 1
        logger.shutdown()


def test_upload_logs_should_support_delete_after_upload():
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        today_dir = base_dir / date.today().strftime("%Y-%m-%d")
        today_dir.mkdir(parents=True, exist_ok=True)
        sample_file = today_dir / "sample-session.jsonl"
        sample_file.write_text('{"sessionId":"x"}\n', encoding="utf-8")

        logger = AsyncConversationLogger(base_dir=base_dir, flush_interval_seconds=1)
        with patch("core.conversation_logger.httpx.post") as mock_post:
            response = Mock()
            response.is_success = True
            response.status_code = 200
            response.text = "ok"
            mock_post.return_value = response

            result = logger.upload_logs(
                start_date=date.today(),
                end_date=date.today(),
                upload_url="http://example.com/upload",
                delete_after_upload=True,
                timeout_seconds=3,
            )
            assert result.uploaded_files == 1
            assert result.deleted_files == 1
            assert not sample_file.exists()
        logger.shutdown()
