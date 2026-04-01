import pytest
import os
import tempfile
import uuid
import base64
from app.services.chat_service import ChatService
from app.models.chat import ChatMessage
from sqlmodel import Session, create_engine, SQLModel
from unittest.mock import patch, MagicMock

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

class TestFileUpload:
    @pytest.fixture
    def chat_service(self):
        return ChatService()

    def test_extract_text_from_txt(self, chat_service):
        """测试从普通文本提取内容"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello, World!")
            temp_path = f.name
            
        try:
            text = chat_service._extract_text_from_file(temp_path, "text/plain")
            assert text == "Hello, World!"
        finally:
            os.remove(temp_path)

    def test_extract_text_from_csv(self, chat_service):
        """测试从CSV提取内容"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name\n1,Alice\n2,Bob")
            temp_path = f.name
            
        try:
            text = chat_service._extract_text_from_file(temp_path, "text/csv")
            assert "Alice" in text
            assert "Bob" in text
        finally:
            os.remove(temp_path)
            
    def test_extract_text_file_not_found(self, chat_service):
        """测试文件不存在的情况"""
        text = chat_service._extract_text_from_file("/path/to/nonexistent/file.txt", "text/plain")
        assert text == "File not found."
