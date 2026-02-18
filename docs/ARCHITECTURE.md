# Architecture

## Runtime Topology

1. Next.js app (`apps/web`) handles UI and rewrites `/api/py/*` to FastAPI.
2. FastAPI gateway (`apps/api/gateway`) exposes chat, reports, market, and Schwab endpoints.
3. Chat uses LangGraph supervisor flow:
   - `planner` -> `router` -> specialist nodes -> `aggregator`
4. Report generation uses `report_orchestrator` + `report_engine` + quality gate.
5. Tracing/observability writes runs to MLflow (`mlruns`).

## Supervisor V2 Execution Model

- Planner emits normalized task graph:
  - Stable `task_id` per step
  - Canonical agent names
  - Explicit `depends_on` task edges
- Router is dependency-aware:
  - Only dispatches tasks whose dependencies are completed
  - Can fan out to multiple ready agents in parallel
  - Marks tasks as `skipped` when upstream dependencies fail
- Task lifecycle status is tracked in shared state:
  - `pending`, `completed`, `failed`, `skipped`
- Aggregator returns the advisor/specialist synthesis as the final response.

## Multi-Tenant Memory Isolation

- Memory writes include:
  - `tenant_id`
  - `user_id`
  - `conversation_id`
- Retrieval is scoped in order:
  1. conversation + tenant + user
  2. tenant + user fallback (if no conversation matches)
- No unscoped global retrieval is used.

## Trace and UI Contract

- Chat SSE emits structured events:
  - `decision` (task graph and dependencies)
  - `agent_start` / `agent_end`
  - `task_update`
  - `tool_start` / `tool_end`
  - `trace_run` / `trace_link` (MLflow)
- Frontend trace panel renders this stream as a per-run timeline.

## Diagram Source

- Canonical runtime diagram lives in `/Users/advaitdarbare/Documents/ai-stock-assistant/README.md`.

## Agent Set

- `market_data`
- `fundamentals`
- `technical_analysis`
- `sentiment`
- `macro`
- `advisor`

## Data/Infra Dependencies

- Postgres (app state + report inputs)
- Redis (cache)
- Qdrant (memory/vector context)
- External providers (Schwab/Alpaca/news/sentiment/FRED)
