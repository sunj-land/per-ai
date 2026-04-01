# MasterAgent Refactor Design

**Date:** 2026-04-01  
**Scope:** `agents/core/master_agent.py`, `agents/core/react_loop.py`, `agents/core/router.py`  
**Goal:** Make logic clearer and more transparent; explicitly define the agent's call looping and exit mechanisms.

---

## Problem Statement

The current `MasterAgent` has three intertwined issues:

1. **Opaque loop exits** — `run_agent_loop` returns a plain 4-tuple; the three exit conditions (clean finish, max iterations, LLM error) are distinguishable only by inspecting the returned string.
2. **Routing logic leak** — the 5-level priority routing chain is split across `AgentRouter.resolve_route_target` (sync) and inlined async logic in `process_request`, including a raw `_PURPOSE_AGENT_MAP` import.
3. **Monolithic `process_request`** — a ~90-line method mixing session management, routing, loop execution, and persistence with no clear phase boundaries.

---

## Design

### A3 — `LoopResult` dataclass with typed exit reason

**File:** `agents/core/react_loop.py`

Add two new types:

```python
class LoopExitReason(str, Enum):
    DONE           = "done"           # LLM returned no tool calls → clean finish
    MAX_ITERATIONS = "max_iterations" # hit the iteration cap
    LLM_ERROR      = "llm_error"      # LLM returned finish_reason == "error"

@dataclass
class LoopResult:
    content:         str
    tools_used:      list[str]
    messages:        list[dict]
    reasoning_trace: list[str]
    exit_reason:     LoopExitReason
    iterations:      int
```

`run_agent_loop` returns `LoopResult` instead of the 4-tuple. Each of the three exit paths sets `exit_reason` explicitly before returning. No exceptions are raised for abnormal exits — all outcomes are visible in one return value.

---

### B3 — Routing strategy chain

**File:** `agents/core/router.py`

Add a result type and replace the split sync/async routing with a unified async resolver:

```python
@dataclass
class RouteResult:
    target_agent: Optional[str]
    source:       Optional[str]   # "agent_name" | "purpose" | "purpose_inferred" | "purpose_inferred_llm" | None
    purpose:      Optional[str]
    confidence:   Optional[float]
```

`AgentRouter.__init__` registers strategies in priority order:

```python
self._strategies: list[RoutingStrategy] = [
    self._strategy_explicit_agent,    # parameters["agent_name"]
    self._strategy_explicit_purpose,  # parameters["purpose"]
    self._strategy_keyword_infer,     # keyword match (sync, wrapped)
    self._strategy_llm_infer,         # LLM inference (async, confidence threshold)
]
```

New public method:

```python
async def resolve(self, query: str, parameters: Optional[dict]) -> RouteResult:
    for strategy in self._strategies:
        result = await strategy(query, parameters)
        if result and result.target_agent:
            return result
    return RouteResult(None, None, None, None)
```

Each strategy is a private async method. The raw `_PURPOSE_AGENT_MAP` import in `process_request` is removed — routing is fully encapsulated in `AgentRouter`. Each strategy is independently testable.

**Existing methods preserved** (for any external callers):
- `resolve_route_target` — kept but delegated to `_strategy_explicit_agent` + `_strategy_explicit_purpose` + `_strategy_keyword_infer`
- `infer_purpose_from_query` — kept, used by `_strategy_keyword_infer`
- `infer_purpose_with_llm` — kept, used by `_strategy_llm_infer`

---

### C1 — `process_request` decomposition

**File:** `agents/core/master_agent.py`

`process_request` becomes a ~15-line orchestrator:

```python
async def process_request(self, request: AgentRequest) -> AgentResponse:
    start_time = time.time()
    try:
        session, messages = self._setup_session(request)
        route = await self._route_request(request)
        if route.target_agent:
            response = await self._delegate_to_agent(request, session, route, start_time)
            if response is not None:
                return response
        loop_result = await self._run_react_loop(request, messages)
        return self._persist_and_respond(request, session, loop_result, start_time)
    except Exception as e:
        logger.error("MasterAgent process failed: %s", e, exc_info=True)
        return AgentResponse(
            answer="An internal error occurred.",
            source_agent="system",
            latency_ms=(time.time() - start_time) * 1000,
            error=str(e),
        )
```

**Four private helpers:**

| Method | Signature | Responsibility |
|--------|-----------|---------------|
| `_setup_session` | `(request) -> tuple[Session, list[dict]]` | get/create session, add user message, build initial messages, inject reasoning prompt |
| `_route_request` | `async (request) -> RouteResult` | calls `self.router.resolve(request.query, request.parameters)` |
| `_run_react_loop` | `async (request, messages) -> LoopResult` | resolves effective model, calls `run_agent_loop`, returns `LoopResult` |
| `_persist_and_respond` | `(request, session, loop_result, start_time) -> AgentResponse` | appends new messages to session, saves, builds `AgentResponse` with `exit_reason` in metadata |

**`_delegate_to_agent` signature change:**  
Accepts `RouteResult` instead of 4 separate fields (`target_agent`, `route_source`, `resolved_purpose`, `resolved_confidence`).

**`_inject_reasoning_prompt`:**  
Stays as a static method; called inside `_setup_session` (side-effect is now visible at the right abstraction level).

---

## Data Flow (after refactor)

```
process_request(AgentRequest)
  │
  ├─ _setup_session()         → (Session, initial_messages)
  ├─ _route_request()         → RouteResult
  │    └─ router.resolve()
  │         ├─ _strategy_explicit_agent
  │         ├─ _strategy_explicit_purpose
  │         ├─ _strategy_keyword_infer
  │         └─ _strategy_llm_infer
  │
  ├─ [if routed] _delegate_to_agent(RouteResult)  → AgentResponse
  │
  ├─ [else] _run_react_loop() → LoopResult
  │    └─ run_agent_loop()
  │         ├─ iteration 1..N
  │         │    ├─ LLM call
  │         │    ├─ tool calls (if any)
  │         │    └─ exit check → LoopExitReason
  │         └─ returns LoopResult(exit_reason, iterations, ...)
  │
  └─ _persist_and_respond()   → AgentResponse
```

---

## Files Changed

| File | Change |
|------|--------|
| `agents/core/react_loop.py` | Add `LoopExitReason`, `LoopResult`; change return type of `run_agent_loop` |
| `agents/core/router.py` | Add `RouteResult`; add `resolve()` and 4 private strategy methods; preserve existing public methods |
| `agents/core/master_agent.py` | Extract `_setup_session`, `_route_request`, `_run_react_loop`, `_persist_and_respond`; update `_delegate_to_agent` signature; remove inline routing logic |

---

## Out of Scope

- Changes to `SessionManager`, `ContextBuilder`, `MemoryConsolidator`, or any sub-agent
- Adding new routing purposes or agents
- Streaming support
- Changes to `AgentRequest` / `AgentResponse` protocol fields (only `metadata` content in `AgentResponse` gains `exit_reason`)
