from typing import Dict, List, Optional

from langchain_core.tools import tool


def _extract_closes(price_data: Optional[List[Dict]]) -> list[float]:
    if not price_data:
        return []
    closes: list[float] = []
    for row in price_data:
        if "close" in row and row["close"] is not None:
            closes.append(float(row["close"]))
    return closes


def _ema(values: list[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    ema_val = sum(values[:period]) / period
    for price in values[period:]:
        ema_val = (price - ema_val) * multiplier + ema_val
    return ema_val


def _rsi(values: list[float], period: int = 14) -> Optional[float]:
    if len(values) <= period:
        return None
    gains = []
    losses = []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_sma(symbol: str, period: int = 14, price_data: Optional[List[Dict]] = None):
    """Calculate simple moving average for a symbol."""
    closes = _extract_closes(price_data)
    if len(closes) < period:
        return {"error": f"Not enough data for SMA-{period}. Got {len(closes)} points."}

    sma = sum(closes[-period:]) / period
    current_price = closes[-1]
    return {
        "symbol": symbol.upper(),
        "indicator": "SMA",
        "period": period,
        "value": round(sma, 2),
        "signal": "buy" if current_price > sma else "sell",
    }


@tool
def calculate_sma_tool(symbol: str, period: int = 14, price_data: Optional[List[Dict]] = None):
    """Calculate simple moving average for a symbol."""
    return calculate_sma(symbol, period, price_data)


def calculate_rsi(symbol: str, period: int = 14, price_data: Optional[List[Dict]] = None):
    """Calculate RSI for a symbol."""
    closes = _extract_closes(price_data)
    rsi = _rsi(closes, period)
    if rsi is None:
        return {"error": f"Not enough data for RSI-{period}. Got {len(closes)} points."}

    sentiment = "neutral"
    if rsi > 70:
        sentiment = "overbought"
    elif rsi < 30:
        sentiment = "oversold"

    return {
        "symbol": symbol.upper(),
        "indicator": "RSI",
        "period": period,
        "value": round(rsi, 2),
        "signal": sentiment,
    }


@tool
def calculate_rsi_tool(symbol: str, period: int = 14, price_data: Optional[List[Dict]] = None):
    """Calculate RSI for a symbol."""
    return calculate_rsi(symbol, period, price_data)


def calculate_macd(symbol: str, price_data: Optional[List[Dict]] = None):
    """Calculate MACD using EMA-12 and EMA-26 (signal as EMA-9 approximation)."""
    closes = _extract_closes(price_data)
    if len(closes) < 35:
        return {"error": f"Not enough data for MACD. Got {len(closes)} points."}

    macd_series = []
    for i in range(26, len(closes)):
        window = closes[: i + 1]
        ema12 = _ema(window, 12)
        ema26 = _ema(window, 26)
        if ema12 is None or ema26 is None:
            continue
        macd_series.append(ema12 - ema26)

    if len(macd_series) < 9:
        return {"error": "Not enough MACD points for signal line."}

    signal_line = _ema(macd_series, 9)
    macd_line = macd_series[-1]
    histogram = macd_line - float(signal_line or 0)

    return {
        "symbol": symbol.upper(),
        "indicator": "MACD",
        "macd_line": round(macd_line, 4),
        "signal_line": round(float(signal_line or 0), 4),
        "histogram": round(histogram, 4),
        "signal": "buy" if histogram > 0 else "sell",
    }


@tool
def calculate_macd_tool(symbol: str, price_data: Optional[List[Dict]] = None):
    """Calculate MACD using EMA-12 and EMA-26 (signal as EMA-9 approximation)."""
    return calculate_macd(symbol, price_data)


@tool
def analyze_technicals(symbol: str, price_data: Optional[List[Dict]] = None):
    """Run a composite technical snapshot for a symbol."""
    closes = _extract_closes(price_data)
    if len(closes) < 200:
        return {"error": f"Not enough data for technical analysis. Got {len(closes)} points."}

    sma20 = calculate_sma(symbol, period=20, price_data=price_data)
    sma50 = calculate_sma(symbol, period=50, price_data=price_data)
    sma200 = calculate_sma(symbol, period=200, price_data=price_data)
    rsi = calculate_rsi(symbol, period=14, price_data=price_data)
    macd = calculate_macd(symbol, price_data=price_data)

    if "error" in sma20 or "error" in sma50 or "error" in sma200 or "error" in rsi or "error" in macd:
        return {
            "symbol": symbol.upper(),
            "error": "Unable to compute one or more indicators.",
            "details": {
                "sma20": sma20,
                "sma50": sma50,
                "sma200": sma200,
                "rsi": rsi,
                "macd": macd,
            },
        }

    recent_window = closes[-20:]
    support = min(recent_window)
    resistance = max(recent_window)
    trend = "Bullish" if closes[-1] > float(sma50["value"]) else "Bearish"

    return {
        "symbol": symbol.upper(),
        "rsi_14": rsi["value"],
        "sma_20": sma20["value"],
        "sma_50": sma50["value"],
        "sma_200": sma200["value"],
        "macd": macd["macd_line"],
        "macd_signal": macd["signal_line"],
        "trend": trend,
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "signal": macd["signal"],
    }
