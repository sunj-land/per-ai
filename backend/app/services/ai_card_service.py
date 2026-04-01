from typing import Dict, Any, Optional
from app.service_client.agents_async_client import AgentsServiceAsyncClient
from app.service_client.models import ChatCompletionRequestContract
import logging

logger = logging.getLogger(__name__)

class AICardService:
    def __init__(self):
        pass

    async def generate_card_code(self, prompt: str, model_config: Dict[str, Any]) -> str:
        """
        Generates Vue 3 component code for a card based on the user prompt.
        """
        system_prompt = """
You are an expert Vue 3 frontend developer specializing in Arco Design.
Your task is to generate a single-file Vue component (.vue) based on the user's description.

STRICT RULES:
1. Use <script setup> syntax.
2. Use Arco Design Vue components (e.g., <a-card>, <a-button>, <a-table>, <a-descriptions>).
3. The component MUST be self-contained. Do NOT import external local components.
4. Define props using `defineProps`. The component should be reusable.
5. Use Scoped CSS (<style scoped>).
6. Return ONLY the code, starting with <template> or <script>. Do NOT wrap in markdown code blocks (```vue ... ```).
7. If the user asks for charts, use 'echarts' and 'vue-echarts' (assume they are available globally or import them).
8. Ensure the root element is a `div` or `a-card`.

EXAMPLE STRUCTURE:
<script setup>
import { ref, computed } from 'vue';
const props = defineProps({
  title: { type: String, default: 'Card Title' },
  data: { type: Array, default: () => [] }
});
</script>

<template>
  <a-card :title="title">
    <!-- Content -->
  </a-card>
</template>

<style scoped>
/* Styles */
</style>
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a Vue 3 component for: {prompt}"}
        ]

        # 从 model_config 提取模型名称
        model_name = model_config.get("model_name") or "ollama/qwen2.5-coder:14b"
        
        request_contract = ChatCompletionRequestContract(
            messages=messages,
            model=model_name,
            stream=True,
            temperature=model_config.get("temperature", 0.2),
            max_tokens=4096
        )
        
        client = AgentsServiceAsyncClient()
        full_response = ""
        try:
            # Collect the stream
            generator = client.chat_completion_stream(request_contract)
            async for chunk in generator:
                import json
                try:
                    data = json.loads(chunk)
                    if "content" in data:
                        full_response += data["content"]
                except json.JSONDecodeError:
                    if not chunk.startswith("Error:"):
                        full_response += chunk
            
            # Clean up response if it contains markdown code blocks
            full_response = full_response.strip()
            if full_response.startswith("```vue"):
                full_response = full_response[6:]
            elif full_response.startswith("```"):
                full_response = full_response[3:]
            
            if full_response.endswith("```"):
                full_response = full_response[:-3]
                
            return full_response.strip()
        except Exception as e:
            logger.error(f"Error generating card code: {e}")
            raise e
