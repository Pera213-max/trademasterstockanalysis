"use client";

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3, TrendingUp, TrendingDown, ArrowLeft, Globe, Flag,
  Sparkles, Building2, Activity, ChevronRight, Star, AlertTriangle,
  ArrowUpRight, ArrowDownRight, Filter, Search, RefreshCw, PieChart,
  Target, Zap, Clock
} from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';
import {
  getFiScreener,
  getFiMovers,
  getFiSectors,
  getFiSignificantEvents,
  getFiMacro,
  getFiUniverse,
  getFiPotential,
  FiRankedStock,
  FiStock,
  FiMover,
  FiNewsEvent,
  FiMacroIndicator,
  FiPotentialStock,
} from '@/lib/api';

// Suomenkieliset tekstit
const t = {
  title: 'TradeMaster Pro',
  subtitle: 'Suomen Osakkeet',
  exchange: 'Nasdaq Helsinki',
  topRanked: 'Parhaat Osakkeet',
  topRankedDesc: 'Huippupisteytetyt parhaat suomalaiset osakkeet',
  movers: 'Päivän Liikkujat',
  gainers: 'Nousijat',
  losers: 'Laskijat',
  sectors: 'Toimialat',
  events: 'Tiedotteet & sisäpiiri',
  eventsDesc: 'Viimeisimmät pörssitiedotteet ja merkittävät tapahtumat',
  score: 'Pisteet',
  risk: 'Riski',
  price: 'Hinta',
  change: 'Muutos',
  return3m: '3kk tuotto',
  return12m: '12kk tuotto',
  volatility: 'Volatiliteetti',
  viewAnalysis: 'Katso analyysi',
  loading: 'Ladataan...',
  error: 'Virhe ladattaessa dataa',
  noData: 'Ei dataa saatavilla',
  allStocks: 'Kaikki osakkeet',
  liveData: 'Live Data',
  riskLow: 'Matala',
  riskMedium: 'Keskitaso',
  riskHigh: 'Korkea',
  disclaimer: 'Tämä ei ole sijoitusneuvontaa. Sijoittamiseen liittyy aina riskejä.',
  macro: 'Markkinakatsaus',
  macroDesc: 'Indeksit, valuutat ja korot',
  indices: 'Indeksit',
  currencies: 'Valuutat & Raaka-aineet',
  rates: 'Korot',
};

// Risk level badge
const RiskBadge = ({ level }: { level: string }) => {
  const colors = {
    LOW: 'bg-green-500/20 text-green-400 border-green-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    HIGH: 'bg-red-500/20 text-red-400 border-red-500/30',
  };
  const labels = {
    LOW: t.riskLow,
    MEDIUM: t.riskMedium,
    HIGH: t.riskHigh,
  };
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded border ${colors[level as keyof typeof colors] || colors.MEDIUM}`}>
      {labels[level as keyof typeof labels] || level}
    </span>
  );
};

// Format number with EUR currency
const formatEur = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('fi-FI', { style: 'currency', currency: 'EUR' }).format(value);
};

// Format percentage
const formatPercent = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '—';
  const formatted = value.toFixed(2);
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${formatted}%`;
};

const formatMacroValue = (indicator: FiMacroIndicator, kind: 'index' | 'currency' | 'rate') => {
  if (indicator.price === null || indicator.price === undefined) return '—';
  if (kind === 'rate') {
    return `${indicator.price.toFixed(2)}%`;
  }
  const isFx = indicator.code.includes('/') || indicator.symbol.includes('=X');
  const maxFraction = isFx ? 4 : 2;
  return indicator.price.toLocaleString('fi-FI', { maximumFractionDigits: maxFraction });
};

const formatMacroChange = (indicator: FiMacroIndicator) => {
  if (indicator.changePercent === null || indicator.changePercent === undefined) return null;
  const prefix = indicator.changePercent > 0 ? '+' : '';
  return `${prefix}${indicator.changePercent.toFixed(2)}%`;
};

const macroKindConfig = {
  index: {
    label: 'Indeksi',
    accent: 'from-cyan-500/30 to-blue-500/10',
    border: 'border-cyan-500/30',
    badge: 'bg-cyan-500/20 text-cyan-200 border-cyan-500/30',
    icon: Activity,
  },
  currency: {
    label: 'Valuutta',
    accent: 'from-emerald-500/30 to-teal-500/10',
    border: 'border-emerald-500/30',
    badge: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/30',
    icon: Globe,
  },
  rate: {
    label: 'Korko',
    accent: 'from-amber-500/30 to-orange-500/10',
    border: 'border-amber-500/30',
    badge: 'bg-amber-500/20 text-amber-200 border-amber-500/30',
    icon: TrendingUp,
  },
} as const;

