import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.core.llm import llm_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS = [
    {
        "id": "local-ollama",
        "model": "ollama/qwen3-vl:8b",
        "api_key": "",
        "base_url": "http://localhost:11434"
    },
    {
        "id": "deepseek-reasoner",
        "model": "deepseek-reasoner", # litellm might map this or use openai/deepseek-reasoner
        "api_key": "sk-ac636b2b4e4f4b7aa76e6269b9e2bfb7",
        "base_url": "https://api.deepseek.com"
    },
    {
        "id": "minimax-api",
        "model": "abab6.5-chat",
        "api_key": "sk-api--IFCAz7IoF1jb2GCLcpFC2CeMD0DR4a2df6QNNDB55_Zf9Wd8fR9CG7JJN46AnPf5s0xOpSTgyAlIJjJqaqUY5gU5FEEouLk1TbFR7ZzqlB6lPtvmi4YBks",
        "base_url": "https://api.minimax.chat/v1"
    }
]

async def test_model(config):
    logger.info(f"Testing model: {config['id']} ({config['model']})")
    messages = [{"role": "user", "content": "Hello, simply say 'ok'."}]
    
    try:
        # We need to specify provider prefix for litellm if not obvious
        # For deepseek, it is openai compatible usually, but let's see.
        # litellm supports "deepseek/..." or "openai/..."
        
        model_name = config['model']
        if config['id'] == "deepseek-reasoner":
            # DeepSeek via OpenAI compatible endpoint
            # litellm needs "openai/deepseek-reasoner" if using openai client under hood with base_url
            model_name = "openai/deepseek-reasoner"
        elif config['id'] == "minimax-api":
            model_name = "openai/abab6.5-chat"
        
        response = await llm_service.chat(
            messages=messages,
            model=model_name,
            api_key=config['api_key'],
            base_url=config['base_url']
        )
        logger.info(f"SUCCESS: {config['id']} response: {response}")
        return True
    except Exception as e:
        logger.error(f"FAILED: {config['id']} error: {e}")
        return False

async def main():
    results = {}
    for config in MODELS:
        success = await test_model(config)
        results[config['id']] = success
    
    print("\nConnectivity Test Results:")
    for mid, status in results.items():
        print(f"{mid}: {'PASS' if status else 'FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())
