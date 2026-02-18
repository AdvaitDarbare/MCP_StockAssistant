"""Runtime helpers for v2 dependency-aware task execution."""

from __future__ import annotations

from typing import Iterable

from apps.api.agents.supervisor.state import AgentTask, ExecutionPlan


AGENT_ALIASES = {
    "technicals": "technical_analysis",
    "technicals_analysis": "technical_analysis",
    "portfolio": "advisor",
}


def canonical_agent(agent: str) -> str:
    value = (agent or "").strip()
    return AGENT_ALIASES.get(value, value)


def deps_satisfied(task: AgentTask, task_status: dict[str, str]) -> bool:
    for dep in task.depends_on or []:
        if task_status.get(dep) != "completed":
            return False
    return True


def get_ready_tasks_for_agent(
    *,
    plan: ExecutionPlan | None,
    task_status: dict[str, str],
    agent_names: Iterable[str],
) -> list[AgentTask]:
    if not plan or not getattr(plan, "steps", None):
        return []
    aliases = {canonical_agent(name) for name in agent_names}
    ready: list[AgentTask] = []
    for step in plan.steps:
        step_agent = canonical_agent(step.agent)
        if step_agent not in aliases:
            continue
        if task_status.get(step.task_id, "pending") != "pending":
            continue
        if not deps_satisfied(step, task_status):
            continue
        ready.append(step)
    return ready


def merge_queries(tasks: list[AgentTask], prefix: str | None = None) -> str:
    if not tasks:
        return ""
    queries = [str(t.query or "").strip() for t in tasks if str(t.query or "").strip()]
    if not queries:
        return ""
    if len(queries) == 1:
        return queries[0]
    header = prefix or "Execute these requests together"
    return f"{header}:\n" + "\n".join(f"- {q}" for q in queries)
