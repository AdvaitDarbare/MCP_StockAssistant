from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.gateway.routers.reports import router as reports_router
from apps.api.services.report_engine import REPORT_BUILDERS, list_report_types


class ReportsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(reports_router, prefix="/api")
        self.client = TestClient(app)

    def test_types_include_all_workflows_and_exact_prompts(self) -> None:
        response = self.client.get("/api/reports/types")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        report_types = payload["types"]
        self.assertEqual(len(report_types), 10)

        ids = {item["id"] for item in report_types}
        self.assertEqual(ids, set(REPORT_BUILDERS.keys()))

        goldman = next(item for item in report_types if item["id"] == "goldman_screener")
        self.assertIn(
            "You are a senior equity analyst at Goldman Sachs with 20 years of experience",
            goldman["prompt_template"],
        )

    def test_get_prompt_endpoint(self) -> None:
        response = self.client.get("/api/reports/morgan_dcf/prompt")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], "morgan_dcf")
        self.assertIn("The stock I want valued: [ENTER TICKER SYMBOL AND COMPANY NAME]", payload["prompt_template"])

    def test_templates_endpoint(self) -> None:
        mocked_templates = [
            {
                "id": "goldman_screener",
                "title": "Goldman Sachs Stock Screener",
                "default_prompt": "default",
                "effective_prompt": "effective",
                "is_overridden": True,
            }
        ]
        with patch("apps.api.gateway.routers.reports.list_templates", new=AsyncMock(return_value=mocked_templates)):
            response = self.client.get("/api/reports/templates?owner_key=user-1")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["templates"][0]["id"], "goldman_screener")

    def test_update_template_endpoint(self) -> None:
        mocked = {
            "owner_key": "user-1",
            "id": "morgan_dcf",
            "effective_prompt": "edited",
            "is_overridden": True,
        }
        with patch("apps.api.gateway.routers.reports.save_template_override", new=AsyncMock(return_value=mocked)):
            response = self.client.put(
                "/api/reports/templates/morgan_dcf",
                json={"owner_key": "user-1", "prompt_text": "edited"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["is_overridden"], True)

    def test_delete_template_endpoint(self) -> None:
        mocked = {
            "owner_key": "user-1",
            "id": "morgan_dcf",
            "effective_prompt": "default",
            "is_overridden": False,
            "removed": True,
        }
        with patch("apps.api.gateway.routers.reports.reset_template_override", new=AsyncMock(return_value=mocked)):
            response = self.client.delete("/api/reports/templates/morgan_dcf?owner_key=user-1")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_overridden"])

    def test_run_report_success(self) -> None:
        mocked = {
            "report_type": "goldman_screener",
            "title": "Goldman Sachs Stock Screener",
            "generated_at": "2026-02-18T00:00:00Z",
            "markdown": "# ok",
            "thread_id": "abc",
            "effective_prompt": "prompt",
            "follow_up_supported": True,
        }
        with patch("apps.api.gateway.routers.reports.orchestrate_report", new=AsyncMock(return_value=mocked)):
            response = self.client.post("/api/reports/goldman_screener", json={"payload": {"limit": 10}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Goldman Sachs Stock Screener")
        self.assertTrue(response.json()["follow_up_supported"])

    def test_report_followup_success(self) -> None:
        mocked = {
            "report_type": "goldman_screener",
            "title": "Goldman Sachs Stock Screener",
            "generated_at": "2026-02-18T00:00:00Z",
            "markdown": "# follow-up",
            "thread_id": "abc",
            "follow_up_supported": True,
        }
        with patch("apps.api.gateway.routers.reports.orchestrate_report_followup", new=AsyncMock(return_value=mocked)):
            response = self.client.post(
                "/api/reports/goldman_screener/followup",
                json={
                    "owner_key": "user-1",
                    "thread_id": "abc",
                    "question": "yeah",
                    "refresh_data": False,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["thread_id"], "abc")

    def test_run_report_bad_request(self) -> None:
        with patch(
            "apps.api.gateway.routers.reports.orchestrate_report",
            new=AsyncMock(side_effect=ValueError("Ticker is required for DCF report.")),
        ):
            response = self.client.post("/api/reports/morgan_dcf", json={"payload": {}})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Ticker is required", response.json()["detail"])

    def test_list_report_types_contract(self) -> None:
        report_types = list_report_types()
        self.assertEqual({t["id"] for t in report_types}, set(REPORT_BUILDERS.keys()))
        self.assertTrue(all("prompt_template" in t for t in report_types))


if __name__ == "__main__":
    unittest.main()
