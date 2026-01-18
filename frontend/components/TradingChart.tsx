"use client";

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, HistogramData } from 'lightweight-charts';
import { TrendingUp, Maximize2, Settings, Loader2 } from 'lucide-react';
import { formatPrice, getPriceHistory, type PriceData } from '@/lib/api';
import { useWebSocket } from '@/lib/websocket';

interface TradingChartProps {
  ticker: string;
  timeframe?: '1d' | '1h' | '15m';
  height?: number;
  title?: string;
}

interface NormalizedBar {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

const TradingChart: React.FC<TradingChartProps> = ({
  ticker,
  timeframe: initialTimeframe = '1d',
  height,
  title,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const [timeframe, setTimeframe] = useState<'1d' | '1h' | '15m'>(initialTimeframe);
  const resolvedHeight = height ?? 460;

  const { data: apiData, isLoading } = useQuery({
    queryKey: ['price-history', ticker, timeframe],
    queryFn: () => getPriceHistory(ticker, timeframe, 100),
    staleTime: 1000 * 60,
  });

  const { data: wsPrice } = useWebSocket('prices', ticker);

  const convertToChartData = (data: PriceData[]) => {
    const sorted = data
      .map((item) => {
        let time: number | null = null;

        if (typeof item.time === 'number' && Number.isFinite(item.time)) {
          time = item.time;
        } else if (typeof item.time === 'string') {
          const numeric = Number(item.time);
          if (Number.isFinite(numeric)) {
            time = numeric;
          } else {
            const parsed = Date.parse(item.time);
            if (Number.isFinite(parsed)) {
              time = Math.floor(parsed / 1000);
            }
          }
        } else if (item.timestamp !== undefined && item.timestamp !== null) {
          if (typeof item.timestamp === 'number' && Number.isFinite(item.timestamp)) {
            time = item.timestamp;
          } else if (typeof item.timestamp === 'string') {
            const numeric = Number(item.timestamp);
            if (Number.isFinite(numeric)) {
              time = numeric;
            } else {
              const parsed = Date.parse(item.timestamp);
              if (Number.isFinite(parsed)) {
                time = Math.floor(parsed / 1000);
              }
            }
          }
        }

        if (time !== null && Number.isFinite(time)) {
          time = time > 1e12 ? Math.floor(time / 1000) : Math.floor(time);
        }

        const open = Number(item.open);
        const high = Number(item.high);
        const low = Number(item.low);
        const close = Number(item.close);
        const volume = Number(item.volume);

        if (time === null || !Number.isFinite(time) || time <= 0 || !Number.isFinite(open) || !Number.isFinite(high) ||
            !Number.isFinite(low) || !Number.isFinite(close) || !Number.isFinite(volume)) {
          return null;
        }

        return { time, open, high, low, close, volume } as NormalizedBar;
      })
      .filter((item): item is NormalizedBar => item !== null)
      .sort((a, b) => a.time - b.time);

    const normalized: NormalizedBar[] = [];
    for (const item of sorted) {
      const last = normalized[normalized.length - 1];
      if (!last || item.time > last.time) {
        normalized.push(item);
      } else if (item.time === last.time) {
        normalized[normalized.length - 1] = item;
      }
    }

    const candles: CandlestickData[] = normalized.map((item) => ({
      time: item.time as any,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    }));

    const volumes: HistogramData[] = normalized.map((item) => ({
      time: item.time as any,
      value: item.volume,
      color: item.close >= item.open ? 'rgba(16, 185, 129, 0.5)' : 'rgba(239, 68, 68, 0.5)',
    }));

    return {
      candles,
      volumes,
      latest: normalized[normalized.length - 1],
      previous: normalized[normalized.length - 2],
    };
  };

  const chartData = useMemo(() => {
    if (!apiData?.data || !Array.isArray(apiData.data)) {
      return null;
    }
    return convertToChartData(apiData.data);
  }, [apiData]);

  const formatMaybePrice = (value?: number | null) => {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return '-';
    }
    return formatPrice(value);
  };

  const formatCompactNumber = (value?: number | null) => {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return '-';
    }
    return new Intl.NumberFormat('en-US', {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value);
  };

  const formatTimestamp = (value: number, includeTime: boolean) => {
    const options: Intl.DateTimeFormatOptions = {
      dateStyle: 'medium',
      timeZone: 'UTC',
    };
    if (includeTime) {
      options.timeStyle = 'short';
      options.timeZoneName = 'short';
    }
    return new Intl.DateTimeFormat('en-US', options).format(new Date(value * 1000));
  };

  const latestCandle = chartData?.latest;
  const previousCandle = chartData?.previous;
  const changeValue = latestCandle && previousCandle
    ? latestCandle.close - previousCandle.close
    : null;
  const changePercent = latestCandle && previousCandle && previousCandle.close
    ? (changeValue || 0) / previousCandle.close * 100
    : null;
  const includeTimeInRange = timeframe !== '1d';
  const rangeLabel = useMemo(() => {
    if (!chartData?.candles.length) {
      return null;
    }
    const first = chartData.candles[0]?.time;
    const last = chartData.candles[chartData.candles.length - 1]?.time;
    if (typeof first !== 'number' || typeof last !== 'number') {
      return null;
    }
    return `${formatTimestamp(first, includeTimeInRange)} - ${formatTimestamp(last, includeTimeInRange)}`;
  }, [chartData, includeTimeInRange]);
  const lastUpdateLabel = latestCandle?.time
    ? formatTimestamp(latestCandle.time, includeTimeInRange)
    : 'Live';
  const timeframeLabel = timeframe === '1d' ? '1D' : timeframe === '1h' ? '1H' : '15M';

  useEffect(() => {
    if (!chartContainerRef.current || !chartData?.candles.length) return;

    const container = chartContainerRef.current;
    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#cbd5f5',
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      width: container.clientWidth,
      height: container.clientHeight || resolvedHeight,
      timeScale: {
        timeVisible: timeframe !== '1d',
        secondsVisible: false,
        borderColor: '#334155',
      },
      rightPriceScale: {
        borderColor: '#334155',
        scaleMargins: {
          top: 0.15,
          bottom: 0.25,
        },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#475569',
          width: 1,
          style: 3,
          labelBackgroundColor: '#334155',
        },
        horzLine: {
          color: '#475569',
          width: 1,
          style: 3,
          labelBackgroundColor: '#334155',
        },
      },
      localization: {
        locale: 'en-US',
      },
    });

