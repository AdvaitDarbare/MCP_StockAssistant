"""Unit tests for the supervisor graph pure functions (T-2).

These tests cover the dependency-aware routing logic without requiring any
LLM calls or external services.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.agents.supervisor.state import AgentTask, ExecutionPlan  # noqa: E402
from apps.api.agents.supervisor.task_runtime import (  # noqa: E402
    canonical_agent,
    deps_satisfied,
    get_ready_tasks_for_agent,
    merge_queries,
)
from apps.api.agents.supervisor.graph import (  # noqa: E402
    RESEARCH_AGENTS,
    SYNTHESIS_AGENTS,
    _ready_agents_from_tier,
)


def _make_plan(*steps: AgentTask) -> ExecutionPlan:
    return ExecutionPlan(reasoning="test", steps=list(steps))


def _task(task_id: str, agent: str, depends_on: list[str] | None = None) -> AgentTask:
    return AgentTask(task_id=task_id, agent=agent, query=f"query for {agent}", depends_on=depends_on or [])


class CanonicalAgentTests(unittest.TestCase):
    def test_alias_resolution(self) -> None:
        self.assertEqual(canonical_agent("technicals"), "technical_analysis")
        self.assertEqual(canonical_agent("technicals_analysis"), "technical_analysis")
        self.assertEqual(canonical_agent("portfolio"), "advisor")

    def test_passthrough_for_known_agents(self) -> None:
        for agent in ("market_data", "fundamentals", "sentiment", "macro", "advisor"):
            self.assertEqual(canonical_agent(agent), agent)

    def test_empty_string(self) -> None:
        self.assertEqual(canonical_agent(""), "")

    def test_whitespace_stripped(self) -> None:
        self.assertEqual(canonical_agent("  market_data  "), "market_data")


class DepsSatisfiedTests(unittest.TestCase):
    def test_no_deps_always_satisfied(self) -> None:
        task = _task("t1", "market_data")
        self.assertTrue(deps_satisfied(task, {}))

    def test_dep_completed(self) -> None:
        task = _task("t2", "technical_analysis", depends_on=["t1"])
        self.assertTrue(deps_satisfied(task, {"t1": "completed"}))

    def test_dep_pending(self) -> None:
        task = _task("t2", "technical_analysis", depends_on=["t1"])
        self.assertFalse(deps_satisfied(task, {"t1": "pending"}))

    def test_dep_failed(self) -> None:
        task = _task("t2", "technical_analysis", depends_on=["t1"])
        self.assertFalse(deps_satisfied(task, {"t1": "failed"}))

    def test_multiple_deps_all_completed(self) -> None:
        task = _task("t3", "advisor", depends_on=["t1", "t2"])
        self.assertTrue(deps_satisfied(task, {"t1": "completed", "t2": "completed"}))

    def test_multiple_deps_one_pending(self) -> None:
        task = _task("t3", "advisor", depends_on=["t1", "t2"])
        self.assertFalse(deps_satisfied(task, {"t1": "completed", "t2": "pending"}))


class GetReadyTasksTests(unittest.TestCase):
    def test_returns_ready_tasks_for_agent(self) -> None:
        plan = _make_plan(
            _task("t1", "market_data"),
            _task("t2", "fundamentals"),
        )
        ready = get_ready_tasks_for_agent(
            plan=plan,
            task_status={},
            agent_names=["market_data"],
        )
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].task_id, "t1")

    def test_skips_completed_tasks(self) -> None:
        plan = _make_plan(_task("t1", "market_data"))
        ready = get_ready_tasks_for_agent(
            plan=plan,
            task_status={"t1": "completed"},
            agent_names=["market_data"],
        )
        self.assertEqual(ready, [])

    def test_skips_tasks_with_unmet_deps(self) -> None:
        plan = _make_plan(_task("t2", "technical_analysis", depends_on=["t1"]))
        ready = get_ready_tasks_for_agent(
            plan=plan,
            task_status={"t1": "pending"},
            agent_names=["technical_analysis"],
        )
        self.assertEqual(ready, [])

    def test_alias_resolution_in_agent_names(self) -> None:
        plan = _make_plan(_task("t1", "technical_analysis"))
        ready = get_ready_tasks_for_agent(
            plan=plan,
            task_status={},
            agent_names=["technicals"],  # alias
        )
        self.assertEqual(len(ready), 1)


class MergeQueriesTests(unittest.TestCase):
    def test_single_query(self) -> None:
        tasks = [_task("t1", "market_data")]
        tasks[0].query = "What is AAPL price?"
        self.assertEqual(merge_queries(tasks), "What is AAPL price?")

    def test_multiple_queries(self) -> None:
        t1 = _task("t1", "market_data")
        t1.query = "AAPL price"
        t2 = _task("t2", "market_data")
        t2.query = "MSFT price"
        result = merge_queries([t1, t2], prefix="Execute")
        self.assertIn("AAPL price", result)
        self.assertIn("MSFT price", result)
        self.assertIn("Execute", result)

    def test_empty_tasks(self) -> None:
        self.assertEqual(merge_queries([]), "")


class TierSetsTests(unittest.TestCase):
    """Verify the tier membership is correct."""

    def test_research_agents(self) -> None:
        self.assertIn("market_data", RESEARCH_AGENTS)
        self.assertIn("fundamentals", RESEARCH_AGENTS)
        self.assertIn("sentiment", RESEARCH_AGENTS)
        self.assertIn("macro", RESEARCH_AGENTS)
        self.assertNotIn("advisor", RESEARCH_AGENTS)
        self.assertNotIn("technical_analysis", RESEARCH_AGENTS)

    def test_synthesis_agents(self) -> None:
        self.assertIn("advisor", SYNTHESIS_AGENTS)
        self.assertIn("technical_analysis", SYNTHESIS_AGENTS)
        self.assertNotIn("market_data", SYNTHESIS_AGENTS)

    def test_tiers_are_disjoint(self) -> None:
        self.assertEqual(RESEARCH_AGENTS & SYNTHESIS_AGENTS, set())


class ReadyAgentsFromTierTests(unittest.TestCase):
    def _state(self, plan: ExecutionPlan, task_status: dict) -> dict:
        return {"plan": plan, "task_status": task_status}

    def test_returns_research_agents_with_no_deps(self) -> None:
        plan = _make_plan(
            _task("t1", "market_data"),
            _task("t2", "fundamentals"),
        )
        state = self._state(plan, {})
        ready = _ready_agents_from_tier(state, RESEARCH_AGENTS)
        self.assertIn("market_data", ready)
        self.assertIn("fundamentals", ready)

    def test_excludes_synthesis_agents_from_research_tier(self) -> None:
        plan = _make_plan(_task("t1", "advisor"))
        state = self._state(plan, {})
        ready = _ready_agents_from_tier(state, RESEARCH_AGENTS)
        self.assertEqual(ready, [])

    def test_excludes_completed_tasks(self) -> None:
        plan = _make_plan(_task("t1", "market_data"))
        state = self._state(plan, {"t1": "completed"})
        ready = _ready_agents_from_tier(state, RESEARCH_AGENTS)
        self.assertEqual(ready, [])


if __name__ == "__main__":
    unittest.main()
