# CLAUDE.md — Agents

LangGraph-based AI agents microservice. Entry point: `main.py` (LangGraph API server) or `agents/main.py`. Runs on port 8001.

```bash
python -m agents.main
# or via LangGraph CLI
langgraph up
```

---

## Directory Layout

```
agents/
├── agents/                   # Agent graph implementations (one folder per agent)
│   ├── entries.py            # Registers all agent graphs with LangGraph runtime
│   └── <agent_name>/
│       ├── graph.py          # LangGraph StateGraph definition
│       ├── prompt.py         # System/user prompt templates
│       ├── tools.py          # Agent-specific tool bindings
│       └── state.py          # Custom state schema (if needed)
├── core/                     # Agent framework infrastructure
├── skills/                   # Reusable skill definitions
│   └── impl/                 # Domain-grouped skill implementations
├── api/                      # FastAPI endpoints exposed to backend
├── providers/                # LLM provider adapters
├── service_client/           # HTTP client back to backend service
├── tools/                    # Shared tool implementations
├── utils/                    # Shared utilities
├── tests/                    # pytest test suite
├── langgraph.json            # LangGraph graph registry
└── pyproject.toml
```

---

## Registered Agents (11)

Defined in `langgraph.json` and implemented in `agents/<name>/`:

| Agent | Purpose |
|-------|---------|
| `article_agent` | Summarise and analyse RSS articles |
| `content_generator_agent` | Generate written content from prompts |
| `data_agent` | Query and transform structured data |
| `image_agent` | Image analysis and description |
| `learning_planner_agent` | Build personalised learning plans |
| `rss_quality_agent` | Score RSS article quality |
| `shell_risk_agent` | Assess shell command risk level |
| `skill_caller_agent` | Dynamically invoke installed skills |
| `system_expert_agent` | General system/technical Q&A |
| `text_agent` | General-purpose text processing |
| `workflow_agent` | Multi-step workflow orchestration |
| `comprehensive_demo_agent` | Demo agent with full feature showcase |

---

## Adding a New Agent

1. Create `agents/<agent_name>/` with at minimum `graph.py`.
2. Define a `StateGraph` in `graph.py` and export the compiled graph.
3. Register in `langgraph.json`:
   ```json
   "<agent_name>": {"path": "./agents/<agent_name>/graph.py:graph"}
   ```
4. Add an entry in `agents/entries.py`.
5. Run `python update_langgraph_json.py` if the script manages graph config.

---

## Core Framework (`core/`)

| Module | Role |
|--------|------|
| `agent.py` | `BaseAgent` class — wraps LangGraph graph with common lifecycle |
| `master_agent.py` | Top-level router that dispatches to sub-agents |
| `router.py` | Intent classification → agent selection |
| `registry.py` | Agent type registry |
| `manager.py` | Agent instance lifecycle management |
| `session.py` | Per-conversation session state |
| `memory.py` | Conversation memory (window + summary) |
| `context.py` | Shared execution context passed through graph |
| `llm.py` / `llm_client.py` | LLM client factory; wraps LiteLLM |
| `react_loop.py` | ReAct reasoning loop implementation |
| `skill.py` / `skill_framework.py` | Skill invocation protocol |
| `skills_loader.py` | Loads skill definitions at startup |
| `collaboration.py` | Multi-agent collaboration primitives |
| `monitor.py` | Execution monitoring and logging |
| `protocol.py` | Shared message/event protocol types |
| `state.py` | Base graph state schema |
| `conversation_logger.py` | Structured conversation logging |

---

## Skills (`skills/`)

Skills are reusable callable units that agents can invoke by name. Defined as Python functions decorated with skill metadata.

`skills/impl/` — domain-grouped implementations:

| File | Domain |
|------|--------|
| `content_skills.py` | Content generation, summarisation |
| `data_skills.py` | Data query, transformation |
| `image_skills.py` | Image processing |
| `learning_skills.py` | Learning plan, progress tracking |
| `schedule_skills.py` | Scheduling, reminders |
| `text_skills.py` | Text processing, NLP |
| `workflow_skills.py` | Workflow execution |

`skills/registry.py` — skill registration and lookup.
`skills/example_weather_skill.py` — reference implementation.

### Adding a New Skill

1. Implement the skill function in the relevant `impl/` file (or create a new domain file).
2. Register it in `skills/registry.py`.
3. If the skill needs to be installable via the UI, ensure it is also registered in the backend's skill catalog.

---

## LLM Providers (`providers/`)

| Provider | File |
|----------|------|
| LiteLLM (default) | `litellm_provider.py` |
| Azure OpenAI | `azure_openai_provider.py` |
| OpenAI Codex | `openai_codex_provider.py` |

`registry.py` selects the provider based on `LLM_MODEL` env var. `base.py` defines the provider ABC.

---

## API Endpoints (`api/`)

| Module | Purpose |
|--------|---------|
| `endpoints.py` | Main agent invocation endpoints |
| `interrupt_endpoints.py` | Human-in-the-loop interrupt/resume |
| `service.py` | Shared request/response handling |
| `main.py` | FastAPI app factory for agents service |

---

## Tools (`tools/`)

Shared tool implementations usable by multiple agents:

| File | Tools |
|------|-------|
| `base.py` | `BaseTool` ABC |
| `filesystem.py` | File read/write/list |
| `article_search.py` | RSS article search against backend |

---

## Backend Communication

Agents call back to the backend via `service_client/backend_client.py`. Authentication uses the `SERVICE_JWT_TOKEN` header — same token the backend uses for outbound calls.

---

## LangGraph Configuration (`langgraph.json`)

Registers all 11 agent graphs with the LangGraph runtime. Update this file when adding or renaming agents. `update_langgraph_json.py` can regenerate it from the `agents/` directory structure.

---

## Testing

```bash
cd agents

# Unit tests
pytest tests/

# Integration test (requires backend running on port 8000)
pytest tests/ -m integration

# Full CI integration
cd .. && pytest tests/test_agent_center_ci_integration.py
```
