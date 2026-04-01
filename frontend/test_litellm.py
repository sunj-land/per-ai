import asyncio
from litellm import acompletion
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    try:
        response = await acompletion(
            model="openai/deepseek-reasoner",
            messages=[{"role": "user", "content": "hello"}],
            api_base="https://api.deepseek.com",
            api_key=os.getenv("DASHSCOPE_API_KEY") # wait, DashScope URL is different, deepseek is different.
            # The config in model-config.json has key sk-ac636b2b4e4f4b7aa76e6269b9e2bfb7
        )
        print(response)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
