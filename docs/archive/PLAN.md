# AI Stock Assistant v2 — Complete Rebuild Plan

## Why Rebuild?

The current system works but is built on **outdated patterns** (LangGraph 0.0.55, basic HTTP agent calls, no streaming, no memory, no real portfolio management). The finance domain demands **real-time data, persistent memory, actionable intelligence, and actual portfolio tracking** — not just chat answers.

The goal: **a tool you actually use to make investment decisions**, not a chatbot that answers stock questions.

---

## Current State → Target State

| Area | Current (v1) | Target (v2) |
|------|-------------|-------------|
| Orchestration | LangGraph 0.0.55, basic router | LangGraph 0.3+, supervisor + swarm patterns |
| Agent Comms | Raw HTTP `/mcp` calls | A2A protocol + MCP tools |
| Frontend | React + manual fetch | Next.js + Vercel AI SDK, streaming UI |
| Memory | None (stateless) | Vector DB (Qdrant) + conversation memory |
| Streaming | None (wait for full response) | SSE token streaming, live agent status |
| Portfolio | None | Real portfolio tracking, P&L, alerts |
| Data Sources | Schwab, Finviz, Reddit, Tavily | + SEC EDGAR, Alpha Vantage, FRED, earnings calendars |
| Analysis | Basic price + news lookup | Technical analysis, DCF models, sector rotation |
| Auth | None | User accounts, saved watchlists, portfolio persistence |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                       │
│  Vercel AI SDK │ Streaming UI │ Portfolio Dashboard       │
│  Watchlists │ Alerts │ Charts (Lightweight Charts)        │
└──────────────────────┬──────────────────────────────────┘
                       │ SSE / WebSocket
┌──────────────────────▼──────────────────────────────────┐
│              FastAPI Gateway (API Layer)                  │
│  Auth │ Rate Limiting │ Session Management │ WebSocket    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│            LangGraph Supervisor (Orchestrator)            │
│                                                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │ Planner │  │ Executor │  │ Reviewer │  │ Memory  │  │
│  │  Agent  │  │  Agent   │  │  Agent   │  │ Manager │  │
│  └─────────┘  └──────────┘  └──────────┘  └─────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ A2A Protocol
┌──────────────────────▼──────────────────────────────────┐
│              Specialist Agent Pool                        │
│                                                          │
│  ┌────────────────┐  ┌─────────────────┐                │
│  │ Market Data    │  │ Fundamental     │                │
│  │ Agent          │  │ Analysis Agent  │                │
│  │ • Schwab API   │  │ • SEC EDGAR     │                │
│  │ • Alpha Vantage│  │ • Finviz        │                │
│  │ • Real-time    │  │ • Earnings      │                │
│  │   quotes       │  │ • DCF models    │                │
│  └────────────────┘  └─────────────────┘                │
│                                                          │
│  ┌────────────────┐  ┌─────────────────┐                │
│  │ Technical      │  │ Sentiment       │                │
│  │ Analysis Agent │  │ Agent           │                │
│  │ • Indicators   │  │ • Reddit/X      │                │
│  │ • Pattern      │  │ • News NLP      │                │
│  │   recognition  │  │ • Fear & Greed  │                │
│  │ • Support/     │  │ • Insider flow  │                │
│  │   Resistance   │  │ • Capitol trades│                │
│  └────────────────┘  └─────────────────┘                │
│                                                          │
│  ┌────────────────┐  ┌─────────────────┐                │
│  │ Portfolio      │  │ Macro           │                │
│  │ Agent          │  │ Agent           │                │
│  │ • Holdings     │  │ • FRED data     │                │
│  │ • P&L tracking │  │ • Sector ETFs   │                │
│  │ • Rebalancing  │  │ • Bond yields   │                │
│  │ • Tax lots     │  │ • Economic cal. │                │
│  └────────────────┘  └─────────────────┘                │
└─────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  Data & Memory Layer                      │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐ │
│  │ Qdrant   │  │ Postgres │  │ Redis                  │ │
│  │ (Vector) │  │ (State)  │  │ (Cache + Real-time)    │ │
│  │          │  │          │  │                        │ │
│  │ Research │  │ Users    │  │ Quote cache            │ │
│  │ memory   │  │ Portfol. │  │ Session state          │ │
│  │ Analysis │  │ Watchlist│  │ Rate limiting          │ │
│  │ history  │  │ Alerts   │  │ Agent result cache     │ │
│  └──────────┘  └──────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation (Week 1-2) ✅ COMPLETE

