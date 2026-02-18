"""Pydantic models for API requests/responses and agent state."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────

class AgentType(str, Enum):
    MARKET_DATA = "market_data"
    FUNDAMENTALS = "fundamentals"
    TECHNICALS = "technicals"
    SENTIMENT = "sentiment"
    PORTFOLIO = "portfolio"
    MACRO = "macro"
    ADVISOR = "advisor"


class AlertCondition(str, Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE = "percent_change"
    RSI_ABOVE = "rsi_above"
    RSI_BELOW = "rsi_below"
    INSIDER_BUY = "insider_buy"
    INSIDER_SELL = "insider_sell"
    EARNINGS_UPCOMING = "earnings_upcoming"
    VOLUME_SPIKE = "volume_spike"


class TransactionAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"


# ── Chat / Streaming ──────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: str = "00000000-0000-0000-0000-000000000001"


class StreamEvent(BaseModel):
    """SSE event sent to frontend."""
    type: str  # token, agent_start, agent_end, tool_call, error, done
    content: Optional[str] = None
    agent: Optional[str] = None
    tool: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


# ── Supervisor / Agent State ──────────────────────────────

class AgentTask(BaseModel):
    """A single task in the supervisor's execution plan."""
    agent: AgentType
    query: str
    depends_on: list[str] = Field(default_factory=list)
    priority: int = 1


class ExecutionPlan(BaseModel):
    """Plan created by the supervisor before executing agents."""
    reasoning: str
    tasks: list[AgentTask]
    parallel_groups: list[list[AgentType]] = Field(default_factory=list)


class AgentResult(BaseModel):
    """Result from a specialist agent."""
    agent: AgentType
    content: str
    symbols: list[str] = Field(default_factory=list)
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


# ── Portfolio ─────────────────────────────────────────────

class HoldingCreate(BaseModel):
    symbol: str
    shares: Decimal
    avg_cost: Decimal
    acquired_at: Optional[datetime] = None
    sector: Optional[str] = None
    notes: Optional[str] = None


class HoldingResponse(BaseModel):
    id: str
    symbol: str
    shares: Decimal
    avg_cost: Decimal
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    gain_loss: Optional[Decimal] = None
    gain_loss_pct: Optional[float] = None
    day_change: Optional[Decimal] = None
    day_change_pct: Optional[Decimal] = None
    sector: Optional[str] = None
    acquired_at: Optional[datetime] = None


class TransactionCreate(BaseModel):
    symbol: str
    action: TransactionAction
    shares: Decimal
    price: Decimal
    fees: Decimal = Decimal("0")
    executed_at: datetime
    notes: Optional[str] = None


class PortfolioSummary(BaseModel):
    total_value: Decimal
    total_cost: Decimal
    total_gain_loss: Decimal
    total_gain_loss_pct: float
    day_change: Decimal
    day_change_pct: float
    holdings: list[HoldingResponse]
    allocation: dict[str, float]  # symbol -> % of portfolio


# ── Watchlist / Alerts ────────────────────────────────────

class WatchlistAdd(BaseModel):
    symbol: str
    target_price_low: Optional[Decimal] = None
    target_price_high: Optional[Decimal] = None
    notes: Optional[str] = None


class WatchlistResponse(BaseModel):
    id: str
    symbol: str
    target_price_low: Optional[Decimal] = None
    target_price_high: Optional[Decimal] = None
    notes: Optional[str] = None
    added_at: datetime


class AlertCreate(BaseModel):
    symbol: str
    condition_type: AlertCondition
    threshold: dict[str, Any]
    message: Optional[str] = None


class AlertResponse(BaseModel):
    id: str
    symbol: str
    condition_type: AlertCondition
    threshold: dict[str, Any]
    message: Optional[str] = None
    is_active: bool
    triggered_at: Optional[datetime] = None


# ── Market Data ───────────────────────────────────────────

class StockQuote(BaseModel):
    symbol: str
    price: float
    change: float
    percent_change: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    trade_time: Optional[str] = None


class PriceCandle(BaseModel):
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class TechnicalIndicators(BaseModel):
    symbol: str
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    atr_14: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None
    trend: Optional[str] = None  # bullish, bearish, neutral
