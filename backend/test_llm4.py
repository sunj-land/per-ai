import asyncio
from agents.core.llm import llm_service
import json
import re

async def test():
    prompt = "Return a JSON object with keys 'goal_type', 'deadline_date', 'daily_hours', 'current_level'."
    response = await llm_service.chat([{"role": "user", "content": prompt}], json_mode=False)
    print("Raw Response:", repr(response))
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r'(\{.*?\})', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response
    print("Parsed JSON String:", repr(json_str))
    data = json.loads(json_str)
    print("Final Data:", data)

asyncio.run(test())
