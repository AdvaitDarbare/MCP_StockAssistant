"""Reddit client for stock sentiment analysis — upgraded from v1."""

import re
from datetime import datetime, timedelta

import praw

from apps.api.config import settings
from apps.api.services.cache import cache_get_or_fetch

_reddit = None

STOCK_SUBREDDITS = [
    "wallstreetbets", "stocks", "investing", "options", "stockmarket",
    "dividends", "SecurityAnalysis", "ValueInvesting", "pennystocks",
    "thetagang", "Daytrading", "algotrading", "FluentInFinance", "StockMarket",
]

SENTIMENT_POSITIVE = [
    "bull", "calls", "moon", "rocket", "buy", "long", "pump", "green",
    "breakout", "undervalued", "squeeze", "diamond hands", "tendies",
    "to the moon", "ath", "all time high", "strong buy",
]
SENTIMENT_NEGATIVE = [
    "bear", "puts", "crash", "dump", "sell", "short", "red", "overvalued",
    "bubble", "bag holder", "loss", "paper hands", "rug pull", "down",
    "recession", "correction",
]


def _get_reddit():
    global _reddit
    if _reddit is None:
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
            _reddit = praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT or "StockAssistant/2.0",
            )
    return _reddit


def _analyze_sentiment(text: str) -> dict:
    """Simple keyword-based sentiment analysis."""
    text_lower = text.lower()
    pos = sum(1 for word in SENTIMENT_POSITIVE if word in text_lower)
    neg = sum(1 for word in SENTIMENT_NEGATIVE if word in text_lower)
    total = pos + neg
    if total == 0:
        return {"score": 0.5, "label": "neutral", "positive": 0, "negative": 0}

    score = pos / total
    label = "bullish" if score > 0.6 else "bearish" if score < 0.4 else "neutral"
    return {"score": round(score, 2), "label": label, "positive": pos, "negative": neg}


def _extract_symbols(text: str) -> list[str]:
    """Extract stock symbols from text."""
    pattern = r'\$([A-Z]{1,5})\b'
    symbols = re.findall(pattern, text)
    # Also match uppercase words that look like tickers (3-5 chars)
    words = re.findall(r'\b([A-Z]{3,5})\b', text)
    common_words = {"THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
                    "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "HAS", "HIS",
                    "HOW", "ITS", "LET", "MAY", "NEW", "NOW", "OLD", "SEE",
                    "WAY", "WHO", "OIL", "DID", "GET", "HIM", "GOT", "TOP",
                    "TOO", "ANY", "DAY", "HAD", "HOT", "FAR", "WHY", "JUST",
                    "MOST", "SOME", "VERY", "WHEN", "WHAT", "WITH", "WILL",
                    "THEY", "THIS", "THAT", "FROM", "HAVE", "BEEN", "EDIT",
                    "TLDR", "YOLO", "IMHO", "FWIW", "IMO"}
    tickers = [w for w in words if w not in common_words]
    return list(set(symbols + tickers))[:10]


async def get_trending_posts(limit: int = 20) -> dict | None:
    """Get trending stock-related posts across subreddits."""
    cache_key = f"reddit:trending:{limit}"

    async def _fetch():
        reddit = _get_reddit()
        if not reddit:
            return None

        posts = []
        for sub_name in STOCK_SUBREDDITS[:5]:  # Top 5 for speed
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.hot(limit=limit // 5):
                    sentiment = _analyze_sentiment(f"{post.title} {post.selftext[:500]}")
                    symbols = _extract_symbols(f"{post.title} {post.selftext[:500]}")

                    posts.append({
                        "subreddit": sub_name,
                        "title": post.title,
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "url": f"https://reddit.com{post.permalink}",
                        "created_utc": datetime.fromtimestamp(post.created_utc).isoformat(),
                        "sentiment": sentiment,
                        "symbols": symbols,
                    })
            except Exception as e:
                print(f"Error fetching from r/{sub_name}: {e}")

        posts.sort(key=lambda x: x["score"], reverse=True)
        return {"posts": posts[:limit], "count": len(posts)}

    return await cache_get_or_fetch(cache_key, _fetch, "reddit_sentiment")


async def get_stock_sentiment(symbol: str, limit: int = 15) -> dict | None:
    """Get sentiment for a specific stock from Reddit."""
    cache_key = f"reddit:sentiment:{symbol.upper()}"

    async def _fetch():
        reddit = _get_reddit()
        if not reddit:
            return None

        posts = []
        sentiments = []

        for sub_name in STOCK_SUBREDDITS[:8]:
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.search(symbol.upper(), time_filter="week", limit=5):
                    text = f"{post.title} {post.selftext[:500]}"
                    sentiment = _analyze_sentiment(text)
                    sentiments.append(sentiment["score"])

                    posts.append({
                        "subreddit": sub_name,
                        "title": post.title,
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "url": f"https://reddit.com{post.permalink}",
                        "sentiment": sentiment,
                    })
            except Exception:
                pass

        # Aggregate sentiment
        avg_score = sum(sentiments) / len(sentiments) if sentiments else 0.5
        overall = "bullish" if avg_score > 0.6 else "bearish" if avg_score < 0.4 else "neutral"

        posts.sort(key=lambda x: x["score"], reverse=True)
        return {
            "symbol": symbol.upper(),
            "overall_sentiment": overall,
            "sentiment_score": round(avg_score, 2),
            "post_count": len(posts),
            "posts": posts[:limit],
        }

    return await cache_get_or_fetch(cache_key, _fetch, "reddit_sentiment")
