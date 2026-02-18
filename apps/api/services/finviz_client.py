"""Finviz client for fundamental data — upgraded from v1."""

import pandas as pd
from pyfinviz.screener import Screener
from pyfinviz.quote import Quote
from apps.api.services.cache import cache_get_or_fetch
import asyncio

def _safe_str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        cleaned = [str(item).strip() for item in v if str(item).strip()]
        return ", ".join(cleaned)
    if isinstance(v, float) and pd.isna(v):
        return ""
    return str(v)

def _first_row_dict(df: pd.DataFrame | None) -> dict:
    if df is None or df.empty:
        return {}
    return {str(k): v for k, v in df.iloc[0].to_dict().items()}

async def get_company_overview(symbol: str) -> dict | None:
    """Get company overview data from Finviz."""
    cache_key = f"finviz:overview:{symbol.upper()}"

    async def _fetch():
        try:
            def _get_data():
                stock = Quote(ticker=symbol.upper())
                return _first_row_dict(getattr(stock, "fundamental_df", None)), getattr(stock, "company_name", symbol.upper()), getattr(stock, "sectors", "")

            info, company_name, sectors = await asyncio.to_thread(_get_data)
            if not info:
                return None

            return {
                "symbol": symbol.upper(),
                "company": _safe_str(company_name),
                "sector": _safe_str(sectors),
                "industry": "",
                "country": "",
                "market_cap": info.get("Market Cap", ""),
                "pe": info.get("P/E", ""),
                "forward_pe": info.get("Forward P/E", ""),
                "peg": info.get("PEG", ""),
                "ps": info.get("P/S", ""),
                "pb": info.get("P/B", ""),
                "payout_ratio": info.get("Payout", ""),
                "eps": info.get("EPS (ttm)", ""),
                "eps_next_y": info.get("EPS next Y", ""),
                "eps_past_5y": info.get("EPS past 5Y", ""),
                "sales_past_5y": info.get("Sales past 5Y", ""),
                "dividend_yield": info.get("Dividend %", ""),
                "roe": info.get("ROE", ""),
                "roi": info.get("ROI", ""),
                "debt_eq": info.get("Debt/Eq", ""),
                "gross_margin": info.get("Gross Margin", ""),
                "oper_margin": info.get("Oper. Margin", ""),
                "profit_margin": info.get("Profit Margin", ""),
                "revenue": info.get("Revenue", ""),
                "income": info.get("Income", ""),
                "employees": info.get("Employees", ""),
                "short_float": info.get("Short Float", ""),
                "target_price": info.get("Target Price", ""),
                "52w_range": info.get("52W Range", ""),
                "rsi_14": info.get("RSI (14)", ""),
                "avg_volume": info.get("Avg Volume", ""),
                "rel_volume": info.get("Rel Volume", ""),
                "beta": info.get("Beta", ""),
                "sma20": info.get("SMA20", ""),
                "sma50": info.get("SMA50", ""),
                "sma200": info.get("SMA200", ""),
            }
        except Exception as e:
            print(f"Error fetching Finviz data for {symbol}: {e}")
            return None

    return await cache_get_or_fetch(cache_key, _fetch, "analyst_ratings")

async def get_analyst_ratings(symbol: str) -> dict | None:
    """Get analyst ratings and price targets."""
    cache_key = f"finviz:ratings:{symbol.upper()}"

    async def _fetch():
        try:
            def _get_ratings():
                stock = Quote(ticker=symbol.upper())
                return getattr(stock, "outer_ratings_df", None)

            ratings_df = await asyncio.to_thread(_get_ratings)

            ratings = []
            if ratings_df is not None and not ratings_df.empty:
                for _, row in ratings_df.head(10).iterrows():
                    ratings.append({
                        "date": str(row.get("Date", "")),
                        "action": str(row.get("Status", "")),
                        "analyst": str(row.get("Outer", "")),
                        "rating": str(row.get("Rating", "")),
                        "price_target": str(row.get("Price", "")),
                    })

            return {
                "symbol": symbol.upper(),
                "ratings": ratings,
                "count": len(ratings),
            }
        except Exception as e:
            print(f"Error fetching analyst ratings for {symbol}: {e}")
            return None

    return await cache_get_or_fetch(cache_key, _fetch, "analyst_ratings")

async def get_insider_trades(symbol: str, limit: int = 10) -> dict | None:
    """Get insider trading activity."""
    cache_key = f"finviz:insider:{symbol.upper()}"

    async def _fetch():
        try:
            def _get_insider():
                stock = Quote(ticker=symbol.upper())
                return getattr(stock, "insider_trading_df", None)

            insider_df = await asyncio.to_thread(_get_insider)

            trades = []
            if insider_df is not None and not insider_df.empty:
                for _, row in insider_df.head(limit).iterrows():
                    raw = {str(k): _safe_str(v) for k, v in row.to_dict().items()}
                    cols = list(raw.keys())
                    vals = list(raw.values())
                    trades.append({
                        "insider": raw.get("Insider", raw.get("Insider Trading", vals[0] if vals else "")),
                        "relationship": raw.get("Relationship", cols[2] if len(cols) > 2 else ""),
                        "date": raw.get("Date", cols[3] if len(cols) > 3 else ""),
                        "transaction": raw.get("Transaction", vals[4] if len(vals) > 4 else ""),
                        "value": raw.get("Value", vals[5] if len(vals) > 5 else ""),
                        "shares": raw.get("#Shares Total", raw.get("Shares", vals[6] if len(vals) > 6 else "")),
                        "raw": raw,
                    })

            return {
                "symbol": symbol.upper(),
                "insider_trades": trades,
                "count": len(trades),
            }
        except Exception as e:
            print(f"Error fetching insider trades for {symbol}: {e}")
            return None

    return await cache_get_or_fetch(cache_key, _fetch, "insider_trades")

async def get_company_news(symbol: str, limit: int = 10) -> dict | None:
    """Get recent company news."""
    cache_key = f"finviz:news:{symbol.upper()}"

    async def _fetch():
        try:
            def _get_news():
                stock = Quote(ticker=symbol.upper())
                return getattr(stock, "outer_news_df", None)

            news_df = await asyncio.to_thread(_get_news)

            articles = []
            if news_df is not None and not news_df.empty:
                for _, row in news_df.head(limit).iterrows():
                    row_dict = row.to_dict()
                    articles.append({
                        "date": _safe_str(row_dict.get("Date", "")),
                        "headline": _safe_str(
                            row_dict.get("Title", row_dict.get("Headline", row_dict.get("Header", "")))
                        ),
                        "source": _safe_str(row_dict.get("Source", row_dict.get("From", ""))),
                        "link": _safe_str(row_dict.get("Link", row_dict.get("URL", ""))),
                    })

            return {
                "symbol": symbol.upper(),
                "news": articles,
                "count": len(articles),
            }
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
            return None

    return await cache_get_or_fetch(cache_key, _fetch, "news")
