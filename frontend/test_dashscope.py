import asyncio
from litellm import acompletion
import os

async def main():
    try:
        response = await acompletion(
            model="openai/deepseek-r1",
            messages=[{"role": "user", "content": "hello"}],
            api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="sk-1fac9281c385455eb3362279a6164fc8"
        )
        print(response)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
