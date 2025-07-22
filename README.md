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

## 🧠 AI-Powered Query Understanding

The assistant uses Claude AI to intelligently parse natural language queries and determine:

- **Query Type**: Single quote, multiple quotes, or historical analysis
- **Stock Symbols**: Extracts tickers from company names or symbols
- **Time Periods**: Understands phrases like "past month", "this year", "6 months"
- **Intent Recognition**: Distinguishes between price checks, comparisons, and performance analysis

### Smart Query Examples:
```
✅ "What's Apple doing?" → Single quote for AAPL
✅ "Compare big tech stocks" → Multi-quote for AAPL, GOOGL, MSFT, etc.
✅ "How did GameStop perform last year?" → Price history for GME
✅ "PLTR vs SNOW performance" → Multi-quote comparison
✅ "Calculate SOFI percentage change over 3 months" → Historical analysis
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

## 📊 API Coverage

### Implemented (3/9 endpoints):
- ✅ Single Stock Quotes
- ✅ Multi-Stock Quotes  
- ✅ Price History

### Available for Future Implementation:
- ⏳ Option Chains (calls/puts with Greeks)
- ⏳ Market Movers (top gainers/losers)
- ⏳ Market Hours (trading schedules)
- ⏳ Option Expiration Dates
- ⏳ Instrument Search
- ⏳ CUSIP Lookup

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

---

**Built with**: Python, FastAPI, Claude AI, Charles Schwab API, asyncio

**Status**: ✅ Production Ready - Core functionality implemented and tested