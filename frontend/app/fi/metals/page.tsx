"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft, TrendingUp, TrendingDown, Activity,
  ArrowUpRight, ArrowDownRight, RefreshCw
} from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';
import { getFiMetalDetail, FiMetalDetail, FiMetalHistory } from '@/lib/api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area
} from 'recharts';

// Time period options
const TIME_PERIODS = [
  { value: '1mo', label: '1kk' },
  { value: '3mo', label: '3kk' },
  { value: '6mo', label: '6kk' },
  { value: '1y', label: '1v' },
  { value: '2y', label: '2v' },
] as const;

// Finnish translations
const t = {
  title: 'Jalometallit',
  subtitle: 'Kulta & Hopea',
  backToDashboard: 'Takaisin',
  loading: 'Ladataan...',
  error: 'Virhe ladattaessa dataa',
  noData: 'Ei dataa saatavilla',
  price: 'Hinta',
  change: 'Muutos',
  dayRange: 'Päivän vaihteluväli',
  yearRange: '52 vkn vaihteluväli',
  fiftyDayAvg: '50 pv keskiarvo',
  twoHundredDayAvg: '200 pv keskiarvo',
  volume: 'Volyymi',
  priceChart: 'Hintakehitys',
  disclaimer: 'Hinnat ovat viitteellisiä. Tämä ei ole sijoitusneuvontaa.',
  gold: 'Kulta',
  silver: 'Hopea',
};

// Format USD currency
const formatUsd = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
};

// Format percentage
const formatPercent = (value: number | null | undefined, decimals = 2) => {
  if (value === null || value === undefined) return '—';
  const formatted = value.toFixed(decimals).replace('.', ',');
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${formatted}%`;
};

// Format number
const formatNumber = (value: number | null | undefined, decimals = 2) => {
  if (value === null || value === undefined) return '—';
  return value.toFixed(decimals).replace('.', ',');
};

// Format large number
const formatLargeNumber = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '—';
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)} M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)} K`;
  return value.toFixed(0);
};

