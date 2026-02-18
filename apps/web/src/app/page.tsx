'use client';

import { useEffect, useRef } from 'react';
import { useSupervisorChat } from '@/hooks/use-supervisor-chat';
import { ChatMessage } from '@/components/chat-message';
import { ArrowUp, Loader2, Plug, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import Link from 'next/link';

const STARTER_QUERIES = [
    'Why did RIVN rise then drop in the last 3 days?',
    'Compare AAPL vs MSFT fundamentals',
    'Run a pre-earnings brief for NVDA',
    'What macro risks matter most this month?',
];

const REPORT_TEMPLATES = [
    {
        name: 'Citadel Technical Analysis',
        prompt: 'You are a senior quantitative trader at Citadel who combines technical analysis with statistical models to time entries and exits. I need a full technical analysis breakdown of a stock. Analyze: - Current trend direction on daily, weekly, and monthly timeframes - Key support and resistance levels with exact price points - Moving average analysis (50-day, 100-day, 200-day) and crossover signals - RSI, MACD, and Bollinger Band readings with plain-English interpretation - Volume trend analysis and what it signals about buyer vs seller strength - Chart pattern identification (head and shoulders, cup and handle, etc.) - Fibonacci retracement levels for potential bounce zones - Ideal entry price, stop-loss level, and profit target - Risk-to-reward ratio for the current setup - Confidence rating: strong buy, buy, neutral, sell, strong sell Format as a technical analysis report card with a clear trade plan summary. The stock to analyze: [PLTR]'
    },
    {
        name: 'Goldman Sachs Stock Screener',
        prompt: 'You are a Goldman Sachs equity research analyst running a systematic stock screening process. Screen for high-quality growth stocks with the following criteria: - Market cap > $1B - Revenue growth > 15% YoY - Positive earnings growth trajectory - Strong balance sheet (debt-to-equity < 0.5) - High return on equity (ROE > 15%) - Institutional ownership > 60% - Analyst coverage with buy ratings - Recent insider buying activity - Technical momentum (stock above 50-day MA) - Sector diversification across growth industries Provide top 10 recommendations with brief rationale for each, including key metrics, growth drivers, and risk factors. Format as a Goldman Sachs equity research note.'
    },
    {
        name: 'Morgan Stanley DCF Valuation',
        prompt: 'You are a Morgan Stanley equity research analyst conducting a comprehensive DCF valuation analysis. Perform a detailed discounted cash flow model for the specified company including: - 5-year revenue projections with growth assumptions - Operating margin analysis and expansion potential - Free cash flow forecasting with working capital impacts - Terminal value calculation using perpetual growth method - Weighted average cost of capital (WACC) determination - Sensitivity analysis across different growth and discount rate scenarios - Comparable company trading multiples for validation - Sum-of-the-parts analysis if applicable - Bull, base, and bear case price targets - Investment recommendation with detailed rationale Format as a Morgan Stanley research report with executive summary. The company to analyze: [AAPL]'
    },
    {
        name: 'Bridgewater Risk Assessment',
        prompt: 'You are a Bridgewater Associates portfolio manager conducting a comprehensive risk assessment. Analyze the portfolio risk profile including: - Asset allocation breakdown and concentration risk - Correlation analysis between holdings during stress periods - Value-at-Risk (VaR) calculations at 95% and 99% confidence levels - Maximum drawdown scenarios and historical stress testing - Factor exposure analysis (growth, value, momentum, quality) - Geographic and sector concentration risks - Liquidity risk assessment for each position - Currency exposure and hedging considerations - Tail risk scenarios (market crash, recession, inflation spike) - Risk-adjusted return metrics (Sharpe ratio, Sortino ratio) - Recommended portfolio adjustments to optimize risk-return profile Format as a Bridgewater risk management report with actionable recommendations.'
    },
    {
        name: 'JPMorgan Earnings Analysis',
        prompt: 'You are a JPMorgan equity research analyst preparing a comprehensive pre-earnings analysis. Conduct detailed earnings preview including: - Consensus estimates vs your proprietary forecasts - Key metrics to watch (revenue, margins, guidance) - Segment-by-segment performance expectations - Management commentary themes and guidance updates - Competitive positioning and market share trends - Margin pressure points and cost management initiatives - Capital allocation priorities (buybacks, dividends, capex) - Regulatory or macro headwinds/tailwinds - Options flow and institutional positioning ahead of earnings - Post-earnings price target scenarios based on different outcomes - Trading recommendations for earnings play (long, short, straddle) Format as JPMorgan earnings preview with clear investment thesis. The company to analyze: [NVDA]'
    },
    {
        name: 'BlackRock Portfolio Builder',
        prompt: 'You are a BlackRock portfolio strategist designing a comprehensive investment portfolio. Build a diversified portfolio based on client profile: - Age, income, investment timeline, and risk tolerance assessment - Strategic asset allocation across equities, bonds, alternatives, and cash - Geographic diversification (US, international developed, emerging markets) - Sector and style allocation (growth vs value, large vs small cap) - Fixed income duration and credit quality positioning - Alternative investments (REITs, commodities, private equity allocation) - ESG integration and sustainable investing considerations - Tax optimization strategies for the account type - Rebalancing methodology and frequency - Fee-conscious fund selection with expense ratio analysis - Performance benchmarking and risk monitoring framework Format as BlackRock investment proposal with detailed allocation rationale.'
    },
    {
        name: 'Harvard Endowment Dividend Strategy',
        prompt: 'You are managing Harvard Endowment\'s dividend-focused strategy. Design a sophisticated dividend income portfolio including: - High-quality dividend aristocrats with 20+ year track records - Dividend growth analysis and sustainability metrics - Yield optimization while maintaining capital preservation - Sector diversification across defensive and cyclical industries - International dividend opportunities and currency considerations - REIT allocation for real estate income exposure - Utility and infrastructure investments for stable cash flows - Dividend coverage ratios and payout sustainability analysis - Tax-efficient dividend strategies and qualified dividend treatment - Reinvestment vs distribution strategies based on market conditions - Risk management through dividend cuts and economic cycles Format as Harvard Endowment investment committee presentation with income projections.'
    },
    {
        name: 'Bain Competitive Analysis',
        prompt: 'You are a Bain & Company consultant conducting a comprehensive competitive landscape analysis. Perform strategic industry analysis including: - Market structure and competitive dynamics assessment - Key players market share and positioning analysis - Competitive advantages and moats evaluation - Pricing power and margin sustainability across competitors - Innovation cycles and R&D investment comparison - Supply chain and operational efficiency benchmarking - Customer loyalty and switching costs analysis - Regulatory environment and compliance requirements - Emerging threats from new entrants or disruptive technologies - M&A activity and consolidation trends in the industry - Strategic recommendations for market positioning Format as Bain strategy consulting report with actionable insights. The industry to analyze: [semiconductors]'
    },
    {
        name: 'Renaissance Pattern Finder',
        prompt: 'You are a Renaissance Technologies quantitative researcher identifying statistical patterns and anomalies. Conduct systematic pattern analysis including: - Historical price pattern recognition and statistical significance - Mean reversion vs momentum signal identification - Seasonal and cyclical pattern analysis across multiple timeframes - Volume and volatility pattern correlations - Cross-asset pattern relationships and spillover effects - Market microstructure patterns and order flow analysis - News sentiment patterns and market reaction quantification - Options flow patterns and institutional positioning signals - Statistical arbitrage opportunities and pair trading setups - Machine learning feature importance for predictive modeling - Backtesting results with risk-adjusted performance metrics Format as Renaissance research note with quantitative rigor and statistical validation. The asset to analyze: [AMD]'
    },
    {
        name: 'McKinsey Macro Economic Impact',
        prompt: 'You are a McKinsey Global Institute economist analyzing macroeconomic impacts on investment portfolios. Conduct comprehensive macro analysis including: - Global economic growth forecasts and regional variations - Central bank policy impacts on different asset classes - Inflation expectations and real return implications - Currency movements and international investment effects - Commodity price cycles and supply chain disruptions - Geopolitical risk assessment and market implications - Demographic trends and long-term structural changes - Technology disruption impacts on traditional industries - Climate change and ESG regulatory impacts on valuations - Fiscal policy changes and government spending priorities - Scenario planning for different economic outcomes (recession, stagflation, growth) Format as McKinsey Global Institute research with portfolio positioning recommendations.'
    }
];

export default function Home() {
    const { messages, input, handleInputChange, setInputValue, handleSubmit, isLoading, activeAgent, agentLabel } =
        useSupervisorChat();
    const bottomRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }, [messages, isLoading, activeAgent]);

    return (
        <div className="h-screen overflow-hidden bg-[radial-gradient(circle_at_0%_0%,#eaf1ff_0%,#f4f7fb_45%,#f9fbff_100%)] text-slate-900">
            <div className="mx-auto flex h-full w-full max-w-[1200px] flex-col px-4 py-4 sm:px-6">
                {/* Header */}
                <header className="flex items-center justify-between rounded-2xl border border-slate-200/80 bg-white/85 px-4 py-3 shadow-[0_12px_32px_rgba(15,23,42,0.06)] backdrop-blur">
                    <div className="flex items-center gap-3">
                        <div className="grid h-9 w-9 place-items-center rounded-lg bg-[#1e66f5] text-white shadow-[0_10px_25px_rgba(30,102,245,0.35)]">
                            <Sparkles size={16} />
                        </div>
                        <div>
                            <h1 className="text-base font-semibold tracking-tight">AI Stock Assistant</h1>
                            <p className="text-xs text-slate-500">Research workspace with integrated reports</p>
                        </div>
                    </div>
                    <nav className="flex items-center gap-2">
                        <Link
                            href="/integrations/schwab"
                            className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                        >
                            <Plug size={14} />
                            Integrations
                        </Link>
                    </nav>
                </header>

                {/* Main conversation area */}
                <main className="mt-4 flex-1 min-h-0 flex gap-4">
                    {/* Conversation Section */}
                    <section className="flex-1 flex h-full min-h-0 flex-col rounded-2xl border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
                        <div className="border-b border-slate-200 px-5 py-3">
                            <p className="text-sm font-medium text-slate-800">Conversation</p>
                            <p className="text-xs text-slate-500">Ask questions, generate reports, and iterate with follow-ups.</p>
                        </div>

                        <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5">
                            {messages.length === 0 ? (
                                <div className="flex h-full flex-col items-center justify-center px-4 text-center">
                                    <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
                                        Ask questions or generate reports
                                    </h2>
                                    <p className="mt-2 max-w-xl text-sm text-slate-500">
                                        Get market insights or generate institutional-style reports. Use the report templates on the right to get started.
                                    </p>
                                    <div className="mt-6 grid w-full max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2">
                                        {STARTER_QUERIES.map((query) => (
                                            <button
                                                key={query}
                                                type="button"
                                                onClick={() => setInputValue(query)}
                                                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 transition-colors"
                                            >
                                                {query}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-5">
                                    {messages.map((message) => (
                                        <ChatMessage key={message.id} message={message} />
                                    ))}
                                    {(isLoading || activeAgent !== 'idle') && (
                                        <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                                            <Loader2 size={14} className="animate-spin text-[#1e66f5]" />
                                            {activeAgent !== 'idle' ? agentLabel : 'Thinking...'}
                                        </div>
                                    )}
                                    <div ref={bottomRef} />
                                </div>
                            )}
                        </div>

                        <div className="border-t border-slate-200 p-3">
                            <form onSubmit={handleSubmit} className="flex items-end gap-2">
                                <textarea
                                    rows={2}
                                    className="min-h-[44px] w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e66f5]/30"
                                    value={input}
                                    placeholder="Ask a market question or request a report (e.g., 'technical analysis for AAPL')..."
                                    onChange={handleInputChange}
                                />
                                <Button
                                    type="submit"
                                    disabled={isLoading || !input?.trim()}
                                    className={cn(
                                        'h-11 bg-[#1e66f5] px-4 text-white hover:bg-[#1655d5]',
                                        (!input?.trim() || isLoading) && 'opacity-60'
                                    )}
                                >
                                    <ArrowUp size={14} />
                                </Button>
                            </form>
                        </div>
                    </section>

                    {/* Report Templates Card */}
                    <aside className="w-80 flex-shrink-0">
                        <div className="h-full rounded-2xl border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
                            <div className="border-b border-slate-200 px-4 py-3">
                                <p className="text-sm font-medium text-slate-800">Institutional Reports</p>
                                <p className="text-xs text-slate-500">Click any template to add it to your input</p>
                            </div>
                            <div className="p-4 space-y-2 max-h-[calc(100vh-200px)] overflow-y-auto">
                                {REPORT_TEMPLATES.map((template, index) => (
                                    <button
                                        key={template.name}
                                        type="button"
                                        onClick={() => setInputValue(template.prompt)}
                                        className="w-full text-left rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 hover:border-slate-300 transition-colors"
                                    >
                                        <span className="text-xs text-slate-500 font-medium">
                                            {index + 1}.
                                        </span>{' '}
                                        {template.name}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </aside>
                </main>
            </div>
        </div>
    );
}
