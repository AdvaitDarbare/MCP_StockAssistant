# AI Stock Assistant

An intelligent stock market assistant powered by Claude AI and the Charles Schwab Market Data API. The assistant can understand natural language queries and provide real-time stock quotes, multi-stock comparisons, and historical performance analysis.

## 🚀 Features

### ✅ Currently Implemented

#### **1. Single Stock Quotes**
- **API Endpoint**: `/{symbol_id}/quotes`
- **Usage**: Get real-time quote data for any stock
- **Example Queries**:
  - "What's AAPL price?"
  - "Show me Tesla stock quote"
  - "Current price of NVDA"

**Sample Response**:
```
📈 AAPL Quote:
Price: $212.48 (+10.98, +5.45%)
High: $216.23, Low: $198.96, Open: $201.62
52W Range: $164.08 - $237.23
Trade Time: 2025-01-22T21:00:00
```

#### **2. Multi-Stock Comparisons**
- **API Endpoint**: `/quotes`
- **Usage**: Compare multiple stocks side-by-side
- **Example Queries**:
  - "Compare AAPL, TSLA, MSFT"
  - "Show me Apple vs Tesla vs Google"
  - "UBER, LYFT, and DASH comparison"

**Sample Response**:
```
📊 Stock Comparison:

🟢 AAPL: $212.48 (+10.98, +5.45%) Vol: 45,123,456
🔴 TSLA: $354.21 (-12.34, -3.37%) Vol: 89,765,432
🟢 MSFT: $445.67 (+8.90, +2.04%) Vol: 23,456,789
```

#### **3. Historical Performance Analysis**
- **API Endpoint**: `/pricehistory`
- **Usage**: Analyze stock performance over time
- **Supported Periods**: 1 month, 3 months, 6 months, 1 year, YTD
- **Example Queries**:
  - "Calculate the percentage change over the past month for AAPL"
  - "How has Tesla performed this year?"
  - "SOFI price history last 6 months"
  - "AMD trend since January"

**Sample Response**:
```
📈 AAPL - 1 month(s) Performance:
🟢 Period Change: +10.98 (+5.45%)
Period High: $216.23
Period Low: $198.96
Current: $212.48
Data Points: 20 trading days
```

#### **4. Market Movers**
- **API Endpoint**: `/movers/{index}`
- **Usage**: Get top 10 movers for major indices with advanced filtering
- **Supported Indices**: 
  - **$SPX** (S&P 500), **$DJI** (Dow Jones), **$COMPX** (NASDAQ Composite)
  - **NYSE**, **NASDAQ**, **OTCBB** (exchanges)
  - **INDEX_ALL**, **EQUITY_ALL**, **OPTION_ALL**, **OPTION_PUT**, **OPTION_CALL**
- **Sort Options**:
  - **PERCENT_CHANGE_UP** - Top gainers (default)
  - **PERCENT_CHANGE_DOWN** - Top losers  
  - **VOLUME** - Most active by volume
  - **TRADES** - Most active by trade count
- **Frequency Thresholds**: Filter by minimum change percentage
  - **0** - Show all moves (no minimum)
  - **1** - Show moves ≥ 1% (default)
  - **5** - Show moves ≥ 5% (moderate moves)
  - **10** - Show moves ≥ 10% (major moves)
  - **30** - Show moves ≥ 30% (substantial moves)
  - **60** - Show moves ≥ 60% (extreme moves)
- **Example Queries**:
  - "Show me top gainers in the S&P 500" → Biggest % winners
  - "NASDAQ most active by volume" → Highest trading volume
  - "Show me 5% movers" → Stocks with ≥5% change
  - "Major moves today" → Stocks with ≥10% change
  - "All NASDAQ movers" → All moves regardless of size

**Sample Responses**:
```
🚀 Top Gainers ($SPX):
1. 🟢 TSLA: $332.11 (+3.62) Vol: 77,130,475
2. 🟢 AAPL: $214.40 (+1.92) Vol: 46,348,818

📈 Most Active by Volume ($SPX):
1. 🟢 NVDA: $167.03 (-4.35) Vol: 192,489,403  
2. 🟢 WBD: $12.85 (+0.05) Vol: 89,947,116

⚡ Most Active by Trades ($DJI):
1. 🔴 NVDA: $167.03 (-4.35) Vol: 1,946,802 trades
2. 🟢 TSLA: $332.11 (+3.62) Vol: 1,065,551 trades
```

