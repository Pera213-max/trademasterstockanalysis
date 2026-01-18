"use client";

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { useQuery, useQueries } from '@tanstack/react-query';
import {
  ArrowLeft,
  BarChart3,
  Plus,
  X,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';
import { getFiUniverse, getFiAnalysis, getFiHistory, FiAnalysis } from '@/lib/api';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

const MAX_COMPARE = 4;

const safeNumber = (value: any): number | null => {
  if (value === null || value === undefined) return null;
  const num = typeof value === 'number' ? value : parseFloat(value);
  if (isNaN(num) || !isFinite(num)) return null;
  return num;
};

const formatEur = (value: number | null | undefined, compact = false) => {
  const num = safeNumber(value);
  if (num === null) return '—';
  if (compact && Math.abs(num) >= 1e9) {
    return `${(num / 1e9).toFixed(2)} mrd €`;
  }
  if (compact && Math.abs(num) >= 1e6) {
    return `${(num / 1e6).toFixed(2)} M €`;
  }
  return new Intl.NumberFormat('fi-FI', { style: 'currency', currency: 'EUR' }).format(num);
};

const formatPercent = (value: number | null | undefined, decimals = 2) => {
  const num = safeNumber(value);
  if (num === null) return '—';
  const prefix = num > 0 ? '+' : '';
  return `${prefix}${num.toFixed(decimals)}%`;
};

const formatNumber = (value: number | null | undefined, decimals = 2) => {
  const num = safeNumber(value);
  if (num === null) return '—';
  return num.toFixed(decimals);
};

const formatPercentFromDecimal = (value: number | null | undefined) => {
  const num = safeNumber(value);
  if (num === null) return '—';
  const pct = num > 1 ? num : num * 100;
  return `${pct.toFixed(1)}%`;
};

const safeToFixed = (value: any, decimals: number = 0): string => {
  const num = safeNumber(value);
  if (num === null) return '—';
  return num.toFixed(decimals);
};

export default function FiComparePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const [chartRange, setChartRange] = useState<'3mo' | '6mo' | '1y'>('6mo');

  const { data: universeData } = useQuery({
    queryKey: ['fi-universe'],
    queryFn: getFiUniverse,
    staleTime: 60 * 60 * 1000,
  });

  const stocks = universeData?.stocks || [];

  const filteredStocks = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return stocks.slice(0, 24);
    return stocks
      .filter((s) => s.ticker.toLowerCase().includes(q) || s.name.toLowerCase().includes(q))
      .slice(0, 24);
  }, [stocks, searchQuery]);

  const addTicker = (ticker: string) => {
    if (selected.includes(ticker)) return;
    if (selected.length >= MAX_COMPARE) return;
    setSelected((prev) => [...prev, ticker]);
  };

  const removeTicker = (ticker: string) => {
    setSelected((prev) => prev.filter((t) => t !== ticker));
  };

  const analysisQueries = useQueries({
    queries: selected.map((ticker) => ({
      queryKey: ['fi-analysis', ticker],
      queryFn: () => getFiAnalysis(ticker),
      staleTime: 5 * 60 * 1000,
    })),
  });

  const historyQueries = useQueries({
    queries: selected.map((ticker) => ({
      queryKey: ['fi-history', ticker, chartRange],
      queryFn: () => getFiHistory(ticker, chartRange, '1d'),
      staleTime: 24 * 60 * 60 * 1000, // 24 hours - history data updates once daily
      gcTime: 24 * 60 * 60 * 1000,
      enabled: selected.length > 0,
    })),
  });

  const analysisByTicker = useMemo(() => {
    const map: Record<string, FiAnalysis | null> = {};
    selected.forEach((ticker, idx) => {
      map[ticker] = analysisQueries[idx]?.data?.data || null;
    });
    return map;
  }, [analysisQueries, selected]);

  const chartColors = ['#22c55e', '#38bdf8', '#a78bfa', '#f97316'];
  const { series: chartSeries, chartData } = useMemo(() => {
    const series = selected
      .map((ticker, idx) => {
        const points = historyQueries[idx]?.data?.data || [];
        if (!points.length) return null;
        const baseClose = safeNumber(points[0]?.close);
        if (!baseClose || baseClose === 0) return null;
        const normalized = points
          .map((p: any) => {
            const closePrice = safeNumber(p.close);
            if (closePrice === null) return null;
            return {
              date: p.date,
              value: (closePrice / baseClose) * 100,
            };
          })
          .filter(Boolean) as Array<{ date: string; value: number }>;
        if (!normalized.length) return null;
        return { ticker, color: chartColors[idx % chartColors.length], points: normalized };
      })
      .filter(Boolean) as Array<{ ticker: string; color: string; points: Array<{ date: string; value: number }> }>;

    const map = new Map<string, Record<string, any>>();
    for (const seriesItem of series) {
      for (const point of seriesItem.points) {
        if (!map.has(point.date)) {
          map.set(point.date, { date: point.date });
        }
        map.get(point.date)![seriesItem.ticker] = point.value;
      }
    }

    const data = Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date));
    return { series, chartData: data };
  }, [historyQueries, selected, chartRange]);

  const chartLoading = historyQueries.some((query) => query.isLoading);

  const rows = [
    { label: 'Hinta', get: (a: FiAnalysis) => formatEur(a.quote?.price), tone: 'neutral' },
    { label: 'Päivän muutos', get: (a: FiAnalysis) => formatPercent(a.quote?.changePercent), tone: 'change' },
    { label: '3kk tuotto', get: (a: FiAnalysis) => formatPercent(a.metrics?.return3m), tone: 'change' },
    { label: '12kk tuotto', get: (a: FiAnalysis) => formatPercent(a.metrics?.return12m), tone: 'change' },
    { label: 'Volatiliteetti', get: (a: FiAnalysis) => formatPercent(a.metrics?.volatility), tone: 'neutral' },
    { label: 'Markkina-arvo', get: (a: FiAnalysis) => formatEur(a.fundamentals?.marketCap, true), tone: 'neutral' },
    { label: 'P/E', get: (a: FiAnalysis) => formatNumber(a.fundamentals?.peRatio, 1), tone: 'neutral' },
    { label: 'P/B', get: (a: FiAnalysis) => formatNumber(a.fundamentals?.priceToBook, 2), tone: 'neutral' },
    { label: 'Osinkotuotto', get: (a: FiAnalysis) => formatPercentFromDecimal(a.fundamentals?.dividendYield), tone: 'neutral' },
    { label: 'ROE', get: (a: FiAnalysis) => formatPercentFromDecimal(a.fundamentals?.returnOnEquity), tone: 'neutral' },
    { label: 'Velkaantumisaste', get: (a: FiAnalysis) => formatPercent(a.fundamentals?.debtToEquity, 0), tone: 'neutral' },
    { label: 'Riskitaso', get: (a: FiAnalysis) => a.riskLevel, tone: 'neutral' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <header className="border-b border-slate-800/50 bg-slate-950/70 backdrop-blur">
        <div className="max-w-[2400px] mx-auto px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40 py-5 2xl:py-8 flex flex-col sm:flex-row gap-4 2xl:gap-6 sm:items-center sm:justify-between">
          <div className="flex items-center gap-3 2xl:gap-5">
            <Link
              href="/fi/dashboard"
              className="inline-flex items-center gap-2 2xl:gap-3 text-sm 2xl:text-2xl text-slate-400 hover:text-slate-200"
            >
              <ArrowLeft className="w-4 h-4 2xl:w-6 2xl:h-6" />
              Takaisin
            </Link>
            <div className="flex items-center gap-2 2xl:gap-4">
              <div className="p-2 2xl:p-3 rounded-lg 2xl:rounded-xl bg-cyan-500/20 border border-cyan-500/30">
                <BarChart3 className="w-5 h-5 2xl:w-8 2xl:h-8 text-cyan-300" />
              </div>
              <div>
                <h1 className="text-lg 2xl:text-4xl font-semibold text-white">Osakevertailu</h1>
                <p className="text-xs 2xl:text-base text-slate-400">Valitse 2–4 yhtiötä ja vertaa avainlukuja</p>
              </div>
            </div>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-[2400px] mx-auto px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40 py-6 md:py-10 2xl:py-16 space-y-8 2xl:space-y-12">
        <section className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
          <div className="flex flex-col lg:flex-row gap-4 2xl:gap-6 lg:items-center lg:justify-between">
            <div>
              <h2 className="text-lg 2xl:text-4xl font-semibold text-white mb-1 2xl:mb-3">Valitse vertailuun</h2>
              <p className="text-xs 2xl:text-xl text-slate-400">Voit valita enintään {MAX_COMPARE} osaketta.</p>
            </div>
            <div className="w-full lg:w-80 2xl:w-[450px]">
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Hae tickerillä tai nimellä"
                className="w-full bg-slate-900/70 border border-slate-700/50 rounded-lg 2xl:rounded-xl px-3 2xl:px-5 py-2 2xl:py-4 text-sm 2xl:text-2xl text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
              />
            </div>
          </div>

          <div className="mt-4 2xl:mt-8 flex flex-wrap gap-2 2xl:gap-4">
            {selected.length === 0 && (
              <span className="text-xs 2xl:text-xl text-slate-500">Ei valittuja osakkeita.</span>
            )}
            {selected.map((ticker) => (
              <span
                key={ticker}
                className="inline-flex items-center gap-2 2xl:gap-3 px-3 2xl:px-5 py-1 2xl:py-2 rounded-full bg-slate-900/60 border border-slate-700/60 text-xs 2xl:text-xl text-slate-200"
              >
                {ticker}
                <button
                  type="button"
                  onClick={() => removeTicker(ticker)}
                  className="text-slate-400 hover:text-red-400 transition-colors"
                >
                  <X className="w-3 h-3 2xl:w-5 2xl:h-5" />
                </button>
              </span>
            ))}
          </div>

          <div className="mt-5 2xl:mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 2xl:gap-5">
            {filteredStocks.map((stock) => {
              const isSelected = selected.includes(stock.ticker);
              return (
                <button
                  key={stock.ticker}
                  type="button"
                  onClick={() => addTicker(stock.ticker)}
                  disabled={isSelected || selected.length >= MAX_COMPARE}
                  className={`text-left p-3 2xl:p-5 rounded-lg 2xl:rounded-xl border transition-colors ${
                    isSelected
                      ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-200'
                      : 'border-slate-700/50 bg-slate-900/60 hover:border-cyan-500/40'
                  } ${selected.length >= MAX_COMPARE && !isSelected ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm 2xl:text-2xl font-semibold text-white">{stock.name}</div>
                      <div className="text-xs 2xl:text-base text-slate-400">{stock.ticker} • {stock.sector}</div>
                    </div>
                    {!isSelected && (
                      <span className="inline-flex items-center gap-1 2xl:gap-2 text-xs 2xl:text-base text-cyan-300">
                        <Plus className="w-3 h-3 2xl:w-5 2xl:h-5" />
                        Lisää
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        <section className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 2xl:gap-6 mb-4 2xl:mb-8">
            <div>
              <h2 className="text-lg 2xl:text-4xl font-semibold text-white">Hintakäyrät päällekkäin</h2>
              <p className="text-xs 2xl:text-xl text-slate-400 mt-1 2xl:mt-2">Indeksoitu: 100 = jakson alku</p>
            </div>
            <div className="flex items-center gap-2 2xl:gap-4">
              {(['3mo', '6mo', '1y'] as const).map((range) => (
                <button
                  key={range}
                  type="button"
                  onClick={() => setChartRange(range)}
                  className={`px-3 2xl:px-6 py-1.5 2xl:py-3 rounded-lg 2xl:rounded-xl text-xs 2xl:text-xl font-semibold border transition-colors ${
                    chartRange === range
                      ? 'bg-cyan-500/20 text-cyan-200 border-cyan-500/40'
                      : 'bg-slate-900/60 text-slate-300 border-slate-700/60 hover:border-cyan-500/30'
                  }`}
                >
                  {range === '3mo' ? '3 kk' : range === '6mo' ? '6 kk' : '1 v'}
                </button>
              ))}
            </div>
          </div>

          {selected.length < 2 ? (
            <div className="text-sm 2xl:text-2xl text-slate-400">Valitse vähintään 2 osaketta vertailuun.</div>
          ) : chartLoading ? (
            <div className="text-sm 2xl:text-2xl text-slate-400">Ladataan käyrät...</div>
          ) : chartData.length === 0 ? (
            <div className="text-sm 2xl:text-2xl text-slate-400">Ei dataa saatavilla.</div>
          ) : (
            <>
              <div className="h-[240px] sm:h-[320px] 2xl:h-[450px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: '#94a3b8', fontSize: 11 }}
                      tickFormatter={(value) =>
                        new Date(value).toLocaleDateString('fi-FI', { day: 'numeric', month: 'short' })
                      }
                    />
                    <YAxis
                      tick={{ fill: '#94a3b8', fontSize: 11 }}
                      tickFormatter={(value) => safeToFixed(value, 0)}
                      domain={['dataMin - 3', 'dataMax + 3']}
                    />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                      labelStyle={{ color: '#e2e8f0' }}
                      formatter={(value: any) => [safeToFixed(value, 1), 'Indeksi']}
                      labelFormatter={(label) =>
                        new Date(label).toLocaleDateString('fi-FI', { day: 'numeric', month: 'short', year: 'numeric' })
                      }
                    />
                    {chartSeries.map((series) => (
                      <Line
                        key={series.ticker}
                        type="monotone"
                        dataKey={series.ticker}
                        stroke={series.color}
                        strokeWidth={2}
                        dot={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap gap-2 2xl:gap-4 mt-4 2xl:mt-8">
                {chartSeries.map((series) => (
                  <span
                    key={series.ticker}
                    className="inline-flex items-center gap-2 2xl:gap-3 px-3 2xl:px-5 py-1 2xl:py-2 rounded-full bg-slate-900/60 border border-slate-700/60 text-xs 2xl:text-xl text-slate-200"
                  >
                    <span className="w-2 h-2 2xl:w-4 2xl:h-4 rounded-full" style={{ backgroundColor: series.color }} />
                    {series.ticker}
                  </span>
                ))}
              </div>
            </>
          )}
        </section>

        <section className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
          <div className="flex items-center justify-between gap-3 2xl:gap-5 mb-4 2xl:mb-8">
            <h2 className="text-lg 2xl:text-4xl font-semibold text-white">Vertailutaulukko</h2>
            {selected.length === 0 && (
              <span className="text-xs 2xl:text-xl text-slate-500">Valitse osakkeita yllä.</span>
            )}
          </div>

          {selected.length > 0 && (
            <>
              <div className="space-y-4 2xl:space-y-6 md:hidden">
                {selected.map((ticker) => {
                  const analysis = analysisByTicker[ticker];
                  return (
                    <div key={ticker} className="rounded-xl 2xl:rounded-2xl border border-slate-700/60 bg-slate-900/60 p-4 2xl:p-6">
                      <div className="text-sm 2xl:text-2xl font-semibold text-white">{analysis?.name || ticker}</div>
                      <div className="text-xs 2xl:text-base text-slate-400">{ticker}</div>
                      <div className="mt-3 2xl:mt-5 grid grid-cols-2 gap-2 2xl:gap-4 text-xs 2xl:text-base">
                        {rows.map((row) => {
                          const value = analysis ? row.get(analysis) : '—';
                          return (
                            <div key={`${ticker}-${row.label}`} className="rounded-lg 2xl:rounded-xl border border-slate-800/70 bg-slate-950/40 p-2 2xl:p-4">
                              <div className="text-[11px] 2xl:text-sm text-slate-500">{row.label}</div>
                              <div className="text-sm 2xl:text-xl text-slate-100 mt-1 2xl:mt-2">{value}</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full text-sm 2xl:text-2xl text-slate-200">
                  <thead>
                    <tr className="border-b border-slate-700/60">
                      <th className="text-left py-2 2xl:py-4 pr-4 2xl:pr-8 text-slate-400 font-medium">Mittari</th>
                      {selected.map((ticker) => (
                        <th key={ticker} className="text-left py-2 2xl:py-4 px-4 2xl:px-8 font-semibold text-white">
                          {analysisByTicker[ticker]?.name || ticker}
                          <div className="text-xs 2xl:text-base text-slate-400">{ticker}</div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.label} className="border-b border-slate-800/60">
                        <td className="py-3 2xl:py-5 pr-4 2xl:pr-8 text-slate-400">{row.label}</td>
                        {selected.map((ticker) => {
                          const analysis = analysisByTicker[ticker];
                          const value = analysis ? row.get(analysis) : '—';
                          const isChangeRow = row.tone === 'change';
                          const changeValue = analysis?.quote?.changePercent ?? analysis?.metrics?.return3m ?? 0;
                          const isPositive = changeValue >= 0;
                          return (
                            <td key={`${row.label}-${ticker}`} className="py-3 2xl:py-5 px-4 2xl:px-8">
                              <div className={`inline-flex items-center gap-1 2xl:gap-2 ${isChangeRow ? (isPositive ? 'text-emerald-400' : 'text-red-400') : 'text-slate-100'}`}>
                                {isChangeRow ? (
                                  isPositive ? <ArrowUpRight className="w-3 h-3 2xl:w-5 2xl:h-5" /> : <ArrowDownRight className="w-3 h-3 2xl:w-5 2xl:h-5" />
                                ) : null}
                                <span>{value}</span>
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
