# CLAUDE.md

## Project Overview

Monorepo — full-stack AI platform for RSS management, intelligent agents, multi-channel messaging, and learning planning.

| Service | Tech | Port |
|---------|------|------|
| `backend/` | FastAPI + SQLModel (Python 3.12) | 8000 |
| `agents/` | LangGraph + LiteLLM (Python 3.12) | 8001 |
| `frontend/` | Vue 3 + Vite + Arco Design (Node/pnpm) | 3000 |

Each sub-project has its own `CLAUDE.md` with detailed architecture notes.

---

## Quick Start

```bash
# Install
pip install -r backend/requirements.txt
pip install -e agents/
cd frontend && pnpm install

# Start all (or individually — see sub-project CLAUDE.md)
bash scripts/start-dev.sh
```

---

## Environment Variables

Copy `.env.example` → `.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key |
| `GEMINI_API_KEY` | — | Google Gemini key |
| `AZURE_ENDPOINT` | — | Azure OpenAI endpoint |
| `LLM_MODEL` | `gpt-4` | Default LLM model |
| `LLM_MAX_TOKENS` | `1024` | Max tokens per request |
| `LLM_TEMPERATURE` | `0.7` | LLM temperature |
| `AGENTS_BASE_URL` | `http://localhost:8001` | Agents service URL |
| `BACKEND_BASE_URL` | `http://localhost:8000` | Backend service URL |
| `LOG_LEVEL` | `INFO` | TRACE/DEBUG/INFO/WARN/ERROR |
| `SERVICE_JWT_TOKEN` | `change-me` | Inter-service auth token — **change in prod** |

---

## Inter-Service Communication

Services communicate via HTTP only — no shared Python imports across service boundaries.

| Direction | Client file |
|-----------|-------------|
| backend → agents | `backend/app/service_client/agents_async_client.py` |
| agents → backend | `agents/service_client/backend_client.py` |

Auth uses `SERVICE_JWT_TOKEN` header for inter-service calls.

---

## CI/CD

GitHub Actions (`.github/workflows/agent-center-integration.yml`):
1. Python 3.12 + Node 20 + pnpm 10
2. Install all deps
3. Start all three services, wait for health checks
4. Run `pytest tests/test_agent_center_ci_integration.py`

---

## Dev Proxy (Frontend)

Vite proxies in development:
- `/api` → `http://localhost:8000`
- `/agents-api` → `http://localhost:8001/api`

Production: `frontend/dist/` is served by the FastAPI backend at `/`.

---

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **perAll** (2843 symbols, 6827 relationships, 216 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/perAll/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/perAll/context` | Codebase overview, check index freshness |
| `gitnexus://repo/perAll/clusters` | All functional areas |
| `gitnexus://repo/perAll/processes` | All execution flows |
| `gitnexus://repo/perAll/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## CLI

- Re-index: `npx gitnexus analyze`
- Check freshness: `npx gitnexus status`
- Generate docs: `npx gitnexus wiki`

<!-- gitnexus:end -->
