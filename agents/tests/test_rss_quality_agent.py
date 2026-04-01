import asyncio
import unittest

from agents.rss_quality_agent.graph import RSSQualityAgent


class TestRSSQualityAgent(unittest.TestCase):
    def setUp(self):
        self.agent = RSSQualityAgent(name="test_rss_quality_agent")

    def test_agent_initialization(self):
        self.assertEqual(self.agent.name, "test_rss_quality_agent")
        self.assertIsNotNone(self.agent.workflow)

    def test_process_task_returns_backend_payload(self):
        async def _mock_execute(payload):
            return {
                "batchId": "batch-1",
                "summary": {
                    "total": len(payload.get("article_ids", [])),
                    "success": len(payload.get("article_ids", [])),
                    "failed": 0,
                    "averageScore": 88.6,
                },
                "results": [],
            }

        self.agent.scoring_tool.execute = _mock_execute
        result = asyncio.run(
            self.agent.process_task(
                {
                    "article_ids": [1, 2],
                    "concurrency": 2,
                }
            )
        )
        self.assertEqual(result["batchId"], "batch-1")
        self.assertEqual(result["summary"]["total"], 2)


if __name__ == "__main__":
    unittest.main()