### 1.1 Project Restructure ✅
- Restructured into `apps/api` and `apps/web`
- Docker Compose and Turbo setup

### 1.2 Upgrade Core Dependencies ✅
- LangGraph > 0.3
- FastAPI, AsyncPG, Redis, Qdrant setup

### 1.3 Streaming Infrastructure ✅
- SSE streaming implemented in `apps/api/gateway/stream.py`

---

## Phase 2: Agent Rebuild (Week 2-4) ✅ COMPLETE

### 2.1 LangGraph Supervisor Pattern ✅
- Implemented `apps/api/agents/supervisor/graph.py`
- Planner, Router, and Synthesizer nodes operational

### 2.2 Specialist Agents (MCP Tools) ✅
- **Market Data**: Implemented (mock + Schwab client ready)
- **Fundamentals**: Finviz integration complete
- **Technical Analysis**: `ta` library integration complete
- **Sentiment**: Tavily & Reddit integration complete
- **Portfolio**: Postgres-backed agent operational
- **Macro**: FRED API integration complete

### 2.3 Agent-to-Agent (A2A) Protocol ✅
- Managed via Supervisor state and specific routing logic

---

## Phase 3: Memory & Intelligence (Week 3-5) 🚧 IN PROGRESS

### 3.1 Conversation Memory (Qdrant) ✅
- `apps/api/agents/memory` implemented
- Vector store integration using FastEmbed

### 3.2 Portfolio Tracking (Postgres) ✅
- Schema initialized
- Portfolio agent tools connected to DB

### 3.3 Smart Caching (Redis) ✅
- `apps/api/services/cache.py` with TTL map implemented

---

## Phase 4: Frontend Rebuild (Week 4-6) ⏳ NEXT

### 4.1 Next.js + Vercel AI SDK

**Chat Interface** — Streaming tokens with live agent status indicators
- Show which agent is currently working ("Analyzing technicals for AAPL...")
- Stream markdown as it arrives
- Inline charts when market data is returned

**Portfolio Dashboard**
- Holdings table with real-time P&L
- Allocation pie chart
- Performance vs benchmarks (S&P 500, QQQ)
- Dividend calendar
- Tax lot viewer

**Watchlist & Alerts**
- Configurable price alerts
- Insider trading alerts
- Earnings date reminders
- Custom conditions ("alert me if RSI > 70")

**Stock Research View**
- TradingView Lightweight Charts (candlestick, volume)
- Technical indicators overlay
- Analyst consensus panel
- News feed
- Insider activity timeline
- Congressional trading activity

### 4.2 Key UI Components

```
components/
├── chat/
│   ├── ChatInterface.tsx       # Main chat with streaming
│   ├── AgentStatusBar.tsx      # Shows active agents
│   ├── MessageBubble.tsx       # Rich message rendering
│   ├── ToolResultCard.tsx      # Structured tool output display
│   └── FollowUpChips.tsx       # Suggestion chips
├── portfolio/
│   ├── HoldingsTable.tsx       # Portfolio grid
│   ├── PerformanceChart.tsx    # P&L over time
│   ├── AllocationChart.tsx     # Sector/position allocation
│   └── DividendCalendar.tsx    # Upcoming dividends
├── research/
│   ├── StockChart.tsx          # TradingView charts
│   ├── TechnicalPanel.tsx      # Indicators display
│   ├── FundamentalsPanel.tsx   # Key metrics
│   ├── SentimentGauge.tsx      # Sentiment visualization
│   └── InsiderTimeline.tsx     # Insider trade timeline
└── common/
    ├── SymbolSearch.tsx         # Autocomplete stock search
    ├── WatchlistSidebar.tsx     # Quick-access watchlist
    └── AlertBadge.tsx           # Alert notifications
```

---

## Phase 5: Advanced Features (Week 6-8)

### 5.1 Investment Advisor 2.0

