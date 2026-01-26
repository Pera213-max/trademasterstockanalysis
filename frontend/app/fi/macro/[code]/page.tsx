"use client";

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft, TrendingUp, TrendingDown, Activity, Calendar,
  ArrowUpRight, ArrowDownRight, BarChart3
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart
} from 'recharts';
import { getFiMacroHistory } from '@/lib/api';

const PERIODS = [
  { value: '1mo', label: '1kk' },
  { value: '3mo', label: '3kk' },
  { value: '6mo', label: '6kk' },
  { value: '1y', label: '1v' },
  { value: '2y', label: '2v' },
  { value: '5y', label: '5v' },
];

const MACRO_NAMES: Record<string, { name: string; unit: string; category: string }> = {
  'OMXH25': { name: 'Helsinki 25', unit: 'pistettä', category: 'Indeksi' },
  'STOXX50': { name: 'Euro Stoxx 50', unit: 'pistettä', category: 'Indeksi' },
  'DAX': { name: 'DAX 40', unit: 'pistettä', category: 'Indeksi' },
  'VIX': { name: 'Volatiliteetti-indeksi', unit: '', category: 'Indeksi' },
  'EUR/USD': { name: 'Euro / Dollari', unit: 'USD', category: 'Valuutta' },
  'EUR/SEK': { name: 'Euro / Kruunu', unit: 'SEK', category: 'Valuutta' },
  'KULTA': { name: 'Kulta', unit: 'USD/oz', category: 'Raaka-aine' },
  'ÖLJY': { name: 'Brent-öljy', unit: 'USD', category: 'Raaka-aine' },
  'US10Y': { name: 'USA 10v korko', unit: '%', category: 'Korko' },
};

export default function MacroChartPage() {
  const params = useParams();
  const code = decodeURIComponent(params.code as string);
  const [period, setPeriod] = useState('1y');

  const macroInfo = MACRO_NAMES[code] || { name: code, unit: '', category: 'Muu' };

  const { data, isLoading, error } = useQuery({
    queryKey: ['macro-history', code, period],
    queryFn: () => getFiMacroHistory(code, period),
    staleTime: 5 * 60 * 1000,
  });

  const chartData = useMemo(() => {
    if (!data?.data?.history) return [];
    return data.data.history.map((item: any) => ({
      date: new Date(item.date).toLocaleDateString('fi-FI', { day: 'numeric', month: 'short' }),
      fullDate: item.date,
      close: item.close,
      high: item.high,
      low: item.low,
      open: item.open,
    }));
  }, [data]);

  const stats = useMemo(() => {
    if (!chartData.length) return null;
    const closes = chartData.map((d: any) => d.close);
    const current = closes[closes.length - 1];
    const first = closes[0];
    const high = Math.max(...closes);
    const low = Math.min(...closes);
    const change = current - first;
    const changePercent = ((change / first) * 100);
    return { current, first, high, low, change, changePercent };
  }, [chartData]);

  const isPositive = stats ? stats.changePercent >= 0 : true;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link
                href="/fi/dashboard"
                className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span className="hidden sm:inline">Takaisin</span>
              </Link>
              <div className="h-6 w-px bg-slate-700" />
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                  <Activity className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-white">{macroInfo.name}</h1>
                  <p className="text-xs text-slate-400">{macroInfo.category} • {code}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4">
              <div className="text-xs text-slate-400 mb-1">Nykyinen</div>
              <div className="text-2xl font-bold text-white">
                {stats.current.toLocaleString('fi-FI', { maximumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-slate-500">{macroInfo.unit}</div>
            </div>
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4">
              <div className="text-xs text-slate-400 mb-1">Muutos ({PERIODS.find(p => p.value === period)?.label})</div>
              <div className={`text-2xl font-bold flex items-center gap-1 ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                {isPositive ? <ArrowUpRight className="w-5 h-5" /> : <ArrowDownRight className="w-5 h-5" />}
                {stats.changePercent.toFixed(2)}%
              </div>
              <div className="text-xs text-slate-500">
                {isPositive ? '+' : ''}{stats.change.toLocaleString('fi-FI', { maximumFractionDigits: 2 })}
              </div>
            </div>
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4">
              <div className="text-xs text-slate-400 mb-1">Korkein</div>
              <div className="text-2xl font-bold text-emerald-400">
                {stats.high.toLocaleString('fi-FI', { maximumFractionDigits: 2 })}
              </div>
            </div>
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4">
              <div className="text-xs text-slate-400 mb-1">Matalin</div>
              <div className="text-2xl font-bold text-red-400">
                {stats.low.toLocaleString('fi-FI', { maximumFractionDigits: 2 })}
              </div>
            </div>
          </div>
        )}

        {/* Period Selector */}
        <div className="flex items-center gap-2 mb-6">
          <Calendar className="w-4 h-4 text-slate-400" />
          <span className="text-sm text-slate-400 mr-2">Aikaväli:</span>
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                period === p.value
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-700/60'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Chart */}
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-6">
            <BarChart3 className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-semibold text-white">Hintakehitys</h2>
          </div>

          {isLoading ? (
            <div className="h-[400px] flex items-center justify-center">
              <div className="animate-spin w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full" />
            </div>
          ) : error ? (
            <div className="h-[400px] flex items-center justify-center text-red-400">
              Virhe ladattaessa dataa
            </div>
          ) : chartData.length === 0 ? (
            <div className="h-[400px] flex items-center justify-center text-slate-400">
              Ei dataa saatavilla
            </div>
          ) : (
            <div className="h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={isPositive ? "#10b981" : "#ef4444"} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={isPositive ? "#10b981" : "#ef4444"} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="date"
                    stroke="#64748b"
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    tickLine={{ stroke: '#475569' }}
                  />
                  <YAxis
                    stroke="#64748b"
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    tickLine={{ stroke: '#475569' }}
                    domain={['auto', 'auto']}
                    tickFormatter={(value) => value.toLocaleString('fi-FI', { maximumFractionDigits: 0 })}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#f1f5f9'
                    }}
                    formatter={(value: number) => [value.toLocaleString('fi-FI', { maximumFractionDigits: 2 }), 'Arvo']}
                    labelFormatter={(label) => `Päivä: ${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="close"
                    stroke={isPositive ? "#10b981" : "#ef4444"}
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorValue)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
