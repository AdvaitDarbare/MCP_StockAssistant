'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useState } from 'react';
import {
    Activity,
    ArrowLeft,
    Clock,
    FlaskConical,
    Info,
    RefreshCw,
    ShieldAlert,
    TrendingDown,
    TrendingUp,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { useMarketData } from '@/hooks/use-market-data';
import { ResearchChart } from '@/components/research/research-chart';

type HistoryPoint = {
    date: string;
    open?: number;
    high?: number;
    low?: number;
    close: number;
    volume?: number;
};

type NewsItem = {
    source?: string;
    timestamp: string;
    headline: string;
    summary?: string;
    url: string;
};

export default function ResearchDetailPage() {
    const { symbol } = useParams() as { symbol: string };
    const { quote, technicals, history, news, isLoading } = useMarketData(symbol);
    const router = useRouter();
    const [actionMessage] = useState<string>('');

    if (isLoading && !quote) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_0%_0%,#eaf1ff_0%,#f4f7fb_45%,#f9fbff_100%)]">
                <div className="flex flex-col items-center gap-3">
                    <RefreshCw className="animate-spin text-[#1e66f5]" size={36} />
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Loading {symbol} snapshot...</p>
                </div>
            </div>
        );
    }

    const chartData = ((history as HistoryPoint[] | undefined) || []).map((point) => ({
        time: point.date,
        open: point.open ?? point.close,
        high: point.high ?? point.close * 1.01,
        low: point.low ?? point.close * 0.99,
        close: point.close,
        volume: point.volume ?? 1000000,
    }));

    const isUp = quote && quote.change !== undefined && quote.change >= 0;

    return (
        <div className="min-h-screen overflow-y-auto bg-[radial-gradient(circle_at_0%_0%,#eaf1ff_0%,#f4f7fb_45%,#f9fbff_100%)] text-slate-900">
            <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6">
                <header className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/80 bg-white/85 px-4 py-3 shadow-[0_12px_32px_rgba(15,23,42,0.06)] backdrop-blur">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => router.back()}
                            className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                        >
                            <ArrowLeft size={16} />
                        </button>
                        <div>
                            <h1 className="text-base font-semibold tracking-tight">{symbol} Research Snapshot</h1>
                            <p className="text-xs text-slate-500">Live quote, trend context, and recent headlines.</p>
                        </div>
                    </div>

                </header>

                <section className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
                    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.08)] md:col-span-2">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Price</p>
                        <div className="mt-1 flex items-end gap-3">
                            <h2 className="text-3xl font-semibold tracking-tight text-slate-900">${quote?.price?.toLocaleString() || '---'}</h2>
                            <span
                                className={cn(
                                    'mb-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
                                    isUp ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                                )}
                            >
                                {isUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                                {quote?.change !== undefined && quote.change > 0 ? '+' : ''}
                                {quote?.change ?? '0.00'} ({quote?.percent_change ?? '0.00'}%)
                            </span>
                        </div>
                        <p className="mt-2 inline-flex items-center gap-1 text-xs text-slate-500">
                            <Clock size={12} />
                            {quote?.timestamp ? new Date(quote.timestamp).toLocaleString() : 'Timestamp unavailable'}
                        </p>
                    </div>

                    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Technicals</p>
                        <div className="mt-2 space-y-1 text-sm text-slate-700">
                            <div>RSI: <strong>{technicals?.rsi ?? 'n/a'}</strong></div>
                            <div>Trend: <strong>{technicals?.trend ?? 'n/a'}</strong></div>
                            <div>Support: <strong>{technicals?.support ?? 'n/a'}</strong></div>
                            <div>Resistance: <strong>{technicals?.resistance ?? 'n/a'}</strong></div>
                        </div>
                    </div>

                    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Reference</p>
                        <div className="mt-2 space-y-1 text-sm text-slate-700">
                            <div>52W High: <strong>{quote?.week_52_high ?? 'n/a'}</strong></div>
                            <div>52W Low: <strong>{quote?.week_52_low ?? 'n/a'}</strong></div>
                            <div>P/E: <strong>{quote?.pe_ratio ?? 'n/a'}</strong></div>
                            <div>Source: <strong>{quote?.provider ?? 'n/a'}</strong></div>
                        </div>
                    </div>
                </section>

                <section className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
                    <div className="space-y-4 lg:col-span-2">
                        <ResearchChart data={chartData} symbol={symbol} />

                        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
                            <div className="mb-2 inline-flex items-center gap-2 text-sm font-semibold text-slate-900">
                                <Info size={16} className="text-[#1e66f5]" />
                                Research usage
                            </div>
                            <p className="text-sm text-slate-600">
                                This page is a quick snapshot. For a full structured memo with assumptions, tool plan, and quality checks,
                                run the <strong>Research Report Lab</strong> workflow.
                            </p>
                            {actionMessage ? <p className="mt-2 text-xs text-[#1e66f5]">{actionMessage}</p> : null}
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
                            <h3 className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                                <Activity size={14} className="text-[#1e66f5]" />
                                Latest news
                            </h3>
                            <div className="mt-3 space-y-3">
                                {Array.isArray(news) && news.length > 0 ? (
                                    (news as NewsItem[]).map((item, index) => (
                                        <a
                                            key={`${item.url}-${index}`}
                                            href={item.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="block rounded-lg border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100"
                                        >
                                            <div className="mb-1 flex items-center justify-between gap-2">
                                                <span className="text-[11px] font-semibold uppercase tracking-wide text-[#1e66f5]">{item.source || 'News'}</span>
                                                <span className="text-[11px] text-slate-500">{new Date(item.timestamp).toLocaleDateString()}</span>
                                            </div>
                                            <p className="text-sm font-medium leading-snug text-slate-800">{item.headline}</p>
                                            {item.summary ? <p className="mt-1 text-xs text-slate-600">{item.summary}</p> : null}
                                        </a>
                                    ))
                                ) : (
                                    <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-500">
                                        No recent headlines returned for {symbol}.
                                    </p>
                                )}
                            </div>
                        </div>

                        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900 shadow-[0_16px_40px_rgba(15,23,42,0.06)]">
                            <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
                                <ShieldAlert size={14} />
                                Safety
                            </p>
                            <p className="mt-2 text-sm">
                                This app is analysis-first. Any future trade flow must remain explicit human-in-the-loop.
                            </p>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}
