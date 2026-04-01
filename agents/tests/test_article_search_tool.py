import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock
from tools.article_search import ArticleSearchTool
from service_client.models import BackendVectorSearchResponse

@pytest.fixture
def tool():
    return ArticleSearchTool()

@pytest.mark.asyncio
async def test_article_search_tool_with_query(tool):
    """
    Test article search tool with a query, triggering vector search.
    """
    mock_articles = [
        {
            "id": 1,
            "score": 0.9,
            "content": "This is a test article.",
            "metadata": {
                "title": "Test Title",
                "feed_id": 10,
                "published_at": "2023-01-01T12:00:00Z"
            }
        }
    ]

    mock_response = BackendVectorSearchResponse(
        count=1,
        articles=mock_articles,
        summary="Found 1 relevant articles."
    )

    with patch('tools.article_search.BackendServiceClient') as MockClient:
        mock_client_instance = MockClient.return_value
        mock_client_instance.search_vectors = AsyncMock(return_value=mock_response)
        mock_client_instance.close = AsyncMock()

        result_str = await tool.execute(query="test", limit=5)
        result = json.loads(result_str)

        assert result["count"] == 1
        assert len(result["articles"]) == 1
        assert result["articles"][0]["content"] == "This is a test article."
        mock_client_instance.search_vectors.assert_called_once()

@pytest.mark.asyncio
async def test_article_search_tool_without_query(tool):
    """
    Test article search tool without a query, triggering rss articles fetch.
    """
    mock_articles = [
        {
            "id": 2,
            "title": "Another Test",
            "content": "Regular fetch content.",
            "published_at": "2023-01-02T12:00:00Z"
        }
    ]

    with patch('tools.article_search.BackendServiceClient') as MockClient:
        mock_client_instance = MockClient.return_value
        mock_client_instance.get_articles = AsyncMock(return_value=mock_articles)
        mock_client_instance.close = AsyncMock()

        result_str = await tool.execute(limit=5)
        result = json.loads(result_str)

        assert result["count"] == 1
        assert len(result["articles"]) == 1
        assert result["articles"][0]["title"] == "Another Test"
        mock_client_instance.get_articles.assert_called_once_with(limit=5, feed_id=None, group_id=None)

class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)
