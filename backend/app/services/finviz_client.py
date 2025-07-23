# backend/finviz_client.py
import pandas as pd
from pyfinviz.quote import Quote
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

def get_company_overview(ticker: str) -> dict | None:
    """Get company overview information including basic details and sectors
    
    Tool: Company Overview
    Purpose: Get basic company information, exchange, sectors
    """
    try:
        # Initialize with API key if available
        finviz_api_key = os.getenv("FINVIZ_API_KEY")
        if finviz_api_key:
            q = Quote(ticker=ticker, api_key=finviz_api_key)
        else:
            q = Quote(ticker=ticker)
        
        # Check if ticker exists
        if not q.exists:
            print(f"❌ Ticker {ticker} not found")
            return None
        
        return {
            "ticker": q.ticker,
            "company_name": q.company_name,
            "exchange": q.exchange,
            "sectors": q.sectors,
            "exists": q.exists
        }
        
    except Exception as e:
        print(f"❌ Error fetching company overview for {ticker}: {e}")
        return None

def get_analyst_ratings(ticker: str) -> pd.DataFrame | None:
    """Get analyst ratings and recommendations
    
    Tool: Analyst Ratings
    Purpose: Get analyst recommendations, price targets, ratings changes
    """
    try:
        # Initialize with API key if available
        finviz_api_key = os.getenv("FINVIZ_API_KEY")
        if finviz_api_key:
            q = Quote(ticker=ticker, api_key=finviz_api_key)
        else:
            q = Quote(ticker=ticker)
        
        # Check if ticker exists
        if not q.exists:
            print(f"❌ Ticker {ticker} not found")
            return None
        
        # Try to get analyst ratings - return the DataFrame for better formatting
        if hasattr(q, 'outer_ratings_df'):
            try:
                return q.outer_ratings_df
            except Exception as e:
                print(f"Error accessing ratings: {str(e)}")
                return None
        else:
            print("Analyst ratings not available in this version")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching analyst ratings for {ticker}: {e}")
        return None

def get_company_news(ticker: str, limit: int = 8) -> pd.DataFrame | None:
    """Get recent company news and articles
    
    Tool: Company News
    Purpose: Get recent news articles, press releases, headlines
    """
    try:
        # Initialize with API key if available
        finviz_api_key = os.getenv("FINVIZ_API_KEY")
        if finviz_api_key:
            q = Quote(ticker=ticker, api_key=finviz_api_key)
        else:
            q = Quote(ticker=ticker)
        
        # Check if ticker exists
        if not q.exists:
            print(f"❌ Ticker {ticker} not found")
            return None
        
        # Try to get news data - matching your working script
        if hasattr(q, 'outer_news_df'):
            news_df = q.outer_news_df
            if news_df is not None and not news_df.empty:
                # Return the requested number of articles
                return news_df.head(limit) if limit > 0 else news_df
            else:
                print(f"❌ No news data available for {ticker}")
                return None
        else:
            print(f"❌ News data not available in this version of pyfinviz")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching news for {ticker}: {e}")
        return None

def get_insider_trading(ticker: str, limit: int = 8) -> pd.DataFrame | None:
    """Get insider trading activity
    
    Tool: Insider Trading
    Purpose: Get insider buy/sell activity, officer transactions
    """
    try:
        # Initialize with API key if available
        finviz_api_key = os.getenv("FINVIZ_API_KEY")
        if finviz_api_key:
            q = Quote(ticker=ticker, api_key=finviz_api_key)
        else:
            q = Quote(ticker=ticker)
        
        # Check if ticker exists
        if not q.exists:
            print(f"❌ Ticker {ticker} not found")
            return None
        
        # Try to get insider trading data - matching your working script
        if hasattr(q, 'insider_trading_df'):
            insider_df = q.insider_trading_df
            if insider_df is not None and not insider_df.empty:
                # Return the requested number of transactions
                return insider_df.head(limit) if limit > 0 else insider_df
            else:
                print(f"❌ No insider trading data available for {ticker}")
                return None
        else:
            print(f"❌ Insider trading data not available in this version of pyfinviz")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching insider trading for {ticker}: {e}")
        return None

def get_all_insights(ticker: str) -> dict:
    """Get comprehensive equity insights including all available data
    
    Tool: All Insights
    Purpose: Get company overview, analyst ratings, news, and insider trading
    """
    try:
        print(f"🔍 Fetching comprehensive insights for {ticker}...")
        
        # Fetch all data types
        overview = get_company_overview(ticker)
        ratings = get_analyst_ratings(ticker)
        news = get_company_news(ticker)
        insider = get_insider_trading(ticker)
        
        return {
            "ticker": ticker,
            "overview": overview,
            "analyst_ratings": ratings,
            "news": news,
            "insider_trading": insider
        }
        
    except Exception as e:
        print(f"❌ Error fetching comprehensive insights for {ticker}: {e}")
        return {
            "ticker": ticker,
            "overview": None,
            "analyst_ratings": None,
            "news": None,
            "insider_trading": None,
            "error": str(e)
        }

# Fallback functions for when pyfinviz data is unavailable
def get_fallback_company_overview(ticker: str) -> dict:
    """Fallback company overview data"""
    return {
        "ticker": ticker,
        "company_name": f"{ticker} Corporation",
        "exchange": "Unknown",
        "sectors": "Data unavailable - using fallback",
        "exists": True,
        "note": "Company overview data unavailable - using fallback"
    }

def get_fallback_insights() -> dict:
    """Fallback when all insights are unavailable"""
    return {
        "note": "Equity insights unavailable - please verify ticker symbol and try again later",
        "suggestion": "Try checking major tickers like AAPL, MSFT, GOOGL, TSLA, etc."
    }