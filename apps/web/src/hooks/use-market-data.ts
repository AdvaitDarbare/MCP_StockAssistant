import useSWR from 'swr';
import { StockQuote, TechnicalIndicators } from '@/lib/types';

const API_BASE_URL = '/api/py';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export function useMarketData(symbol: string) {
    const { data: quote, error: quoteError, isLoading: quoteLoading } = useSWR<StockQuote>(
        symbol ? `${API_BASE_URL}/market/quote/${symbol}` : null,
        fetcher
    );

    const { data: technicals, error: techError, isLoading: techLoading } = useSWR<TechnicalIndicators>(
        symbol ? `${API_BASE_URL}/market/technicals/${symbol}` : null,
        fetcher
    );

    const { data: history, error: historyError, isLoading: historyLoading } = useSWR(
        symbol ? `${API_BASE_URL}/market/history/${symbol}?interval=1d&days=365` : null,
        fetcher
    );

    const { data: news, error: newsError, isLoading: newsLoading } = useSWR(
        symbol ? `${API_BASE_URL}/market/news/${symbol}` : null,
        fetcher
    );

    return {
        quote,
        technicals,
        history,
        news,
        isLoading: quoteLoading || techLoading || historyLoading || newsLoading,
        isError: quoteError || techError || historyError || newsError
    };
}

export function useMarketMovers() {
    const { data, error, isLoading } = useSWR(
        `${API_BASE_URL}/market/movers`,
        fetcher
    );

    return {
        movers: data,
        isLoading,
        isError: error
    };
}
