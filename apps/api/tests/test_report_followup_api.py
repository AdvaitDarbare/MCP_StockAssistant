from __future__ import annotations

import pathlib
import sys
import unittest
from unittest.mock import AsyncMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.report_orchestrator import orchestrate_report_followup  # noqa: E402


class ReportFollowupTests(unittest.IsolatedAsyncioTestCase):
    async def test_followup_uses_thread_context(self) -> None:
        thread = {
            "id": "thread-1",
            "owner_key": "user-1",
            "report_type": "morgan_dcf",
            "base_payload": {"ticker": "AAPL"},
            "effective_prompt": "prompt",
            "latest_report": {
                "report_type": "morgan_dcf",
                "title": "Morgan",
                "markdown": "# prior",
                "tool_plan": [{"tool": "x", "reason": "y"}],
                "sources_used": ["finviz"],
            },
        }

        with patch("apps.api.services.report_orchestrator.get_thread", new=AsyncMock(return_value=thread)), \
            patch("apps.api.services.report_orchestrator.append_thread_message", new=AsyncMock(return_value={})), \
            patch("apps.api.services.report_orchestrator.list_thread_messages", new=AsyncMock(return_value=[])), \
            patch("apps.api.services.report_orchestrator.update_thread_latest_report", new=AsyncMock(return_value=thread)), \
            patch("apps.api.services.report_orchestrator.log_report_run_to_mlflow") as mlflow_mock:
            mlflow_mock.return_value.enabled = False
            mlflow_mock.return_value.run_id = None
            mlflow_mock.return_value.error = None
            result = await orchestrate_report_followup(
                report_type="morgan_dcf",
                owner_key="user-1",
                thread_id="thread-1",
                question="yeah",
                refresh_data=False,
            )

        self.assertEqual(result["thread_id"], "thread-1")
        self.assertEqual(result["follow_up_question"], "yeah")
        self.assertTrue(result["follow_up_supported"])

    async def test_followup_refresh_data_reruns_builder(self) -> None:
        thread = {
            "id": "thread-2",
            "owner_key": "user-1",
            "report_type": "goldman_screener",
            "base_payload": {"limit": 10},
            "effective_prompt": "prompt",
            "latest_report": {
                "report_type": "goldman_screener",
                "title": "Goldman",
                "markdown": "# prior",
                "tool_plan": [{"tool": "x", "reason": "y"}],
                "sources_used": ["finviz"],
            },
        }
        refreshed = {
            "report_type": "goldman_screener",
            "title": "Goldman",
            "markdown": "# refreshed",
            "tool_plan": [{"tool": "x", "reason": "y"}],
            "sources_used": ["finviz"],
            "assumptions": ["a"],
            "limitations": ["l"],
        }

        with patch("apps.api.services.report_orchestrator.get_thread", new=AsyncMock(return_value=thread)), \
            patch("apps.api.services.report_orchestrator.generate_report", new=AsyncMock(return_value=refreshed)) as gen_mock, \
            patch("apps.api.services.report_orchestrator.append_thread_message", new=AsyncMock(return_value={})), \
            patch("apps.api.services.report_orchestrator.list_thread_messages", new=AsyncMock(return_value=[])), \
            patch("apps.api.services.report_orchestrator.update_thread_latest_report", new=AsyncMock(return_value=thread)), \
            patch("apps.api.services.report_orchestrator.log_report_run_to_mlflow") as mlflow_mock:
            mlflow_mock.return_value.enabled = False
            mlflow_mock.return_value.run_id = None
            mlflow_mock.return_value.error = None
            await orchestrate_report_followup(
                report_type="goldman_screener",
                owner_key="user-1",
                thread_id="thread-2",
                question="update",
                refresh_data=True,
            )

        gen_mock.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