const MacroRow = ({ indicator, kind }: { indicator: FiMacroIndicator; kind: 'index' | 'currency' | 'rate' }) => {
  const changeValue = indicator.changePercent ?? indicator.change ?? 0;
  const isUp = changeValue >= 0;
  const changeText = formatMacroChange(indicator);
  const config = macroKindConfig[kind];
  const Icon = config.icon;
  const barWidth = Math.min(100, Math.max(12, Math.abs(changeValue) * 12));
  return (
    <div className="group relative overflow-hidden rounded-xl 2xl:rounded-2xl border border-slate-700/50 bg-slate-900/60 p-3 2xl:p-5 transition-all hover:border-slate-600/70">
      <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-r ${config.accent}`} />
      <div className="relative flex items-center gap-3 2xl:gap-5">
        <div className={`w-11 h-11 2xl:w-16 2xl:h-16 rounded-xl 2xl:rounded-2xl border ${config.border} bg-slate-900/70 flex items-center justify-center shadow-sm`}>
          <Icon className="w-5 h-5 2xl:w-8 2xl:h-8 text-slate-100" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 2xl:gap-3">
            <span className={`text-[10px] 2xl:text-sm font-semibold tracking-wide px-2 2xl:px-3 py-0.5 2xl:py-1 rounded-full border ${config.badge}`}>
              {indicator.code}
            </span>
            <span className="text-sm 2xl:text-2xl text-white font-semibold truncate">{indicator.name}</span>
          </div>
          <div className="flex items-center gap-2 mt-1 2xl:mt-2 text-[11px] 2xl:text-lg text-slate-400">
            <span>{indicator.symbol}</span>
            <span className="text-slate-600">•</span>
            <span>{config.label}</span>
          </div>
          <div className="mt-2 2xl:mt-3 h-1.5 2xl:h-2.5 w-full rounded-full bg-slate-800/80 overflow-hidden">
            <div
              className={`h-full rounded-full ${isUp ? 'bg-emerald-400' : 'bg-red-400'}`}
              style={{ width: `${barWidth}%` }}
            />
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg 2xl:text-3xl font-semibold text-white">
            {formatMacroValue(indicator, kind)}
          </div>
          <div className={`mt-1 2xl:mt-2 inline-flex items-center gap-1 2xl:gap-2 px-2 2xl:px-3 py-0.5 2xl:py-1 rounded-full text-xs 2xl:text-lg font-medium ${isUp ? 'bg-emerald-500/15 text-emerald-300' : 'bg-red-500/15 text-red-300'
            }`}>
            {isUp ? <ArrowUpRight className="w-3 h-3 2xl:w-5 2xl:h-5" /> : <ArrowDownRight className="w-3 h-3 2xl:w-5 2xl:h-5" />}
            {changeText ?? '—'}
          </div>
        </div>
      </div>
    </div>
  );
};

const getHelsinkiMarketStatus = () => {
  const helsinkiNow = new Date(
    new Date().toLocaleString('en-US', { timeZone: 'Europe/Helsinki' })
  );
  const day = helsinkiNow.getDay(); // 0=Sun, 6=Sat
  const minutes = helsinkiNow.getHours() * 60 + helsinkiNow.getMinutes();
  const openMinutes = 10 * 60;
  const closeMinutes = 18 * 60 + 30;
  const isWeekend = day === 0 || day === 6;
  const isOpen = !isWeekend && minutes >= openMinutes && minutes < closeMinutes;
  const timeLabel = helsinkiNow.toLocaleTimeString('fi-FI', {
    hour: '2-digit',
    minute: '2-digit',
  });

  return { isOpen, timeLabel };
};

export default function FiDashboardPage() {
  const [stockSearch, setStockSearch] = useState<string>('');
  const [topMode, setTopMode] = useState<'best' | 'worst'>('best');
  const [showTopInfo, setShowTopInfo] = useState<boolean>(false);
  const [topSector, setTopSector] = useState<string>('');
  const [marketStatus, setMarketStatus] = useState(getHelsinkiMarketStatus());
  const [potentialTimeframe, setPotentialTimeframe] = useState<'short' | 'medium' | 'long'>('short');

  useEffect(() => {
    const id = setInterval(() => {
      setMarketStatus(getHelsinkiMarketStatus());
    }, 60 * 1000);
    return () => clearInterval(id);
  }, []);

  const {
    data: topListData,
    isLoading: topListLoading,
    error: topListError,
    refetch: refetchTopList
  } = useQuery({
    queryKey: ['fi-top-list', topMode, topSector],
    queryFn: () => getFiScreener({
      sort_by: 'score',
      sort_order: topMode === 'best' ? 'desc' : 'asc',
      limit: 25,
      sector: topSector || undefined,
    }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch movers
  const {
    data: moversData,
    isLoading: moversLoading,
    error: moversError
  } = useQuery({
    queryKey: ['fi-movers'],
    queryFn: () => getFiMovers(10),
    staleTime: 60 * 1000, // 1 minute
  });

  // Fetch sectors
  const {
    data: sectorsData,
    isLoading: sectorsLoading
  } = useQuery({
    queryKey: ['fi-sectors'],
    queryFn: getFiSectors,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });

  const { data: universeData } = useQuery({
    queryKey: ['fi-universe'],
    queryFn: getFiUniverse,
    staleTime: 60 * 60 * 1000, // 1 hour
  });

  // Fetch significant events (filtered, no duplicates, last 7 days)
  const {
    data: eventsData,
    isLoading: eventsLoading,
    error: eventsError
  } = useQuery({
    queryKey: ['fi-significant-events'],
    queryFn: () => getFiSignificantEvents(7, 8),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch macro indicators
  const {
    data: macroData,
    isLoading: macroLoading,
  } = useQuery({
    queryKey: ['fi-macro'],
    queryFn: getFiMacro,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch potential picks
  const {
    data: potentialData,
    isLoading: potentialLoading,
  } = useQuery({
    queryKey: ['fi-potential', potentialTimeframe],
    queryFn: () => getFiPotential(potentialTimeframe, 8),
    staleTime: 15 * 60 * 1000, // 15 minutes
  });

  const potentialStocks = potentialData?.data || [];

  const gainers = moversData?.gainers || [];
  const losers = moversData?.losers || [];
  const sectors = useMemo(
    () => (sectorsData?.data || []).slice().sort((a, b) => b.count - a.count),
    [sectorsData]
  );
  const sectorOptions = useMemo(() => sectors.map((s) => s.sector), [sectors]);
  const events = eventsData?.data || [];
  const macro = macroData?.data;
  const topList = topListData?.data || [];
  const allStocks: FiStock[] = universeData?.stocks || [];
  const macroUpdated = macro?.timestamp
    ? new Date(macro.timestamp).toLocaleTimeString('fi-FI', { hour: '2-digit', minute: '2-digit' })
    : null;
  const universeTotal = universeData?.totalCount ?? 173;
  const macroItems = [
    ...(macro?.indices || []),
    ...(macro?.currencies || []),
    ...(macro?.rates || []),
  ];
  const macroPositive = macroItems.filter((i) => (i.changePercent ?? 0) > 0).length;
  const macroNegative = macroItems.filter((i) => (i.changePercent ?? 0) < 0).length;
  const macroSignal =
    macroPositive - macroNegative >= 2
      ? { label: 'Risk-on', color: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' }
      : macroNegative - macroPositive >= 2
        ? { label: 'Risk-off', color: 'bg-red-500/15 text-red-300 border-red-500/30' }
        : { label: 'Neutraali', color: 'bg-slate-500/15 text-slate-300 border-slate-500/30' };

  const searchResults = useMemo(() => {
    const q = stockSearch.trim().toLowerCase();
    if (!q) return [];
    return allStocks
      .filter((stock) =>
        stock.ticker.toLowerCase().includes(q) ||
        stock.name.toLowerCase().includes(q)
      )
      .slice(0, 10);
  }, [stockSearch, allStocks]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-[2400px] mx-auto px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40 py-4 lg:py-5 2xl:py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 md:gap-4">
              {/* Back to Home */}
              <Link
                href="/"
                className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors text-slate-400 hover:text-white"
                title="Takaisin markkinavalintaan"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>

              {/* Logo */}
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl blur-lg opacity-50"></div>
                <div className="relative p-2 md:p-3 bg-gradient-to-br from-cyan-600 to-blue-600 rounded-xl">
                  <BarChart3 className="w-6 h-6 md:w-7 md:h-7 text-white" />
                </div>
              </div>

              {/* Brand */}
              <div>
                <h1 className="text-xl md:text-2xl lg:text-3xl 2xl:text-5xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                  {t.title}
                </h1>
                <div className="flex items-center gap-2 text-xs md:text-sm lg:text-base 2xl:text-xl text-slate-400">
                  <Flag className="w-3 h-3 lg:w-4 lg:h-4 2xl:w-5 2xl:h-5 text-cyan-400" />
                  <span>{t.subtitle}</span>
                  <span className="text-slate-600">•</span>
                  <span>{t.exchange}</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap justify-end">
              <Link
                href="/fi/screener"
                className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 sm:py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 rounded-lg text-cyan-400 transition-colors"
              >
                <Filter className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                <span className="hidden sm:inline text-sm font-medium">Seulonta</span>
              </Link>
              <Link
                href="/fi/compare"
                className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 sm:py-2 bg-slate-800/60 hover:bg-slate-700/60 border border-slate-700/50 rounded-lg text-slate-200 transition-colors"
              >
                <BarChart3 className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-cyan-300" />
                <span className="hidden sm:inline text-sm font-medium">Vertailu</span>
              </Link>
              <Link
                href="/fi/portfolio"
                className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 sm:py-2 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-emerald-200 transition-colors"
              >
                <PieChart className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-300" />
                <span className="hidden sm:inline text-sm font-medium">Salkkuanalyysi</span>
              </Link>
              <Link
                href="/fi/technicals"
                className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 sm:py-2 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg text-purple-200 transition-colors"
              >
                <Activity className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-purple-300" />
                <span className="hidden sm:inline text-sm font-medium">Tekninen</span>
              </Link>
              <div className="hidden lg:flex items-center gap-2 px-3 py-2 bg-slate-800/60 border border-slate-700/50 rounded-lg">
                <div className={`w-2 h-2 rounded-full ${marketStatus.isOpen ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`}></div>
                <span className="text-xs text-slate-200">Helsinki {marketStatus.timeLabel}</span>
                <span className={`text-xs font-semibold ${marketStatus.isOpen ? 'text-emerald-400' : 'text-red-400'}`}>
                  {marketStatus.isOpen ? 'AUKI' : 'SULJETTU'}
                </span>
              </div>
              <div className="hidden lg:flex items-center gap-2 px-3 py-2 bg-green-500/10 rounded-lg border border-green-500/20">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-green-400">{t.liveData}</span>
              </div>
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[2400px] mx-auto px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40 py-6 md:py-10 lg:py-12 2xl:py-16">
        <div className="space-y-8 lg:space-y-10 2xl:space-y-14">

          {/* Macro Indicators Section */}
          {!macroLoading && macro && (
            <section className="relative overflow-hidden bg-gradient-to-br from-slate-900/70 via-slate-900/40 to-slate-950/70 border border-slate-700/50 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-3 sm:p-4 md:p-6 lg:p-8 2xl:p-12">
              <div className="absolute -top-20 -right-20 w-48 h-48 rounded-full bg-cyan-500/10 blur-3xl"></div>
              <div className="absolute -bottom-24 -left-16 w-56 h-56 rounded-full bg-emerald-500/10 blur-3xl"></div>
              <div className="relative">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 sm:gap-4 mb-4 sm:mb-5 lg:mb-6 2xl:mb-10">
                  <div className="flex items-center gap-2 lg:gap-3 2xl:gap-4">
                    <Globe className="w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 2xl:w-8 2xl:h-8 text-blue-400" />
                    <div>
                      <h3 className="text-base sm:text-lg lg:text-xl 2xl:text-4xl font-semibold text-white">{t.macro}</h3>
                      <p className="text-[11px] sm:text-xs lg:text-sm 2xl:text-xl text-slate-400">{t.macroDesc}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-[10px] sm:text-[11px] px-2 sm:px-3 py-0.5 sm:py-1 rounded-full border ${macroSignal.color}`}>
                      {macroSignal.label}
                    </span>
                    {macroUpdated && (
                      <div className="text-[10px] sm:text-[11px] text-slate-500 bg-slate-900/60 border border-slate-700/40 rounded-full px-2 sm:px-3 py-0.5 sm:py-1">
                        Päivitetty {macroUpdated}
                      </div>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3 lg:gap-4 2xl:gap-6 mb-4 sm:mb-6 lg:mb-8 2xl:mb-12">
                  <div className="rounded-lg sm:rounded-xl 2xl:rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-2 sm:p-3 lg:p-4 2xl:p-6">
                    <div className="text-[10px] sm:text-xs lg:text-sm 2xl:text-xl text-emerald-200">Nousussa</div>
                    <div className="text-xl sm:text-2xl lg:text-3xl 2xl:text-6xl font-semibold text-white">{macroPositive}</div>
                  </div>
                  <div className="rounded-lg sm:rounded-xl 2xl:rounded-2xl border border-red-500/30 bg-red-500/10 p-2 sm:p-3 lg:p-4 2xl:p-6">
                    <div className="text-[10px] sm:text-xs lg:text-sm 2xl:text-xl text-red-200">Laskussa</div>
                    <div className="text-xl sm:text-2xl lg:text-3xl 2xl:text-6xl font-semibold text-white">{macroNegative}</div>
                  </div>
                  <div className="rounded-lg sm:rounded-xl 2xl:rounded-2xl border border-slate-600/40 bg-slate-900/50 p-2 sm:p-3 lg:p-4 2xl:p-6">
                    <div className="text-[10px] sm:text-xs lg:text-sm 2xl:text-xl text-slate-400">Seurannassa</div>
                    <div className="text-xl sm:text-2xl lg:text-3xl 2xl:text-6xl font-semibold text-white">{macroItems.length}</div>
                  </div>
                  <div className="rounded-lg sm:rounded-xl 2xl:rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-2 sm:p-3 lg:p-4 2xl:p-6">
                    <div className="text-[10px] sm:text-xs lg:text-sm 2xl:text-xl text-cyan-200">Signaali</div>
                    <div className="text-sm sm:text-base lg:text-lg 2xl:text-3xl font-semibold text-white mt-0.5 sm:mt-1">{macroSignal.label}</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-4 lg:gap-5 2xl:gap-8">
                  {/* Indices */}
                  <div className="rounded-xl sm:rounded-2xl 2xl:rounded-3xl border border-slate-700/50 bg-slate-900/60 p-3 sm:p-4 lg:p-5 2xl:p-8 shadow-sm overflow-hidden">
                    <div className="flex items-center justify-between mb-2 sm:mb-3 lg:mb-4 2xl:mb-6">
                      <div className="flex items-center gap-1.5 sm:gap-2 2xl:gap-3 text-slate-200">
                        <Activity className="w-3.5 h-3.5 sm:w-4 sm:h-4 lg:w-5 lg:h-5 2xl:w-7 2xl:h-7 text-cyan-400" />
                        <span className="text-xs sm:text-sm lg:text-base 2xl:text-2xl font-semibold">{t.indices}</span>
                      </div>
                      <span className="text-[10px] sm:text-[11px] lg:text-xs 2xl:text-lg text-slate-500">
                        {macro.indices?.length || 0} kpl
                      </span>
                    </div>
                    <div className="space-y-2">
                      {macro.indices?.filter((i: FiMacroIndicator) => i.price !== null).map((indicator: FiMacroIndicator) => (
                        <MacroRow key={indicator.code} indicator={indicator} kind="index" />
                      ))}
                    </div>
                  </div>
                  {/* Currencies & Commodities */}
                  <div className="rounded-xl sm:rounded-2xl 2xl:rounded-3xl border border-slate-700/50 bg-slate-900/60 p-3 sm:p-4 2xl:p-8 shadow-sm overflow-hidden">
                    <div className="flex items-center justify-between mb-2 sm:mb-3 2xl:mb-6">
                      <div className="flex items-center gap-1.5 sm:gap-2 2xl:gap-3 text-slate-200">
                        <Globe className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-7 2xl:h-7 text-emerald-400" />
                        <span className="text-xs sm:text-sm 2xl:text-2xl font-semibold">{t.currencies}</span>
                      </div>
                      <span className="text-[10px] sm:text-[11px] 2xl:text-lg text-slate-500">
                        {macro.currencies?.length || 0} kpl
                      </span>
                    </div>
                    <div className="space-y-2">
                      {macro.currencies?.filter((i: FiMacroIndicator) => i.price !== null).map((indicator: FiMacroIndicator) => (
                        <MacroRow key={indicator.code} indicator={indicator} kind="currency" />
                      ))}
                    </div>
                  </div>
                  {/* Rates */}
                  <div className="rounded-xl sm:rounded-2xl 2xl:rounded-3xl border border-slate-700/50 bg-slate-900/60 p-3 sm:p-4 2xl:p-8 shadow-sm overflow-hidden">
                    <div className="flex items-center justify-between mb-2 sm:mb-3 2xl:mb-6">
                      <div className="flex items-center gap-1.5 sm:gap-2 2xl:gap-3 text-slate-200">
                        <TrendingUp className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-7 2xl:h-7 text-yellow-400" />
                        <span className="text-xs sm:text-sm 2xl:text-2xl font-semibold">{t.rates}</span>
                      </div>
                      <span className="text-[10px] sm:text-[11px] 2xl:text-lg text-slate-500">
                        {macro.rates?.length || 0} kpl
                      </span>
                    </div>
                    <div className="space-y-2">
                      {macro.rates?.filter((i: FiMacroIndicator) => i.price !== null).map((indicator: FiMacroIndicator) => (
                        <MacroRow key={indicator.code} indicator={indicator} kind="rate" />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Top Movers Section */}
          <section className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 lg:gap-8 2xl:gap-12">
            {/* Gainers */}
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl lg:rounded-2xl 2xl:rounded-3xl p-3 sm:p-5 lg:p-6 2xl:p-10">
              <div className="flex items-center gap-2 lg:gap-3 2xl:gap-4 mb-3 sm:mb-4 lg:mb-5 2xl:mb-8">
                <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 2xl:w-9 2xl:h-9 text-green-400" />
                <h3 className="text-base sm:text-lg lg:text-xl 2xl:text-4xl font-semibold text-white">{t.gainers}</h3>
              </div>
              {moversLoading ? (
                <div className="text-slate-400 text-sm 2xl:text-2xl">{t.loading}</div>
              ) : moversError ? (
                <div className="text-red-400 text-sm 2xl:text-2xl">{t.error}</div>
              ) : gainers.length === 0 ? (
                <div className="text-slate-400 text-sm 2xl:text-2xl">{t.noData}</div>
              ) : (
                <div className="space-y-2 lg:space-y-3 2xl:space-y-5">
                  {gainers.slice(0, 5).map((stock: FiMover) => (
                    <Link
                      key={stock.ticker}
                      href={`/fi/stocks/${stock.ticker.replace('.HE', '')}`}
                      className="flex items-center justify-between p-3 lg:p-4 2xl:p-6 bg-slate-900/50 hover:bg-slate-900 rounded-lg lg:rounded-xl 2xl:rounded-2xl transition-colors group"
                    >
                      <div>
                        <div className="font-medium text-white text-sm lg:text-base 2xl:text-3xl group-hover:text-cyan-400 transition-colors">
                          {stock.ticker.replace('.HE', '')}
                        </div>
                        <div className="text-xs lg:text-sm 2xl:text-xl text-slate-400 truncate max-w-[150px] lg:max-w-[200px] 2xl:max-w-[300px]">{stock.name}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-white text-sm lg:text-base 2xl:text-3xl">{formatEur(stock.price)}</div>
                        <div className="text-green-400 text-sm lg:text-base 2xl:text-2xl flex items-center gap-1 2xl:gap-2 justify-end">
                          <ArrowUpRight className="w-3 h-3 lg:w-4 lg:h-4 2xl:w-6 2xl:h-6" />
                          {formatPercent(stock.changePercent)}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* Losers */}
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl lg:rounded-2xl 2xl:rounded-3xl p-3 sm:p-5 lg:p-6 2xl:p-10">
              <div className="flex items-center gap-2 lg:gap-3 2xl:gap-4 mb-3 sm:mb-4 lg:mb-5 2xl:mb-8">
                <TrendingDown className="w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 2xl:w-9 2xl:h-9 text-red-400" />
                <h3 className="text-base sm:text-lg lg:text-xl 2xl:text-4xl font-semibold text-white">{t.losers}</h3>
              </div>
              {moversLoading ? (
                <div className="text-slate-400 text-sm lg:text-base 2xl:text-2xl">{t.loading}</div>
              ) : moversError ? (
                <div className="text-red-400 text-sm lg:text-base 2xl:text-2xl">{t.error}</div>
              ) : losers.length === 0 ? (
                <div className="text-slate-400 text-sm lg:text-base 2xl:text-2xl">{t.noData}</div>
              ) : (
                <div className="space-y-2 lg:space-y-3 2xl:space-y-5">
                  {losers.slice(0, 5).map((stock: FiMover) => (
                    <Link
                      key={stock.ticker}
                      href={`/fi/stocks/${stock.ticker.replace('.HE', '')}`}
                      className="flex items-center justify-between p-3 lg:p-4 2xl:p-6 bg-slate-900/50 hover:bg-slate-900 rounded-lg lg:rounded-xl 2xl:rounded-2xl transition-colors group"
                    >
                      <div>
                        <div className="font-medium text-white text-sm lg:text-base 2xl:text-3xl group-hover:text-cyan-400 transition-colors">
                          {stock.ticker.replace('.HE', '')}
                        </div>
                        <div className="text-xs lg:text-sm 2xl:text-xl text-slate-400 truncate max-w-[150px] lg:max-w-[200px] 2xl:max-w-[300px]">{stock.name}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-white text-sm lg:text-base 2xl:text-3xl">{formatEur(stock.price)}</div>
                        <div className="text-red-400 text-sm lg:text-base 2xl:text-2xl flex items-center gap-1 2xl:gap-2 justify-end">
                          <ArrowDownRight className="w-3 h-3 lg:w-4 lg:h-4 2xl:w-6 2xl:h-6" />
                          {formatPercent(stock.changePercent)}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* Potential Picks Section */}
          <section className="bg-gradient-to-br from-purple-900/30 to-pink-900/30 border border-purple-700/40 rounded-lg sm:rounded-xl lg:rounded-2xl 2xl:rounded-3xl p-3 sm:p-5 lg:p-6 2xl:p-10">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4 lg:mb-6 2xl:mb-8">
              <div className="flex items-center gap-2 lg:gap-3 2xl:gap-4">
                <Target className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7 2xl:w-10 2xl:h-10 text-purple-400" />
                <div>
                  <h3 className="text-base sm:text-lg lg:text-xl 2xl:text-4xl font-semibold text-white">Potentiaali</h3>
                  <p className="text-[11px] sm:text-xs lg:text-sm 2xl:text-xl text-slate-400">Parhaan tuottopotentiaalin osakkeet</p>
                </div>
              </div>
              <div className="flex gap-1 sm:gap-2 2xl:gap-3 bg-slate-900/50 rounded-lg 2xl:rounded-xl p-1 2xl:p-2">
                <button
                  onClick={() => setPotentialTimeframe('short')}
                  className={`flex items-center gap-1 2xl:gap-2 px-2 sm:px-3 2xl:px-5 py-1 sm:py-1.5 2xl:py-3 rounded-md 2xl:rounded-lg text-xs sm:text-sm 2xl:text-xl font-medium transition-all ${potentialTimeframe === 'short'
                      ? 'bg-purple-600 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`}
                >
                  <Zap className="w-3 h-3 sm:w-3.5 sm:h-3.5 2xl:w-5 2xl:h-5" />
                  Lyhyt
                </button>
                <button
                  onClick={() => setPotentialTimeframe('medium')}
                  className={`flex items-center gap-1 2xl:gap-2 px-2 sm:px-3 2xl:px-5 py-1 sm:py-1.5 2xl:py-3 rounded-md 2xl:rounded-lg text-xs sm:text-sm 2xl:text-xl font-medium transition-all ${potentialTimeframe === 'medium'
                      ? 'bg-purple-600 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`}
                >
                  <Clock className="w-3 h-3 sm:w-3.5 sm:h-3.5 2xl:w-5 2xl:h-5" />
                  Keski
                </button>
                <button
                  onClick={() => setPotentialTimeframe('long')}
                  className={`flex items-center gap-1 2xl:gap-2 px-2 sm:px-3 2xl:px-5 py-1 sm:py-1.5 2xl:py-3 rounded-md 2xl:rounded-lg text-xs sm:text-sm 2xl:text-xl font-medium transition-all ${potentialTimeframe === 'long'
                      ? 'bg-purple-600 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`}
                >
                  <TrendingUp className="w-3 h-3 sm:w-3.5 sm:h-3.5 2xl:w-5 2xl:h-5" />
                  Pitkä
                </button>
              </div>
            </div>
            <div className="text-[10px] sm:text-xs 2xl:text-lg text-slate-500 mb-3 2xl:mb-5">
              {potentialTimeframe === 'short' && 'Päivistä viikkoihin: Momentum, päivän liike, tekninen analyysi'}
              {potentialTimeframe === 'medium' && 'Viikoista kuukausiin: Kasvu, arvostus, sektorimomentti'}
              {potentialTimeframe === 'long' && 'Kuukausista vuosiin: Aliarvostus, laatu, osingot'}
            </div>
            {potentialLoading ? (
              <div className="text-slate-400 text-sm 2xl:text-2xl">{t.loading}</div>
            ) : potentialStocks.length === 0 ? (
              <div className="text-slate-400 text-sm 2xl:text-2xl">{t.noData}</div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 2xl:gap-6">
                {potentialStocks.slice(0, 8).map((stock: FiPotentialStock, index: number) => (
                  <Link
                    key={stock.ticker}
                    href={`/fi/stocks/${stock.ticker.replace('.HE', '')}`}
                    className="group bg-slate-900/60 hover:bg-slate-900 border border-slate-700/40 hover:border-purple-500/50 rounded-lg lg:rounded-xl 2xl:rounded-2xl p-3 lg:p-4 2xl:p-6 transition-all"
                  >
                    <div className="flex items-start justify-between mb-2 2xl:mb-4">
                      <div>
                        <div className="flex items-center gap-1.5 2xl:gap-3 mb-1">
                          <span className="text-[10px] sm:text-xs 2xl:text-base px-1.5 2xl:px-3 py-0.5 2xl:py-1 bg-purple-500/30 text-purple-300 rounded 2xl:rounded-lg font-bold">
                            #{index + 1}
                          </span>
                          <span className="font-semibold text-white text-sm lg:text-base 2xl:text-2xl group-hover:text-purple-400 transition-colors">
                            {stock.ticker.replace('.HE', '')}
                          </span>
                        </div>
                        <div className="text-[10px] sm:text-xs 2xl:text-lg text-slate-400 truncate max-w-[120px] lg:max-w-[150px] 2xl:max-w-[200px]">
                          {stock.name}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-purple-400 font-bold text-sm lg:text-base 2xl:text-2xl">
                          {stock.potentialScore.toFixed(0)}
                        </div>
                        <div className="text-[9px] sm:text-[10px] 2xl:text-sm text-slate-500">pistettä</div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-[10px] sm:text-xs 2xl:text-lg mb-2 2xl:mb-4">
                      <span className="text-slate-300">{formatEur(stock.price)}</span>
                      <span className={stock.change >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                      </span>
                    </div>
                    {stock.reasons.length > 0 && (
                      <div className="space-y-1 2xl:space-y-2">
                        {stock.reasons.slice(0, 2).map((reason, i) => (
                          <div key={i} className="text-[9px] sm:text-[10px] 2xl:text-sm text-slate-400 flex items-start gap-1 2xl:gap-2">
                            <span className="text-purple-400 mt-0.5">•</span>
                            <span className="line-clamp-1">{reason}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </section>

          {/* Latest Disclosures */}
          <section className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl lg:rounded-2xl 2xl:rounded-3xl p-3 sm:p-5 lg:p-6 2xl:p-10">
            <div className="flex items-center gap-2 lg:gap-3 2xl:gap-4 mb-3 sm:mb-4 lg:mb-5 2xl:mb-8">
              <Star className="w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 2xl:w-9 2xl:h-9 text-yellow-400" />
              <div>
                <h3 className="text-base sm:text-lg lg:text-xl 2xl:text-4xl font-semibold text-white">{t.events}</h3>
                <p className="text-[11px] sm:text-xs lg:text-sm 2xl:text-xl text-slate-400">{t.eventsDesc}</p>
              </div>
            </div>
            {eventsLoading ? (
              <div className="text-slate-400 text-sm 2xl:text-2xl">{t.loading}</div>
            ) : eventsError ? (
              <div className="text-red-400 text-sm 2xl:text-2xl">{t.error}</div>
            ) : events.length === 0 ? (
              <div className="text-slate-400 text-sm 2xl:text-2xl">{t.noData}</div>
            ) : (
              <div className="space-y-2 2xl:space-y-4">
                {events.map((event: FiNewsEvent) => (
                  <div
                    key={event.id}
                    className="p-3 2xl:p-6 bg-slate-900/50 rounded-lg 2xl:rounded-2xl border border-slate-700/40"
                  >
                    <div className="flex items-start justify-between gap-2 2xl:gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 2xl:gap-3 mb-1 2xl:mb-3 flex-wrap">
                          {event.ticker && (
                            <Link
                              href={`/fi/stocks/${event.ticker.replace('.HE', '')}`}
                              className="text-xs 2xl:text-lg font-medium px-2 2xl:px-4 py-0.5 2xl:py-1.5 bg-cyan-500/20 text-cyan-400 rounded 2xl:rounded-lg hover:bg-cyan-500/30"
                            >
                              {event.ticker.replace('.HE', '')}
                            </Link>
                          )}
                          {event.impact && (
                            <span className={`text-xs 2xl:text-lg px-2 2xl:px-4 py-0.5 2xl:py-1.5 rounded 2xl:rounded-lg ${event.impact === 'POSITIVE' ? 'bg-green-500/20 text-green-400' :
                                event.impact === 'NEGATIVE' ? 'bg-red-500/20 text-red-400' :
                                  event.impact === 'MIXED' ? 'bg-yellow-500/20 text-yellow-400' :
                                    'bg-slate-500/20 text-slate-400'
                              }`}>
                              {event.impact === 'POSITIVE' ? 'Positiivinen' :
                                event.impact === 'NEGATIVE' ? 'Negatiivinen' :
                                  event.impact === 'MIXED' ? 'Sekalainen' : 'Neutraali'}
                            </span>
                          )}
                          <span className="text-xs 2xl:text-lg text-slate-500">
                            {event.published_at ? new Date(event.published_at).toLocaleDateString('fi-FI') : ''}
                          </span>
                        </div>
                        <div className="font-medium text-white text-sm 2xl:text-2xl">{event.title}</div>
                        {event.summary && (
                          <div className="text-xs 2xl:text-xl text-slate-400 mt-1 2xl:mt-2 line-clamp-2">
                            {event.summary}
                          </div>
                        )}
                        {event.source_url && (
                          <a
                            href={event.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs 2xl:text-lg text-cyan-400 hover:text-cyan-300 mt-1 2xl:mt-2 inline-block"
                          >
                            {event.source || 'Lähde'} →
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Top Ranked Stocks */}
          <section className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl lg:rounded-2xl 2xl:rounded-3xl p-3 sm:p-5 md:p-6 lg:p-8 2xl:p-12">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 sm:gap-4 lg:gap-6 2xl:gap-10 mb-4 sm:mb-6 lg:mb-8 2xl:mb-12">
              <div>
                <div className="flex items-center gap-2 lg:gap-3 2xl:gap-4 mb-1 2xl:mb-3">
                  <Sparkles className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7 2xl:w-10 2xl:h-10 text-yellow-400" />
                  <h2 className="text-lg sm:text-xl md:text-2xl lg:text-3xl 2xl:text-6xl font-bold text-white">{t.topRanked}</h2>
                </div>
                <p className="text-slate-400 text-xs sm:text-sm lg:text-base 2xl:text-2xl">{t.topRankedDesc}</p>
              </div>

              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 2xl:gap-4">
                <div className="flex items-center gap-0.5 sm:gap-1 2xl:gap-2 bg-slate-900/60 border border-slate-700 rounded-full p-0.5 sm:p-1 2xl:p-2 text-[10px] sm:text-xs 2xl:text-xl">
                  <button
                    onClick={() => setTopMode('best')}
                    className={`px-2 sm:px-3 2xl:px-5 py-0.5 sm:py-1 2xl:py-2 rounded-full transition ${topMode === 'best'
                        ? 'bg-cyan-600 text-white'
                        : 'text-slate-300 hover:text-white'
                      }`}
                  >
                    <span className="hidden sm:inline">Top 25 </span>parhaat
                  </button>
                  <button
                    onClick={() => setTopMode('worst')}
                    className={`px-2 sm:px-3 2xl:px-5 py-0.5 sm:py-1 2xl:py-2 rounded-full transition ${topMode === 'worst'
                        ? 'bg-cyan-600 text-white'
                        : 'text-slate-300 hover:text-white'
                      }`}
                  >
                    <span className="hidden sm:inline">Top 25 </span>heikoimmat
                  </button>
                </div>

                <div className="hidden sm:flex items-center gap-2 2xl:gap-3 bg-slate-900/60 border border-slate-700 rounded-full px-3 2xl:px-5 py-1 2xl:py-2 text-xs 2xl:text-xl">
                  <span className="text-slate-500">Toimiala</span>
                  <select
                    value={topSector}
                    onChange={(e) => setTopSector(e.target.value)}
                    className="bg-transparent text-slate-200 text-xs 2xl:text-xl focus:outline-none max-w-[140px] 2xl:max-w-[250px] truncate"
                  >
                    <option value="">Kaikki</option>
                    {sectorOptions.map((sector) => (
                      <option key={sector} value={sector}>{sector}</option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  onClick={() => setShowTopInfo((prev) => !prev)}
                  className="w-6 h-6 sm:w-7 sm:h-7 2xl:w-10 2xl:h-10 rounded-full border border-slate-600 text-slate-300 text-[10px] sm:text-xs 2xl:text-xl font-semibold flex items-center justify-center hover:border-cyan-500/50 hover:text-cyan-200 transition"
                  aria-label="Ohje"
                >
                  ?
                </button>

                <button
                  onClick={() => refetchTopList()}
                  className="p-1.5 sm:p-2 2xl:p-3 bg-slate-900/60 border border-slate-700 rounded-lg 2xl:rounded-xl text-slate-400 hover:text-white hover:border-cyan-500 transition-colors"
                  title="Päivitä"
                >
                  <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-6 2xl:h-6" />
                </button>
              </div>
            </div>

            {showTopInfo && (
              <div className="mb-3 sm:mb-4 2xl:mb-6 rounded-lg 2xl:rounded-xl border border-slate-700/60 bg-slate-900/80 p-2 sm:p-3 2xl:p-5 text-[11px] sm:text-xs 2xl:text-xl text-slate-300">
                Listassa näkyy vain 25 parasta tai 25 heikointa. Haku näyttää tulokset kaikista osakkeista ilman kokolistaa.
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 2xl:gap-4 mb-3 sm:mb-4 2xl:mb-8">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 sm:left-3 2xl:left-5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-6 2xl:h-6 text-slate-400" />
                <input
                  type="text"
                  placeholder="Hae osaketta (ticker tai nimi)"
                  value={stockSearch}
                  onChange={(e) => setStockSearch(e.target.value)}
                  className="pl-8 sm:pl-10 2xl:pl-14 pr-3 sm:pr-4 2xl:pr-6 py-1.5 sm:py-2 2xl:py-4 bg-slate-900/60 border border-slate-700 rounded-lg 2xl:rounded-xl text-white placeholder-slate-500 text-xs sm:text-sm 2xl:text-2xl focus:outline-none focus:border-cyan-500 w-full"
                />
              </div>
              {stockSearch && (
                <button
                  onClick={() => setStockSearch('')}
                  className="px-3 2xl:px-6 py-1.5 sm:py-2 2xl:py-4 bg-slate-900/60 border border-slate-700 rounded-lg 2xl:rounded-xl text-slate-300 text-xs sm:text-sm 2xl:text-2xl hover:text-white"
                >
                  Tyhjennä
                </button>
              )}
            </div>

            {stockSearch ? (
              <div className="space-y-3 2xl:space-y-6">
                <div className="text-xs 2xl:text-xl text-slate-400">Hakutulokset ({searchResults.length})</div>
                {searchResults.length === 0 ? (
                  <div className="text-sm 2xl:text-2xl text-slate-400">Ei osumia.</div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 2xl:gap-4">
                    {searchResults.map((stock) => (
                      <Link
                        key={stock.ticker}
                        href={`/fi/stocks/${stock.ticker.replace('.HE', '')}`}
                        className="flex items-center justify-between rounded-lg 2xl:rounded-2xl border border-slate-700/60 bg-slate-900/60 px-3 2xl:px-6 py-2 2xl:py-5 text-sm 2xl:text-2xl text-slate-200 hover:border-cyan-500/40"
                      >
                        <div>
                          <div className="font-semibold 2xl:text-3xl">{stock.ticker.replace('.HE', '')}</div>
                          <div className="text-xs 2xl:text-xl text-slate-500 truncate max-w-[200px] 2xl:max-w-[350px]">{stock.name}</div>
                        </div>
                        <div className="flex items-center gap-1 2xl:gap-2 text-xs 2xl:text-xl text-cyan-300">
                          <span className="hidden sm:inline">Katso analyysi</span>
                          <ChevronRight className="w-4 h-4 2xl:w-6 2xl:h-6 text-slate-400" />
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ) : topListLoading ? (
              <div className="flex items-center justify-center py-10 2xl:py-16">
                <div className="animate-spin rounded-full h-8 w-8 2xl:h-12 2xl:w-12 border-b-2 border-cyan-400"></div>
                <span className="ml-3 2xl:ml-5 text-slate-400 2xl:text-2xl">{t.loading}</span>
              </div>
            ) : topListError ? (
              <div className="text-center py-10 2xl:py-16">
                <AlertTriangle className="w-12 h-12 2xl:w-16 2xl:h-16 text-red-400 mx-auto mb-3 2xl:mb-5" />
                <p className="text-red-400 2xl:text-2xl">{t.error}</p>
              </div>
            ) : topList.length === 0 ? (
              <div className="text-center py-10 2xl:py-16 text-slate-400 2xl:text-2xl">{t.noData}</div>
            ) : (
              <div className="space-y-3 2xl:space-y-6">
                {topList.map((stock: FiRankedStock, index: number) => {
                  const isPositive = stock.change >= 0;
                  const return3m = stock.return3m;
                  const return12m = stock.return12m;
                  const return3mClass = return3m === null || return3m === undefined
                    ? 'text-slate-400'
                    : return3m >= 0
                      ? 'text-green-400'
                      : 'text-red-400';
                  const return12mClass = return12m === null || return12m === undefined
                    ? 'text-slate-400'
                    : return12m >= 0
                      ? 'text-green-400'
                      : 'text-red-400';
                  const scoreValue = Math.max(0, Math.min(100, Number(stock.score) || 0));
                  const accent = topMode === 'best' ? 'from-cyan-500 to-blue-500' : 'from-red-500 to-orange-500';
                  const accentBorder = topMode === 'best' ? 'border-l-cyan-500/60' : 'border-l-red-500/60';
                  const badgeClass = topMode === 'best'
                    ? 'bg-cyan-500/20 text-cyan-200 border-cyan-500/30'
                    : 'bg-red-500/20 text-red-200 border-red-500/30';
                  const riskClass = stock.riskLevel === 'LOW'
                    ? 'bg-emerald-500/20 text-emerald-200 border-emerald-500/30'
                    : stock.riskLevel === 'HIGH'
                      ? 'bg-red-500/20 text-red-200 border-red-500/30'
                      : 'bg-yellow-500/20 text-yellow-200 border-yellow-500/30';
                  const riskLabel = stock.riskLevel === 'LOW'
                    ? t.riskLow
                    : stock.riskLevel === 'HIGH'
                      ? t.riskHigh
                      : t.riskMedium;
                  return (
                    <Link
                      key={stock.ticker}
                      href={`/fi/stocks/${stock.ticker.replace('.HE', '')}`}
                      className={`block w-full group rounded-2xl 2xl:rounded-3xl border border-slate-700/60 border-l-4 ${accentBorder} bg-slate-900/70 p-4 2xl:p-8 transition-all hover:border-cyan-500/40`}
                    >
                      <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_minmax(0,240px)] lg:grid-cols-[minmax(0,1fr)_minmax(0,320px)] 2xl:grid-cols-[minmax(0,1fr)_minmax(0,500px)] gap-4 2xl:gap-8 items-start">
                        <div className="flex items-start gap-4 2xl:gap-6 min-w-0">
                          <div className={`w-12 h-12 2xl:w-20 2xl:h-20 rounded-xl 2xl:rounded-2xl flex items-center justify-center text-sm 2xl:text-3xl font-bold border ${badgeClass}`}>
                            #{index + 1}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2 2xl:gap-4">
                              <span className="text-lg 2xl:text-4xl font-semibold text-white">{stock.ticker.replace('.HE', '')}</span>
                              <span className="text-xs 2xl:text-2xl text-slate-400 truncate max-w-[220px] 2xl:max-w-[400px]">{stock.name}</span>
                              {stock.sector && (
                                <span className="hidden md:inline text-[11px] 2xl:text-lg text-slate-500">{stock.sector}</span>
                              )}
                            </div>
                            <div className="mt-2 2xl:mt-4 flex flex-wrap items-center gap-2 2xl:gap-3 text-xs 2xl:text-xl">
                              <span className={`px-2 2xl:px-4 py-0.5 2xl:py-1.5 rounded-full border ${badgeClass}`}>
                                Pisteet {stock.score}
                              </span>
                              <span className={`px-2 2xl:px-4 py-0.5 2xl:py-1.5 rounded-full border ${riskClass}`}>
                                {riskLabel}
                              </span>
                              {stock.volatility !== null && stock.volatility !== undefined && (
                                <span className="px-2 2xl:px-4 py-0.5 2xl:py-1.5 rounded-full border border-slate-600/60 text-slate-300">
                                  Vol {stock.volatility.toFixed(1)}%
                                </span>
                              )}
                            </div>
                            <div className="mt-2 2xl:mt-4 h-2 2xl:h-3 w-full rounded-full bg-slate-800/80 overflow-hidden">
                              <div
                                className={`h-full bg-gradient-to-r ${accent}`}
                                style={{ width: `${scoreValue}%` }}
                              />
                            </div>
                            <div className="mt-2 2xl:mt-4 inline-flex items-center gap-1 2xl:gap-2 text-[11px] 2xl:text-xl text-cyan-300">
                              <span className="hidden sm:inline">Katso analyysi</span>
                              <ChevronRight className="w-3 h-3 2xl:w-5 2xl:h-5" />
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 2xl:gap-4 text-left md:text-right w-full md:w-auto md:min-w-[240px] lg:min-w-[320px] 2xl:min-w-[500px]">
                          <div className="min-w-0 rounded-lg 2xl:rounded-xl border border-slate-700/60 bg-slate-900/60 p-2 2xl:p-4">
                            <div className="text-[10px] sm:text-[11px] 2xl:text-lg text-slate-500">Hinta</div>
                            <div className="text-sm 2xl:text-3xl font-semibold text-white">{formatEur(stock.price)}</div>
                          </div>
                          <div className="min-w-0 rounded-lg 2xl:rounded-xl border border-slate-700/60 bg-slate-900/60 p-2 2xl:p-4">
                            <div className="text-[10px] sm:text-[11px] 2xl:text-lg text-slate-500">Paiva</div>
                            <div className={`text-sm 2xl:text-3xl font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                              {formatPercent(stock.change)}
                            </div>
                          </div>
                          <div className="min-w-0 rounded-lg 2xl:rounded-xl border border-slate-700/60 bg-slate-900/60 p-2 2xl:p-4">
                            <div className="text-[10px] sm:text-[11px] 2xl:text-lg text-slate-500">3kk</div>
                            <div className={`text-sm 2xl:text-3xl font-semibold ${return3mClass}`}>
                              {formatPercent(return3m)}
                            </div>
                          </div>
                          <div className="min-w-0 rounded-lg 2xl:rounded-xl border border-slate-700/60 bg-slate-900/60 p-2 2xl:p-4">
                            <div className="text-[10px] sm:text-[11px] 2xl:text-lg text-slate-500">12kk</div>
                            <div className={`text-sm 2xl:text-3xl font-semibold ${return12mClass}`}>
                              {formatPercent(return12m)}
                            </div>
                          </div>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}

          </section>

          {/* Sectors */}
          {sectors.length > 0 && (
            <section className="bg-slate-900/60 border border-slate-700/60 rounded-lg sm:rounded-2xl 2xl:rounded-3xl p-3 sm:p-5 2xl:p-10">
              <div className="flex items-center gap-2 2xl:gap-4 mb-3 sm:mb-4 2xl:mb-8">
                <Building2 className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8 text-purple-400" />
                <h3 className="text-base sm:text-lg 2xl:text-4xl font-semibold text-white">{t.sectors}</h3>
                <span className="text-[10px] sm:text-xs 2xl:text-xl text-slate-500">• {sectors.length} toimialaa</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 sm:gap-3 2xl:gap-5">
                <button
                  type="button"
                  onClick={() => setTopSector('')}
                  className={`p-2 sm:p-3 2xl:p-5 rounded-lg sm:rounded-xl 2xl:rounded-2xl border text-left transition ${topSector === ''
                      ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-200'
                      : 'bg-slate-950/60 border-slate-700/60 text-slate-300 hover:border-slate-500/70'
                    }`}
                >
                  <div className="font-medium text-xs sm:text-sm 2xl:text-2xl">Kaikki</div>
                  <div className="text-[10px] sm:text-xs 2xl:text-lg text-slate-500">Top-lista</div>
                </button>
                {sectors.map((sector) => {
                  const active = topSector === sector.sector;
                  return (
                    <button
                      key={sector.sector}
                      type="button"
                      onClick={() => setTopSector(sector.sector)}
                      className={`p-2 sm:p-3 2xl:p-5 rounded-lg sm:rounded-xl 2xl:rounded-2xl border text-left transition ${active
                          ? 'bg-purple-500/15 border-purple-500/40 text-purple-200'
                          : 'bg-slate-950/60 border-slate-700/60 text-slate-300 hover:border-slate-500/70'
                        }`}
                    >
                      <div className="font-medium text-xs sm:text-sm 2xl:text-2xl truncate">{sector.sector}</div>
                      <div className="text-[10px] sm:text-xs 2xl:text-lg text-slate-500">{sector.count} osaketta</div>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 bg-slate-900/30 mt-8 sm:mt-12 2xl:mt-20 py-6 sm:py-8 2xl:py-12">
        <div className="max-w-[2400px] mx-auto px-4 md:px-6 2xl:px-40">
          <div className="flex flex-col md:flex-row items-center justify-between gap-3 sm:gap-4 2xl:gap-8 text-xs sm:text-sm 2xl:text-2xl text-slate-500">
            <div className="flex items-center gap-1.5 sm:gap-2 2xl:gap-4 flex-wrap justify-center">
              <BarChart3 className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8 text-cyan-400" />
              <span>TradeMaster Pro</span>
              <span className="hidden sm:inline">•</span>
              <span className="hidden sm:inline">Nasdaq Helsinki</span>
              <span className="hidden sm:inline">•</span>
              <span className="hidden sm:inline">{universeTotal} osaketta</span>
            </div>
            <p className="text-center md:text-right max-w-md 2xl:max-w-2xl text-[11px] sm:text-sm 2xl:text-xl">
              {t.disclaimer}
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
