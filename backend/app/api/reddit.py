from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from datetime import datetime
from ..services.reddit_client import (
    get_trending_posts,
    get_stock_discussions, 
    get_market_sentiment_summary,
    get_subreddit_activity
)

router = APIRouter()

@router.get("/trending")
async def get_reddit_trending_posts(limit: int = Query(20, ge=1, le=50)):
    """Get trending stock-related posts from Reddit"""
    try:
        posts = get_trending_posts(limit)
        return {
            "success": True,
            "data": posts,
            "count": len(posts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trending posts: {str(e)}")

@router.get("/discussions/{symbol}")
async def get_reddit_stock_discussions(symbol: str, limit: int = Query(10, ge=1, le=20)):
    """Get Reddit discussions about a specific stock symbol"""
    try:
        discussions = get_stock_discussions(symbol.upper(), limit)
        return {
            "success": True,
            "symbol": symbol.upper(),
            "data": discussions,
            "count": len(discussions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching discussions for {symbol}: {str(e)}")

@router.get("/sentiment")
async def get_reddit_market_sentiment():
    """Get overall market sentiment from Reddit posts"""
    try:
        sentiment_data = get_market_sentiment_summary()
        
        if 'error' in sentiment_data:
            raise HTTPException(status_code=500, detail=sentiment_data['error'])
        
        return {
            "success": True,
            "data": sentiment_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating market sentiment: {str(e)}")

@router.get("/subreddits")
async def get_reddit_subreddit_activity():
    """Get activity overview for tracked subreddits"""
    try:
        activity_data = get_subreddit_activity()
        return {
            "success": True,
            "data": activity_data,
            "count": len(activity_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching subreddit activity: {str(e)}")

@router.get("/dashboard")
async def get_reddit_dashboard_data():
    """Get simplified Reddit dashboard data - trending posts and active communities only"""
    try:
        # Only fetch trending posts and subreddit activity to reduce API calls
        trending_posts = get_trending_posts(15)
        subreddit_activity = get_subreddit_activity()
        
        return {
            "success": True,
            "data": {
                "trending_posts": trending_posts,
                "subreddit_activity": subreddit_activity[:8],  # Top 8 subreddits
                "last_updated": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard data: {str(e)}")

@router.get("/search")
async def search_reddit_posts(
    query: str = Query(..., min_length=2, max_length=50),
    limit: int = Query(10, ge=1, le=20)
):
    """Search Reddit posts for specific terms"""
    try:
        # For now, we'll search for stock symbols
        # This could be expanded to do more comprehensive search
        if len(query) <= 5 and query.isalpha():
            # Assume it's a stock symbol
            discussions = get_stock_discussions(query.upper(), limit)
            return {
                "success": True, 
                "query": query,
                "data": discussions,
                "count": len(discussions)
            }
        else:
            # Return empty for now - could implement full text search later
            return {
                "success": True,
                "query": query, 
                "data": [],
                "count": 0,
                "message": "Currently only stock symbol search is supported"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching posts: {str(e)}")