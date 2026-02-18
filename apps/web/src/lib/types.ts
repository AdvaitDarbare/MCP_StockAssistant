export interface ChartDataPoint {
    time: string;
    value: number;
}

export interface StockQuote {
    symbol: string;
    price: number;
    change: number;
    percent_change: number;
    timestamp: string;
    provider?: string;
    pe_ratio?: number;
    week_52_high?: number;
    week_52_low?: number;
}

export interface TechnicalIndicators {
    symbol: string;
    rsi?: number;
    macd?: number;
    macd_signal?: number;
    sma_20?: number;
    sma_50?: number;
    sma_200?: number;
    trend?: string;
    support?: number;
    resistance?: number;
}
