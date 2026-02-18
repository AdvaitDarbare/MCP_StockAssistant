from __future__ import annotations

import pathlib
import sys
import unittest
from unittest.mock import AsyncMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.mlflow_tracker import MlflowRunResult
from apps.api.services.report_orchestrator import orchestrate_report


class ReportOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_orchestrator_adds_quality_and_trace(self) -> None:
        mock_report = {
            "report_type": "morgan_dcf",
            "title": "Morgan",
            "generated_at": "2026-02-18T00:00:00Z",
            "markdown": "# Morgan DCF\nAAPL analysis body with enough detail for quality checks.",
            "assumptions": ["x"],
            "limitations": ["y"],
            "sources_used": ["market_data_provider"],
            "tool_plan": [{"tool": "x", "reason": "y"}],
        }
        with patch(
            "apps.api.services.report_orchestrator.generate_report",
            new=AsyncMock(return_value=mock_report),
        ), patch(
            "apps.api.services.report_orchestrator.log_report_run_to_mlflow",
            return_value=MlflowRunResult(enabled=True, run_id="mlf-1"),
        ):
            out = await orchestrate_report("morgan_dcf", {"ticker": "AAPL"})

        self.assertIn("quality_gate", out)
        self.assertGreaterEqual(out["quality_gate"]["score"], 0.7)
        self.assertIn("orchestration_trace", out)
        self.assertEqual(out["mlflow_run_id"], "mlf-1")


if __name__ == "__main__":
    unittest.main()
