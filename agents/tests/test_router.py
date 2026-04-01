import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.router import AgentRouter, RouteResult


def make_router():
    llm = MagicMock()
    return AgentRouter(llm=llm, model_name="test-model")


def test_route_result_is_dataclass():
    r = RouteResult(target_agent="article_query_agent", source="agent_name", purpose=None, confidence=None)
    assert r.target_agent == "article_query_agent"
    assert r.source == "agent_name"


def test_resolve_explicit_agent_name():
    router = make_router()
    result = asyncio.run(router.resolve("any query", {"agent_name": "text_agent"}))
    assert result.target_agent == "text_agent"
    assert result.source == "agent_name"


def test_resolve_explicit_purpose():
    router = make_router()
    result = asyncio.run(router.resolve("any query", {"purpose": "text_summarize"}))
    assert result.target_agent == "text_agent"
    assert result.source == "purpose"
    assert result.purpose == "text_summarize"


def test_resolve_keyword_infer():
    router = make_router()
    result = asyncio.run(router.resolve("帮我总结一下这段内容", {}))
    assert result.target_agent == "text_agent"
    assert result.source == "purpose_inferred"


def test_resolve_falls_through_to_none():
    router = make_router()
    mock_resp = MagicMock()
    mock_resp.finish_reason = "stop"
    mock_resp.content = '{"purpose": "general", "confidence": 0.5}'
    router._llm.chat_with_retry = AsyncMock(return_value=mock_resp)

    result = asyncio.run(router.resolve("hello world", {}))
    assert result.target_agent is None
    assert result.source is None


def test_resolve_master_agent_alias_is_not_routed():
    router = make_router()
    result = asyncio.run(router.resolve("any query", {"agent_name": "master_agent"}))
    assert result.target_agent is None


def test_resolve_llm_infer_high_confidence():
    router = make_router()
    mock_resp = MagicMock()
    mock_resp.finish_reason = "stop"
    mock_resp.content = '{"purpose": "data_analysis", "confidence": 0.95}'
    router._llm.chat_with_retry = AsyncMock(return_value=mock_resp)

    result = asyncio.run(router.resolve("what insights can you provide", {}))
    assert result.target_agent == "data_agent"
    assert result.source == "purpose_inferred_llm"
    assert result.confidence == pytest.approx(0.95)
