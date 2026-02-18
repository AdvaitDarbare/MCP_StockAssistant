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

from apps.api.config import settings
from apps.api.gateway.routers.schwab import router as schwab_router


class SchwabRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(schwab_router, prefix="/api")
        self.client = TestClient(app)

    def test_observability_endpoint(self) -> None:
        snapshot = {"event_count": 0, "recent_events": [], "counters": {}, "last_errors": {}}
        with patch(
            "apps.api.gateway.routers.schwab.get_schwab_observability_snapshot",
            return_value=snapshot,
        ):
            response = self.client.get("/api/schwab/observability?limit=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["event_count"], 0)

    def test_preview_order_flow(self) -> None:
        with patch(
            "apps.api.gateway.routers.schwab.audit_trade_request",
            new=AsyncMock(return_value=None),
        ) as audit_mock, patch(
            "apps.api.gateway.routers.schwab.preview_order",
            new=AsyncMock(return_value={"orderValidationResult": "ok"}),
        ):
            response = self.client.post(
                "/api/schwab/accounts/12345678/orders/preview",
                json={"order": {"orderType": "MARKET"}},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["account_number"], "12345678")
        self.assertEqual(audit_mock.await_count, 1)

    def test_submit_order_blocked_when_live_trading_disabled(self) -> None:
        original_live = settings.ENABLE_LIVE_TRADING
        original_hitl = settings.REQUIRE_HITL_FOR_TRADES
        try:
            settings.ENABLE_LIVE_TRADING = False
            settings.REQUIRE_HITL_FOR_TRADES = True
            with patch(
                "apps.api.gateway.routers.schwab.audit_trade_request",
                new=AsyncMock(return_value=None),
            ), patch(
                "apps.api.gateway.routers.schwab.place_order",
                new=AsyncMock(return_value={"status": "ok"}),
            ):
                response = self.client.post(
                    "/api/schwab/accounts/12345678/orders/submit",
                    json={"order": {"orderType": "MARKET"}},
                )
            self.assertEqual(response.status_code, 403)
            self.assertIn("Live order placement is disabled", response.json()["detail"])
        finally:
            settings.ENABLE_LIVE_TRADING = original_live
            settings.REQUIRE_HITL_FOR_TRADES = original_hitl

    def test_submit_order_success_with_hitl(self) -> None:
        original_live = settings.ENABLE_LIVE_TRADING
        original_hitl = settings.REQUIRE_HITL_FOR_TRADES
        original_secret = settings.HITL_SHARED_SECRET
        try:
            settings.ENABLE_LIVE_TRADING = True
            settings.REQUIRE_HITL_FOR_TRADES = True
            settings.HITL_SHARED_SECRET = ""
            with patch(
                "apps.api.gateway.routers.schwab.audit_trade_request",
                new=AsyncMock(return_value=None),
            ) as audit_mock, patch(
                "apps.api.gateway.routers.schwab.place_order",
                new=AsyncMock(return_value={"order_id": "abc123"}),
            ) as place_mock:
                response = self.client.post(
                    "/api/schwab/accounts/12345678/orders/submit",
                    json={
                        "order": {"orderType": "MARKET"},
                        "hitl": {
                            "approved": True,
                            "reviewer": "advait",
                            "ticket_id": "HITL-42",
                            "reason": "manual approval",
                        },
                    },
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "submitted")
            self.assertEqual(place_mock.await_count, 1)
            self.assertGreaterEqual(audit_mock.await_count, 2)
        finally:
            settings.ENABLE_LIVE_TRADING = original_live
            settings.REQUIRE_HITL_FOR_TRADES = original_hitl
            settings.HITL_SHARED_SECRET = original_secret


if __name__ == "__main__":
    unittest.main()
