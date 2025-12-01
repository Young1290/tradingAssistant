'use client';
import { createChart, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import React, { useEffect, useRef } from 'react';

export const Chart = (props) => {
    const { data } = props;
    const chartContainerRef = useRef();

    useEffect(() => {
        if (!chartContainerRef.current || !data || data.length === 0) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { color: '#ffffff' },
                textColor: '#333',
            },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            grid: {
                vertLines: { color: '#e1e1e1' },
                horzLines: { color: '#e1e1e1' },
            },
        });

        // 1. 创建 K 线图
        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#26a69a',
            downColor: '#ef5350', 
            borderVisible: false, 
            wickUpColor: '#26a69a', 
            wickDownColor: '#ef5350'
        });

        // 2. 创建成交量柱状图
        const volumeSeries = chart.addSeries(HistogramSeries, {
            color: '#26a69a',
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '', // 使用独立的价格刻度
        });

        // 设置成交量显示在底部 20% 区域
        volumeSeries.priceScale().applyOptions({
            scaleMargins: {
                top: 0.8, // 留白 80%
                bottom: 0,
            },
        });

        // 格式化 K 线数据
        const chartData = data.map(d => ({
            time: d.time,
            open: parseFloat(d.open),
            high: parseFloat(d.high),
            low: parseFloat(d.low),
            close: parseFloat(d.close)
        }));

        // 格式化成交量数据（涨绿跌红）
        const volumeData = data.map(d => ({
            time: d.time,
            value: parseFloat(d.volume),
            color: parseFloat(d.close) >= parseFloat(d.open) 
                ? 'rgba(38, 166, 154, 0.5)' 
                : 'rgba(239, 83, 80, 0.5)'
        }));

        candlestickSeries.setData(chartData);
        volumeSeries.setData(volumeData);
        chart.timeScale().fitContent();

        const handleResize = () => {
            chart.applyOptions({ width: chartContainerRef.current.clientWidth });
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data]);

    return (
        <div ref={chartContainerRef} className="w-full relative" />
    );
};
