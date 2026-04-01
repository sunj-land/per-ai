# Plan: LangGraph & LLM Integration and Refactoring

## 1. Skill Migration (Priority High)
**Objective**: Move `agents/skills/` to `skills/` at the project root to decouple skills from the agent framework.
**Steps**:
1.  Create a migration script `scripts/migrate-skills.sh`.
    -   **Backup**: Copy `agents/skills` to `agents/skills.bak`.
    -   **Move**: Move `agents/skills` to `skills/`.
    -   **Init**: Create `skills/__init__.py`.
    -   **Refactor**: Use `sed` to replace imports in all `.py` files:
        -   `from agents.skills` -> `from skills`
        -   `import agents.skills` -> `import skills`
    -   **Rollback**: Implement a `--rollback` flag to reverse changes.
2.  Execute `scripts/migrate-skills.sh` to perform the migration.
3.  Verify imports in `agents/instances/` and `agents/core/` are updated.

## 2. LangGraph Configuration Automation
**Objective**: Automatically generate `langgraph.json` configurations for all agents.
**Steps**:
1.  Create directory `agents/entries/` with `__init__.py`.
2.  Create script `scripts/generate_langgraph_config.py`.
    -   **Scan**: Recursively find `*_agent.py` in `agents/instances/`.
    -   **Parse**: Extract agent class name and `DEPENDENCIES` (if present) via AST.
    -   **Generate Wrappers**: For each agent, create `agents/entries/<name>_entry.py`:
        ```python
        from agents.instances.<name>_agent import <AgentClass>
        agent = <AgentClass>()
        graph = agent.workflow
        ```
    -   **Update Config**: Load `agents/langgraph.json`, update `graphs` key with `"name": "agents.entries.<name>_entry:graph"`, and save with deterministic formatting (sorted keys).
3.  Run the script to generate the initial configuration.

## 3. Dev Script Update
**Objective**: Enhance `scripts/start-dev.sh` to support `langgraph-cli` debugging.
**Steps**:
1.  Modify `scripts/start-dev.sh`:
    -   Add function `check_langgraph_config()` to validate JSON syntax of `agents/langgraph.json`.
    -   Add command option (e.g., `debug-cli`) to start `langgraph dev`:
        -   Flags: `--host 0.0.0.0`, `--port 8000`, `--config agents/langgraph.json`, `--watch` (hot reload).
        -   Environment: Load `.env` if exists.
    -   Add error handling to capture exit codes and log output.

## 4. LLM Client & Nodes
**Objective**: Implement unified LLM client and standard processing nodes.
**Steps**:
1.  **Core Client**:
    -   Create `.env.example` with keys (`OPENAI_API_KEY`, etc.).
    -   Create `core/llm_client.py`: Singleton class wrapping `litellm`.
    -   Expose `chat_completion`, `embedding`, `moderation`.
2.  **LLM Nodes**:
    -   Create `nodes/` directory.
    -   Implement `nodes/llm_text_generate.py`: Text generation node.
    -   Implement `nodes/llm_text_classify.py`: Classification node.
    -   Implement `nodes/llm_text_summarize.py`: Summarization node.
    -   **Features**: Support config via env vars or runtime args (model, temp, max_tokens, retries).
3.  **Testing**:
    -   Create `tests/nodes/test_llm_nodes.py`.
    -   Test cases: Normal success, retry logic, timeout, token limit, invalid response.
4.  **Evaluation**:
    -   Create `docs/llm_node_evaluation.md` template.
    -   (Optional) Run a script to populate basic metrics if possible, or leave as a report template for the user.

## Verification
-   Run `scripts/migrate-skills.sh` and check file structure.
-   Run `scripts/generate_langgraph_config.py` and inspect `agents/langgraph.json` and `agents/entries/`.
-   Run `pytest tests/nodes/` to verify LLM nodes.
-   Check `scripts/start-dev.sh` syntax.
