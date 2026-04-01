import asyncio
import time
from tools.article_search import ArticleSearchTool
from unittest.mock import patch, MagicMock

class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

async def run_benchmark():
    tool = ArticleSearchTool()
    
    # Mock the backend client to simulate network delay
    with patch('tools.article_search.BackendServiceClient') as MockClient:
        mock_instance = MockClient.return_value
        
        # Simulate 50ms latency for vector search
        async def mock_search_vectors(*args, **kwargs):
            await asyncio.sleep(0.05)
            from service_client.models import BackendVectorSearchResponse
            return BackendVectorSearchResponse(
                count=10,
                articles=[{"id": i, "content": f"Mock article {i}"} for i in range(10)],
                summary="Found 10 relevant articles."
            )
        
        mock_instance.search_vectors = mock_search_vectors
        mock_instance.close = AsyncMock()
        
        print("Starting Benchmark: ArticleSearchTool with Vector Search")
        start_time = time.time()
        iterations = 100
        for _ in range(iterations):
            await tool.execute(query="test query", limit=10)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / iterations
        print(f"Total time for {iterations} iterations: {total_time:.4f}s")
        print(f"Average time per execution: {avg_time*1000:.2f}ms")
        print("Benchmark completed.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