#### **5. Market Hours**
- **API Endpoints**: `/markets` (bulk) and `/markets/{market_id}` (single)
- **Usage**: Get current trading schedules and market status with date support
- **Supported Markets**: 
  - **equity** - Stock market (pre-market, regular, post-market)
  - **option** - Options trading (equity options, index options)
  - **bond** - Bond markets
  - **future** - Futures markets  
  - **forex** - Foreign exchange markets
- **Features**:
  - **Single Market**: "What are equity market hours?"
  - **Multiple Markets**: "Show me stock and options trading hours"
  - **Date Specification**: "What are market hours for 2025-07-25?"
  - **Live Status**: Shows if markets are currently open/closed
- **Example Queries**:
  - "What are equity market hours?" → Stock market schedule
  - "Show me options trading hours" → Options market schedule  
  - "What are bond market hours for tomorrow?" → Future date query
  - "Are forex markets open now?" → Live status check

**Sample Response**:
```
🕐 Market Hours:

**Equity Market:**
  Equity: 🟢 OPEN
    Pre Market: 07:00 - 09:30
    Regular Market: 09:30 - 16:00
    Post Market: 16:00 - 20:00

**Option Market:**
  Equity Option: 🟢 OPEN
    Regular Market: 09:30 - 16:00

  Index Option: 🟢 OPEN
    Regular Market: 09:30 - 16:15
```

## 🧠 AI-Powered Query Understanding

The assistant uses Claude AI to intelligently parse natural language queries and determine:

- **Query Type**: Single quote, multiple quotes, or historical analysis
- **Stock Symbols**: Extracts tickers from company names or symbols
- **Time Periods**: Understands phrases like "past month", "this year", "6 months"
- **Intent Recognition**: Distinguishes between price checks, comparisons, and performance analysis

## 🛠️ Available Tools

The stock agent has access to **5 specialized tools**, each corresponding to a Schwab API endpoint:

### **Current Tools (5/9 implemented)**

| Tool | Function | API Endpoint | Purpose |
|------|----------|--------------|---------|
| **Single Quote** | `get_stock_data(symbol)` | `/quotes/{symbol}` | Get real-time quote for one stock |
| **Multi Quote** | `get_multiple_quotes(symbols)` | `/quotes` | Compare multiple stocks side-by-side |
| **Price History** | `get_price_history(symbol, params)` | `/pricehistory` | Analyze historical performance |
| **Market Movers** | `get_market_movers(index, sort, frequency)` | `/movers/{index}` | Find top gainers/losers/volume leaders |
| **Market Hours** | `get_market_hours(markets, date)` | `/markets` | Get trading schedules and market status |

### **How Tool Selection Works**

1. **Query Analysis**: Claude AI analyzes the user's natural language input
2. **Intent Classification**: Determines query type (`single_quote`, `multiple_quotes`, `price_history`, `market_movers`, `market_hours`)
3. **Tool Routing**: Routes to the appropriate tool based on classified intent
4. **Parameter Extraction**: Extracts symbols, time periods, indices, etc.
5. **API Call**: Executes the selected tool with extracted parameters

### **Future Tools (4 available for implementation)**

| Tool | Function | API Endpoint | Purpose |
|------|----------|--------------|---------|
| **Option Chains** | `get_option_chains(symbol, params)` | `/chains` | Get options data with Greeks |
| **Option Expirations** | `get_option_expirations(symbol)` | `/expirationchain` | Get available expiration dates |
| **Instrument Search** | `search_instruments(query, type)` | `/instruments` | Search for securities by name/symbol |
| **CUSIP Lookup** | `get_instruments_cusip(cusip)` | `/instruments/{cusip}` | Convert CUSIP to symbol/details |

### Smart Query Examples:
```
✅ "What's Apple doing?" → Single quote for AAPL
✅ "Compare big tech stocks" → Multi-quote for AAPL, GOOGL, MSFT, etc.
✅ "How did GameStop perform last year?" → Price history for GME
✅ "PLTR vs SNOW performance" → Multi-quote comparison
✅ "Calculate SOFI percentage change over 3 months" → Historical analysis
✅ "Show me top gainers today" → Market movers for S&P 500
✅ "NASDAQ most active by volume" → Volume leaders in NASDAQ
✅ "Show me 5% movers" → Market movers with ≥5% change
✅ "Major moves in NASDAQ today" → Market movers with ≥10% change
✅ "What are equity market hours?" → Stock market schedule
✅ "Show me options trading hours for tomorrow" → Options schedule with date
✅ "Are forex markets open now?" → Live market status
```