Not just "should I buy AAPL?" but a proper analysis framework:

```
User: "Should I add NVDA to my portfolio?"

Advisor Agent:
1. Checks current portfolio (Portfolio Agent)
   → You hold 0 shares, portfolio is 40% tech
2. Gets current price + technicals (Market Data + Technical Agent)
   → $890, RSI 68, above 200 DMA, near resistance at $910
3. Gets fundamentals (Fundamental Agent)
   → P/E 65, revenue growing 94% YoY, $61B cash
4. Gets sentiment (Sentiment Agent)
   → Reddit bullish (78%), 3 insider sells last month, fear/greed: 62
5. Gets macro context (Macro Agent)
   → Fed holding rates, semiconductor cycle peaking, China restrictions

Synthesized recommendation:
- Adding NVDA would increase tech concentration to 45% (above 40% threshold)
- Strong growth story but elevated valuation and high RSI suggest waiting
- Suggestion: Start 1/3 position now, add on pullback to $820 support
- Set alert: Price below $830 OR RSI below 40
```

### 5.2 Proactive Monitoring

Background agents that run on schedules:

- **Morning Brief**: Pre-market summary of watchlist, overnight news, futures
- **Earnings Watch**: Alerts before earnings for held/watched stocks
- **Insider Alert**: Flags unusual insider buying in watchlist
- **Portfolio Risk Check**: Daily concentration and drawdown monitoring
- **Macro Dashboard**: Weekly economic calendar and key data releases

### 5.3 Backtesting Agent (Future)

- "What if I had bought NVDA 6 months ago?"
- "Show me how DCA into QQQ would have performed over 2 years"
- Historical portfolio simulation

---

## Implementation Priority

| Priority | Feature | Impact | Effort |
|----------|---------|--------|--------|
| P0 | Streaming chat + LangGraph upgrade | Core UX | Medium |
| P0 | Supervisor + specialist agents | Core arch | High |
| P0 | Next.js frontend rebuild | Core UX | Medium |
| P1 | Portfolio tracking (DB + agent) | Key feature | High |
| P1 | Technical analysis agent | Analysis depth | Medium |
| P1 | Memory (Qdrant) | Intelligence | Medium |
| P1 | Watchlist & alerts | Daily usage | Medium |
| P2 | Macro agent (FRED) | Context | Low |
| P2 | A2A protocol | Architecture | Medium |
| P2 | Stock research view + charts | Visual appeal | Medium |
| P3 | Proactive monitoring | Power feature | High |
| P3 | Backtesting | Nice to have | High |

---

## Key Design Decisions

1. **LangGraph over CrewAI** — More control over financial workflows, better state management, production-proven
2. **Next.js over React SPA** — SSR for SEO, API routes, Vercel AI SDK integration, better DX
3. **Qdrant over Pinecone** — Open source, self-hostable, free for development, excellent performance
4. **Postgres over SQLite** — Real relational data (portfolios, holdings, alerts), production-ready
5. **Redis for caching** — Market data needs fast, TTL-aware caching; also handles session state
6. **Claude 4.5 Sonnet as default model** — Best balance of intelligence and speed for financial analysis; Haiku for routing
7. **MCP for tool exposure** — Standard protocol, future-proof, works with any LLM framework
8. **A2A for agent-to-agent** — Clean separation, discoverable agents, can scale to microservices later
9. **Turborepo monorepo** — Shared types between frontend and backend, unified build pipeline

---

## What This Enables You To Do

1. **"Show me my portfolio performance this month"** → Real P&L with benchmark comparison
2. **"Should I sell my TSLA position?"** → Multi-factor analysis considering YOUR portfolio context
3. **"Set an alert if AAPL drops below $180"** → Persistent alerts that notify you
4. **"What's the market sentiment for AI stocks?"** → Reddit, news, insider, and congress data aggregated
5. **"Run a technical analysis on NVDA"** → RSI, MACD, support/resistance, pattern recognition
6. **"What did we discuss about AMD last week?"** → Memory recall from past research sessions
7. **"Give me a morning briefing"** → Pre-market summary of your watchlist and market conditions
8. **"How exposed am I to a tech downturn?"** → Portfolio concentration and correlation analysis
