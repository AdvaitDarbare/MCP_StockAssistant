#!/usr/bin/env python3
"""
Schwab API Authentication Setup

This script helps you authenticate with the Schwab API and create the required token.
Run this script once to set up authentication before using the Schwab client.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from schwab.auth import easy_client

def setup_schwab_auth():
    """Set up Schwab API authentication"""
    
    # Load environment variables
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    
    # Check if credentials are available
    client_id = os.getenv("SCHWAB_CLIENT_ID")
    client_secret = os.getenv("SCHWAB_CLIENT_SECRET")
    redirect_uri = os.getenv("SCHWAB_REDIRECT_URI")
    
    if not all([client_id, client_secret, redirect_uri]):
        print("❌ Missing Schwab API credentials in .env file")
        print("Required variables:")
        print("  - SCHWAB_CLIENT_ID")
        print("  - SCHWAB_CLIENT_SECRET") 
        print("  - SCHWAB_REDIRECT_URI")
        return False
    
    token_path = "/tmp/token.json"
    
    print("🔐 Setting up Schwab API authentication...")
    print(f"Client ID: {client_id}")
    print(f"Redirect URI: {redirect_uri}")
    print(f"Token will be saved to: {token_path}")
    print()
    
    try:
        # This will open a browser for authentication
        client = easy_client(
            api_key=client_id,
            app_secret=client_secret,
            callback_url=redirect_uri,
            token_path=token_path,
            enforce_enums=False
        )
        
        print("✅ Schwab authentication successful!")
        print(f"✅ Token saved to {token_path}")
        print("✅ You can now use the Schwab API client")
        
        # Test the connection
        print("\n🧪 Testing API connection...")
        resp = client.get_quotes("AAPL")
        
        if resp.status_code == 200:
            data = resp.json()
            if "AAPL" in data:
                price = data["AAPL"]["quote"]["lastPrice"]
                print(f"✅ Test successful! AAPL price: ${price}")
            else:
                print("⚠️ Test returned unexpected data format")
        else:
            print(f"⚠️ Test failed with status code: {resp.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure your Schwab app is configured correctly")
        print("2. Check that your redirect URI matches exactly")
        print("3. Ensure your app has the correct permissions")
        return False

if __name__ == "__main__":
    print("🚀 Schwab API Authentication Setup")
    print("=" * 40)
    
    success = setup_schwab_auth()
    
    if success:
        print("\n🎉 Setup complete! You can now use the stock assistant.")
    else:
        print("\n❌ Setup failed. Please check your configuration.")