## 🏗️ Architecture

### Backend Structure
```
backend/
├── app/
│   ├── agents/
│   │   └── stock_agent.py          # Main MCP-compliant agent
│   └── services/
│       └── schwab_client.py        # Schwab API client
├── requirements.txt
└── .env                           # API credentials
```

### Key Components

#### **1. Stock Agent** (`stock_agent.py`)
- **MCP-compliant server** for Claude integration
- **Intelligent query analysis** using Claude Haiku
- **Response formatting** with emoji indicators
- **Error handling** with helpful suggestions

#### **2. Schwab Client** (`schwab_client.py`)
- **Primary API integration** with Charles Schwab
- **Fallback API support** for development/reliability
- **Data normalization** across different API sources
- **Robust error handling**

#### **3. Query Processing Flow**
1. **Natural Language Input** → Claude analyzes query intent
2. **Symbol Extraction** → Identifies stock tickers and companies
3. **API Route Selection** → Chooses appropriate Schwab endpoint
4. **Data Retrieval** → Fetches real-time or historical data
5. **Response Formatting** → Presents data in user-friendly format

## 📊 Tool Coverage

### **Implemented Tools (5/9 total)**:
✅ **Single Quote Tool** - Real-time stock quotes  
✅ **Multi Quote Tool** - Multi-stock comparisons  
✅ **Price History Tool** - Historical performance analysis  
✅ **Market Movers Tool** - Top gainers/losers with advanced filtering  
✅ **Market Hours Tool** - Trading schedules across all markets  

### **Available for Implementation (4/9 remaining)**:
⏳ **Option Chains Tool** - Options data with Greeks (delta, gamma, theta, vega)  
⏳ **Option Expirations Tool** - Available expiration dates for options  
⏳ **Instrument Search Tool** - Search securities by name or description  
⏳ **CUSIP Lookup Tool** - Convert CUSIP identifiers to symbols

## 🛠️ Technical Features

### **Robust Fallback System**
- Primary: Charles Schwab Market Data API
- Fallback: Financial Modeling Prep API (free tier)
- Graceful degradation when APIs are unavailable

### **Smart Parameter Handling**
- **Enum Support**: Handles Schwab's strict API requirements
- **Period Mapping**: Converts natural language to API parameters
- **Flexible Symbols**: Supports any ticker (AAPL to obscure penny stocks)

### **Performance Optimizations**
- **Bulk API calls** for multi-stock queries
- **Concise LLM prompts** for faster processing
- **Efficient data parsing** and formatting

## 🚦 Getting Started

### Prerequisites
- Python 3.8+
- Charles Schwab Developer Account
- Claude API Key

### Setup
1. **Clone the repository**
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Configure environment variables**:
   ```bash
   SCHWAB_CLIENT_ID=your_client_id
   SCHWAB_CLIENT_SECRET=your_client_secret
   SCHWAB_REDIRECT_URI=your_redirect_uri
   CLAUDE_API_KEY=your_claude_key
   ```
4. **Run the agent**: Stock agent runs as FastAPI server on `/mcp` endpoint

### Usage
Send POST requests to `/mcp` with natural language stock queries:

```json
{
  "input": "Calculate the percentage change over the past month for AAPL"
}
```

## 📈 Supported Assets

- **Stocks**: All US equities (NYSE, NASDAQ, OTC)
- **ETFs**: Exchange-traded funds
- **Indices**: $SPX, $DJI, $COMPX, etc.
- **Mutual Funds**: Traditional mutual funds
- **International**: Basic support for major international stocks

## 🎯 Use Cases

### **Portfolio Management**
- Compare holdings performance
- Track individual stock changes
- Analyze historical trends

### **Investment Research**
- Quick price checks
- Multi-timeframe analysis  
- Performance comparisons

### **Market Monitoring**
- Real-time quote updates
- Historical performance tracking
- Trend identification
- Top gainers/losers tracking
- Trading schedule awareness

---

**Built with**: Python, LangGraph, MCP, FastAPI, Claude AI, Charles Schwab API, asyncio