    chartRef.current = chart;

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
      priceLineVisible: false,
      lastValueVisible: true,
    });

    candlestickSeriesRef.current = candlestickSeries;

    const volumeSeries = chart.addHistogramSeries({
      color: '#64748b',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.75,
        bottom: 0,
      },
    });

    volumeSeriesRef.current = volumeSeries;

    candlestickSeries.setData(chartData.candles);
    volumeSeries.setData(chartData.volumes);

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (!container) return;
      chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight || resolvedHeight,
      });
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [chartData, resolvedHeight, timeframe]);

  useEffect(() => {
    if (wsPrice && candlestickSeriesRef.current) {
      console.log('WebSocket price update:', wsPrice);
    }
  }, [wsPrice]);

  const timeframes = [
    { value: '15m' as const, label: '15m' },
    { value: '1h' as const, label: '1h' },
    { value: '1d' as const, label: '1D' },
  ];

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-7 h-7 text-blue-500" />
            {title ?? ticker}
          </h2>
        </div>
        <div
          className="bg-slate-800/30 rounded-lg border border-slate-700/50 flex items-center justify-center"
          style={{ height: resolvedHeight }}
        >
          <Loader2 className="w-10 h-10 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  const isEmpty = !chartData?.candles.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-7 h-7 text-blue-500" />
            {title ?? ticker}
          </h2>
          <div className="flex flex-col gap-1 px-3 py-1 bg-slate-800/50 rounded-lg">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-slate-400">Last update: {lastUpdateLabel}</span>
            </div>
            {rangeLabel && (
              <span className="text-xs text-slate-400">
                Range: {rangeLabel} ({timeframeLabel} candles)
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-slate-800/50 rounded-lg p-1">
            {timeframes.map((tf) => (
              <button
                key={tf.value}
                onClick={() => setTimeframe(tf.value)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  timeframe === tf.value
                    ? 'bg-blue-500 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>

          <button className="p-2 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg transition-colors">
            <Settings className="w-5 h-5 text-slate-400" />
          </button>
          <button className="p-2 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg transition-colors">
            <Maximize2 className="w-5 h-5 text-slate-400" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
        <div>
          <div className="text-xs text-slate-500 mb-1">Open</div>
          <div className="text-white font-semibold">{formatMaybePrice(latestCandle?.open)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">High</div>
          <div className="text-green-400 font-semibold">{formatMaybePrice(latestCandle?.high)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">Low</div>
          <div className="text-red-400 font-semibold">{formatMaybePrice(latestCandle?.low)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">Close</div>
          <div className="text-white font-semibold">{formatMaybePrice(latestCandle?.close)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">Change</div>
          <div className={`font-semibold ${changeValue === null ? 'text-slate-400' : changeValue >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {changeValue === null || changePercent === null
              ? '-'
              : `${changeValue >= 0 ? '+' : ''}${changeValue.toFixed(2)} (${changePercent.toFixed(2)}%)`}
          </div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">Volume</div>
          <div className="text-white font-semibold">{formatCompactNumber(latestCandle?.volume)}</div>
        </div>
      </div>

      <div className="relative bg-slate-800/30 rounded-lg border border-slate-700/50 overflow-hidden">
        <div ref={chartContainerRef} className="w-full" style={{ height: resolvedHeight }} />
        {isEmpty && (
          <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">
            No chart data available for this timeframe.
          </div>
        )}
      </div>

      <div className="flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded"></div>
          <span className="text-slate-400">Bullish</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 rounded"></div>
          <span className="text-slate-400">Bearish</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-slate-600 rounded"></div>
          <span className="text-slate-400">Volume</span>
        </div>
      </div>

      <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700/50">
        <div className="text-sm text-slate-400 mb-2">Chart Controls:</div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs text-slate-500">
          <div>Zoom: Scroll wheel</div>
          <div>Pan: Click and drag</div>
          <div>Crosshair: Hover over chart</div>
          <div>Reset: Double click</div>
        </div>
      </div>
    </div>
  );
};

export default TradingChart;
