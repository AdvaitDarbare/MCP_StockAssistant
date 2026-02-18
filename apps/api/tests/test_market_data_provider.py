"""Unit tests for market_data_provider pure functions (T-3).

Tests the staleness check, period mapping, and history normalization without
any network calls.
"""

from __future__ import annotations

import pathlib
import sys
import unittest
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.market_data_provider import (  # noqa: E402
    _is_history_stale,
    _map_days_to_schwab_period,
    _normalize_history,
)


def _row(date_str: str) -> dict:
    return {"date": date_str, "open": 100.0, "high": 105.0, "low": 99.0, "close": 102.0, "volume": 1_000_000}


def _recent_date(days_ago: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _old_date(days_ago: int = 30) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


class IsHistoryStaleTests(unittest.TestCase):
    def test_empty_rows_is_stale(self) -> None:
        self.assertTrue(_is_history_stale([]))

    def test_recent_data_not_stale(self) -> None:
        rows = [_row(_recent_date(1))]
        self.assertFalse(_is_history_stale(rows, max_age_days=7))

    def test_old_data_is_stale(self) -> None:
        rows = [_row(_old_date(30))]
        self.assertTrue(_is_history_stale(rows, max_age_days=7))

    def test_exactly_at_boundary_not_stale(self) -> None:
        rows = [_row(_recent_date(7))]
        self.assertFalse(_is_history_stale(rows, max_age_days=7))

    def test_one_day_over_boundary_is_stale(self) -> None:
        rows = [_row(_recent_date(8))]
        self.assertTrue(_is_history_stale(rows, max_age_days=7))

    def test_missing_date_field_is_stale(self) -> None:
        rows = [{"date": "", "close": 100.0}]
        self.assertTrue(_is_history_stale(rows))

    def test_invalid_date_format_is_stale(self) -> None:
        rows = [{"date": "not-a-date", "close": 100.0}]
        self.assertTrue(_is_history_stale(rows))

    def test_uses_last_row_not_first(self) -> None:
        """Staleness is determined by the LAST row (most recent candle)."""
        rows = [_row(_old_date(30)), _row(_recent_date(1))]
        self.assertFalse(_is_history_stale(rows, max_age_days=7))


class MapDaysToSchwabPeriodTests(unittest.TestCase):
    def test_30_days(self) -> None:
        self.assertEqual(_map_days_to_schwab_period(30), ("month", 1))

    def test_31_days(self) -> None:
        self.assertEqual(_map_days_to_schwab_period(31), ("month", 2))

    def test_60_days(self) -> None:
        self.assertEqual(_map_days_to_schwab_period(60), ("month", 2))

    def test_90_days(self) -> None:
        self.assertEqual(_map_days_to_schwab_period(90), ("month", 3))

    def test_180_days(self) -> None:
        self.assertEqual(_map_days_to_schwab_period(180), ("month", 6))

    def test_365_days(self) -> None:
        self.assertEqual(_map_days_to_schwab_period(365), ("year", 1))

    def test_730_days(self) -> None:
        self.assertEqual(_map_days_to_schwab_period(730), ("year", 2))

    def test_1825_days(self) -> None:
        self.assertEqual(_map_days_to_schwab_period(1825), ("year", 5))

    def test_over_1825_days(self) -> None:
        self.assertEqual(_map_days_to_schwab_period(3650), ("year", 10))


class NormalizeHistoryTests(unittest.TestCase):
    def _schwab_candle(self, timestamp_ms: int) -> dict:
        return {
            "datetime": timestamp_ms,
            "open": 150.0,
            "high": 155.0,
            "low": 148.0,
            "close": 152.0,
            "volume": 5_000_000,
        }

    def test_empty_raw_returns_empty(self) -> None:
        result = _normalize_history({}, "AAPL", 30)
        self.assertEqual(result, [])

    def test_none_raw_returns_empty(self) -> None:
        result = _normalize_history(None, "AAPL", 30)
        self.assertEqual(result, [])

    def test_timestamp_ms_converted_to_date(self) -> None:
        # Use a fixed timestamp and verify the date string is 10 chars in YYYY-MM-DD format
        # (exact date depends on local timezone, so we just check format and round-trip)
        ts_ms = int(datetime(2024, 1, 15, 12, 0, 0).timestamp() * 1000)  # noon local time
        raw = {"candles": [self._schwab_candle(ts_ms)]}
        result = _normalize_history(raw, "AAPL", 30)
        self.assertEqual(len(result), 1)
        date_str = result[0]["date"]
        # Must be a valid YYYY-MM-DD date string
        self.assertRegex(date_str, r"^\d{4}-\d{2}-\d{2}$")

    def test_symbol_uppercased(self) -> None:
        ts_ms = int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp() * 1000)
        raw = {"candles": [self._schwab_candle(ts_ms)]}
        result = _normalize_history(raw, "aapl", 30)
        self.assertEqual(result[0]["symbol"], "AAPL")

    def test_days_limit_applied(self) -> None:
        """Only the last `days` candles should be returned."""
        candles = [
            self._schwab_candle(int(datetime(2024, 1, i + 1, tzinfo=timezone.utc).timestamp() * 1000))
            for i in range(10)
        ]
        raw = {"candles": candles}
        result = _normalize_history(raw, "AAPL", 5)
        self.assertEqual(len(result), 5)

    def test_string_date_passthrough(self) -> None:
        raw = {"candles": [{"datetime": "2024-06-01T00:00:00", "open": 1, "high": 2, "low": 0, "close": 1, "volume": 0}]}
        result = _normalize_history(raw, "MSFT", 30)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["date"][:10], "2024-06-01")

    def test_ohlcv_fields_present(self) -> None:
        ts_ms = int(datetime(2024, 3, 1, tzinfo=timezone.utc).timestamp() * 1000)
        raw = {"candles": [self._schwab_candle(ts_ms)]}
        result = _normalize_history(raw, "TSLA", 30)
        row = result[0]
        for field in ("open", "high", "low", "close", "volume"):
            self.assertIn(field, row)


if __name__ == "__main__":
    unittest.main()
