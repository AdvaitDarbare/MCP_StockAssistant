# V2 Agent Architecture Plan

## Objectives

1. True parallel specialist execution when tasks are independent.
2. Deterministic dependency execution for task graphs.
3. Multi-tenant memory isolation across users/conversations.
4. Organized, explainable outputs and live execution trace UX.

## Exact Upgrades

### 1) Planner Graph Normalization
- Add stable task IDs (`task_id`) to every planned step.
- Canonicalize agent aliases (`technicals` -> `technical_analysis`).
- Resolve `depends_on` references to task IDs.
- Initialize per-task lifecycle map in supervisor state.

### 2) Dependency-Aware Runtime Scheduler
- Add runtime helpers to compute ready tasks by agent.
- Route only dependency-satisfied tasks.
- Dispatch multiple ready agents in parallel fanout.
- Mark downstream tasks `skipped` when dependencies fail/skip.

### 3) Agent Node Contract
- Each specialist consumes all ready tasks for that agent in one node run.
- Merge sub-queries into a single agent prompt when appropriate.
- Return updated `task_status` for streaming and observability.

### 4) Multi-Tenant Memory Isolation
- Require memory metadata keys on write: `tenant_id`, `user_id`, `conversation_id`.
- Scope retrieval by conversation first, then tenant/user fallback.
- Remove unscoped global retrieval behavior.

### 5) Streaming and Trace UX
- Stream planner decision graph (task IDs + dependencies).
- Stream task lifecycle updates (`task_update`) in real time.
- Show per-run trace timeline in chat UI.
- Persist trace to MLflow and surface run link in trace panel.

### 6) Architecture Visibility
- Keep architecture visualization in repository docs (README diagram) as the single source of truth.

## Current Implementation Status

- Implemented: planner normalization, dependency scheduler, parallel fanout, task lifecycle tracking, memory scoping, task update SSE, dynamic architecture view, trace UX updates.
- Verified: backend compile, frontend lint, health endpoint, and chat SSE trace with task updates.

## Acceptance Checks

1. Multi-agent query shows simultaneous `agent_start` events for independent tasks.
2. Dependent tasks do not execute until parent task is completed.
3. Trace panel shows planner route, dependencies, and task status transitions.
4. Memory retrieval remains scoped to tenant/user/conversation boundaries.
5. Final output includes execution summary counts.
