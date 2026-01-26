"use client";

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3, Filter, TrendingUp, TrendingDown, Search,
  ChevronRight, ArrowUpRight, ArrowDownRight, RefreshCw,
  Percent, Activity, DollarSign, Shield, Zap, Building2,
  ArrowLeft, X, ChevronUp, ChevronDown
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// Preset filters
const PRESETS = [
  {
    id: 'high_dividend',
    name: 'Korkea osinko',
    description: 'Osinkotuotto yli 3%',
    filters: { min_dividend_yield: 3 },
    sort_by: 'dividend_yield',
    icon: Percent,
    color: 'text-green-400 bg-green-500/20'
  },
  {
    id: 'value',
    name: 'Arvo-osakkeet',
    description: 'P/E alle 15',
    filters: { max_pe: 15 },
    sort_by: 'pe',
    sort_order: 'asc',
    icon: DollarSign,
    color: 'text-blue-400 bg-blue-500/20'
  },
  {
    id: 'growth',
    name: 'Kasvuosakkeet',
    description: '12kk tuotto yli 20%',
    filters: { min_return_12m: 20 },
    sort_by: 'return_12m',
    icon: TrendingUp,
    color: 'text-purple-400 bg-purple-500/20'
  },
  {
    id: 'momentum',
    name: 'Momentum',
    description: '3kk tuotto yli 10%',
    filters: { min_return_3m: 10 },
    sort_by: 'return_3m',
    icon: Zap,
    color: 'text-yellow-400 bg-yellow-500/20'
  },
  {
    id: 'low_risk',
    name: 'Matala riski',
    description: 'Volatiliteetti alle 25%',
    filters: { max_volatility: 25 },
    sort_by: 'volatility',
    sort_order: 'asc',
    icon: Shield,
    color: 'text-cyan-400 bg-cyan-500/20'
  },
  {
    id: 'large_cap',
    name: 'Suuryhtiöt',
    description: 'Markkina-arvo yli 1 mrd',
    filters: { min_market_cap: 1000000000 },
    sort_by: 'market_cap',
    icon: Building2,
    color: 'text-orange-400 bg-orange-500/20'
  },
  {
    id: 'low_pb',
    name: 'Matala P/B',
    description: 'Järjestä P/B mukaan',
    filters: {},
    sort_by: 'pb',
    sort_order: 'asc',
    icon: Activity,
    color: 'text-pink-400 bg-pink-500/20'
  }
];

const SECTORS = [
  'Industrials', 'Technology', 'Financials', 'Materials',
  'Consumer Discretionary', 'Consumer Staples', 'Communication Services',
  'Healthcare', 'Real Estate', 'Utilities', 'Energy'
];

interface ScreenerFilters {
  sector?: string;
  market?: string;
  min_dividend_yield?: number;
  max_pe?: number;
  min_pe?: number;
  max_volatility?: number;
  min_return_12m?: number;
  min_return_3m?: number;
  min_market_cap?: number;
  risk_level?: string;
}

async function fetchScreener(
  filters: ScreenerFilters,
  sortBy: string,
  sortOrder: string
) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      params.append(key, String(value));
    }
  });

  params.append('sort_by', sortBy);
  params.append('sort_order', sortOrder);
  params.append('limit', '100');

  const res = await fetch(`${API_BASE}/api/fi/screener?${params}`);
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
}