// Metal card component
const MetalCard = ({ code, name }: { code: string; name: string }) => {
  const [selectedPeriod, setSelectedPeriod] = useState<string>('1y');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['fiMetalDetail', code],
    queryFn: () => getFiMetalDetail(code),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 5 * 60 * 1000, // Auto refresh every 5 minutes
  });

  const metal = data?.data;

  // Filter history based on selected period
  const getFilteredHistory = () => {
    if (!metal?.history) return [];

    const now = new Date();
    let cutoffDate: Date;

    switch (selectedPeriod) {
      case '1mo':
        cutoffDate = new Date(now.setMonth(now.getMonth() - 1));
        break;
      case '3mo':
        cutoffDate = new Date(now.setMonth(now.getMonth() - 3));
        break;
      case '6mo':
        cutoffDate = new Date(now.setMonth(now.getMonth() - 6));
        break;
      case '2y':
        cutoffDate = new Date(now.setFullYear(now.getFullYear() - 2));
        break;
      case '1y':
      default:
        cutoffDate = new Date(now.setFullYear(now.getFullYear() - 1));
        break;
    }

    return metal.history.filter(h => new Date(h.date) >= cutoffDate);
  };

  const filteredHistory = getFilteredHistory();

  // Calculate min/max for chart
  const chartData = filteredHistory.map(h => ({
    date: h.date,
    close: h.close,
  }));

  const minPrice = chartData.length > 0 ? Math.min(...chartData.map(d => d.close)) * 0.98 : 0;
  const maxPrice = chartData.length > 0 ? Math.max(...chartData.map(d => d.close)) * 1.02 : 100;

  // Determine if price is up or down
  const isUp = metal?.change && metal.change >= 0;

  if (isLoading) {
    return (
      <div className="bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-slate-700 rounded-lg animate-pulse"></div>
          <div className="flex-1">
            <div className="h-6 bg-slate-700 rounded w-24 animate-pulse mb-2"></div>
            <div className="h-4 bg-slate-700 rounded w-32 animate-pulse"></div>
          </div>
        </div>
        <div className="h-64 bg-slate-700 rounded animate-pulse"></div>
      </div>
    );
  }

  if (error || !metal) {
    return (
      <div className="bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700/50 p-6">
        <div className="text-center text-slate-400 py-8">
          <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>{t.error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-slate-700/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${
              code === 'GOLD'
                ? 'bg-yellow-500/20 border border-yellow-500/30'
                : 'bg-slate-500/20 border border-slate-500/30'
            }`}>
              <span className="text-2xl">{code === 'GOLD' ? '🥇' : '🥈'}</span>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">{name}</h2>
              <p className="text-sm text-slate-400">{metal.description}</p>
            </div>
          </div>
          <button
            onClick={() => refetch()}
            className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-600/50 text-slate-400 hover:text-white transition-colors"
            title="Päivitä"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>

        {/* Price and change */}
        <div className="mt-6 flex items-end gap-6">
          <div>
            <p className="text-sm text-slate-400 mb-1">{t.price}</p>
            <p className="text-4xl font-bold text-white">{formatUsd(metal.price)}</p>
            <p className="text-xs text-slate-500 mt-1">{metal.unit}</p>
          </div>
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
            isUp ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            {isUp ? <ArrowUpRight className="w-5 h-5" /> : <ArrowDownRight className="w-5 h-5" />}
            <span className="font-semibold">{formatUsd(metal.change)}</span>
            <span className="text-sm">({formatPercent(metal.changePercent)})</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">{t.priceChart}</h3>
          <div className="flex gap-1 bg-slate-700/50 rounded-lg p-1">
            {TIME_PERIODS.map(period => (
              <button
                key={period.value}
                onClick={() => setSelectedPeriod(period.value)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  selectedPeriod === period.value
                    ? 'bg-sky-600 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-slate-600/50'
                }`}
              >
                {period.label}
              </button>
            ))}
          </div>
        </div>

        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id={`gradient-${code}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={isUp ? '#22c55e' : '#ef4444'} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={isUp ? '#22c55e' : '#ef4444'} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="date"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return date.toLocaleDateString('fi-FI', { month: 'short', day: 'numeric' });
                }}
                interval="preserveStartEnd"
                minTickGap={50}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                domain={[minPrice, maxPrice]}
                tickFormatter={(value) => formatNumber(value, 0)}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                }}
                formatter={(value: number) => [formatUsd(value), t.price]}
                labelFormatter={(label) => new Date(label).toLocaleDateString('fi-FI', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              />
              <Area
                type="monotone"
                dataKey="close"
                stroke={isUp ? '#22c55e' : '#ef4444'}
                fill={`url(#gradient-${code})`}
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Key metrics */}
      <div className="p-6 border-t border-slate-700/50">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-700/30 rounded-lg p-4">
            <p className="text-xs text-slate-400 mb-1">{t.dayRange}</p>
            <p className="text-sm font-medium text-white">
              {formatUsd(metal.low)} - {formatUsd(metal.high)}
            </p>
          </div>
          <div className="bg-slate-700/30 rounded-lg p-4">
            <p className="text-xs text-slate-400 mb-1">{t.yearRange}</p>
            <p className="text-sm font-medium text-white">
              {formatUsd(metal.fiftyTwoWeekLow)} - {formatUsd(metal.fiftyTwoWeekHigh)}
            </p>
          </div>
          <div className="bg-slate-700/30 rounded-lg p-4">
            <p className="text-xs text-slate-400 mb-1">{t.fiftyDayAvg}</p>
            <p className="text-sm font-medium text-white">{formatUsd(metal.fiftyDayAverage)}</p>
          </div>
          <div className="bg-slate-700/30 rounded-lg p-4">
            <p className="text-xs text-slate-400 mb-1">{t.twoHundredDayAvg}</p>
            <p className="text-sm font-medium text-white">{formatUsd(metal.twoHundredDayAverage)}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default function MetalsPage() {
  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link
                href="/fi/dashboard"
                className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span className="hidden sm:inline">{t.backToDashboard}</span>
              </Link>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🥇</span>
                <h1 className="text-xl font-bold text-white">{t.title}</h1>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page title */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">{t.title}</h1>
          <p className="text-slate-400 mt-2">{t.subtitle}</p>
        </div>

        {/* Metal cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MetalCard code="GOLD" name={t.gold} />
          <MetalCard code="SILVER" name={t.silver} />
        </div>

        {/* Disclaimer */}
        <div className="mt-8 p-4 bg-slate-800/30 rounded-lg border border-slate-700/30">
          <p className="text-xs text-slate-500 text-center">{t.disclaimer}</p>
        </div>
      </main>
    </div>
  );
}
