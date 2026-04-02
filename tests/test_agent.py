import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'agents'))

from core.master_agent import MasterAgent
from core.protocol import AgentRequest

async def main():
    agent = MasterAgent()
    req = AgentRequest(
        query="rss订阅源中分数较高的文章有哪些",
        session_id="test_session"
    )
    res = await agent.process_request(req)
    print("FINAL RESPONSE:", res)

if __name__ == "__main__":
    asyncio.run(main())
