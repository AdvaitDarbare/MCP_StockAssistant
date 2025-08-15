import os
import praw
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv


# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# Initialize Reddit client
reddit = None

try:
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )
    
    print("✅ Reddit client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Reddit client: {e}")
    reddit = None

# Popular stock-related subreddits
STOCK_SUBREDDITS = [
    "stocks",
    "investing", 
    "SecurityAnalysis",
    "ValueInvesting",
    "StockMarket",
    "financialindependence",
    "options",
    "pennystocks",
    "dividends",
    "ETFs"
]

# High-activity subreddits (separate for different feed types)
TRENDING_SUBREDDITS = [
    "wallstreetbets",
    "Daytrading", 
    "RobinHood",
    "investing"
]

def extract_stock_symbols(text: str) -> List[str]:
    """Extract stock symbols from text using regex patterns"""
    if not text:
        return []
    
    # Common patterns for stock mentions
    patterns = [
        r'\$([A-Z]{1,5})\b',  # $AAPL format
        r'\b([A-Z]{2,5})\s+(?:stock|shares|calls|puts|options)\b',  # AAPL stock
        r'\b([A-Z]{2,5})\s+(?:to the moon|rocket|diamond hands)\b',  # WSB lingo
    ]
    
    symbols = set()
    for pattern in patterns:
        matches = re.findall(pattern, text.upper())
        symbols.update(matches)
    
    # Filter out common false positives
    false_positives = {'DD', 'YOLO', 'FD', 'PUT', 'CALL', 'WSB', 'SEC', 'FDA', 'CEO', 'IPO', 'ETF', 'NYSE', 'NASDAQ'}
    symbols = symbols - false_positives
    
    return list(symbols)

def calculate_sentiment_score(post) -> Dict[str, any]:
    """Calculate basic sentiment score based on upvotes, comments, and keywords"""
    
    # Positive keywords
    positive_words = ['buy', 'bullish', 'moon', 'rocket', 'calls', 'long', 'hold', 'diamond', 'strong']
    negative_words = ['sell', 'bearish', 'crash', 'puts', 'short', 'dump', 'paper', 'weak']
    
    title_lower = post.title.lower()
    
    positive_count = sum(1 for word in positive_words if word in title_lower)
    negative_count = sum(1 for word in negative_words if word in title_lower)
    
    # Base sentiment from keywords
    keyword_sentiment = positive_count - negative_count
    
    # Engagement factor (upvotes and comments)
    engagement_score = min(post.score / 100, 5) + min(post.num_comments / 50, 3)
    
    # Combine scores
    sentiment_score = keyword_sentiment + (engagement_score * 0.1)
    
    return {
        'score': round(sentiment_score, 2),
        'label': 'bullish' if sentiment_score > 0.5 else 'bearish' if sentiment_score < -0.5 else 'neutral',
        'confidence': min(abs(sentiment_score) / 3, 1.0)
    }

def get_trending_posts(limit: int = 20) -> List[Dict]:
    """Get trending posts from stock-related subreddits"""
    if not reddit:
        print("❌ Reddit client not initialized")
        return []
    
    trending_posts = []
    
    try:
        for subreddit_name in TRENDING_SUBREDDITS:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                
                # Get hot posts from last 24 hours
                for post in subreddit.hot(limit=10):
                    # Skip stickied posts
                    if post.stickied:
                        continue
                    
                    # Check if post is recent (last 24 hours)
                    post_time = datetime.fromtimestamp(post.created_utc)
                    if datetime.now() - post_time > timedelta(days=1):
                        continue
                    
                    # Extract stock symbols
                    symbols = extract_stock_symbols(f"{post.title} {post.selftext}")
                    
                    # Calculate sentiment
                    sentiment = calculate_sentiment_score(post)
                    
                    post_data = {
                        'id': post.id,
                        'title': post.title,
                        'subreddit': subreddit_name,
                        'author': str(post.author) if post.author else '[deleted]',
                        'score': post.score,
                        'upvote_ratio': post.upvote_ratio,
                        'num_comments': post.num_comments,
                        'created_utc': post.created_utc,
                        'created_time': post_time.isoformat(),
                        'url': f"https://reddit.com{post.permalink}",
                        'selftext': post.selftext[:500] if post.selftext else '',
                        'symbols': symbols,
                        'sentiment': sentiment,
                        'is_trending': True
                    }
                    
                    trending_posts.append(post_data)
                    
            except Exception as e:
                print(f"❌ Error fetching from r/{subreddit_name}: {e}")
                continue
    
    except Exception as e:
        print(f"❌ Error fetching trending posts: {e}")
        return []
    
    # Sort by engagement (score + comments)
    trending_posts.sort(key=lambda x: x['score'] + x['num_comments'], reverse=True)
    
    return trending_posts[:limit]

