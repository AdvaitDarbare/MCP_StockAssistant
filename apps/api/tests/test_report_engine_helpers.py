"""Unit tests for report_engine pure helper functions (T-4).

Tests the shared financial math utilities used by all 10 report builders,
without any network calls or LLM invocations.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.report_engine import (  # noqa: E402
    _safe_float,
    _safe_pct,
    _moat_rating,
    _risk_score,
    _daily_returns,
    _correlation,
    _fmt_num,
    _fmt_pct,
)


class SafeFloatTests(unittest.TestCase):
    def test_plain_float(self) -> None:
        self.assertAlmostEqual(_safe_float(1.5), 1.5)

    def test_integer(self) -> None:
        self.assertAlmostEqual(_safe_float(42), 42.0)

    def test_string_float(self) -> None:
        self.assertAlmostEqual(_safe_float("3.14"), 3.14)

    def test_string_with_commas(self) -> None:
        self.assertAlmostEqual(_safe_float("1,234.56"), 1234.56)

    def test_billions_suffix(self) -> None:
        result = _safe_float("1.5B")
        self.assertAlmostEqual(result, 1_500_000_000.0)

    def test_millions_suffix(self) -> None:
        result = _safe_float("250M")
        self.assertAlmostEqual(result, 250_000_000.0)

    def test_trillions_suffix(self) -> None:
        result = _safe_float("2T")
        self.assertAlmostEqual(result, 2_000_000_000_000.0)

    def test_none_returns_none(self) -> None:
        self.assertIsNone(_safe_float(None))

    def test_empty_string_returns_none(self) -> None:
        self.assertIsNone(_safe_float(""))

    def test_dash_returns_none(self) -> None:
        self.assertIsNone(_safe_float("-"))

    def test_na_returns_none(self) -> None:
        self.assertIsNone(_safe_float("N/A"))

    def test_negative_value(self) -> None:
        self.assertAlmostEqual(_safe_float("-5.5"), -5.5)


class SafePctTests(unittest.TestCase):
    def test_decimal_fraction(self) -> None:
        """Values < 1 are treated as already-fractional (e.g. 0.25 = 25%)."""
        result = _safe_pct(0.25)
        self.assertAlmostEqual(result, 0.25)

    def test_percentage_string(self) -> None:
        result = _safe_pct("12.5%")
        self.assertAlmostEqual(result, 0.125)

    def test_none_returns_none(self) -> None:
        self.assertIsNone(_safe_pct(None))

    def test_dash_returns_none(self) -> None:
        self.assertIsNone(_safe_pct("-"))


class MoatRatingTests(unittest.TestCase):
    def _overview(self, roe=None, profit_margin=None, revenue_growth=None) -> dict:
        return {
            "roe": str(roe) if roe is not None else "-",
            "profit_margin": str(profit_margin) if profit_margin is not None else "-",
            "sales_past_5y": str(revenue_growth) if revenue_growth is not None else "-",
        }

    def test_strong_moat_high_roe(self) -> None:
        ov = self._overview(roe=0.30, profit_margin=0.25, revenue_growth=0.15)
        self.assertEqual(_moat_rating(ov), "strong")

    def test_weak_moat_low_metrics(self) -> None:
        ov = self._overview(roe=0.02, profit_margin=0.01, revenue_growth=0.01)
        self.assertEqual(_moat_rating(ov), "weak")

    def test_empty_overview_returns_weak(self) -> None:
        self.assertEqual(_moat_rating({}), "weak")


class RiskScoreTests(unittest.TestCase):
    def test_returns_tuple(self) -> None:
        overview = {"beta": "1.2", "debt_eq": "0.5", "short_float": "5%"}
        quote = {"price": 100.0}
        score, reason = _risk_score(overview, quote)
        self.assertIsInstance(score, (int, float))
        self.assertIsInstance(reason, str)

    def test_score_in_valid_range(self) -> None:
        overview = {"beta": "2.5", "debt_eq": "3.0", "short_float": "25%"}
        quote = {"price": 50.0}
        score, _ = _risk_score(overview, quote)
        self.assertGreaterEqual(score, 1)
        self.assertLessEqual(score, 10)

    def test_empty_inputs_returns_default(self) -> None:
        score, reason = _risk_score({}, {})
        self.assertIsInstance(score, (int, float))
        self.assertIsInstance(reason, str)


class DailyReturnsTests(unittest.TestCase):
    def _history(self, closes: list[float]) -> list[dict]:
        return [{"close": c, "date": f"2024-01-{i+1:02d}"} for i, c in enumerate(closes)]

    def test_basic_returns(self) -> None:
        history = self._history([100.0, 110.0, 99.0])
        returns = _daily_returns(history)
        self.assertEqual(len(returns), 2)
        self.assertAlmostEqual(returns[0], 0.10, places=5)
        self.assertAlmostEqual(returns[1], -0.10, places=4)

    def test_empty_history(self) -> None:
        self.assertEqual(_daily_returns([]), [])

    def test_single_row(self) -> None:
        self.assertEqual(_daily_returns(self._history([100.0])), [])

    def test_zero_close_handled(self) -> None:
        """Zero close should not raise ZeroDivisionError (may skip the row)."""
        history = self._history([0.0, 100.0])
        try:
            returns = _daily_returns(history)
            # Either skips the row or returns 0 — both are acceptable
            self.assertIsInstance(returns, list)
        except ZeroDivisionError:
            self.fail("_daily_returns raised ZeroDivisionError on zero close")


class CorrelationTests(unittest.TestCase):
    def test_perfect_positive_correlation(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertAlmostEqual(_correlation(a, a), 1.0, places=5)

    def test_perfect_negative_correlation(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [-1.0, -2.0, -3.0, -4.0, -5.0]
        self.assertAlmostEqual(_correlation(a, b), -1.0, places=5)

    def test_empty_returns_none_or_zero(self) -> None:
        """_correlation returns None for empty inputs (implementation-defined)."""
        result = _correlation([], [])
        self.assertIn(result, [None, 0.0])

    def test_mismatched_lengths_returns_none_or_zero(self) -> None:
        result = _correlation([1.0, 2.0], [1.0])
        self.assertIn(result, [None, 0.0])

    def test_constant_series_returns_none_or_zero(self) -> None:
        """Constant series has zero variance — correlation is undefined."""
        a = [1.0, 1.0, 1.0]
        b = [1.0, 2.0, 3.0]
        result = _correlation(a, b)
        self.assertIn(result, [None, 0.0])


class FmtNumTests(unittest.TestCase):
    def test_integer(self) -> None:
        result = _fmt_num(1000)
        # _fmt_num includes decimal places; just verify it contains the number
        self.assertIn("1,000", result)

    def test_float_default_decimals(self) -> None:
        result = _fmt_num(3.14159)
        self.assertIn("3.14", result)

    def test_none_returns_na(self) -> None:
        self.assertEqual(_fmt_num(None), "N/A")


class FmtPctTests(unittest.TestCase):
    def test_fraction_to_percent(self) -> None:
        result = _fmt_pct(0.1234)
        self.assertIn("12.3", result)
        self.assertIn("%", result)

    def test_none_returns_na(self) -> None:
        self.assertEqual(_fmt_pct(None), "N/A")


if __name__ == "__main__":
    unittest.main()
