#!/usr/bin/env python3
"""
Test Reddit API connectivity
"""

import os
import praw
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def test_reddit_connection():
    """Test Reddit API connection"""
    
    print("🔍 Testing Reddit API Connection")
    print("=" * 40)
    
    # Check credentials
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")
    
    print(f"Client ID: {client_id}")
    print(f"User Agent: {user_agent}")
    print(f"Client Secret: {'*' * len(client_secret) if client_secret else 'Not set'}")
    print()
    
    if not all([client_id, client_secret, user_agent]):
        print("❌ Missing Reddit credentials in .env file")
        return False
    
    try:
        # Initialize Reddit client
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
        print("✅ Reddit client initialized")
        
        # Test basic functionality - get subreddit info
        subreddit = reddit.subreddit("stocks")
        print(f"✅ Connected to r/stocks")
        print(f"   Subscribers: {subreddit.subscribers:,}")
        print(f"   Description: {subreddit.public_description[:100]}...")
        
        # Try to get a few posts
        print("\n🔍 Testing post retrieval...")
        posts = list(subreddit.hot(limit=3))
        print(f"✅ Retrieved {len(posts)} posts")
        
        for i, post in enumerate(posts, 1):
            print(f"   {i}. {post.title[:50]}... (Score: {post.score})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        if "401" in str(e):
            print("\n🔧 Troubleshooting 401 Error:")
            print("1. Check that your Reddit app credentials are correct")
            print("2. Make sure your app is configured as 'script' type")
            print("3. Verify the client ID and secret match your Reddit app")
            print("4. Try recreating the Reddit app at https://old.reddit.com/prefs/apps/")
        
        return False

if __name__ == "__main__":
    test_reddit_connection()