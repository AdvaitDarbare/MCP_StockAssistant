'use client';

import { createChart, ColorType, IChartApi, Time, AreaSeries } from 'lightweight-charts';
import React, { useEffect, useRef } from 'react';

interface ChartData {
    time: string; // YYYY-MM-DD
    value: number;
}

interface StockChartProps {
    data: ChartData[];
    colors?: {
        backgroundColor?: string;
        lineColor?: string;
        textColor?: string;
        areaTopColor?: string;
        areaBottomColor?: string;
    };
}

export const StockChart = ({ data, colors = {} }: StockChartProps) => {
    const {
        backgroundColor = 'transparent',
        lineColor = '#2962FF',
        textColor = 'white',
        areaTopColor = '#2962FF',
        areaBottomColor = 'rgba(41, 98, 255, 0.28)',
    } = colors;

    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const handleResize = () => {
            chartRef.current?.applyOptions({ width: chartContainerRef.current!.clientWidth });
        };

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: backgroundColor },
                textColor,
            },
            width: chartContainerRef.current.clientWidth,
            height: 300,
            grid: {
                vertLines: { color: 'rgba(197, 203, 206, 0.1)' },
                horzLines: { color: 'rgba(197, 203, 206, 0.1)' },
            }
        });
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (chartRef.current as any) = chart;
        const newSeries = chart.addSeries(AreaSeries, {
            lineColor,
            topColor: areaTopColor,
            bottomColor: areaBottomColor,
        });

        // Convert data to lightweight-charts format
        const chartData = data.map(d => ({ time: d.time as Time, value: d.value }));
        newSeries.setData(chartData);
        chart.timeScale().fitContent();

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data, backgroundColor, lineColor, textColor, areaTopColor, areaBottomColor]);

    return (
        <div
            ref={chartContainerRef}
            className="w-full relative"
        />
    );
};
