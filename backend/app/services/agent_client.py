import httpx
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

AGENT_API_URL = os.getenv("AGENT_API_URL", "http://localhost:8001/agents")
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "default-insecure-key")

class AgentClient:
    async def execute_task(self, agent_name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task on a specific agent via HTTP.
        """
        url = f"{AGENT_API_URL}/{agent_name}/task"
        headers = {
            "X-API-Key": AGENT_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {"task": task}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=65.0)
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "completed":
                    return data.get("result", {})
                else:
                    raise Exception(f"Agent execution failed: {data}")
            except httpx.HTTPStatusError as e:
                # 尝试解析 Agent 返回的详细错误信息
                try:
                    error_data = e.response.json()
                    detail = error_data.get("detail", "")
                    if "大模型调用超时" in detail:
                        raise TimeoutError("大模型调用超时")
                except ValueError:
                    pass
                logger.error(f"Failed to call agent {agent_name} with status error: {e.response.text}")
                raise
            except httpx.TimeoutException as e:
                logger.error(f"Timeout calling agent {agent_name}: {e}")
                raise TimeoutError("大模型调用超时")
            except Exception as e:
                logger.error(f"Failed to call agent {agent_name}: {e}")
                raise

agent_client = AgentClient()
