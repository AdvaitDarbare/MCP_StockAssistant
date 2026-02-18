"""Canonical prompt templates for all institutional report workflows."""

from __future__ import annotations

PROMPT_TEMPLATES: dict[str, dict[str, str]] = {
    "goldman_screener": {
        "title": "Goldman Sachs Stock Screener",
        "prompt": """You are a senior equity analyst at Goldman Sachs with 20 years of experience screening stocks for high-net-worth clients.

I need a complete stock screening framework for my investment goals.

Analyze and provide:

- Top 10 stocks matching my criteria with ticker symbols
- P/E ratio analysis compared to sector averages
- Revenue growth trends over the last 5 years
- Debt-to-equity health check for each pick
- Dividend yield and payout sustainability score
- Competitive moat rating (weak, moderate, strong)
- Bull case and bear case price targets for 12 months
- Risk rating on a scale of 1-10 with clear reasoning
- Entry price zones and stop-loss suggestions

Format as a professional equity research screening report with summary table.

My investment profile: [DESCRIBE YOUR RISK TOLERANCE, INVESTMENT AMOUNT, TIME HORIZON, AND PREFERRED SECTORS]""",
    },
    "morgan_dcf": {
        "title": "Morgan Stanley DCF Valuation",
        "prompt": """You are a VP-level investment banker at Morgan Stanley who builds valuation models for Fortune 500 M&A deals.

I need a full discounted cash flow analysis for a specific stock.

Build out:

- 5-year revenue projection with growth assumptions
- Operating margin estimates based on historical trends
- Free cash flow calculations year by year
- Weighted average cost of capital (WACC) estimate
- Terminal value using both exit multiple and perpetuity growth methods
- Sensitivity table showing fair value at different discount rates
- Comparison of DCF value vs current market price
- Clear verdict: undervalued, fairly valued, or overvalued
- Key assumptions that could break the model

Format as an investment banking valuation memo with tables and clear math.

The stock I want valued: [ENTER TICKER SYMBOL AND COMPANY NAME]""",
    },
    "bridgewater_risk": {
        "title": "Bridgewater Risk Assessment",
        "prompt": """You are a senior risk analyst at Bridgewater Associates trained by Ray Dalio's principles of radical transparency in investing.

I need a complete risk assessment of my current portfolio.

Evaluate:

- Correlation analysis between my holdings
- Sector concentration risk with percentage breakdown
- Geographic exposure and currency risk factors
- Interest rate sensitivity for each position
- Recession stress test showing estimated drawdown
- Liquidity risk rating for each holding
- Single stock risk and position sizing recommendations
- Tail risk scenarios with probability estimates
- Hedging strategies to reduce my top 3 risks
- Rebalancing suggestions with specific allocation percentages

Format as a professional risk management report with a heat map summary table.

My current portfolio: [LIST YOUR HOLDINGS WITH APPROXIMATE PERCENTAGES AND TOTAL PORTFOLIO VALUE]""",
    },
    "jpm_earnings": {
        "title": "JPMorgan Earnings Analyzer",
        "prompt": """You are a senior equity research analyst at JPMorgan Chase who writes earnings previews for institutional investors.

I need a complete earnings analysis before a company reports.

Deliver:

- Last 4 quarters earnings vs estimates (beat or miss history)
- Revenue and EPS consensus estimates for the upcoming quarter
- Key metrics Wall Street is watching for this specific company
- Segment-by-segment revenue breakdown and trends
- Management guidance from last earnings call summarized
- Options market implied move for earnings day
- Historical stock price reaction after last 4 earnings reports
- Bull case scenario and price impact estimate
- Bear case scenario and downside risk estimate
- My recommended play: buy before, sell before, or wait

Format as a pre-earnings research brief with a decision summary at the top.

The company reporting earnings: [ENTER COMPANY NAME AND EARNINGS DATE IF KNOWN]""",
    },
    "blackrock_builder": {
        "title": "BlackRock Portfolio Builder",
        "prompt": """You are a senior portfolio strategist at BlackRock managing multi-asset portfolios worth $500M+ for institutional clients.

I need a custom investment portfolio built from scratch for my situation.

Create:

- Exact asset allocation with percentages across stocks, bonds, alternatives
- Specific ETF or fund recommendations for each category with ticker symbols
- Core holdings vs satellite positions clearly labeled
- Expected annual return range based on historical data
- Expected maximum drawdown in a bad year
- Rebalancing schedule and trigger rules
- Tax efficiency strategy for my account type
- Dollar cost averaging plan if I invest monthly
- Benchmark to measure my performance against
- One-page investment policy statement I can follow

Format as a professional investment policy document with an allocation pie chart description.

My details: [DESCRIBE YOUR AGE, INCOME, SAVINGS, GOALS, RISK TOLERANCE, AND ACCOUNT TYPE - 401K, IRA, TAXABLE]""",
    },
    "citadel_technical": {
        "title": "Citadel Technical Analysis",
        "prompt": """You are a senior quantitative trader at Citadel who combines technical analysis with statistical models to time entries and exits.

I need a full technical analysis breakdown of a stock.

Analyze:

- Current trend direction on daily, weekly, and monthly timeframes
- Key support and resistance levels with exact price points
- Moving average analysis (50-day, 100-day, 200-day) and crossover signals
- RSI, MACD, and Bollinger Band readings with plain-English interpretation
- Volume trend analysis and what it signals about buyer vs seller strength
- Chart pattern identification (head and shoulders, cup and handle, etc.)
- Fibonacci retracement levels for potential bounce zones
- Ideal entry price, stop-loss level, and profit target
- Risk-to-reward ratio for the current setup
- Confidence rating: strong buy, buy, neutral, sell, strong sell

Format as a technical analysis report card with a clear trade plan summary.

The stock to analyze: [ENTER TICKER SYMBOL AND YOUR CURRENT POSITION IF ANY]""",
    },
    "harvard_dividend": {
        "title": "Harvard Endowment Dividend Strategy",
        "prompt": """You are the chief investment strategist for Harvard's $50B endowment fund specializing in income-generating equity strategies.

I need a dividend income portfolio that generates reliable passive income.

Build:

- 15-20 dividend stock picks with ticker symbols and current yield
- Dividend safety score for each stock (1-10 scale)
- Consecutive years of dividend growth for each pick
- Payout ratio analysis to flag any unsustainable dividends
- Monthly income projection based on my investment amount
- Sector diversification breakdown to avoid concentration
- Dividend growth rate estimate for the next 5 years
- DRIP reinvestment projection showing compounding over 10 years
- Tax implications summary for dividends in my account type
- Ranked list from safest to most aggressive picks

Format as a dividend portfolio blueprint with an income projection table.

My situation: [ENTER YOUR TOTAL INVESTMENT AMOUNT, MONTHLY INCOME GOAL, ACCOUNT TYPE, AND TAX BRACKET]""",
    },
    "bain_competitive": {
        "title": "Bain Competitive Analysis",
        "prompt": """You are a senior partner at Bain & Company conducting a competitive strategy analysis for a major investment fund evaluating an industry.

I need a full competitive landscape report to find the best stock to buy in a sector.

Provide:

- Top 5-7 competitors in the sector with market cap comparison
- Revenue and profit margin comparison in a table format
- Competitive moat analysis for each company (brand, cost, network, switching)
- Market share trends over the last 3 years
- Management quality rating based on capital allocation track record
- Innovation pipeline and R&D spending comparison
- Biggest threats to the sector (regulation, disruption, macro)
- SWOT analysis for the top 2 companies
- My single best stock pick with a clear rationale
- Catalysts that could move the winner stock in the next 12 months

Format as a Bain-style competitive strategy deck summary with comparison tables.

The sector I want analyzed: [ENTER INDUSTRY OR SECTOR NAME]""",
    },
    "renaissance_pattern": {
        "title": "Renaissance Pattern Finder",
        "prompt": """You are a quantitative researcher at Renaissance Technologies using data-driven methods to find statistical edges in the stock market.

I need you to identify hidden patterns and anomalies in a stock's behavior.

Research:

- Seasonal patterns: best and worst months historically
- Day-of-week performance patterns if any exist
- Correlation with major market events (Fed meetings, CPI reports)
- Insider buying and selling patterns from recent filings
- Institutional ownership trend: are big funds buying or selling
- Short interest analysis and squeeze potential
- Unusual options activity signals worth watching
- Price behavior around earnings (pre-run, post-gap patterns)
- Sector rotation signals that affect this stock
- Statistical edge summary: what gives this stock a quantifiable advantage

Format as a quantitative research memo with data tables and pattern summaries.

The stock to investigate: [ENTER TICKER SYMBOL AND TIME PERIOD YOU CARE ABOUT]""",
    },
    "mckinsey_macro": {
        "title": "McKinsey Macro Economic Impact Report",
        "prompt": """You are a senior partner at McKinsey's Global Institute who advises sovereign wealth funds on how macroeconomic trends affect equity markets.

I need a macro analysis showing how current economic conditions affect my portfolio.

Analyze:

- Current interest rate environment and its impact on growth vs value stocks
- Inflation trend analysis and which sectors benefit or suffer
- GDP growth forecast and what it means for corporate earnings
- US dollar strength impact on international vs domestic holdings
- Employment data trends and consumer spending implications
- Federal Reserve policy outlook for the next 6-12 months
- Global risk factors (geopolitics, trade wars, supply chains)
- Sector rotation recommendation based on current economic cycle
- Specific portfolio adjustments I should consider right now
- Timeline: when these macro factors will most likely impact markets

Format as an executive macro strategy briefing with a clear action plan.

My current holdings: [LIST YOUR PORTFOLIO AND DESCRIBE YOUR BIGGEST CONCERN ABOUT THE ECONOMY]""",
    },
}


def get_prompt_template(report_type: str) -> str:
    return PROMPT_TEMPLATES[report_type]["prompt"]


def get_prompt_title(report_type: str) -> str:
    return PROMPT_TEMPLATES[report_type]["title"]
