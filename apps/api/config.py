"""Central configuration for AI Stock Assistant v2."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")

    # Legacy single-app Schwab config (kept for backward compatibility)
    SCHWAB_CLIENT_ID: str = os.getenv("SCHWAB_CLIENT_ID", "")
    SCHWAB_CLIENT_SECRET: str = os.getenv("SCHWAB_CLIENT_SECRET", "")
    SCHWAB_REDIRECT_URI: str = os.getenv("SCHWAB_REDIRECT_URI", "https://127.0.0.1:8182")
    SCHWAB_TOKEN_PATH: str = os.getenv("SCHWAB_TOKEN_PATH", "/tmp/token.json")

    # Dual-app Schwab config
    SCHWAB_MARKET_CLIENT_ID: str = os.getenv("SCHWAB_MARKET_CLIENT_ID", os.getenv("SCHWAB_CLIENT_ID", ""))
    SCHWAB_MARKET_CLIENT_SECRET: str = os.getenv("SCHWAB_MARKET_CLIENT_SECRET", os.getenv("SCHWAB_CLIENT_SECRET", ""))
    SCHWAB_MARKET_TOKEN_PATH: str = os.getenv("SCHWAB_MARKET_TOKEN_PATH", os.getenv("SCHWAB_TOKEN_PATH", "/tmp/token.json"))

    SCHWAB_TRADER_CLIENT_ID: str = os.getenv("SCHWAB_TRADER_CLIENT_ID", os.getenv("SCHWAB_CLIENT_ID", ""))
    SCHWAB_TRADER_CLIENT_SECRET: str = os.getenv("SCHWAB_TRADER_CLIENT_SECRET", os.getenv("SCHWAB_CLIENT_SECRET", ""))
    SCHWAB_TRADER_TOKEN_PATH: str = os.getenv("SCHWAB_TRADER_TOKEN_PATH", "/tmp/schwab_trader_token.json")
    SCHWAB_HTTP_TIMEOUT_SECONDS: float = float(os.getenv("SCHWAB_HTTP_TIMEOUT_SECONDS", "20"))
    SCHWAB_MAX_RETRIES: int = int(os.getenv("SCHWAB_MAX_RETRIES", "3"))
    SCHWAB_RETRY_BACKOFF_SECONDS: float = float(os.getenv("SCHWAB_RETRY_BACKOFF_SECONDS", "0.5"))
    SCHWAB_OBSERVABILITY_BUFFER_SIZE: int = int(os.getenv("SCHWAB_OBSERVABILITY_BUFFER_SIZE", "200"))

    ENABLE_LIVE_TRADING: bool = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
    REQUIRE_HITL_FOR_TRADES: bool = os.getenv("REQUIRE_HITL_FOR_TRADES", "true").lower() == "true"
    HITL_SHARED_SECRET: str = os.getenv("HITL_SHARED_SECRET", "")

    # MLflow observability
    MLFLOW_ENABLED: bool = os.getenv("MLFLOW_ENABLED", "true").lower() == "true"
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    MLFLOW_EXPERIMENT_NAME: str = os.getenv("MLFLOW_EXPERIMENT_NAME", "ai-stock-assistant-reports")
    MLFLOW_CHAT_EXPERIMENT_NAME: str = os.getenv("MLFLOW_CHAT_EXPERIMENT_NAME", "ai-stock-assistant-chat")

    MARKET_DATA_PROVIDER: str = os.getenv("MARKET_DATA_PROVIDER", "auto").lower()

    ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "")
    ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
    ALPACA_PAPER: bool = os.getenv("ALPACA_PAPER", "true").lower() == "true"
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "")
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://stockapp:stockapp_dev@localhost:5432/stock_assistant"
    )
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC", "postgresql://stockapp:stockapp_dev@localhost:5432/stock_assistant"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Qdrant
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))

    # LangSmith
    LANGSMITH_TRACING: str = os.getenv("LANGSMITH_TRACING", "true")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "StockAssistant-v2")

    # Models
    SUPERVISOR_MODEL: str = "claude-3-5-sonnet-latest"
    ROUTING_MODEL: str = "claude-3-5-sonnet-latest"
    ANALYSIS_MODEL: str = "claude-3-haiku-20240307"
    DEFAULT_MODEL: str = "claude-3-haiku-20240307"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    ENABLE_EMBEDDED_REPORT_LAB: bool = os.getenv("ENABLE_EMBEDDED_REPORT_LAB", "true").lower() == "true"
    # CORS — comma-separated list of allowed origins; defaults to local dev origins.
    # In production, set ALLOWED_ORIGINS=https://yourdomain.com
    ALLOWED_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001").split(",")
        if o.strip()
    ]

    # Default user for dev
    DEV_USER_ID: str = "00000000-0000-0000-0000-000000000001"
    DEV_PORTFOLIO_ID: str = "00000000-0000-0000-0000-000000000002"


settings = Settings()
