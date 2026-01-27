"use client";

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3, TrendingUp, TrendingDown, ArrowLeft, Flag,
  Activity, AlertTriangle, ChevronRight, Star, Target,
  ArrowUpRight, ArrowDownRight, Info, RefreshCw, ExternalLink,
  Shield, Zap, PieChart, Calendar, DollarSign
} from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';
import { getFiAnalysis, getFiHistory, getFiTechnicals, FiHistoryPoint } from '@/lib/api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Area, AreaChart
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
  title: 'OsakedataX',
  subtitle: 'Osakeanalyysi',
  backToDashboard: 'Takaisin',
  loading: 'Ladataan...',
  error: 'Virhe ladattaessa dataa',
  noData: 'Ei dataa saatavilla',
  summary: 'Yhteenveto',
  strengths: 'Vahvuudet',
  risks: 'Huomioitavaa',
  keyFacts: 'Avainluvut',
  riskLevel: 'Riskitaso',
  riskLow: 'Matala',
  riskMedium: 'Keskitaso',
  riskHigh: 'Korkea',
  currentPrice: 'Hinta',
  change: 'Muutos',
  previousClose: 'Edellinen päätös',
  dayRange: 'Päivän vaihteluväli',
  open: 'Avaus',
  volume: 'Volyymi',
  metrics: 'Tunnusluvut',
  volatility: 'Volatiliteetti',
  maxDrawdown: 'Maks. lasku',
  sharpeRatio: 'Sharpe Ratio',
  return3m: '3kk tuotto',
  return12m: '12kk tuotto',
  valuation: 'Arvostus',
  marketCap: 'Markkina-arvo',
  peRatio: 'P/E',
  forwardPE: 'Forward P/E',
  priceToBook: 'P/B',
  pegRatio: 'PEG',
  dividendYield: 'Osinkotuotto',
  evEbit: 'EV/EBIT',
  profitability: 'Kannattavuus',
  profitMargin: 'Voittomarginaali',
  returnOnEquity: 'ROE',
  roic: 'ROIC',
  growth: 'Kasvu',
  revenueGrowth: 'Liikevaihdon kasvu',
  earningsGrowth: 'Tuloksen kasvu',
  balance: 'Tase ja riski',
  debtToEquity: 'Velkaantumisaste',
  beta: 'Beta',
  yearRange: '52 vkn vaihteluväli',
  avgVolume: 'Kesk. volyymi',
  priceChart: 'Hintakehitys (1v)',
  sector: 'Toimiala',
  industry: 'Ala',
  exchange: 'Pörssi',
  currency: 'Valuutta',
  disclaimer: 'Tämä ei ole sijoitusneuvontaa. Sijoittamiseen liittyy aina riskejä.',
  newsEvents: 'Tiedotteet & uutiset',
  eventSummary: '30 pv yhteenveto',
  impactPositive: 'Positiivinen',
  impactNegative: 'Negatiivinen',
  impactNeutral: 'Neutraali',
  impactMixed: 'Sekalainen',
  newsPageLink: 'Nasdaq-tiedotteet',
  irNewsLink: 'IR-uutissivu',
  investorPageLink: 'Sijoittajasivu',
  sourceLabel: 'Lähde',
  disclosures: 'Tiedotteet & sisäpiiri',
  companyNews: 'Yhtiön uutiset',
  irHeadlines: 'IR-uutiset',
  irHeadlinesDesc: 'Uusimmat tiedotteet yhtiön IR-uutissivulta',
  technicalAnalysis: 'Tekninen analyysi',
  recommendation: 'Suositus',
  buy: 'OSTA',
  hold: 'PIDÄ',
  sell: 'MYY',
  buyDesc: 'Hyvä potentiaali',
  holdDesc: 'Odota parempia merkkejä',
  sellDesc: 'Harkitse myyntiä',
};

// Format EUR
const formatEur = (value: number | null | undefined, compact = false) => {
  if (value === null || value === undefined) return '—';
  if (compact && Math.abs(value) >= 1e9) {
    return `${(value / 1e9).toFixed(2)} mrd €`;
  }
  if (compact && Math.abs(value) >= 1e6) {
    return `${(value / 1e6).toFixed(2)} M €`;
  }
  return new Intl.NumberFormat('fi-FI', { style: 'currency', currency: 'EUR' }).format(value);
};

// Format percentage (Finnish format with comma)
const formatPercent = (value: number | null | undefined, decimals = 2) => {
  if (value === null || value === undefined) return '—';
  const formatted = value.toFixed(decimals).replace('.', ',');
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${formatted}%`;
};

// Format number (Finnish format with comma)
const formatNumber = (value: number | string | null | undefined, decimals = 2, showZeroAsDash = false) => {
  if (value === null || value === undefined) return '—';
  // Handle "Infinity" string or Infinity number
  if (value === 'Infinity' || value === '-Infinity' || value === Infinity || value === -Infinity || (typeof value === 'number' && !isFinite(value))) return '—';
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return '—';
  if (showZeroAsDash && numValue === 0) return '—';
  return numValue.toFixed(decimals).replace('.', ',');
};

// Safe number conversion - returns null for Infinity, NaN, or invalid values
const safeNumber = (value: number | string | null | undefined): number | null => {
  if (value === null || value === undefined) return null;
  if (value === 'Infinity' || value === '-Infinity' || value === Infinity || value === -Infinity) return null;
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue) || !isFinite(numValue)) return null;
  return numValue;
};

// Format large number (Finnish format with comma)
const formatLargeNumber = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '—';
  if (value >= 1e9) return `${(value / 1e9).toFixed(2).replace('.', ',')} mrd`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)} M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(2)} K`;
  return value.toFixed(0);
};

