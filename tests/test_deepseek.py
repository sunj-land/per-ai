import asyncio
from litellm import acompletion
import os

async def main():
    try:
        response = await acompletion(
            model="deepseek/deepseek-chat",
            messages=[{"role": "user", "content": "hello"}],
            api_key="sk-ac636b2b4e4f4b7aa76e6269b9e2bfb7"
        )
        print(response)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
