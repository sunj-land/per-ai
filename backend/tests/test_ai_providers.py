import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from app.core.ai_providers import AIProviderFactory, AgentsServiceProxy
from app.service_client.models import ChatCompletionRequestContract

@pytest.fixture
def mock_sync_client():
    with patch("app.core.ai_providers.AgentsServiceSyncClient") as mock_client:
        yield mock_client.return_value

@pytest.fixture
def mock_async_client():
    with patch("app.core.ai_providers.AgentsServiceAsyncClient") as mock_client:
        yield mock_client.return_value

def test_proxy_layer_format_messages():
    proxy = AgentsServiceProxy()
    messages = [
        {"role": "user", "content": "Hello", "images": ["http://example.com/image.png"]}
    ]
    formatted = proxy._format_messages(messages)
    
    assert len(formatted) == 1
    assert formatted[0]["role"] == "user"
    assert isinstance(formatted[0]["content"], list)
    assert formatted[0]["content"][0]["type"] == "text"
    assert formatted[0]["content"][0]["text"] == "Hello"
    assert formatted[0]["content"][1]["type"] == "image_url"
    assert formatted[0]["content"][1]["image_url"]["url"] == "http://example.com/image.png"

def test_proxy_layer_build_request():
    proxy = AgentsServiceProxy()
    messages = [{"role": "user", "content": "Hello"}]
    model_config = {"model_name": "test-model", "temperature": 0.5, "max_tokens": 100}
    
    req = proxy._build_request(messages, model_config)
    assert isinstance(req, ChatCompletionRequestContract)
    assert req.model == "test-model"
    assert req.temperature == 0.5
    assert req.max_tokens == 100
    assert req.stream is True

def test_generate_stream_success(mock_sync_client):
    proxy = AgentsServiceProxy()
    proxy.sync_client = mock_sync_client
    
    def mock_stream(*args, **kwargs):
        yield '{"content": "Hello"}'
        yield '{"content": " World"}'
        
    mock_sync_client.chat_completion_stream.side_effect = mock_stream
    
    generator = proxy.generate_stream([{"role": "user", "content": "Hi"}], {"model_name": "m1"})
    
    results = list(generator)
    assert len(results) == 2
    assert results[0] == '{"content": "Hello"}'
    assert results[1] == '{"content": " World"}'

def test_generate_stream_error(mock_sync_client):
    proxy = AgentsServiceProxy()
    proxy.sync_client = mock_sync_client
    
    def mock_stream(*args, **kwargs):
        yield "Error: Service Unavailable"
        
    mock_sync_client.chat_completion_stream.side_effect = mock_stream
    
    generator = proxy.generate_stream([{"role": "user", "content": "Hi"}], {"model_name": "m1"})
    
    results = list(generator)
    assert len(results) == 1
    error_json = json.loads(results[0])
    assert "error" in error_json
    assert error_json["error"] == "Error: Service Unavailable"

@pytest.mark.asyncio
async def test_async_generate_stream_success(mock_async_client):
    proxy = AgentsServiceProxy()
    proxy.async_client = mock_async_client
    
    async def mock_async_stream(*args, **kwargs):
        yield '{"content": "Hello"}'
        yield '{"content": " Async"}'
        
    mock_async_client.chat_completion_stream = mock_async_stream
    
    generator = proxy.async_generate_stream([{"role": "user", "content": "Hi"}], {"model_name": "m1"})
    
    results = []
    async for chunk in generator:
        results.append(chunk)
        
    assert len(results) == 2
    assert results[0] == '{"content": "Hello"}'
    assert results[1] == '{"content": " Async"}'

def test_factory_returns_proxy():
    provider = AIProviderFactory.get_provider("any_type")
    assert isinstance(provider, AgentsServiceProxy)
