"""Technical analysis engine using pandas-ta."""

import pandas as pd
import pandas_ta as ta

from apps.api.services.cache import cache_get_or_fetch
from apps.api.services.schwab_client import get_price_history


async def compute_indicators(symbol: str) -> dict | None:
    """Compute technical indicators for a stock."""
    cache_key = f"ta:indicators:{symbol.upper()}"

    async def _fetch():
        # Get 6 months of daily data
        history = await get_price_history(symbol, period_type="month", period=6, frequency_type="daily", frequency=1)
        if not history or not history.get("candles"):
            return None

        df = pd.DataFrame(history["candles"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime").sort_index()

        if len(df) < 30:
            return None

        result = {"symbol": symbol.upper()}

        # RSI
        rsi = ta.rsi(df["close"], length=14)
        if rsi is not None and len(rsi) > 0:
            result["rsi_14"] = round(float(rsi.iloc[-1]), 2) if pd.notna(rsi.iloc[-1]) else None

        # MACD
        macd_result = ta.macd(df["close"], fast=12, slow=26, signal=9)
        if macd_result is not None and len(macd_result) > 0:
            result["macd"] = round(float(macd_result.iloc[-1, 0]), 4) if pd.notna(macd_result.iloc[-1, 0]) else None
            result["macd_signal"] = round(float(macd_result.iloc[-1, 1]), 4) if pd.notna(macd_result.iloc[-1, 1]) else None
            result["macd_histogram"] = round(float(macd_result.iloc[-1, 2]), 4) if pd.notna(macd_result.iloc[-1, 2]) else None

        # Moving Averages
        sma20 = ta.sma(df["close"], length=20)
        sma50 = ta.sma(df["close"], length=50)
        sma200 = ta.sma(df["close"], length=200)
        ema12 = ta.ema(df["close"], length=12)
        ema26 = ta.ema(df["close"], length=26)

        if sma20 is not None and len(sma20) > 0:
            result["sma_20"] = round(float(sma20.iloc[-1]), 2) if pd.notna(sma20.iloc[-1]) else None
        if sma50 is not None and len(sma50) > 0:
            result["sma_50"] = round(float(sma50.iloc[-1]), 2) if pd.notna(sma50.iloc[-1]) else None
        if sma200 is not None and len(sma200) > 0:
            result["sma_200"] = round(float(sma200.iloc[-1]), 2) if pd.notna(sma200.iloc[-1]) else None
        if ema12 is not None and len(ema12) > 0:
            result["ema_12"] = round(float(ema12.iloc[-1]), 2) if pd.notna(ema12.iloc[-1]) else None
        if ema26 is not None and len(ema26) > 0:
            result["ema_26"] = round(float(ema26.iloc[-1]), 2) if pd.notna(ema26.iloc[-1]) else None

        # Bollinger Bands
        bbands = ta.bbands(df["close"], length=20, std=2)
        if bbands is not None and len(bbands) > 0:
            result["bollinger_upper"] = round(float(bbands.iloc[-1, 0]), 2) if pd.notna(bbands.iloc[-1, 0]) else None
            result["bollinger_lower"] = round(float(bbands.iloc[-1, 2]), 2) if pd.notna(bbands.iloc[-1, 2]) else None

        # ATR (Average True Range)
        atr = ta.atr(df["high"], df["low"], df["close"], length=14)
        if atr is not None and len(atr) > 0:
            result["atr_14"] = round(float(atr.iloc[-1]), 2) if pd.notna(atr.iloc[-1]) else None

        # Support / Resistance (simple pivot-based)
        recent = df.tail(20)
        result["support"] = round(float(recent["low"].min()), 2)
        result["resistance"] = round(float(recent["high"].max()), 2)

        # Trend determination
        current_price = float(df["close"].iloc[-1])
        trend = "neutral"
        if result.get("sma_50") and result.get("sma_200"):
            if result["sma_50"] > result["sma_200"] and current_price > result["sma_50"]:
                trend = "bullish"
            elif result["sma_50"] < result["sma_200"] and current_price < result["sma_50"]:
                trend = "bearish"
        result["trend"] = trend
        result["current_price"] = round(current_price, 2)

        # Volume analysis
        avg_vol = float(df["volume"].tail(20).mean())
        latest_vol = float(df["volume"].iloc[-1])
        result["avg_volume_20d"] = int(avg_vol)
        result["latest_volume"] = int(latest_vol)
        result["volume_ratio"] = round(latest_vol / avg_vol, 2) if avg_vol > 0 else 1.0

        return result

    return await cache_get_or_fetch(cache_key, _fetch, "technical_indicators")


async def get_price_data_for_chart(
    symbol: str,
    period_type: str = "month",
    period: int = 6,
) -> dict | None:
    """Get price data formatted for frontend charting."""
    history = await get_price_history(symbol, period_type=period_type, period=period)
    if not history:
        return None

    df = pd.DataFrame(history["candles"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")

    # Add SMA overlays
    sma20 = ta.sma(df["close"], length=20)
    sma50 = ta.sma(df["close"], length=50)

    candles = []
    for i, row in df.iterrows():
        candle = {
            "time": row["datetime"].strftime("%Y-%m-%d"),
            "open": round(row["open"], 2),
            "high": round(row["high"], 2),
            "low": round(row["low"], 2),
            "close": round(row["close"], 2),
            "volume": int(row["volume"]),
        }
        if sma20 is not None and pd.notna(sma20.iloc[i]):
            candle["sma20"] = round(float(sma20.iloc[i]), 2)
        if sma50 is not None and pd.notna(sma50.iloc[i]):
            candle["sma50"] = round(float(sma50.iloc[i]), 2)
        candles.append(candle)

    return {"symbol": symbol.upper(), "candles": candles}