// Risk badge
const RiskBadge = ({ level }: { level: string }) => {
  const config = {
    LOW: { color: 'bg-green-500/20 text-green-400 border-green-500/30', label: t.riskLow, icon: Shield },
    MEDIUM: { color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', label: t.riskMedium, icon: Activity },
    HIGH: { color: 'bg-red-500/20 text-red-400 border-red-500/30', label: t.riskHigh, icon: AlertTriangle },
  };
  const c = config[level as keyof typeof config] || config.MEDIUM;
  const Icon = c.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-sm font-medium rounded-lg border ${c.color}`}>
      <Icon className="w-4 h-4" />
      {c.label}
    </span>
  );
};

// Recommendation badge based on score
const getRecommendation = (score: number, riskLevel: string) => {
  // High score + low/medium risk = BUY
  // Medium score or high risk = HOLD
  // Low score = SELL
  if (score >= 60 && riskLevel !== 'HIGH') {
    return { verdict: 'BUY', label: t.buy, desc: t.buyDesc, color: 'bg-green-500/20 text-green-400 border-green-500/30' };
  } else if (score < 35) {
    return { verdict: 'SELL', label: t.sell, desc: t.sellDesc, color: 'bg-red-500/20 text-red-400 border-red-500/30' };
  } else {
    return { verdict: 'HOLD', label: t.hold, desc: t.holdDesc, color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' };
  }
};

const RecommendationBadge = ({ score, riskLevel }: { score: number | null | undefined; riskLevel: string | null | undefined }) => {
  // Safe defaults if score or riskLevel is missing
  const safeScore = typeof score === 'number' && !isNaN(score) ? score : 50;
  const safeRisk = riskLevel || 'MEDIUM';
  const rec = getRecommendation(safeScore, safeRisk);
  return (
    <div className={`inline-flex flex-col items-center px-4 py-2 rounded-xl border ${rec.color}`}>
      <span className="text-lg 2xl:text-2xl font-bold">{rec.label}</span>
      <span className="text-xs 2xl:text-sm opacity-80">{rec.desc}</span>
    </div>
  );
};

const toRouteTicker = (value: string) => {
  return value.toUpperCase().replace(/\.HE$/i, '');
};

// Generate fact-based insights from data
const generateInsights = (analysis: any) => {
  const strengths: string[] = [];
  const risks: string[] = [];
  const metrics = analysis?.metrics || {};
  const fundamentals = analysis?.fundamentals || {};
  const quote = analysis?.quote || {};

  // Return-based insights
  if (metrics.return12m !== null && metrics.return12m !== undefined) {
    if (metrics.return12m > 20) {
      strengths.push(`Vahva 12kk tuotto: ${metrics.return12m.toFixed(1)}%`);
    } else if (metrics.return12m > 0) {
      strengths.push(`Positiivinen 12kk tuotto: ${metrics.return12m.toFixed(1)}%`);
    } else if (metrics.return12m < -20) {
      risks.push(`Heikko 12kk tuotto: ${metrics.return12m.toFixed(1)}%`);
    }
  }

  if (metrics.return3m !== null && metrics.return3m !== undefined) {
    if (metrics.return3m > 10) {
      strengths.push(`Hyvä 3kk momentum: ${metrics.return3m.toFixed(1)}%`);
    } else if (metrics.return3m < -10) {
      risks.push(`Laskeva 3kk trendi: ${metrics.return3m.toFixed(1)}%`);
    }
  }

  // Volatility insights
  if (metrics.volatility !== null && metrics.volatility !== undefined) {
    if (metrics.volatility < 25) {
      strengths.push(`Matala volatiliteetti: ${metrics.volatility.toFixed(1)}%`);
    } else if (metrics.volatility > 45) {
      risks.push(`Korkea volatiliteetti: ${metrics.volatility.toFixed(1)}%`);
    }
  }

  // PE ratio insights - use safeNumber to handle "Infinity" strings from API
  const peRatio = safeNumber(fundamentals.peRatio);
  if (peRatio && peRatio > 0) {
    if (peRatio < 15) {
      strengths.push(`Edullinen P/E-luku: ${peRatio.toFixed(1)}`);
    } else if (peRatio > 35) {
      risks.push(`Korkea P/E-luku: ${peRatio.toFixed(1)}`);
    }
  }

  // Dividend insights
  const dividendYield = safeNumber(fundamentals.dividendYield);
  if (dividendYield && dividendYield > 3) {
    strengths.push(`Hyvä osinkotuotto: ${dividendYield.toFixed(1)}%`);
  }

  // Profit margin insights
  const profitMargins = safeNumber(fundamentals.profitMargins);
  if (profitMargins !== null) {
    if (profitMargins > 0.15) {
      strengths.push(`Vahva voittomarginaali: ${(profitMargins * 100).toFixed(1)}%`);
    } else if (profitMargins < 0) {
      risks.push('Tappiollinen liiketoiminta');
    }
  }

  // ROE insights
  const returnOnEquity = safeNumber(fundamentals.returnOnEquity);
  if (returnOnEquity && returnOnEquity > 0.15) {
    strengths.push(`Korkea pääoman tuotto (ROE): ${(returnOnEquity * 100).toFixed(1)}%`);
  }

  // Debt insights
  const debtToEquity = safeNumber(fundamentals.debtToEquity);
  if (debtToEquity && debtToEquity > 150) {
    risks.push(`Korkea velkaantuminen: ${debtToEquity.toFixed(0)}%`);
  }

  // Revenue growth insights
  const revenueGrowth = safeNumber(fundamentals.revenueGrowth);
  if (revenueGrowth !== null) {
    if (revenueGrowth > 0.1) {
      strengths.push(`Liikevaihto kasvaa: ${(revenueGrowth * 100).toFixed(1)}%`);
    } else if (revenueGrowth < -0.1) {
      risks.push(`Liikevaihto laskee: ${(revenueGrowth * 100).toFixed(1)}%`);
    }
  }

  // Max drawdown insights
  if (metrics.maxDrawdown && metrics.maxDrawdown < -40) {
    risks.push(`Suuri maksimilasku: ${metrics.maxDrawdown.toFixed(1)}%`);
  }

  return { strengths, risks };
};

// Fact summary component
const FactSummary = ({ analysis }: { analysis: any }) => {
  const { strengths, risks } = generateInsights(analysis);

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-6 2xl:p-10">
      <div className="flex items-center gap-2 2xl:gap-3 mb-4 2xl:mb-6">
        <Info className="w-5 h-5 2xl:w-7 2xl:h-7 text-cyan-400" />
        <h3 className="text-lg 2xl:text-3xl font-semibold text-white">{t.summary}</h3>
      </div>

      {/* Strengths */}
      {strengths.length > 0 && (
        <div className="mb-4 2xl:mb-6">
          <div className="flex items-center gap-2 2xl:gap-3 text-green-400 text-sm 2xl:text-xl font-medium mb-2 2xl:mb-4">
            <TrendingUp className="w-4 h-4 2xl:w-6 2xl:h-6" />
            <span>{t.strengths}</span>
          </div>
          <ul className="space-y-1.5 2xl:space-y-3">
            {strengths.map((s, i) => (
              <li key={i} className="flex items-start gap-2 2xl:gap-3 text-sm 2xl:text-xl text-slate-300">
                <span className="text-green-400 mt-0.5">✓</span>
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Risks */}
      {risks.length > 0 && (
        <div className="mb-4 2xl:mb-6">
          <div className="flex items-center gap-2 2xl:gap-3 text-yellow-400 text-sm 2xl:text-xl font-medium mb-2 2xl:mb-4">
            <AlertTriangle className="w-4 h-4 2xl:w-6 2xl:h-6" />
            <span>{t.risks}</span>
          </div>
          <ul className="space-y-1.5 2xl:space-y-3">
            {risks.map((r, i) => (
              <li key={i} className="flex items-start gap-2 2xl:gap-3 text-sm 2xl:text-xl text-slate-300">
                <span className="text-yellow-400 mt-0.5">!</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {strengths.length === 0 && risks.length === 0 && (
        <p className="text-slate-400 text-sm 2xl:text-xl">Ei riittävästi dataa analyysia varten.</p>
      )}

      {/* Risk level badge */}
      <div className="mt-4 2xl:mt-8 pt-4 2xl:pt-6 border-t border-slate-700/50">
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm 2xl:text-xl">{t.riskLevel}</span>
          <RiskBadge level={analysis?.riskLevel || 'MEDIUM'} />
        </div>
      </div>
    </div>
  );
};

// Metric card
const MetricCard = ({ label, value, subValue, icon: Icon, trend }: {
  label: string;
  value: string;
  subValue?: string;
  icon?: any;
  trend?: 'up' | 'down' | 'neutral';
}) => (
  <div className="bg-slate-900/50 border border-slate-700/30 rounded-lg 2xl:rounded-2xl p-4 2xl:p-6">
    <div className="flex items-center gap-2 2xl:gap-3 text-slate-400 text-xs 2xl:text-base mb-2 2xl:mb-4">
      {Icon && <Icon className="w-4 h-4 2xl:w-6 2xl:h-6" />}
      <span>{label}</span>
    </div>
    <div className={`text-lg 2xl:text-4xl font-semibold ${trend === 'up' ? 'text-green-400' :
        trend === 'down' ? 'text-red-400' :
          'text-white'
      }`}>
      {value}
    </div>
    {subValue && <div className="text-xs 2xl:text-base text-slate-500 mt-1 2xl:mt-2">{subValue}</div>}
  </div>
);

export default function FiStockPage() {
  const params = useParams();
  const tickerParam = params.ticker as string;
  const ticker = tickerParam.includes('.HE') ? tickerParam : `${tickerParam}.HE`;
  const [timePeriod, setTimePeriod] = useState<string>('1y');

  // Fetch analysis
  const {
    data: analysisData,
    isLoading: analysisLoading,
    error: analysisError,
    refetch: refetchAnalysis
  } = useQuery({
    queryKey: ['fi-analysis', ticker],
    queryFn: () => getFiAnalysis(ticker),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch history for chart
  const {
    data: historyData,
    isLoading: historyLoading
  } = useQuery({
    queryKey: ['fi-history', ticker, timePeriod],
    queryFn: () => getFiHistory(ticker, timePeriod, '1d'),
    staleTime: 15 * 60 * 1000,
  });

  // Fetch technical analysis
  const { data: techData } = useQuery({
    queryKey: ['fi-technicals', ticker],
    queryFn: () => getFiTechnicals(ticker),
    staleTime: 5 * 60 * 1000,
  });

  const analysis = analysisData?.data;
  const technicals = techData?.data;
  const history = historyData?.data || [];
  const newsEvents = analysis?.newsEvents || [];
  const eventSummary = analysis?.eventSummary;
  const fundamentalInsight = analysis?.fundamentalInsight;
  const newsPageUrl = analysis?.newsPageUrl;
  const irUrl = analysis?.irUrl;
  const irNewsUrl = analysis?.irNewsUrl;
  const sectorBenchmarks = analysis?.sectorBenchmarks;
  const rankTotal = analysis?.rankTotal ?? null;
  const disclosures = newsEvents.filter((event: any) =>
    ['PRESS_RELEASE', 'INSIDER_TRANSACTION', 'SHORT_POSITION', 'OWNERSHIP_CHANGE'].includes(
      (event.event_type || '').toUpperCase()
    )
  );
  const companyNews = newsEvents.filter((event: any) =>
    ['COMPANY_NEWS', 'NEWS'].includes((event.event_type || '').toUpperCase())
  );

  const rankPosition = analysis?.rankPosition ?? null;

  // Prepare chart data with proper date formatting
  // Only show actual trading days from history (no weekends/holidays)
  const chartData = useMemo(() => {
    return history.map((point: FiHistoryPoint) => ({
      date: point.date,
      price: point.close,
      displayDate: new Date(point.date).toLocaleDateString('fi-FI', { day: 'numeric', month: 'short' }),
    }));
  }, [history]);

  // Calculate chart return
  const chartReturn = useMemo(() => {
    if (chartData.length < 2) return null;
    const first = chartData[0].price;
    const last = chartData[chartData.length - 1].price;
    // Guard against division by zero or invalid data
    if (!first || first === 0 || !last || isNaN(first) || isNaN(last)) return null;
    return ((last - first) / first) * 100;
  }, [chartData]);

  // Get date range for chart header
  const dateRange = useMemo(() => {
    if (chartData.length < 2) return '';
    const first = new Date(chartData[0].date).toLocaleDateString('fi-FI', { day: 'numeric', month: 'short', year: 'numeric' });
    const last = new Date(chartData[chartData.length - 1].date).toLocaleDateString('fi-FI', { day: 'numeric', month: 'short', year: 'numeric' });
    return `${first} – ${last}`;
  }, [chartData]);

  if (analysisLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-400">{t.loading}</p>
        </div>
      </div>
    );
  }

  if (analysisError || !analysis) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">{t.error}</h2>
          <p className="text-slate-400 mb-4">Osaketta {tickerParam.toUpperCase()} ei löytynyt.</p>
          <Link
            href="/fi/dashboard"
            className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            {t.backToDashboard}
          </Link>
        </div>
      </div>
    );
  }

  const quote = analysis.quote;
  const fundamentals = analysis.fundamentals;
  const metrics = analysis.metrics;

  const impactLabel = (impact?: string | null) => {
    switch ((impact || '').toUpperCase()) {
      case 'POSITIVE':
        return t.impactPositive;
      case 'NEGATIVE':
        return t.impactNegative;
      case 'MIXED':
        return t.impactMixed;
      default:
        return t.impactNeutral;
    }
  };

  const impactClass = (impact?: string | null) => {
    switch ((impact || '').toUpperCase()) {
      case 'POSITIVE':
        return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'NEGATIVE':
        return 'text-red-400 bg-red-500/10 border-red-500/30';
      case 'MIXED':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      default:
        return 'text-slate-300 bg-slate-700/30 border-slate-600/30';
    }
  };

  // Safe format helper that handles Infinity strings and non-numbers
  const safeFormat = (v: number | string | null | undefined, decimals: number, suffix = '') => {
    const num = safeNumber(v);
    if (num === null) return '—';
    return `${num.toFixed(decimals)}${suffix}`;
  };

  const benchmarkMetrics = [
    { key: 'peRatio', label: 'P/E', better: 'lower', format: (v: number | string) => safeFormat(v, 1) },
    { key: 'priceToBook', label: 'P/B', better: 'lower', format: (v: number | string) => safeFormat(v, 2) },
    { key: 'dividendYield', label: 'Osinkotuotto', better: 'higher', format: (v: number | string) => safeFormat(v, 1, '%') },
    { key: 'returnOnEquity', label: 'ROE', better: 'higher', format: (v: number | string) => safeFormat(v, 1, '%') },
    { key: 'profitMargins', label: 'Voittomarginaali', better: 'higher', format: (v: number | string) => safeFormat(v, 1, '%') },
    { key: 'debtToEquity', label: 'Velkaantumisaste', better: 'lower', format: (v: number | string) => safeFormat(v, 0, '%') },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-[2400px] mx-auto px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40 py-4 2xl:py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 2xl:gap-5">
              <Link
                href="/fi/dashboard"
                className="p-2 2xl:p-3 hover:bg-slate-700/50 rounded-lg 2xl:rounded-xl transition-colors text-slate-400 hover:text-white"
              >
                <ArrowLeft className="w-5 h-5 2xl:w-7 2xl:h-7" />
              </Link>

              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl 2xl:rounded-2xl blur-lg opacity-50"></div>
                <div className="relative p-2 2xl:p-3 bg-gradient-to-br from-cyan-600 to-blue-600 rounded-xl 2xl:rounded-2xl">
                  <BarChart3 className="w-5 h-5 2xl:w-7 2xl:h-7 text-white" />
                </div>
              </div>

              <div>
                <h1 className="text-lg md:text-xl 2xl:text-4xl font-bold text-white">{t.title}</h1>
                <div className="flex items-center gap-2 text-xs 2xl:text-base text-slate-400">
                  <Flag className="w-3 h-3 2xl:w-4 2xl:h-4 text-cyan-400" />
                  <span>{t.subtitle}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 2xl:gap-4">
              <button
                onClick={() => refetchAnalysis()}
                className="flex items-center gap-2 px-3 py-2 2xl:px-4 2xl:py-3 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg 2xl:rounded-xl text-slate-400 hover:text-white transition-colors"
              >
                <RefreshCw className="w-4 h-4 2xl:w-6 2xl:h-6" />
                <span className="text-xs 2xl:text-base hidden sm:inline">Päivitä saadaksesi reaaliaikaisimman hinnan</span>
              </button>
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[2400px] mx-auto px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40 py-6 md:py-8 2xl:py-12">
        <div className="space-y-6 2xl:space-y-10">

          {/* Stock Header */}
          <section className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 md:p-6 2xl:p-10">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 2xl:gap-8">
              <div>
                <div className="flex items-center gap-3 2xl:gap-4 mb-2 2xl:mb-4 flex-wrap">
                  <h1 className="text-2xl md:text-3xl 2xl:text-6xl font-bold text-white">
                    {tickerParam.toUpperCase()}
                  </h1>
                  <RiskBadge level={analysis.riskLevel} />
                  <span className="inline-flex items-center gap-1 2xl:gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 2xl:px-4 py-1 2xl:py-2 text-xs 2xl:text-base text-cyan-200">
                    <Star className="w-3.5 h-3.5 2xl:w-5 2xl:h-5" />
                    {rankPosition !== null
                      ? (rankTotal ? `Sijoitus #${rankPosition}/${rankTotal}` : `Sijoitus #${rankPosition}`)
                      : 'Sijoitus ei saatavilla'}
                  </span>
                </div>
                <p className="text-lg 2xl:text-3xl text-slate-300 mb-2 2xl:mb-4">{analysis.name}</p>
                <div className="flex flex-wrap items-center gap-3 2xl:gap-4 text-sm 2xl:text-2xl text-slate-400">
                  <span className="flex items-center gap-1 2xl:gap-2">
                    <PieChart className="w-4 h-4 2xl:w-6 2xl:h-6" />
                    {analysis.sector}
                  </span>
                  <span>•</span>
                  <span>{analysis.exchange}</span>
                  <span>•</span>
                  <span>{analysis.currency}</span>
                </div>
              </div>

              <div className="flex flex-col items-end gap-3 2xl:gap-5">
                {/* Recommendation Badges - Fundamental + Technical */}
                <div className="flex items-center gap-3">
                  {/* Fundamental Recommendation */}
                  <div className="text-center">
                    <div className="text-[10px] 2xl:text-xs text-slate-400 mb-1">Fundamentit</div>
                    <RecommendationBadge score={analysis.score} riskLevel={analysis.riskLevel} />
                  </div>
                  {/* Technical Recommendation */}
                  {technicals?.summary?.verdict && (
                    <div className="text-center">
                      <div className="text-[10px] 2xl:text-xs text-slate-400 mb-1">Tekninen</div>
                      <div className={`inline-flex flex-col items-center px-4 py-2 rounded-xl border ${technicals.summary.verdict === 'OSTA' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                          technicals.summary.verdict === 'MYY' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                            'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                        }`}>
                        <span className="text-lg 2xl:text-2xl font-bold">{technicals.summary.verdict}</span>
                        <span className="text-xs 2xl:text-sm opacity-80">{technicals.summary.text?.slice(0, 20) || ''}</span>
                      </div>
                    </div>
                  )}
                </div>

                {quote && (
                  <div className="text-right">
                    <div className="text-3xl md:text-4xl 2xl:text-6xl font-bold text-white mb-1 2xl:mb-3">
                      {formatEur(quote.price)}
                    </div>
                    <div className={`flex items-center justify-end gap-1 2xl:gap-2 text-lg 2xl:text-3xl ${(quote.changePercent || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                      {(quote.changePercent || 0) >= 0 ? (
                        <ArrowUpRight className="w-5 h-5 2xl:w-8 2xl:h-8" />
                      ) : (
                        <ArrowDownRight className="w-5 h-5 2xl:w-8 2xl:h-8" />
                      )}
                      <span>{formatPercent(quote.changePercent)}</span>
                      <span className="text-slate-500">({formatEur(quote.change)})</span>
                    </div>
                  </div>
                )}

                {/* Technical Analysis Link */}
                <Link
                  href={`/fi/technicals?ticker=${tickerParam.toUpperCase()}`}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 rounded-lg text-purple-200 transition-colors text-sm 2xl:text-lg"
                >
                  <Activity className="w-4 h-4 2xl:w-5 2xl:h-5" />
                  {t.technicalAnalysis}
                  <ChevronRight className="w-4 h-4 2xl:w-5 2xl:h-5" />
                </Link>
              </div>
            </div>

          </section>

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 2xl:gap-10">
            {/* Left Column - Fact Summary */}
            <div className="lg:col-span-1">
              <FactSummary analysis={analysis} />

            </div>

            {/* Right Column - Chart */}
            <div className="lg:col-span-2">
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-4 sm:p-5 2xl:p-8">
                {/* Chart Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 2xl:gap-5 mb-4 2xl:mb-6">
                  <div>
                    <h3 className="text-lg 2xl:text-3xl font-semibold text-white">Hintakehitys</h3>
                    {dateRange && (
                      <p className="text-xs 2xl:text-base text-slate-400 mt-0.5">{dateRange}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 2xl:gap-4">
                    {/* Time period selector */}
                    <div className="flex bg-slate-900/60 rounded-lg 2xl:rounded-xl p-0.5 2xl:p-1">
                      {TIME_PERIODS.map((period) => (
                        <button
                          key={period.value}
                          onClick={() => setTimePeriod(period.value)}
                          className={`px-2 sm:px-3 2xl:px-5 py-1.5 2xl:py-2.5 text-xs sm:text-sm 2xl:text-xl font-medium rounded-md 2xl:rounded-lg transition-colors ${timePeriod === period.value
                              ? 'bg-cyan-600 text-white'
                              : 'text-slate-400 hover:text-white'
                            }`}
                        >
                          {period.label}
                        </button>
                      ))}
                    </div>
                    {/* Chart return indicator */}
                    {chartReturn !== null && (
                      <div className={`px-2 2xl:px-4 py-1 2xl:py-2 rounded 2xl:rounded-lg text-xs 2xl:text-xl font-medium ${chartReturn >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                        {chartReturn >= 0 ? '+' : ''}{chartReturn.toFixed(1)}%
                      </div>
                    )}
                  </div>
                </div>

                {historyLoading ? (
                  <div className="h-48 sm:h-64 2xl:h-96 flex items-center justify-center text-slate-400 2xl:text-2xl">
                    <div className="animate-spin rounded-full h-6 w-6 2xl:h-10 2xl:w-10 border-b-2 border-cyan-400 mr-2"></div>
                    {t.loading}
                  </div>
                ) : chartData.length === 0 ? (
                  <div className="h-48 sm:h-64 2xl:h-96 flex items-center justify-center text-slate-400 2xl:text-2xl">
                    {t.noData}
                  </div>
                ) : (
                  <div className="h-48 sm:h-64 2xl:h-96">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={chartReturn && chartReturn >= 0 ? "#22c55e" : "#ef4444"} stopOpacity={0.3} />
                            <stop offset="95%" stopColor={chartReturn && chartReturn >= 0 ? "#22c55e" : "#ef4444"} stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                        <XAxis
                          dataKey="displayDate"
                          stroke="#64748b"
                          tick={{ fill: '#64748b', fontSize: 10 }}
                          tickLine={false}
                          axisLine={false}
                          interval="preserveStartEnd"
                          minTickGap={30}
                        />
                        <YAxis
                          stroke="#64748b"
                          tick={{ fill: '#64748b', fontSize: 10 }}
                          tickLine={false}
                          axisLine={false}
                          domain={['auto', 'auto']}
                          tickFormatter={(v) => `${v.toFixed(0)}€`}
                          width={45}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1e293b',
                            border: '1px solid #334155',
                            borderRadius: '8px',
                            fontSize: '12px',
                          }}
                          labelFormatter={(label) => label}
                          formatter={(value: number) => [formatEur(value), 'Hinta']}
                        />
                        <Area
                          type="monotone"
                          dataKey="price"
                          stroke={chartReturn && chartReturn >= 0 ? "#22c55e" : "#ef4444"}
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#colorPrice)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Metrics Grid */}
          <section className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
            <h3 className="text-lg 2xl:text-4xl font-semibold text-white mb-4 2xl:mb-8">{t.metrics}</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 2xl:gap-6">
              <MetricCard
                label={t.volatility}
                value={metrics?.volatility ? `${formatNumber(metrics.volatility)}%` : '—'}
                icon={Activity}
              />
              <MetricCard
                label={t.maxDrawdown}
                value={metrics?.maxDrawdown ? `${formatNumber(metrics.maxDrawdown)}%` : '—'}
                icon={TrendingDown}
                trend={metrics?.maxDrawdown && metrics.maxDrawdown < -30 ? 'down' : 'neutral'}
              />
              <MetricCard
                label={t.sharpeRatio}
                value={formatNumber(metrics?.sharpeRatio)}
                icon={Target}
              />
              <MetricCard
                label={t.return3m}
                value={formatPercent(metrics?.return3m)}
                icon={Calendar}
                trend={metrics?.return3m ? (metrics.return3m >= 0 ? 'up' : 'down') : 'neutral'}
              />
              <MetricCard
                label={t.return12m}
                value={formatPercent(metrics?.return12m)}
                icon={TrendingUp}
                trend={metrics?.return12m ? (metrics.return12m >= 0 ? 'up' : 'down') : 'neutral'}
              />
            </div>
          </section>

          {/* News & Disclosures */}
          {(disclosures.length > 0 || newsPageUrl || irNewsUrl || irUrl) && (
            <section className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 2xl:gap-5 mb-4 2xl:mb-8">
                <h3 className="text-lg 2xl:text-4xl font-semibold text-white">{t.disclosures}</h3>
                <div className="flex flex-wrap items-center gap-3 2xl:gap-5 gap-y-2 text-xs 2xl:text-xl text-slate-400">
                  {eventSummary && (
                    <span>
                      {t.eventSummary}: +{eventSummary.positive} / {eventSummary.neutral} / -{eventSummary.negative}
                    </span>
                  )}
                  {irNewsUrl && (
                    <a
                      href={irNewsUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 2xl:gap-2 text-emerald-400 hover:text-emerald-300"
                    >
                      {t.irNewsLink}
                      <ExternalLink className="w-3 h-3 2xl:w-5 2xl:h-5" />
                    </a>
                  )}
                  {newsPageUrl && (
                    <a
                      href={newsPageUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 2xl:gap-2 text-cyan-400 hover:text-cyan-300"
                    >
                      {t.newsPageLink}
                      <ExternalLink className="w-3 h-3 2xl:w-5 2xl:h-5" />
                    </a>
                  )}
                  {irUrl && (
                    <a
                      href={irUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 2xl:gap-2 text-purple-400 hover:text-purple-300"
                    >
                      {t.investorPageLink}
                      <ExternalLink className="w-3 h-3 2xl:w-5 2xl:h-5" />
                    </a>
                  )}
                </div>
              </div>
              <div className="space-y-3 2xl:space-y-5">
                {disclosures.map((event: any) => (
                  <div
                    key={event.id}
                    className="p-4 2xl:p-6 rounded-lg 2xl:rounded-2xl border border-slate-700/40 bg-slate-900/50"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 2xl:gap-4">
                      <div>
                        <div className="font-medium text-white 2xl:text-2xl">{event.analysis?.title_fi || event.title}</div>
                        <div className="text-xs 2xl:text-base text-slate-400 mt-1 2xl:mt-2">
                          {event.source || t.sourceLabel} - {event.published_at ? new Date(event.published_at).toLocaleDateString('fi-FI') : ''}
                        </div>
                      </div>
                      <span className={`px-2 2xl:px-4 py-0.5 2xl:py-1.5 text-xs 2xl:text-base rounded 2xl:rounded-lg border ${impactClass(event.impact)}`}>
                        {impactLabel(event.impact)}
                      </span>
                    </div>
                    {(event.summary || event.analysis?.summary) && (
                      <p className="text-sm 2xl:text-xl text-slate-300 mt-2 2xl:mt-4">
                        {event.summary || event.analysis?.summary}
                      </p>
                    )}
                    {event.source_url && (
                      <a
                        href={event.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 2xl:gap-2 text-xs 2xl:text-base text-cyan-400 hover:text-cyan-300 mt-3 2xl:mt-5"
                      >
                        Lue tiedote
                        <ExternalLink className="w-3 h-3 2xl:w-5 2xl:h-5" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 2xl:gap-5 mb-4 2xl:mb-8">
              <h3 className="text-lg 2xl:text-4xl font-semibold text-white">{t.companyNews}</h3>
            </div>
            {companyNews.length === 0 ? (
              <div className="text-slate-400 text-sm 2xl:text-xl">{t.noData}</div>
            ) : (
              <div className="space-y-3 2xl:space-y-5">
                {companyNews.map((event: any) => (
                  <div
                    key={event.id}
                    className="p-4 2xl:p-6 rounded-lg 2xl:rounded-2xl border border-slate-700/40 bg-slate-900/50"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 2xl:gap-4">
                      <div>
                        <div className="font-medium text-white 2xl:text-2xl">{event.analysis?.title_fi || event.title}</div>
                        <div className="text-xs 2xl:text-base text-slate-400 mt-1 2xl:mt-2">
                          {event.source || t.sourceLabel} - {event.published_at ? new Date(event.published_at).toLocaleDateString('fi-FI') : ''}
                        </div>
                      </div>
                      <span className={`px-2 2xl:px-4 py-0.5 2xl:py-1.5 text-xs 2xl:text-base rounded 2xl:rounded-lg border ${impactClass(event.impact)}`}>
                        {impactLabel(event.impact)}
                      </span>
                    </div>
                    {(event.summary || event.analysis?.summary) && (
                      <p className="text-sm 2xl:text-xl text-slate-300 mt-2 2xl:mt-4">
                        {event.summary || event.analysis?.summary}
                      </p>
                    )}
                    {event.source_url && (
                      <a
                        href={event.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 2xl:gap-2 text-xs 2xl:text-base text-cyan-400 hover:text-cyan-300 mt-3 2xl:mt-5"
                      >
                        Lue
                        <ExternalLink className="w-3 h-3 2xl:w-5 2xl:h-5" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* IR headlines are ingested daily and shown under company news */}

          {/* Sector Benchmarks */}
          {sectorBenchmarks && (
            <section className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 2xl:gap-5 mb-4 2xl:mb-8">
                <div>
                  <h3 className="text-lg 2xl:text-4xl font-semibold text-white">Sektorivertailu</h3>
                  <p className="text-xs 2xl:text-xl text-slate-400 mt-1 2xl:mt-2">
                    Medianit sektorilta ({sectorBenchmarks.sampleCount} yhtiötä)
                  </p>
                </div>
                <span className="text-xs 2xl:text-xl text-slate-400">{sectorBenchmarks.sector}</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 2xl:gap-6">
                {benchmarkMetrics.map((metric) => {
                  const rawValue = sectorBenchmarks.values?.[metric.key];
                  const rawMedian = sectorBenchmarks.medians?.[metric.key];
                  // Convert to safe numbers (handles "Infinity" strings)
                  const value = safeNumber(rawValue);
                  const median = safeNumber(rawMedian);
                  const hasData = value !== null && median !== null;
                  const delta = hasData && median !== 0 ? ((value - median) / median) * 100 : null;
                  // Also check if delta is finite
                  const safeDelta = delta !== null && isFinite(delta) ? delta : null;
                  const better = hasData
                    ? metric.better === 'lower'
                      ? value < median
                      : value > median
                    : null;
                  const deltaClass = better === null ? 'text-slate-400' : better ? 'text-emerald-400' : 'text-red-400';
                  const valueLabel = value !== null ? metric.format(value) : '—';
                  const medianLabel = median !== null ? metric.format(median) : '—';
                  const deltaLabel = safeDelta !== null
                    ? `${safeDelta > 0 ? '+' : ''}${safeDelta.toFixed(1)}%`
                    : '—';

                  return (
                    <div key={metric.key} className="rounded-lg 2xl:rounded-2xl border border-slate-700/40 bg-slate-900/50 p-4 2xl:p-6">
                      <div className="text-xs 2xl:text-base text-slate-400 mb-2 2xl:mb-4">{metric.label}</div>
                      <div className="flex items-center justify-between">
                        <span className="text-lg 2xl:text-4xl font-semibold text-white">{valueLabel}</span>
                        <span className={`text-xs 2xl:text-xl font-semibold ${deltaClass} flex items-center gap-1 2xl:gap-2`}>
                          {delta !== null ? (delta >= 0 ? <ArrowUpRight className="w-3 h-3 2xl:w-5 2xl:h-5" /> : <ArrowDownRight className="w-3 h-3 2xl:w-5 2xl:h-5" />) : null}
                          {deltaLabel}
                        </span>
                      </div>
                      <div className="text-[11px] 2xl:text-sm text-slate-500 mt-2 2xl:mt-4">
                        Sektorin mediaani: <span className="text-slate-300">{medianLabel}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Fundamental Insight */}
          {fundamentalInsight && (
            <section className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
              <div className="flex items-center justify-between gap-3 2xl:gap-5 mb-3 2xl:mb-6">
                <h3 className="text-lg 2xl:text-4xl font-semibold text-white">Tulkinta (fundamentit)</h3>
                <span className={`px-2 2xl:px-4 py-0.5 2xl:py-1.5 text-xs 2xl:text-base rounded 2xl:rounded-lg border ${impactClass(fundamentalInsight.impact)}`}>
                  {impactLabel(fundamentalInsight.impact)}
                </span>
              </div>
              <div className="text-sm 2xl:text-2xl text-slate-300 mb-3 2xl:mb-6">
                {fundamentalInsight.summary || fundamentalInsight.title}
              </div>
              {fundamentalInsight.bullets && fundamentalInsight.bullets.length > 0 && (
                <ul className="space-y-1.5 2xl:space-y-3 text-sm 2xl:text-xl text-slate-300">
                  {fundamentalInsight.bullets.map((item: string, idx: number) => (
                    <li key={idx} className="flex items-start gap-2 2xl:gap-3">
                      <span className="text-cyan-400 mt-0.5">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
              {fundamentalInsight.key_metrics && fundamentalInsight.key_metrics.length > 0 && (
                <div className="mt-4 2xl:mt-8 grid grid-cols-1 sm:grid-cols-2 gap-2 2xl:gap-4 text-xs 2xl:text-base text-slate-400">
                  {fundamentalInsight.key_metrics.map((metric: any, idx: number) => (
                    <div key={idx} className="flex justify-between border border-slate-700/40 rounded 2xl:rounded-lg px-2 2xl:px-4 py-1 2xl:py-2">
                      <span>{metric.label}</span>
                      <span className="text-slate-200">
                        {metric.value} {metric.unit || ''}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Fundamentals */}
          {fundamentals && (
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 2xl:gap-10">
              {/* Valuation */}
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
                <h3 className="text-lg 2xl:text-4xl font-semibold text-white mb-4 2xl:mb-8">{t.valuation}</h3>
                <div className="space-y-3 2xl:space-y-5">
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.marketCap}</span>
                    <span className="text-white">{formatEur(fundamentals.marketCap, true)}</span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.peRatio}</span>
                    <span className="text-white">{formatNumber(fundamentals.peRatio, 2, true)}</span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.forwardPE}</span>
                    <span className="text-white">{formatNumber(fundamentals.forwardPE, 2, true)}</span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.priceToBook}</span>
                    <span className="text-white">{formatNumber(fundamentals.priceToBook, 2, true)}</span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.pegRatio}</span>
                    <span className="text-white">{formatNumber(fundamentals.pegRatio, 2, true)}</span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.dividendYield}</span>
                    <span className="text-white">
                      {fundamentals.dividendYield ? formatPercent(fundamentals.dividendYield) : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.evEbit}</span>
                    <span className="text-white">{formatNumber(fundamentals.evEbit, 1, true)}</span>
                  </div>
                </div>
              </div>

              {/* Profitability */}
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
                <h3 className="text-lg 2xl:text-4xl font-semibold text-white mb-4 2xl:mb-8">{t.profitability}</h3>
                <div className="space-y-3 2xl:space-y-5">
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.profitMargin}</span>
                    <span className="text-white">
                      {fundamentals.profitMargins ? formatPercent(fundamentals.profitMargins * 100) : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.returnOnEquity}</span>
                    <span className="text-white">
                      {fundamentals.returnOnEquity ? formatPercent(fundamentals.returnOnEquity * 100) : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.roic}</span>
                    <span className="text-white">
                      {fundamentals.roic ? formatPercent(fundamentals.roic * 100) : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.revenueGrowth}</span>
                    <span className={`${fundamentals.revenueGrowth && fundamentals.revenueGrowth > 0 ? 'text-green-400' : 'text-white'
                      }`}>
                      {fundamentals.revenueGrowth ? formatPercent(fundamentals.revenueGrowth * 100) : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.earningsGrowth}</span>
                    <span className={`${fundamentals.earningsGrowth && fundamentals.earningsGrowth > 0 ? 'text-green-400' : 'text-white'
                      }`}>
                      {fundamentals.earningsGrowth ? formatPercent(fundamentals.earningsGrowth * 100) : '—'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Balance & Risk */}
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl 2xl:rounded-3xl p-5 2xl:p-10">
                <h3 className="text-lg 2xl:text-4xl font-semibold text-white mb-4 2xl:mb-8">{t.balance}</h3>
                <div className="space-y-3 2xl:space-y-5">
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.debtToEquity}</span>
                    <span className="text-white">{formatNumber(fundamentals.debtToEquity)}</span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.beta}</span>
                    <span className="text-white">{formatNumber(fundamentals.beta)}</span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.yearRange}</span>
                    <span className="text-white">
                      {formatEur(fundamentals.fiftyTwoWeekLow)} - {formatEur(fundamentals.fiftyTwoWeekHigh)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm 2xl:text-2xl">
                    <span className="text-slate-400">{t.avgVolume}</span>
                    <span className="text-white">{formatLargeNumber(fundamentals.averageVolume)}</span>
                  </div>
                </div>
              </div>
            </section>
          )}

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 bg-slate-900/30 mt-12 2xl:mt-20 py-6 2xl:py-10">
        <div className="max-w-[2400px] mx-auto px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 2xl:gap-6 text-sm 2xl:text-2xl text-slate-500">
            <div className="flex items-center gap-2 2xl:gap-4">
              <BarChart3 className="w-5 h-5 2xl:w-8 2xl:h-8 text-cyan-400" />
              <span>OsakedataX</span>
              <span>•</span>
              <span>Nasdaq Helsinki</span>
            </div>
            <p className="text-center md:text-right">{t.disclaimer}</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
