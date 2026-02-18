'use client';

import {
    createChart,
    ColorType,
    IChartApi,
    Time,
    CandlestickData,
    CrosshairMode,
    CandlestickSeries,
    HistogramSeries,
} from 'lightweight-charts';
import React, { useEffect, useRef } from 'react';

interface ResearchChartProps {
    data: {
        time: string;
        open: number;
        high: number;
        low: number;
        close: number;
        volume: number;
    }[];
    symbol: string;
}

export function ResearchChart({ data, symbol }: ResearchChartProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#64748b',
            },
            grid: {
                vertLines: { color: 'rgba(148, 163, 184, 0.18)' },
                horzLines: { color: 'rgba(148, 163, 184, 0.18)' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 390,
            crosshair: {
                mode: CrosshairMode.Normal,
                vertLine: {
                    labelBackgroundColor: '#1e66f5',
                },
                horzLine: {
                    labelBackgroundColor: '#1e66f5',
                },
            },
            timeScale: {
                borderColor: 'rgba(148, 163, 184, 0.35)',
                timeVisible: true,
                secondsVisible: false,
            },
            rightPriceScale: {
                borderColor: 'rgba(148, 163, 184, 0.35)',
            },
        });

        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#10b981',
            downColor: '#ef4444',
            borderVisible: false,
            wickUpColor: '#10b981',
            wickDownColor: '#ef4444',
        });

        const volumeSeries = chart.addSeries(HistogramSeries, {
            color: '#1e66f5',
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '',
        });

        volumeSeries.priceScale().applyOptions({
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });

        const formattedData: CandlestickData<Time>[] = data.map((point) => ({
            time: point.time as Time,
            open: point.open,
            high: point.high,
            low: point.low,
            close: point.close,
        }));

        const volumeData = data.map((point) => ({
            time: point.time as Time,
            value: point.volume,
            color: point.close >= point.open ? 'rgba(16,185,129,0.26)' : 'rgba(239,68,68,0.26)',
        }));

        candlestickSeries.setData(formattedData);
        volumeSeries.setData(volumeData);

        chart.timeScale().fitContent();
        chartRef.current = chart;

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data, symbol]);

    return (
        <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
            <div className="pointer-events-none absolute left-5 top-4 opacity-[0.04] select-none">
                <span className="text-8xl font-semibold text-slate-900">{symbol}</span>
            </div>

            <div className="relative z-10 mb-3 flex items-center justify-between">
                <div>
                    <h3 className="text-sm font-semibold text-slate-900">Price action</h3>
                    <p className="text-xs text-slate-500">Candles + volume</p>
                </div>
                <div className="rounded-full bg-[#e9f1ff] px-2 py-1 text-[10px] font-semibold uppercase text-[#1e66f5]">
                    Live chart
                </div>
            </div>

            <div ref={chartContainerRef} className="relative z-10 w-full" />
        </div>
    );
}