export default function ScreenerPage() {
  const [filters, setFilters] = useState<ScreenerFilters>({});
  const [sortBy, setSortBy] = useState('score');
  const [sortOrder, setSortOrder] = useState('desc');
  const [activePreset, setActivePreset] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['fi-screener', filters, sortBy, sortOrder],
    queryFn: () => fetchScreener(filters, sortBy, sortOrder),
    staleTime: 60 * 1000,
  });

  const applyPreset = (preset: typeof PRESETS[0]) => {
    setFilters(preset.filters);
    setSortBy(preset.sort_by);
    setSortOrder(preset.sort_order || 'desc');
    setActivePreset(preset.id);
  };

  const clearFilters = () => {
    setFilters({});
    setSortBy('score');
    setSortOrder('desc');
    setActivePreset(null);
  };

  const hasActiveFilters = Object.keys(filters).length > 0;

  const formatEur = (value: number | null | undefined) => {
    if (!value) return '—';
    if (value >= 1e9) return `${(value / 1e9).toFixed(1)} mrd €`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(0)} M €`;
    return `${value.toFixed(2)} €`;
  };

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '—';
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  // Sortable column header component
  const SortableHeader = ({
    label,
    sortKey,
    className = ''
  }: {
    label: string;
    sortKey: string;
    className?: string;
  }) => {
    const isActive = sortBy === sortKey;
    return (
      <th
        className={`px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 2xl:py-6 cursor-pointer hover:bg-slate-800/50 transition-colors select-none ${className}`}
        onClick={() => {
          if (isActive) {
            setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
          } else {
            setSortBy(sortKey);
            // Default to desc for most fields, asc for pe/pb/volatility/beta
            setSortOrder(['pe', 'pb', 'volatility', 'beta'].includes(sortKey) ? 'asc' : 'desc');
          }
          setActivePreset(null);
        }}
      >
        <div className="flex items-center justify-end gap-1.5 2xl:gap-3">
          <span>{label}</span>
          {isActive && (
            sortOrder === 'desc'
              ? <ChevronDown className="w-4 h-4 lg:w-5 lg:h-5 2xl:w-6 2xl:h-6 text-cyan-400" />
              : <ChevronUp className="w-4 h-4 lg:w-5 lg:h-5 2xl:w-6 2xl:h-6 text-cyan-400" />
          )}
        </div>
      </th>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-[2400px] mx-auto px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40 py-4 lg:py-5 2xl:py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 lg:gap-4 2xl:gap-6">
              <Link
                href="/fi/dashboard"
                className="p-2 lg:p-3 2xl:p-4 hover:bg-slate-700/50 rounded-lg 2xl:rounded-xl transition-colors text-slate-400 hover:text-white"
              >
                <ArrowLeft className="w-5 h-5 lg:w-6 lg:h-6 2xl:w-8 2xl:h-8" />
              </Link>

              <div className="p-2 lg:p-3 2xl:p-4 bg-gradient-to-br from-cyan-600 to-blue-600 rounded-xl 2xl:rounded-2xl">
                <Filter className="w-5 h-5 lg:w-6 lg:h-6 2xl:w-8 2xl:h-8 text-white" />
              </div>

              <div>
                <h1 className="text-xl md:text-2xl lg:text-3xl 2xl:text-6xl font-bold text-white">Osakeseulonta</h1>
                <p className="text-sm lg:text-base 2xl:text-2xl text-slate-400">Löydä parhaat osakkeet kriteereillä</p>
              </div>
            </div>

            <button
              onClick={() => refetch()}
              className="p-2 lg:p-3 2xl:p-4 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg 2xl:rounded-xl text-slate-400 hover:text-white transition-colors"
            >
              <RefreshCw className={`w-5 h-5 lg:w-6 lg:h-6 2xl:w-8 2xl:h-8 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[2400px] mx-auto px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40 py-6 lg:py-8 2xl:py-12">
        {/* Preset Buttons */}
        <section className="mb-6 lg:mb-8 2xl:mb-12">
          <h2 className="text-sm lg:text-base 2xl:text-2xl font-medium text-slate-400 mb-3 lg:mb-4 2xl:mb-6">Pikavalinnat</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:flex xl:flex-wrap gap-2 lg:gap-3 2xl:gap-5">
            {PRESETS.map((preset) => {
              const Icon = preset.icon;
              const isActive = activePreset === preset.id;
              return (
                <button
                  key={preset.id}
                  onClick={() => applyPreset(preset)}
                  className={`flex items-center justify-center sm:justify-start gap-2 lg:gap-3 2xl:gap-4 px-4 lg:px-5 2xl:px-8 py-2.5 lg:py-3 2xl:py-5 rounded-xl 2xl:rounded-2xl border transition-all ${
                    isActive
                      ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                      : 'bg-slate-800/60 border-slate-700/50 text-slate-300 hover:border-slate-600 hover:bg-slate-800'
                  }`}
                >
                  <Icon className="w-4 h-4 lg:w-5 lg:h-5 2xl:w-7 2xl:h-7" />
                  <span className="text-sm lg:text-base 2xl:text-2xl font-medium">{preset.name}</span>
                </button>
              );
            })}

            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="flex items-center gap-2 lg:gap-3 2xl:gap-4 px-4 lg:px-5 2xl:px-8 py-2.5 lg:py-3 2xl:py-5 rounded-xl 2xl:rounded-2xl border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-all"
              >
                <X className="w-4 h-4 lg:w-5 lg:h-5 2xl:w-7 2xl:h-7" />
                <span className="text-sm lg:text-base 2xl:text-2xl font-medium">Tyhjennä</span>
              </button>
            )}
          </div>
        </section>

        {/* Advanced Filters */}
        <section className="mb-6 lg:mb-8 2xl:mb-12 bg-slate-800/40 border border-slate-700/50 rounded-2xl 2xl:rounded-3xl p-4 lg:p-6 xl:p-8 2xl:p-12">
          <h2 className="text-base lg:text-lg 2xl:text-3xl font-medium text-slate-300 mb-4 lg:mb-6 2xl:mb-8">Tarkennettu haku</h2>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 lg:gap-4 xl:gap-5 2xl:gap-8">
            {/* Sector */}
            <div>
              <label className="text-xs lg:text-sm 2xl:text-xl text-slate-400 mb-1.5 lg:mb-2 2xl:mb-3 block font-medium">Toimiala</label>
              <select
                value={filters.sector || ''}
                onChange={(e) => setFilters({ ...filters, sector: e.target.value || undefined })}
                className="w-full px-3 lg:px-4 2xl:px-5 py-2.5 lg:py-3 2xl:py-4 bg-slate-900/60 border border-slate-700 rounded-xl 2xl:rounded-2xl text-sm lg:text-base 2xl:text-2xl text-white focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
              >
                <option value="">Kaikki</option>
                {SECTORS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* Market */}
            <div>
              <label className="text-xs lg:text-sm 2xl:text-xl text-slate-400 mb-1.5 lg:mb-2 2xl:mb-3 block font-medium">Markkina</label>
              <select
                value={filters.market || ''}
                onChange={(e) => setFilters({ ...filters, market: e.target.value || undefined })}
                className="w-full px-3 lg:px-4 2xl:px-5 py-2.5 lg:py-3 2xl:py-4 bg-slate-900/60 border border-slate-700 rounded-xl 2xl:rounded-2xl text-sm lg:text-base 2xl:text-2xl text-white focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
              >
                <option value="">Kaikki</option>
                <option value="Main">Päälista</option>
                <option value="First North">First North</option>
              </select>
            </div>

            {/* Min Dividend */}
            <div>
              <label className="text-xs lg:text-sm 2xl:text-xl text-slate-400 mb-1.5 lg:mb-2 2xl:mb-3 block font-medium">Min. osinko %</label>
              <input
                type="number"
                step="0.5"
                min="0"
                value={filters.min_dividend_yield || ''}
                onChange={(e) => setFilters({ ...filters, min_dividend_yield: e.target.value ? parseFloat(e.target.value) : undefined })}
                className="w-full px-3 lg:px-4 2xl:px-5 py-2.5 lg:py-3 2xl:py-4 bg-slate-900/60 border border-slate-700 rounded-xl 2xl:rounded-2xl text-sm lg:text-base 2xl:text-2xl text-white focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
                placeholder="esim. 3"
              />
            </div>

            {/* Max P/E */}
            <div>
              <label className="text-xs lg:text-sm 2xl:text-xl text-slate-400 mb-1.5 lg:mb-2 2xl:mb-3 block font-medium">Max P/E</label>
              <input
                type="number"
                min="0"
                value={filters.max_pe || ''}
                onChange={(e) => setFilters({ ...filters, max_pe: e.target.value ? parseFloat(e.target.value) : undefined })}
                className="w-full px-3 lg:px-4 2xl:px-5 py-2.5 lg:py-3 2xl:py-4 bg-slate-900/60 border border-slate-700 rounded-xl 2xl:rounded-2xl text-sm lg:text-base 2xl:text-2xl text-white focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
                placeholder="esim. 20"
              />
            </div>

            {/* Max Volatility */}
            <div>
              <label className="text-xs lg:text-sm 2xl:text-xl text-slate-400 mb-1.5 lg:mb-2 2xl:mb-3 block font-medium">Max volatiliteetti %</label>
              <input
                type="number"
                min="0"
                value={filters.max_volatility || ''}
                onChange={(e) => setFilters({ ...filters, max_volatility: e.target.value ? parseFloat(e.target.value) : undefined })}
                className="w-full px-3 lg:px-4 2xl:px-5 py-2.5 lg:py-3 2xl:py-4 bg-slate-900/60 border border-slate-700 rounded-xl 2xl:rounded-2xl text-sm lg:text-base 2xl:text-2xl text-white focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
                placeholder="esim. 30"
              />
            </div>

            {/* Min 12m Return */}
            <div>
              <label className="text-xs lg:text-sm 2xl:text-xl text-slate-400 mb-1.5 lg:mb-2 2xl:mb-3 block font-medium">Min 12kk tuotto %</label>
              <input
                type="number"
                value={filters.min_return_12m || ''}
                onChange={(e) => setFilters({ ...filters, min_return_12m: e.target.value ? parseFloat(e.target.value) : undefined })}
                className="w-full px-3 lg:px-4 2xl:px-5 py-2.5 lg:py-3 2xl:py-4 bg-slate-900/60 border border-slate-700 rounded-xl 2xl:rounded-2xl text-sm lg:text-base 2xl:text-2xl text-white focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
                placeholder="esim. 10"
              />
            </div>
          </div>

          {/* Sort Options */}
          <div className="mt-5 lg:mt-6 2xl:mt-10 pt-5 lg:pt-6 2xl:pt-10 border-t border-slate-700/50 flex flex-wrap items-center gap-4 lg:gap-6 2xl:gap-8">
            <div className="flex items-center gap-2 lg:gap-3 2xl:gap-4">
              <span className="text-sm lg:text-base 2xl:text-2xl text-slate-400 font-medium">Järjestä:</span>
              <select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setActivePreset(null);
                }}
                className="px-3 lg:px-4 2xl:px-6 py-2 lg:py-2.5 2xl:py-4 bg-slate-900/60 border border-slate-700 rounded-xl 2xl:rounded-2xl text-sm lg:text-base 2xl:text-2xl text-white focus:ring-2 focus:ring-cyan-500/50"
              >
                <option value="score">Pisteet</option>
                <option value="dividend_yield">Osinkotuotto %</option>
                <option value="dividend_amount">Osinko €</option>
                <option value="pe">P/E-luku</option>
                <option value="pb">P/B-luku</option>
                <option value="ev_ebit">EV/EBIT</option>
                <option value="roic">ROIC</option>
                <option value="return_12m">12kk tuotto</option>
                <option value="return_3m">3kk tuotto</option>
                <option value="change">Päivän muutos</option>
                <option value="beta">Beta</option>
                <option value="roe">ROE</option>
                <option value="volatility">Volatiliteetti</option>
                <option value="market_cap">Markkina-arvo</option>
              </select>
            </div>

            <div className="flex items-center gap-2 2xl:gap-3">
              <button
                onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
                className={`px-4 lg:px-5 2xl:px-8 py-2 lg:py-2.5 2xl:py-4 rounded-xl 2xl:rounded-2xl border text-sm lg:text-base 2xl:text-2xl font-medium transition-colors ${
                  sortOrder === 'desc'
                    ? 'bg-slate-700/50 border-slate-600 text-white'
                    : 'bg-slate-900/60 border-slate-700 text-slate-400 hover:text-white'
                }`}
              >
                {sortOrder === 'desc' ? '↓ Laskeva' : '↑ Nouseva'}
              </button>
            </div>

            <div className="text-sm lg:text-base 2xl:text-xl text-slate-500">
              Klikkaa sarakkeen otsikkoa järjestääksesi
            </div>
          </div>
        </section>

        {/* Results */}
        <section>
          <div className="flex items-center justify-between mb-4 lg:mb-6 2xl:mb-10">
            <h2 className="text-xl lg:text-2xl 2xl:text-5xl font-semibold text-white">
              Tulokset
              {data && (
                <span className="text-base lg:text-lg 2xl:text-3xl font-normal text-slate-400 ml-3 2xl:ml-5">
                  ({data.total_matches} osaketta)
                </span>
              )}
            </h2>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-16 lg:py-24 2xl:py-32">
              <div className="animate-spin rounded-full h-10 w-10 lg:h-12 lg:w-12 2xl:h-16 2xl:w-16 border-b-2 border-cyan-400"></div>
            </div>
          ) : error ? (
            <div className="text-center py-16 lg:py-24 2xl:py-32 text-red-400 text-lg lg:text-xl 2xl:text-3xl">
              Virhe ladattaessa tuloksia
            </div>
          ) : data?.data?.length === 0 ? (
            <div className="text-center py-16 lg:py-24 2xl:py-32 text-slate-400 text-lg lg:text-xl 2xl:text-3xl">
              Ei tuloksia annetuilla kriteereillä
            </div>
          ) : (
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl 2xl:rounded-3xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-900/60">
                    <tr className="text-left text-xs lg:text-sm xl:text-base 2xl:text-2xl text-slate-400 uppercase tracking-wider">
                      <th className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 2xl:py-6 font-semibold">Osake</th>
                      <th className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 2xl:py-6 text-right font-semibold">Hinta</th>
                      <SortableHeader label="Muutos" sortKey="change" className="text-right font-semibold" />
                      <SortableHeader label="P/E" sortKey="pe" className="text-right hidden sm:table-cell font-semibold" />
                      <SortableHeader label="P/B" sortKey="pb" className="text-right hidden lg:table-cell font-semibold" />
                      <SortableHeader label="EV/EBIT" sortKey="ev_ebit" className="text-right hidden xl:table-cell font-semibold" />
                      <SortableHeader label="ROIC" sortKey="roic" className="text-right hidden xl:table-cell font-semibold" />
                      <SortableHeader label="Osinko %" sortKey="dividend_yield" className="text-right hidden md:table-cell font-semibold" />
                      <SortableHeader label="Osinko €" sortKey="dividend_amount" className="text-right hidden xl:table-cell font-semibold" />
                      <SortableHeader label="12kk" sortKey="return_12m" className="text-right hidden lg:table-cell font-semibold" />
                      <SortableHeader label="Beta" sortKey="beta" className="text-right hidden xl:table-cell font-semibold" />
                      <SortableHeader label="Pisteet" sortKey="score" className="text-right font-semibold" />
                      <th className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 2xl:py-6 text-center hidden sm:table-cell font-semibold">Riski</th>
                      <th className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 2xl:py-6"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/50">
                    {data?.data?.map((stock: any) => (
                      <tr
                        key={stock.ticker}
                        className="hover:bg-slate-700/30 transition-colors"
                      >
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7">
                          <div>
                            <div className="font-semibold text-white text-sm lg:text-base xl:text-lg 2xl:text-3xl">{stock.ticker.replace('.HE', '')}</div>
                            <div className="text-xs lg:text-sm xl:text-base 2xl:text-2xl text-slate-400 truncate max-w-[100px] lg:max-w-[180px] xl:max-w-[250px] 2xl:max-w-[400px]">{stock.name}</div>
                          </div>
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right text-white text-sm lg:text-base xl:text-lg 2xl:text-3xl font-medium">
                          {stock.price != null ? Number(stock.price).toFixed(2) : '—'} €
                        </td>
                        <td className={`px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right text-sm lg:text-base xl:text-lg 2xl:text-3xl font-medium ${Number(stock.change || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatPercent(stock.change)}
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right text-slate-300 text-sm lg:text-base xl:text-lg 2xl:text-3xl hidden sm:table-cell">
                          {stock.peRatio != null && Number(stock.peRatio) > 0 ? Number(stock.peRatio).toFixed(1) : '—'}
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right text-slate-300 text-sm lg:text-base xl:text-lg 2xl:text-3xl hidden lg:table-cell">
                          {stock.pbRatio != null && Number(stock.pbRatio) > 0 ? Number(stock.pbRatio).toFixed(2) : '—'}
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right text-slate-300 text-sm lg:text-base xl:text-lg 2xl:text-3xl hidden xl:table-cell">
                          {stock.evEbit != null && Number(stock.evEbit) > 0 ? Number(stock.evEbit).toFixed(1) : '—'}
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right text-cyan-400 text-sm lg:text-base xl:text-lg 2xl:text-3xl hidden xl:table-cell">
                          {stock.roic != null && Number(stock.roic) > 0 ? `${(Number(stock.roic) * 100).toFixed(1)}%` : '—'}
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right text-green-400 text-sm lg:text-base xl:text-lg 2xl:text-3xl font-medium hidden md:table-cell">
                          {stock.dividendYield != null && Number(stock.dividendYield) > 0 ? `${Number(stock.dividendYield).toFixed(1)}%` : '—'}
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right text-cyan-400 text-sm lg:text-base xl:text-lg 2xl:text-3xl font-medium hidden xl:table-cell">
                          {stock.dividendAmount != null && Number(stock.dividendAmount) > 0 ? `${Number(stock.dividendAmount).toFixed(2)} €` : '—'}
                        </td>
                        <td className={`px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right text-sm lg:text-base xl:text-lg 2xl:text-3xl font-medium hidden lg:table-cell ${Number(stock.return12m || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatPercent(stock.return12m)}
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right text-slate-300 text-sm lg:text-base xl:text-lg 2xl:text-3xl hidden xl:table-cell">
                          {stock.beta != null ? Number(stock.beta).toFixed(2) : '—'}
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-right">
                          <span className={`font-bold text-sm lg:text-base xl:text-lg 2xl:text-3xl ${
                            Number(stock.score) >= 60 ? 'text-green-400' :
                            Number(stock.score) >= 40 ? 'text-yellow-400' : 'text-red-400'
                          }`}>
                            {stock.score ?? '—'}
                          </span>
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7 text-center hidden sm:table-cell">
                          <span className={`px-2 lg:px-3 xl:px-4 2xl:px-6 py-1 lg:py-1.5 2xl:py-2 text-xs lg:text-sm xl:text-base 2xl:text-2xl font-medium rounded-full ${
                            stock.riskLevel === 'LOW' ? 'bg-green-500/20 text-green-400' :
                            stock.riskLevel === 'HIGH' ? 'bg-red-500/20 text-red-400' :
                            'bg-yellow-500/20 text-yellow-400'
                          }`}>
                            {stock.riskLevel === 'LOW' ? 'Matala' :
                             stock.riskLevel === 'HIGH' ? 'Korkea' : 'Keski'}
                          </span>
                        </td>
                        <td className="px-3 lg:px-4 xl:px-5 2xl:px-8 py-3 lg:py-4 xl:py-5 2xl:py-7">
                          <Link
                            href={`/fi/stocks/${stock.ticker}`}
                            className="p-2 lg:p-2.5 xl:p-3 2xl:p-4 hover:bg-slate-600/50 rounded-xl 2xl:rounded-2xl text-slate-400 hover:text-white transition-colors inline-block"
                          >
                            <ChevronRight className="w-4 h-4 lg:w-5 lg:h-5 xl:w-6 xl:h-6 2xl:w-8 2xl:h-8" />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
