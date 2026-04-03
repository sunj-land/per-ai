"""
本文件定义 Agents 模块对外的统一服务接口 (LLM & Nodes)
维护者 SunJie 创建于 2026-03-16
"""

from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import logging
import json
import importlib.util
import inspect
from core.master_agent import MasterAgent
from core.agent import Agent
from core.llm import llm_service

# Configure logger
logger = logging.getLogger("AgentsService")

router = APIRouter(tags=["Unified LLM Service"])

# Security
API_KEY = os.getenv("AGENT_API_KEY", "default-insecure-key")
SERVICE_TOKEN = os.getenv("SERVICE_JWT_TOKEN", "change-me")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key in {API_KEY, SERVICE_TOKEN}:
        return api_key
    # For now, allow internal calls or verify if strict auth is needed
    if not api_key:
         if API_KEY == "default-insecure-key":
             return "default"
    raise HTTPException(status_code=403, detail="Invalid API Key")

# --- Pydantic Models ---

class ChatCompletionRequest(BaseModel):
    messages: List[Dict[str, Any]]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    stream: bool = False
    extra_params: Dict[str, Any] = {}

class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: Optional[str] = None
    extra_params: Dict[str, Any] = {}

class TextGenerateRequest(BaseModel):
    input_text: str
    system_prompt: Optional[str] = "You are a helpful assistant."
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    retries: int = 3

class TextClassifyRequest(BaseModel):
    input_text: str
    categories: List[str]
    system_prompt: Optional[str] = None
    model: Optional[str] = None

class TextSummarizeRequest(BaseModel):
    input_text: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None

class AgentInfo(BaseModel):
    name: str
    description: str
    type: str = "standard"
    status: str = "active"
    config: Dict[str, Any] = {}

# --- Helper Functions ---

def _load_agent_from_file(file_path: str) -> Optional[Agent]:
    """Dynamically load agent instance from python file"""
    try:
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find Agent subclass
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, Agent) and obj != Agent:
                try:
                    # Try to instantiate with default args
                    return obj()
                except Exception as e:
                    logger.warning(f"Could not instantiate {name} from {file_path}: {e}")
                    return None
    except Exception as e:
        logger.error(f"Error loading agent from {file_path}: {e}")
    return None

def _get_agent_instance(agent_name: str) -> Optional[Agent]:
    if agent_name == "MasterAgent":
        try:
            return MasterAgent()
        except Exception as e:
            logger.error(f"Failed to initialize MasterAgent: {e}")
            return None

    # Scan instances
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    instances_dir = os.path.join(base_dir, "instances")

    if os.path.exists(instances_dir):
        for entry in os.scandir(instances_dir):
            if entry.is_file() and entry.name.endswith(".py") and not entry.name.startswith("__"):
                try:
                    agent = _load_agent_from_file(entry.path)
                    if agent and agent.name == agent_name:
                        return agent
                except Exception:
                    continue
    return None

# --- Endpoints ---

@router.get("/models", summary="List enabled models")
async def list_models(token: str = Depends(verify_api_key)):
    """
    Get all enabled AI models.
    """
    # Provide a static list or fetch from config
    return [
        {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "enabled": True},
        {"id": "ollama/qwen3-vl:8b", "name": "Qwen3 VL (8B)", "enabled": True},
        {"id": "ollama/llama3", "name": "Llama 3", "enabled": True},
        {"id": "gpt-4o", "name": "GPT-4o", "enabled": True},
    ]

@router.post("/chat/completions", summary="Unified Chat Completion API")
async def chat_completion(request: ChatCompletionRequest, token: str = Depends(verify_api_key)):
    """
    Unified Chat Completion API using litellm.
    Supports streaming and standard response.
    """
    try:
        response = await llm_service.chat(
            messages=request.messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream,
            **request.extra_params
        )

        if request.stream:
            async def stream_generator():
                async for chunk in response:
                    # Chunk is already a JSON string from llm_service.chat
                    yield chunk + "\n"

            return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

        # Standard response
        return {"content": response}

    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_name}/graph", summary="Get Agent Graph Mermaid")
async def get_agent_graph(agent_name: str, token: str = Depends(verify_api_key)):
    try:
        agent_instance = _get_agent_instance(agent_name)
        if not agent_instance:
             raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

        # Case 1: Has LangGraph workflow
        if hasattr(agent_instance, "workflow") and hasattr(agent_instance.workflow, "get_graph"):
            try:
                graph = agent_instance.workflow.get_graph()
                mermaid = graph.draw_mermaid()
                if mermaid.startswith("---"):
                    parts = mermaid.split("---", 2)
                    if len(parts) >= 3:
                        mermaid = parts[2].strip()
                return {"mermaid": mermaid}
            except Exception as e:
                logger.error(f"Failed to draw mermaid graph for {agent_name}: {e}")
                return {"mermaid": f"graph TD;\n    Error[Failed to generate graph: {str(e)}];"}

        # Case 2: Standard Agent with Skills -> Generate Star Graph
        if hasattr(agent_instance, "skills") and agent_instance.skills:
            mermaid = ["graph TD"]
            safe_agent_name = agent_name.replace(" ", "_")
            mermaid.append(f"    {safe_agent_name}[{agent_name}]")

            for skill_name in agent_instance.skills:
                safe_skill = skill_name.replace(" ", "_")
                mermaid.append(f"    {safe_agent_name} --> {safe_skill}(({skill_name}))")

            return {"mermaid": "\n".join(mermaid)}

        # Case 3: Simple Agent
        return {"mermaid": f"graph TD;\n    Start --> {agent_name} --> End;"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/list", response_model=List[AgentInfo], summary="List available agents")
async def list_agents(token: str = Depends(verify_api_key)):
    agents_list = []

    # 1. MasterAgent
    agents_list.append(AgentInfo(
        name="MasterAgent",
        description="主智能体，负责意图识别、文章检索和通用对话的任务分发与处理。",
        type="workflow",
        status="active",
        config={"model": "llama3"}
    ))

    # 2. Scan instances
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    instances_dir = os.path.join(base_dir, "instances")

    if os.path.exists(instances_dir):
        for entry in os.scandir(instances_dir):
            if entry.is_file() and entry.name.endswith(".py") and not entry.name.startswith("__"):
                try:
                    module_name = os.path.splitext(entry.name)[0]
                    spec = importlib.util.spec_from_file_location(module_name, entry.path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if hasattr(attr, "name") and hasattr(attr, "description") and hasattr(attr, "config") and not isinstance(attr, type):
                             agents_list.append(AgentInfo(
                                 name=attr.name,
                                 description=attr.description,
                                 type="standard",
                                 status="active",
                                 config=attr.config
                             ))
                             break
                except Exception as e:
                    logger.error(f"Failed to load agent from {entry.path}: {e}")

    return agents_list
