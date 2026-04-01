import unittest
import asyncio
from core.agent import AgentStatus
from agents.data_agent.graph import DataAgent
from agents.text_agent.graph import TextAgent

class TestAgents(unittest.TestCase):
    def setUp(self):
        self.data_agent = DataAgent(name="test_data_agent")
        self.text_agent = TextAgent(name="test_text_agent")

    def test_agent_initialization(self):
        self.assertEqual(self.data_agent.name, "test_data_agent")
        self.assertEqual(self.data_agent.status, AgentStatus.IDLE)
        self.assertTrue("DataCleaningSkill" in self.data_agent.skills)

    def test_data_agent_execution(self):
        task = {"type": "clean", "data": [{"a": 1}, {"a": 1}]}
        result = asyncio.run(self.data_agent.execute(task))
        
        # Expecting duplicates removed
        cleaned_data = result.get("cleaned_data")
        self.assertEqual(len(cleaned_data), 1)

    def test_text_agent_execution(self):
        task = {"type": "sentiment", "text": "I am very happy today"}
        result = asyncio.run(self.text_agent.execute(task))
        
        self.assertEqual(result.get("sentiment"), "positive")

if __name__ == "__main__":
    unittest.main()