def get_stock_discussions(symbol: str, limit: int = 10) -> List[Dict]:
    """Get recent discussions about a specific stock symbol"""
    if not reddit:
        print(f"❌ Reddit client not initialized")
        return []
    
    discussions = []
    
    try:
        # Search across multiple subreddits
        search_query = f"${symbol} OR {symbol}"
        
        for subreddit_name in STOCK_SUBREDDITS[:5]:  # Limit to prevent API rate limits
            try:
                subreddit = reddit.subreddit(subreddit_name)
                
                # Search for posts mentioning the symbol
                for post in subreddit.search(search_query, sort='new', time_filter='week', limit=5):
                    
                    # Extract stock symbols to confirm relevance
                    symbols = extract_stock_symbols(f"{post.title} {post.selftext}")
                    
                    if symbol not in symbols:
                        continue
                    
                    # Calculate sentiment
                    sentiment = calculate_sentiment_score(post)
                    
                    post_data = {
                        'id': post.id,
                        'title': post.title,
                        'subreddit': subreddit_name,
                        'author': str(post.author) if post.author else '[deleted]',
                        'score': post.score,
                        'upvote_ratio': post.upvote_ratio,
                        'num_comments': post.num_comments,
                        'created_utc': post.created_utc,
                        'created_time': datetime.fromtimestamp(post.created_utc).isoformat(),
                        'url': f"https://reddit.com{post.permalink}",
                        'selftext': post.selftext[:300] if post.selftext else '',
                        'symbols': symbols,
                        'sentiment': sentiment,
                        'is_trending': False
                    }
                    
                    discussions.append(post_data)
                    
            except Exception as e:
                print(f"❌ Error searching r/{subreddit_name} for {symbol}: {e}")
                continue
        
        # Sort by recency and engagement
        discussions.sort(key=lambda x: x['created_utc'], reverse=True)
        
        return discussions[:limit]
        
    except Exception as e:
        print(f"❌ Error fetching discussions for {symbol}: {e}")
        return []

def get_market_sentiment_summary() -> Dict:
    """Get overall market sentiment from recent posts"""
    if not reddit:
        return {'error': 'Reddit client not initialized'}
    
    try:
        posts = get_trending_posts(50)
        
        if not posts:
            return {'error': 'No posts found'}
        
        # Aggregate sentiment data
        total_bullish = sum(1 for p in posts if p['sentiment']['label'] == 'bullish')
        total_bearish = sum(1 for p in posts if p['sentiment']['label'] == 'bearish')
        total_neutral = sum(1 for p in posts if p['sentiment']['label'] == 'neutral')
        
        # Most mentioned symbols
        symbol_counts = {}
        for post in posts:
            for symbol in post['symbols']:
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Average engagement
        avg_score = sum(p['score'] for p in posts) / len(posts) if posts else 0
        avg_comments = sum(p['num_comments'] for p in posts) / len(posts) if posts else 0
        
        return {
            'total_posts': len(posts),
            'sentiment_breakdown': {
                'bullish': total_bullish,
                'bearish': total_bearish,
                'neutral': total_neutral
            },
            'sentiment_percentages': {
                'bullish': round((total_bullish / len(posts)) * 100, 1),
                'bearish': round((total_bearish / len(posts)) * 100, 1),
                'neutral': round((total_neutral / len(posts)) * 100, 1)
            },
            'top_mentioned_symbols': [{'symbol': s[0], 'mentions': s[1]} for s in top_symbols],
            'average_engagement': {
                'score': round(avg_score, 1),
                'comments': round(avg_comments, 1)
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error calculating market sentiment: {e}")
        return {'error': str(e)}

def get_subreddit_activity() -> List[Dict]:
    """Get activity overview for each tracked subreddit"""
    if not reddit:
        return []
    
    activity_data = []
    
    try:
        for subreddit_name in STOCK_SUBREDDITS + TRENDING_SUBREDDITS:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                
                # Get subreddit info
                activity_data.append({
                    'name': subreddit_name,
                    'display_name': subreddit.display_name,
                    'subscribers': subreddit.subscribers,
                    'active_users': subreddit.active_user_count,
                    'description': subreddit.public_description[:100] if subreddit.public_description else '',
                    'url': f"https://reddit.com/r/{subreddit_name}"
                })
                
            except Exception as e:
                print(f"❌ Error fetching activity for r/{subreddit_name}: {e}")
                continue
        
        # Sort by subscriber count
        activity_data.sort(key=lambda x: x.get('subscribers', 0), reverse=True)
        
        return activity_data
        
    except Exception as e:
        print(f"❌ Error fetching subreddit activity: {e}")
        return []