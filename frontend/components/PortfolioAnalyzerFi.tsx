"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  PieChart,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Shield,
  Activity,
  Briefcase,
  DollarSign,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  X,
  Target,
  Brain,
  Gauge,
  Upload,
  Download,
  Search,
  Wallet,
  Coins,
} from 'lucide-react';
import { getApiBaseUrl, getFiUniverse, FiStock } from '@/lib/api';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

interface PortfolioHolding {
  ticker: string;
  shares: number;
  avgPrice: number;
  currentPrice?: number;
  assetType?: 'OSAKE' | 'ETF' | 'INDEKSI' | 'RAHASTO';
  market?: 'FI' | 'US' | 'EU' | 'OTHER';
  currency?: string;
}

interface PortfolioAnalysis {
  health_score: number;
  risk_analysis: {
    overall_risk: string;
    concentration_risk: number;
    volatility_risk: number;
    losses_risk: number;
    total_risk_score: number;
  };
  diversification: {
    score: number;
    status: string;
    sector_breakdown: Array<{
      sector: string;
      percentage: number;
      count: number;
    }>;
  };
  rebalancing: Array<{
    ticker: string;
    action: string;
    reason: string;
    current_pct: number;
    suggested_pct?: number;
  }>;
  positions: Array<{
    ticker: string;
    name?: string;
    shares: number;
    entry_price: number;
    current_price: number;
    value: number;
    value_eur?: number;
    gain_loss: number;
    gain_loss_eur?: number;
    gain_loss_pct: number;
    weight: number;
    sector: string;
    currency?: string | null;
    dividend_yield?: number;
    expected_annual_dividend?: number;
  }>;
  dividends?: {
    total_expected_annual: number;
    portfolio_yield: number;
    dividend_paying_positions: number;
  };
  total_value: number;
  total_gain_loss: number;
  total_gain_loss_pct: number;
  total_value_eur?: number;
  total_gain_loss_eur?: number;
  total_gain_loss_pct_eur?: number;
  reporting_currency?: string;
  fx_rates?: Record<string, number>;
  correlation?: {
    avg_correlation: number;
    max_correlation?: number;
    assessment?: string;
    message?: string;
  };
  sharpe_ratio?: {
    ratio: number;
    assessment?: string;
    annual_return?: number;
    volatility?: number;
    message?: string;
  };
  benchmark_comparison?: {
    portfolio_return?: number;
    benchmark_return?: number;
    alpha?: number;
    assessment?: string;
    message?: string;
  };
  performance?: {
    winners?: number;
    losers?: number;
    neutral?: number;
    win_rate?: number;
    best_performer?: { ticker: string; return: number; value: number };
    worst_performer?: { ticker: string; return: number; value: number };
    avg_position_return?: number;
    message?: string;
  };
  summary?: {
    status?: string;
    message?: string;
    health_score?: number;
    risk_level?: string;
    diversification_level?: string;
  };
  alerts?: Array<{
    severity: 'LOW' | 'MEDIUM' | 'HIGH';
    type?: string;
    message: string;
    action?: string;
  }>;
}

const t = {
  title: 'Salkkuanalyysi',
  subtitle: 'Kattava salkun terveys- ja riskianalyysi',
  universe: 'Suomi-universumi',
  portfolio: 'Oma salkku',
  universeHint: 'Sektorit Nasdaq Helsingin osakeuniversumissa',
  portfolioHint: 'Syötä omat omistuksesi ja analysoi kokonaisuus',
  addHolding: 'Lisää omistus',
  analyze: 'Analysoi salkku',
  adding: 'Lisätään',
  analyzing: 'Analysoidaan...',
  holdings: 'Omistukset',
  ticker: 'Ticker',
  shares: 'Osakkeet',
  avgPrice: 'Ostohinta',
  currentHoldings: 'Nykyiset omistukset',
  healthScore: 'Terveys',
  totalValue: 'Salkun arvo',
  riskLevel: 'Riskitaso',
  diversification: 'Hajautus',
  positions: 'Positiot',
  entry: 'Ostohinta',
  current: 'Nykyhinta',
  value: 'Arvo',
  gainLoss: 'Tuotto',
  weight: 'Paino',
  sector: 'Toimiala',
  riskBreakdown: 'Riskierittely',
  concentrationRisk: 'Keskittymäriski',
  volatilityRisk: 'Volatiliteetti',
  lossRisk: 'Tappioriski',
  performance: 'Tuottomittarit',
  bestPerformer: 'Paras tuotto',
  worstPerformer: 'Heikoin tuotto',
  winRate: 'Voittosuhde',
  aiInsights: 'AI-salkkuhuomiot',
  sectorBreakdown: 'Toimialajakauma',
  rebalancing: 'Tasapainotusehdotukset',
  remove: 'Poista',
  stopLoss: 'Tappioraja (-8%)',
  takeProfit: 'Voiton kotiutus (+15%)',
  noHoldings: 'Ei omistuksia. Lisää ensimmäinen omistus.',
  universeLoading: 'Ladataan markkinauniversumia...',
  universeError: 'Universumia ei voitu ladata.',
  analyzeError: 'Salkun analysointi epäonnistui. Yritä uudelleen.',
  summary: 'Salkun yhteenveto',
  alerts: 'Hälytykset',
  correlation: 'Korrelaatio',
  sharpe: 'Sharpe-luku',
  benchmark: 'Vertailuindeksi',
  assetMix: 'Instrumenttijakauma',
  performanceChart: 'Salkun kehitys vs. indeksit',
  normalizedNote: 'Indeksoitu: 100 = jakson alku',
  csvImport: 'Tuo CSV',
  csvTemplate: 'CSV-malli',
  csvHelp: 'Sarakkeet: tunnus, osakkeet, ostohinta, markkina, instrumentti, valuutta. CSV-mallissa käytetään englanninkielisiä kenttänimiä.',
  currencyNote: 'Useita valuuttoja - kokonaisarvo on suuntaa-antava.',
  addHint: 'Voit lisätä myös ETF:iä, indeksejä ja USA-osakkeita.',
  presetTitle: 'Pikavalinnat',
  assetType: 'Instrumentti',
  market: 'Markkina',
  passiveIncome: 'Passiivisen tulon suunnittelija',
  passiveIncomeDesc: 'Aseta tavoite kuukausitulolle ja seuraa edistymistä',
  currentMonthly: 'Nykyinen kuukausitulo',
  targetMonthly: 'Tavoite kuukausitulo',
  toGoal: 'Tavoitteeseen',
  dividendYield: 'Osinkotuotto',
  neededShares: 'Tarvittava lisäsijoitus',
  topDividends: 'Parhaat osinko-osakkeet',
  noDiv: 'Ei osinkohistoriaa',
};

interface PortfolioPerformancePoint {
  date: string;
  portfolio?: number;
  [key: string]: number | string | undefined;
}

interface PortfolioPerformanceResponse {
  series: PortfolioPerformancePoint[];
  benchmarks: string[];
  period: string;
  message?: string;
}

const formatMoney = (value: number | null | undefined, currency: string = 'EUR', compact = false) => {
  if (value === null || value === undefined) return '-';
  if (compact && Math.abs(value) >= 1e9) {
    return `${(value / 1e9).toFixed(2)} mrd ${currency}`;
  }
  if (compact && Math.abs(value) >= 1e6) {
    return `${(value / 1e6).toFixed(2)} M ${currency}`;
  }
  try {
    return new Intl.NumberFormat('fi-FI', { style: 'currency', currency }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`;
  }
};

const formatPercent = (value: number | null | undefined, decimals = 2) => {
  if (value === null || value === undefined) return '-';
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(decimals)}%`;
};

const parseNumber = (value: string) => {
  if (!value) return 0;
  const cleaned = value.replace(/\s/g, '').replace(',', '.').replace(/[^0-9.-]/g, '');
  const parsed = Number.parseFloat(cleaned);
  return Number.isFinite(parsed) ? parsed : 0;
};

const detectDelimiter = (line: string) => {
  const candidates = [',', ';', '\t'];
  return candidates.reduce((best, candidate) => {
    const currentCount = line.split(candidate).length;
    const bestCount = line.split(best).length;
    return currentCount > bestCount ? candidate : best;
  }, ',');
};

const normalizeMarket = (value: string): PortfolioHolding['market'] | undefined => {
  const normalized = value.trim().toUpperCase();
  if (!normalized) return undefined;
  if (['FI', 'FIN', 'FINLAND', 'HE', 'HEL', 'HELSINKI'].includes(normalized)) return 'FI';
  if (['US', 'USA', 'NYSE', 'NASDAQ'].includes(normalized)) return 'US';
  if (['EU', 'EUROPE', 'EUR'].includes(normalized)) return 'EU';
  return 'OTHER';
};

const guessMarketFromTicker = (ticker: string): PortfolioHolding['market'] => {
  const upper = ticker.trim().toUpperCase();
  if (!upper) return 'FI';
  if (upper.endsWith('.HE')) return 'FI';
  if (upper.startsWith('^OMX')) return 'FI';
  if (upper.startsWith('^STOXX') || upper.startsWith('^EU')) return 'EU';
  if (upper.startsWith('^')) return 'US';
  return 'US';
};

const normalizeAssetType = (value: string): PortfolioHolding['assetType'] | undefined => {
  const normalized = value.trim().toUpperCase();
  if (!normalized) return undefined;
  if (['ETF', 'ETN', 'ETC'].includes(normalized)) return 'ETF';
  if (['INDEX', 'INDEKSI', 'IND'].includes(normalized)) return 'INDEKSI';
  if (['FUND', 'RAHASTO', 'MUTUAL'].includes(normalized)) return 'RAHASTO';
  if (['STOCK', 'OSAKE', 'SHARE'].includes(normalized)) return 'OSAKE';
  return 'OSAKE';
};

const guessAssetTypeFromTicker = (ticker: string): PortfolioHolding['assetType'] => {
  const upper = ticker.trim().toUpperCase();
  if (upper.startsWith('^')) return 'INDEKSI';
  const etfs = new Set(['SPY', 'QQQ', 'VOO', 'IVV', 'IWM', 'VTI', 'VEA', 'EFA', 'EEM', 'GLD']);
  if (etfs.has(upper)) return 'ETF';
  return 'OSAKE';
};

const normalizeTicker = (value: string, market: PortfolioHolding['market']) => {
  const trimmed = value.trim().toUpperCase();
  if (!trimmed) return '';
  if (trimmed.startsWith('^')) return trimmed;
  if (market === 'FI') {
    if (trimmed.endsWith('.HE')) return trimmed;
    if (trimmed.includes('.')) return trimmed;
    return `${trimmed}.HE`;
  }
  return trimmed;
};

const formatChartDate = (value: string) => {
  if (!value) return '';
  const parts = value.split('-');
  if (parts.length < 2) return value;
  const day = parts[2];
  const month = parts[1];
  return day && month ? `${day}.${month}.` : value;
};

const getHealthColor = (score: number) => {
  if (score >= 80) return 'text-emerald-400 bg-emerald-900/30 border-emerald-500/50';
  if (score >= 60) return 'text-yellow-400 bg-yellow-900/30 border-yellow-500/50';
  return 'text-red-400 bg-red-900/30 border-red-500/50';
};

const getRiskColor = (risk: string) => {
  if (risk === 'LOW') return 'text-emerald-400';
  if (risk === 'MEDIUM') return 'text-yellow-400';
  return 'text-red-400';
};

const getRiskLabel = (risk: string) => {
  if (risk === 'LOW') return 'Matala';
  if (risk === 'MEDIUM') return 'Keskitaso';
  return 'Korkea';
};

const getDiversificationLabel = (status: string) => {
  const key = status?.toUpperCase();
  if (key === 'EXCELLENT') return 'Erinomainen';
  if (key === 'GOOD') return 'Hyvä';
  if (key === 'FAIR') return 'Kohtalainen';
  if (key === 'POOR') return 'Heikko';
  return status || '-';
};

const getActionColor = (action: string) => {
  const colors: Record<string, string> = {
    TRIM: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    HOLD: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    ADD: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    REVIEW: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    TAKE_PROFITS: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  };
  return colors[action] || 'bg-slate-500/20 text-slate-300 border-slate-500/30';
};

const getActionLabel = (action: string) => {
  const labels: Record<string, string> = {
    TRIM: 'Kevennä',
    HOLD: 'Pidä',
    ADD: 'Lisää',
    REVIEW: 'Arvioi',
    TAKE_PROFITS: 'Kotiuta voittoja',
  };
  return labels[action] || action;
};

const guessCurrencyFromMarket = (market?: PortfolioHolding['market']) => {
  if (market === 'US') return 'USD';
  return 'EUR';
};

const getMarketLabel = (market?: PortfolioHolding['market']) => {
  if (market === 'FI') return 'Suomi';
  if (market === 'US') return 'USA';
  if (market === 'EU') return 'Eurooppa';
  if (market === 'OTHER') return 'Globaali';
  return '-';
};

const getAssetLabel = (asset?: PortfolioHolding['assetType']) => {
  if (asset === 'ETF') return 'ETF';
  if (asset === 'INDEKSI') return 'Indeksi';
  if (asset === 'RAHASTO') return 'Rahasto';
  return 'Osake';
};

// Fuzzy search for stocks - matches ticker and company name
const fuzzySearchStocks = (query: string, stocks: FiStock[], maxResults = 8): FiStock[] => {
  if (!query || query.length < 1 || !stocks?.length) return [];
  const q = query.toLowerCase().trim();

  // Score each stock
  const scored = stocks.map((stock) => {
    const ticker = stock.ticker.toLowerCase().replace('.he', '');
    const name = stock.name.toLowerCase();
    let score = 0;

    // Exact ticker match (highest priority)
    if (ticker === q || ticker === q.replace('.he', '')) {
      score = 1000;
    }
    // Ticker starts with query
    else if (ticker.startsWith(q)) {
      score = 500 + (100 - ticker.length);
    }
    // Ticker contains query
    else if (ticker.includes(q)) {
      score = 300 + (100 - ticker.length);
    }
    // Name starts with query word
    else if (name.startsWith(q) || name.split(' ').some(word => word.startsWith(q))) {
      score = 200 + (100 - name.length);
    }
    // Name contains query
    else if (name.includes(q)) {
      score = 100 + (100 - name.length);
    }
    // Fuzzy match - check if letters appear in order
    else {
      let qIdx = 0;
      for (let i = 0; i < name.length && qIdx < q.length; i++) {
        if (name[i] === q[qIdx]) qIdx++;
      }
      if (qIdx === q.length) {
        score = 50;
      }
    }

    return { stock, score };
  });

  return scored
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, maxResults)
    .map((s) => s.stock);
};

const quickPresets: Array<{
  label: string;
  ticker: string;
  market: PortfolioHolding['market'];
  assetType: PortfolioHolding['assetType'];
}> = [
  { label: 'OMXH25 (indeksi)', ticker: '^OMXH25', market: 'FI', assetType: 'INDEKSI' },
  { label: 'S&P 500 (SPY)', ticker: 'SPY', market: 'US', assetType: 'ETF' },
  { label: 'NASDAQ 100 (QQQ)', ticker: 'QQQ', market: 'US', assetType: 'ETF' },
  { label: 'Euro Stoxx 50', ticker: '^STOXX50E', market: 'EU', assetType: 'INDEKSI' },
];

const mergeHoldings = (items: PortfolioHolding[]) => {
  const merged = new Map<string, PortfolioHolding>();
  items.forEach((holding) => {
    const key = holding.ticker;
    if (!key || holding.shares <= 0) return;
    const existing = merged.get(key);
    if (!existing) {
      merged.set(key, { ...holding });
      return;
    }
    const totalShares = existing.shares + holding.shares;
    const weightedAvg =
      totalShares > 0
        ? (existing.avgPrice * existing.shares + holding.avgPrice * holding.shares) / totalShares
        : existing.avgPrice;
    merged.set(key, {
      ...existing,
      shares: totalShares,
      avgPrice: Number.isFinite(weightedAvg) ? weightedAvg : existing.avgPrice,
      market: existing.market || holding.market,
      assetType: existing.assetType || holding.assetType,
      currency: existing.currency || holding.currency,
    });
  });
  return Array.from(merged.values());
};

const parseCsvHoldings = (content: string) => {
  const cleaned = content.replace(/^\uFEFF/, '');
  const rows = cleaned
    .split(/\r?\n/)
    .map((row) => row.trim())
    .filter(Boolean);
  if (!rows.length) {
    throw new Error('CSV on tyhjä.');
  }
  const delimiter = detectDelimiter(rows[0]);
  const rawHeaders = rows[0].split(delimiter).map((cell) => cell.trim());
  const headers = rawHeaders.map((cell) => cell.toLowerCase().replace(/\s+/g, '').replace(/-/g, '_'));
  const headerMap: Record<string, string[]> = {
    ticker: ['ticker', 'symbol', 'osake', 'osakeid', 'instrument'],
    shares: ['shares', 'qty', 'quantity', 'amount', 'kpl', 'osakkeet'],
    avg_price: ['avg_price', 'avgprice', 'avgcost', 'avg_cost', 'cost', 'entry', 'ostohinta'],
    market: ['market', 'markkina', 'exchange'],
    asset_type: ['asset_type', 'asset', 'type', 'instrumentti'],
    currency: ['currency', 'valuutta'],
  };
  const headerLookup = new Map<string, string>();
  Object.entries(headerMap).forEach(([key, aliases]) => {
    aliases.forEach((alias) => headerLookup.set(alias, key));
  });
  const hasHeader = headers.some((header) => headerLookup.has(header));
  const indexMap: Record<string, number> = {};
  if (hasHeader) {
    headers.forEach((header, idx) => {
      const mapped = headerLookup.get(header);
      if (mapped) indexMap[mapped] = idx;
    });
  } else {
    indexMap.ticker = 0;
    indexMap.shares = 1;
    indexMap.avg_price = 2;
    indexMap.market = 3;
    indexMap.asset_type = 4;
    indexMap.currency = 5;
  }

  const dataRows = hasHeader ? rows.slice(1) : rows;
  const parsed: PortfolioHolding[] = [];

  dataRows.forEach((row) => {
    const cells = row.split(delimiter).map((cell) => cell.trim());
    const tickerRaw = cells[indexMap.ticker ?? 0] || '';
    if (!tickerRaw) return;
    const marketRaw = cells[indexMap.market ?? -1] || '';
    const market = normalizeMarket(marketRaw) || guessMarketFromTicker(tickerRaw);
    const normalizedTicker = normalizeTicker(tickerRaw, market);
    if (!normalizedTicker) return;
    const shares = parseNumber(cells[indexMap.shares ?? 1] || '');
    if (shares <= 0) return;
    const avgPrice = parseNumber(cells[indexMap.avg_price ?? 2] || '');
    const assetType =
      normalizeAssetType(cells[indexMap.asset_type ?? -1] || '') || guessAssetTypeFromTicker(normalizedTicker);
    const currencyRaw = (cells[indexMap.currency ?? -1] || '').trim().toUpperCase();
    const currency = currencyRaw || guessCurrencyFromMarket(market);
    parsed.push({
      ticker: normalizedTicker,
      shares,
      avgPrice,
      market,
      assetType,
      currency,
    });
  });

  return mergeHoldings(parsed);
};

const PortfolioAnalyzerFi: React.FC = () => {
  const [showAddHolding, setShowAddHolding] = useState(false);
  const [analysisScope, setAnalysisScope] = useState<'universe' | 'portfolio'>('portfolio');
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([
    { ticker: 'NOKIA.HE', shares: 200, avgPrice: 3.5, assetType: 'OSAKE', market: 'FI', currency: 'EUR' },
    { ticker: 'KNEBV.HE', shares: 20, avgPrice: 42, assetType: 'OSAKE', market: 'FI', currency: 'EUR' },
    { ticker: 'SPY', shares: 3, avgPrice: 430, assetType: 'ETF', market: 'US', currency: 'USD' },
  ]);

  const [newHolding, setNewHolding] = useState<PortfolioHolding>({
    ticker: '',
    shares: 0,
    avgPrice: 0,
  });
  const [newHoldingMarket, setNewHoldingMarket] = useState<PortfolioHolding['market']>('FI');
  const [newHoldingType, setNewHoldingType] = useState<PortfolioHolding['assetType']>('OSAKE');
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [csvError, setCsvError] = useState<string | null>(null);
  const [performanceRange, setPerformanceRange] = useState<'3mo' | '6mo' | '1y'>('6mo');
  const [targetMonthlyIncome, setTargetMonthlyIncome] = useState<number>(300);
  const [showTickerDropdown, setShowTickerDropdown] = useState(false);
  const tickerInputRef = useRef<HTMLInputElement | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  // Always fetch FI universe for autocomplete
  const universeQuery = useQuery({
    queryKey: ['fi-universe'],
    queryFn: getFiUniverse,
    staleTime: 60 * 60 * 1000,
  });

  // Autocomplete suggestions based on ticker input
  const tickerSuggestions = useMemo(() => {
    if (!showTickerDropdown || newHoldingMarket !== 'FI') return [];
    const stocks = universeQuery.data?.stocks || [];
    return fuzzySearchStocks(newHolding.ticker, stocks);
  }, [newHolding.ticker, universeQuery.data?.stocks, showTickerDropdown, newHoldingMarket]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        tickerInputRef.current &&
        !tickerInputRef.current.contains(event.target as Node)
      ) {
        setShowTickerDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const universeSummary = useMemo(() => {
    const data = universeQuery.data;
    if (!data || !data.sectors) return null;
    const total = data.totalCount || Object.values(data.sectors).reduce((sum, count) => sum + count, 0);
    const sector_breakdown = Object.entries(data.sectors)
      .map(([sector, count]) => ({
        sector,
        count,
        percentage: total > 0 ? (count / total) * 100 : 0,
      }))
      .sort((a, b) => b.count - a.count);
    return { total_stocks: total, sector_breakdown };
  }, [universeQuery.data]);

  const analyzePortfolio = useMutation({
    mutationFn: async (portfolioHoldings: PortfolioHolding[]) => {
      const backendHoldings = portfolioHoldings.map((h) => ({
        ticker: h.ticker,
        shares: h.shares,
        avg_cost: h.avgPrice,
        currency: h.currency || guessCurrencyFromMarket(h.market),
        market: h.market,
        asset_type: h.assetType,
      }));

      const response = await fetch(`${getApiBaseUrl()}/api/portfolio/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ holdings: backendHoldings }),
      });
      if (!response.ok) throw new Error('Salkun analysointi epäonnistui.');
      return response.json();
    },
  });

  const analysis = analyzePortfolio.data?.data as PortfolioAnalysis | undefined;
  const summary = analysis?.summary;
  const alerts = analysis?.alerts || [];
  const correlation = analysis?.correlation;
  const sharpe = analysis?.sharpe_ratio;
  const benchmark = analysis?.benchmark_comparison;
  const holdingsMap = useMemo(() => {
    const map = new Map<string, PortfolioHolding>();
    holdings.forEach((holding) => map.set(holding.ticker, holding));
    return map;
  }, [holdings]);
  const currencySet = useMemo(() => {
    const set = new Set<string>();
    (analysis?.positions || []).forEach((pos) => {
      if (pos.currency) set.add(pos.currency);
    });
    return set;
  }, [analysis?.positions]);
  const hasMultiCurrency = currencySet.size > 1;
  const primaryCurrency = currencySet.size === 1 ? Array.from(currencySet)[0] : 'EUR';
  const reportingCurrency = analysis?.reporting_currency || primaryCurrency;
  const totalValue = analysis?.total_value_eur ?? analysis?.total_value;
  const totalGainLoss = analysis?.total_gain_loss_eur ?? analysis?.total_gain_loss;
  const totalGainLossPct = analysis?.total_gain_loss_pct_eur ?? analysis?.total_gain_loss_pct;
  const totalGainLossValue = totalGainLoss ?? 0;
  const totalGainLossPctValue = totalGainLossPct ?? 0;
  const bestPosition = useMemo(() => {
    if (!analysis?.positions?.length) return null;
    return analysis.positions.reduce((best, pos) => (pos.gain_loss_pct > best.gain_loss_pct ? pos : best));
  }, [analysis?.positions]);
  const worstPosition = useMemo(() => {
    if (!analysis?.positions?.length) return null;
    return analysis.positions.reduce((worst, pos) => (pos.gain_loss_pct < worst.gain_loss_pct ? pos : worst));
  }, [analysis?.positions]);
  const assetMix = useMemo(() => {
    if (!analysis?.positions?.length) return [];
    const totals: Record<string, number> = {};
    analysis.positions.forEach((pos) => {
      const holding = holdingsMap.get(pos.ticker);
      const type = getAssetLabel(holding?.assetType);
      totals[type] = (totals[type] || 0) + pos.weight;
    });
    return Object.entries(totals)
      .map(([label, weight]) => ({ label, weight }))
      .sort((a, b) => b.weight - a.weight);
  }, [analysis?.positions, holdingsMap]);

  const holdingsKey = useMemo(() => {
    return holdings
      .map((holding) => `${holding.ticker}:${holding.shares}:${holding.avgPrice}:${holding.currency || ''}`)
      .sort()
      .join('|');
  }, [holdings]);

  const performanceQuery = useQuery({
    queryKey: ['fi-portfolio-performance', holdingsKey, performanceRange],
    enabled: analysisScope === 'portfolio' && holdings.length > 0 && analyzePortfolio.isSuccess,
    staleTime: 15 * 60 * 1000,
    queryFn: async () => {
      const payloadHoldings = holdings
        .filter((holding) => holding.ticker && holding.shares > 0)
        .map((holding) => ({
          ticker: holding.ticker,
          shares: holding.shares,
          avg_cost: holding.avgPrice,
          currency: holding.currency || guessCurrencyFromMarket(holding.market),
          market: holding.market,
          asset_type: holding.assetType,
        }));

      const response = await fetch(`${getApiBaseUrl()}/api/portfolio/performance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          holdings: payloadHoldings,
          period: performanceRange,
          benchmarks: ['^OMXH25', 'SPY'],
        }),
      });
      if (!response.ok) throw new Error('Salkun kehityssarjan lataus epäonnistui.');
      return response.json() as Promise<{ success: boolean; data: PortfolioPerformanceResponse }>;
    },
  });

  const performanceData = performanceQuery.data?.data?.series || [];
  const performanceBenchmarks = performanceQuery.data?.data?.benchmarks || [];
  const performanceMessage = performanceQuery.data?.data?.message;
  const performanceSeriesKeys = useMemo(() => {
    if (!performanceData.length) return [];
    return ['portfolio', ...performanceBenchmarks].filter((key) =>
      performanceData.some((row) => row[key] !== undefined)
    );
  }, [performanceData, performanceBenchmarks]);

  const lineConfig: Record<string, { label: string; color: string; dash?: string; width?: number }> = useMemo(
    () => ({
      portfolio: { label: 'Salkku', color: '#22d3ee', width: 2.5 },
      '^OMXH25': { label: 'OMXH25', color: '#f59e0b', dash: '6 4' },
      SPY: { label: 'S&P 500', color: '#a855f7', dash: '6 4' },
    }),
    []
  );

  const handleAnalyze = () => {
    analyzePortfolio.mutate(holdings);
  };

  const handleAddHolding = () => {
    const normalized = normalizeTicker(newHolding.ticker, newHoldingMarket);
    if (normalized && newHolding.shares > 0 && newHolding.avgPrice > 0) {
      setHoldings([
        ...holdings,
        {
          ...newHolding,
          ticker: normalized,
          assetType: newHoldingType,
          market: newHoldingMarket,
          currency: newHolding.currency || guessCurrencyFromMarket(newHoldingMarket),
        },
      ]);
      setNewHolding({ ticker: '', shares: 0, avgPrice: 0 });
      setShowAddHolding(false);
    }
  };

  const handleRemoveHolding = (index: number) => {
    setHoldings(holdings.filter((_, i) => i !== index));
  };

  const handleCsvUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = parseCsvHoldings(text);
      if (!parsed.length) {
        setCsvError('CSV ei sisältänyt kelvollisia rivejä.');
        return;
      }
      setHoldings(parsed);
      setCsvError(null);
      setShowAddHolding(false);
    } catch (error) {
      setCsvError(error instanceof Error ? error.message : 'CSV:n käsittely epäonnistui.');
    } finally {
      if (event.target) event.target.value = '';
    }
  };

  const downloadCsvTemplate = () => {
    const template = [
      'ticker,shares,avg_price,market,asset_type,currency',
      'NOKIA.HE,100,3.5,FI,OSAKE,EUR',
      'SPY,5,420,US,ETF,USD',
      '^OMXH25,1,100,FI,INDEKSI,EUR',
    ].join('\n');
    const blob = new Blob([template], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'portfolio_template.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  const applyPreset = (preset: typeof quickPresets[number]) => {
    setShowAddHolding(true);
    setNewHolding({
      ticker: preset.ticker,
      shares: 0,
      avgPrice: 0,
      currency: guessCurrencyFromMarket(preset.market),
    });
    setNewHoldingMarket(preset.market);
    setNewHoldingType(preset.assetType);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-600/20 rounded-lg">
            <PieChart className="w-7 h-7 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">{t.title}</h2>
            <p className="text-sm text-slate-400">{t.subtitle}</p>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-2">
          <div className="flex items-center gap-1 bg-slate-900/60 border border-slate-700 rounded-full p-1 text-xs">
            <button
              onClick={() => setAnalysisScope('universe')}
              className={`px-3 py-1 rounded-full transition ${
                analysisScope === 'universe'
                  ? 'bg-cyan-600 text-white'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              {t.universe}
            </button>
            <button
              onClick={() => setAnalysisScope('portfolio')}
              className={`px-3 py-1 rounded-full transition ${
                analysisScope === 'portfolio'
                  ? 'bg-cyan-600 text-white'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              {t.portfolio}
            </button>
          </div>

          {analysisScope === 'portfolio' && (
            <div className="flex flex-wrap items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={handleCsvUpload}
              />
              <button
                onClick={() => setShowAddHolding(!showAddHolding)}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg flex items-center gap-2 transition-colors"
              >
                <Plus className="w-4 h-4" />
                {t.addHolding}
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-100 rounded-lg flex items-center gap-2 border border-slate-700/80 text-sm transition-colors"
              >
                <Upload className="w-4 h-4" />
                {t.csvImport}
              </button>
              <button
                onClick={downloadCsvTemplate}
                className="px-3 py-2 bg-slate-900 hover:bg-slate-800 text-slate-200 rounded-lg flex items-center gap-2 border border-slate-700/60 text-sm transition-colors"
              >
                <Download className="w-4 h-4" />
                {t.csvTemplate}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-700/60 bg-gradient-to-r from-slate-900/70 via-slate-900/30 to-cyan-900/20 p-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <p className="text-sm text-slate-300 font-medium">{t.portfolioHint}</p>
            <p className="text-xs text-slate-400">{t.addHint}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-500">{t.presetTitle}:</span>
            {quickPresets.map((preset) => (
              <button
                key={preset.ticker}
                type="button"
                onClick={() => applyPreset(preset)}
                className="px-3 py-1 rounded-full border border-slate-700/60 bg-slate-900/60 text-xs text-slate-200 hover:border-cyan-500/40 hover:text-cyan-200 transition-colors"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {analysisScope === 'universe' && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white font-semibold">{t.universe}</h3>
            <span className="text-sm text-slate-400">
              {universeSummary ? `${universeSummary.total_stocks} osaketta` : t.universeLoading}
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-4">{t.universeHint}</p>

          {universeQuery.isLoading && (
            <p className="text-sm text-slate-400">{t.universeLoading}</p>
          )}

          {universeSummary && (
            <div className="space-y-3">
              {universeSummary.sector_breakdown.map((sector) => (
                <div key={sector.sector}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-300">{sector.sector}</span>
                    <span className="text-sm font-semibold text-white">
                      {sector.percentage.toFixed(1)}% ({sector.count})
                    </span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-cyan-600 to-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${sector.percentage}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {universeQuery.isError && (
            <p className="text-xs text-red-300 mt-3">{t.universeError}</p>
          )}
        </div>
      )}

      {analysisScope === 'portfolio' && (
        <>
          {showAddHolding && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
              <h3 className="text-white font-semibold mb-3">{t.addHolding}</h3>
              <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
                {/* Ticker input with autocomplete */}
                <div className="md:col-span-2 relative">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      ref={tickerInputRef}
                      type="text"
                      placeholder={newHoldingMarket === 'FI' ? "Hae ticker tai yhtiö..." : "Ticker (esim. AAPL)"}
                      value={newHolding.ticker}
                      onChange={(e) => {
                        setNewHolding({ ...newHolding, ticker: e.target.value.toUpperCase() });
                        if (newHoldingMarket === 'FI' && e.target.value.length >= 1) {
                          setShowTickerDropdown(true);
                        }
                      }}
                      onFocus={() => {
                        if (newHoldingMarket === 'FI' && newHolding.ticker.length >= 1) {
                          setShowTickerDropdown(true);
                        }
                      }}
                      className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  {/* Autocomplete dropdown */}
                  {showTickerDropdown && tickerSuggestions.length > 0 && (
                    <div
                      ref={dropdownRef}
                      className="absolute z-50 w-full mt-1 bg-slate-800 border border-slate-600 rounded-lg shadow-xl max-h-64 overflow-y-auto"
                    >
                      {tickerSuggestions.map((stock) => (
                        <button
                          key={stock.ticker}
                          type="button"
                          onClick={() => {
                            setNewHolding({ ...newHolding, ticker: stock.ticker });
                            setShowTickerDropdown(false);
                          }}
                          className="w-full px-3 py-2 text-left hover:bg-slate-700 transition-colors flex items-center justify-between group"
                        >
                          <div>
                            <span className="font-semibold text-cyan-400 group-hover:text-cyan-300">
                              {stock.ticker.replace('.HE', '')}
                            </span>
                            <span className="text-slate-400 ml-2 text-sm">{stock.name}</span>
                          </div>
                          <span className="text-xs text-slate-500">{stock.sector}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <select
                  value={newHoldingMarket || 'FI'}
                  onChange={(e) => {
                    const market = e.target.value as PortfolioHolding['market'];
                    setNewHoldingMarket(market);
                    setNewHolding((prev) => ({
                      ...prev,
                      currency: prev.currency || guessCurrencyFromMarket(market),
                    }));
                  }}
                  className="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white text-sm"
                >
                  <option value="FI">Suomi (.HE)</option>
                  <option value="US">USA</option>
                  <option value="EU">Eurooppa</option>
                  <option value="OTHER">Muu</option>
                </select>
                <select
                  value={newHoldingType || 'OSAKE'}
                  onChange={(e) => setNewHoldingType(e.target.value as PortfolioHolding['assetType'])}
                  className="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white text-sm"
                >
                  <option value="OSAKE">Osake</option>
                  <option value="ETF">ETF</option>
                  <option value="INDEKSI">Indeksi</option>
                  <option value="RAHASTO">Rahasto</option>
                </select>
                <input
                  type="number"
                  placeholder="Osakkeet"
                  value={newHolding.shares || ''}
                  onChange={(e) => setNewHolding({ ...newHolding, shares: parseFloat(e.target.value) || 0 })}
                  className="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
                />
                <input
                  type="number"
                  placeholder="Ostohinta"
                  value={newHolding.avgPrice || ''}
                  onChange={(e) => setNewHolding({ ...newHolding, avgPrice: parseFloat(e.target.value) || 0 })}
                  className="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
                />
                <button
                  onClick={handleAddHolding}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded transition-colors"
                >
                  {t.addHolding}
                </button>
              </div>
              <div className="mt-3 text-xs text-slate-500">
                Syötä hinta instrumentin omassa valuutassa. Voit käyttää esimerkiksi SPY, QQQ, ^OMXH25 tai ETF-tickereitä.
              </div>
            </div>
          )}

          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
            <h3 className="text-white font-semibold mb-3">{t.currentHoldings} ({holdings.length})</h3>
            <p className="text-xs text-slate-500 mb-2">{t.csvHelp}</p>
            {csvError && (
              <div className="text-xs text-red-300 mb-3">{csvError}</div>
            )}
            {holdings.length === 0 ? (
              <p className="text-sm text-slate-400">{t.noHoldings}</p>
            ) : (
              <div className="space-y-2">
                {holdings.map((holding, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-slate-900/50 rounded border border-slate-700/50">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="font-bold text-white">{holding.ticker}</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800/70 border border-slate-700/60 text-slate-200">
                        {getAssetLabel(holding.assetType)}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800/70 border border-slate-700/60 text-slate-300">
                        {getMarketLabel(holding.market)}
                      </span>
                      <span className="text-slate-400">
                        {holding.shares} kpl @ {formatMoney(holding.avgPrice, holding.currency || guessCurrencyFromMarket(holding.market))}
                      </span>
                    </div>
                    <button
                      onClick={() => handleRemoveHolding(index)}
                      className="p-1 hover:bg-red-500/20 rounded text-red-400 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <button
              onClick={handleAnalyze}
              disabled={analyzePortfolio.isPending || holdings.length === 0}
              className="mt-4 w-full px-4 py-3 bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors"
            >
              {analyzePortfolio.isPending ? t.analyzing : t.analyze}
            </button>
          </div>

          {analysis && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className={`rounded-lg p-4 border ${getHealthColor(analysis.health_score)}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm opacity-80">{t.healthScore}</span>
                    <Shield className="w-5 h-5" />
                  </div>
                  <div className="text-3xl font-bold">{analysis.health_score}/100</div>
                  <div className="text-xs mt-1 opacity-80">
                    {analysis.health_score >= 80
                      ? 'Erinomainen'
                      : analysis.health_score >= 60
                      ? 'Hyvä'
                      : 'Vaatii huomiota'}
                  </div>
                </div>

                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-slate-400">{t.totalValue}</span>
                    <DollarSign className="w-5 h-5 text-slate-400" />
                  </div>
                  <div className="text-3xl font-bold text-white">{formatMoney(totalValue, reportingCurrency, true)}</div>
                  <div className={`text-xs mt-1 flex items-center gap-1 ${totalGainLossValue >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {totalGainLossValue >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                    {formatPercent(totalGainLossPctValue)} ({formatMoney(totalGainLoss, reportingCurrency)})
                  </div>
                </div>

                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-slate-400">{t.riskLevel}</span>
                    <AlertTriangle className={`w-5 h-5 ${getRiskColor(analysis.risk_analysis.overall_risk)}`} />
                  </div>
                  <div className={`text-2xl font-bold ${getRiskColor(analysis.risk_analysis.overall_risk)}`}>
                    {getRiskLabel(analysis.risk_analysis.overall_risk)}
                  </div>
                  <div className="text-xs mt-1 text-slate-400">
                    Pisteet: {analysis.risk_analysis.total_risk_score}/100
                  </div>
                </div>

                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-slate-400">{t.diversification}</span>
                    <Activity className="w-5 h-5 text-slate-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">{analysis.diversification.score}/100</div>
                  <div className="text-xs mt-1 text-slate-400">
                    {getDiversificationLabel(analysis.diversification.status)}
                  </div>
                </div>
              </div>

              {hasMultiCurrency && (
                <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-200">
                  {t.currencyNote} ({Array.from(currencySet).join(', ')} {'->'} {reportingCurrency})
                </div>
              )}

              {summary && (
                <div className="bg-gradient-to-r from-slate-900/70 via-slate-900/40 to-emerald-900/20 border border-slate-700/60 rounded-lg p-5">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                    <div>
                      <h3 className="text-white font-semibold">{t.summary}</h3>
                      <p className="text-sm text-slate-300 mt-1">{summary.message}</p>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      {summary.risk_level && (
                        <span className={`px-2 py-1 rounded-full border ${getRiskColor(summary.risk_level)} border-current`}>
                          Riski: {getRiskLabel(summary.risk_level)}
                        </span>
                      )}
                      {summary.diversification_level && (
                        <span className="px-2 py-1 rounded-full border border-slate-600 text-slate-300">
                          Hajautus: {getDiversificationLabel(summary.diversification_level)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {alerts.length > 0 && (
                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <h3 className="text-white font-semibold mb-3">{t.alerts}</h3>
                  <div className="space-y-2">
                    {alerts.map((alert, idx) => (
                      <div
                        key={idx}
                        className={`rounded-lg border p-3 ${
                          alert.severity === 'HIGH'
                            ? 'border-red-500/40 bg-red-500/10 text-red-200'
                            : alert.severity === 'MEDIUM'
                            ? 'border-yellow-500/40 bg-yellow-500/10 text-yellow-200'
                            : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold">{alert.message}</div>
                            {alert.action && (
                              <div className="text-xs opacity-80 mt-1">{alert.action}</div>
                            )}
                          </div>
                          <span className="text-xs font-semibold uppercase">{alert.severity}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {assetMix.length > 0 && (
                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <h3 className="text-white font-semibold mb-3">{t.assetMix}</h3>
                  <div className="space-y-3">
                    {assetMix.map((item) => (
                      <div key={item.label}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-slate-300">{item.label}</span>
                          <span className="text-sm font-semibold text-white">{item.weight.toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-cyan-600 to-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${item.weight}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                  <Briefcase className="w-5 h-5" />
                  {t.positions}
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-700 text-slate-400 text-sm">
                        <th className="text-left py-2">{t.ticker}</th>
                        <th className="text-right py-2">{t.shares}</th>
                        <th className="text-right py-2">{t.entry}</th>
                        <th className="text-right py-2">{t.current}</th>
                        <th className="text-right py-2">{t.value}</th>
                        <th className="text-right py-2">{t.gainLoss}</th>
                        <th className="text-right py-2">{t.weight}</th>
                        <th className="text-left py-2">{t.sector}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.positions.map((position, idx) => (
                        <tr key={idx} className="border-b border-slate-700/50 text-sm">
                          <td className="py-3">
                            <div className="font-bold text-white">{position.ticker}</div>
                            {position.name && (
                              <div className="text-xs text-slate-500 truncate max-w-[180px]">{position.name}</div>
                            )}
                            {position.currency && (
                              <span className="text-[10px] text-slate-400">{position.currency}</span>
                            )}
                          </td>
                          <td className="text-right text-slate-300">{position.shares}</td>
                          <td className="text-right text-slate-300">{formatMoney(position.entry_price, position.currency || primaryCurrency)}</td>
                          <td className="text-right text-slate-300">{formatMoney(position.current_price, position.currency || primaryCurrency)}</td>
                          <td className="text-right text-white font-semibold">
                            {formatMoney(position.value, position.currency || primaryCurrency)}
                            {hasMultiCurrency && position.value_eur !== undefined && position.currency && position.currency !== reportingCurrency && (
                              <div className="text-xs text-slate-500">~ {formatMoney(position.value_eur, reportingCurrency)}</div>
                            )}
                          </td>
                          <td className={`text-right font-semibold ${position.gain_loss >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {formatPercent(position.gain_loss_pct)}
                          </td>
                          <td className="text-right text-slate-300">{position.weight.toFixed(1)}%</td>
                          <td className="text-slate-400">{position.sector}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-gradient-to-br from-red-900/20 to-orange-900/20 border border-red-500/30 rounded-lg p-6">
                <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                  <Gauge className="w-6 h-6 text-red-400" />
                  {t.riskBreakdown}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-slate-400">{t.concentrationRisk}</span>
                      <AlertTriangle className={`w-4 h-4 ${analysis.risk_analysis.concentration_risk > 70 ? 'text-red-400' : analysis.risk_analysis.concentration_risk > 40 ? 'text-yellow-400' : 'text-emerald-400'}`} />
                    </div>
                    <div className={`text-2xl font-bold ${analysis.risk_analysis.concentration_risk > 70 ? 'text-red-400' : analysis.risk_analysis.concentration_risk > 40 ? 'text-yellow-400' : 'text-emerald-400'}`}>
                      {analysis.risk_analysis.concentration_risk.toFixed(1)}%
                    </div>
                  </div>

                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-slate-400">{t.volatilityRisk}</span>
                      <Activity className={`w-4 h-4 ${analysis.risk_analysis.volatility_risk > 1.3 ? 'text-red-400' : analysis.risk_analysis.volatility_risk > 0.8 ? 'text-yellow-400' : 'text-emerald-400'}`} />
                    </div>
                    <div className={`text-2xl font-bold ${analysis.risk_analysis.volatility_risk > 1.3 ? 'text-red-400' : analysis.risk_analysis.volatility_risk > 0.8 ? 'text-yellow-400' : 'text-emerald-400'}`}>
                      {analysis.risk_analysis.volatility_risk.toFixed(2)}
                    </div>
                  </div>

                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-slate-400">{t.lossRisk}</span>
                      <TrendingDown className={`w-4 h-4 ${analysis.risk_analysis.losses_risk > 6 ? 'text-red-400' : analysis.risk_analysis.losses_risk > 2 ? 'text-yellow-400' : 'text-emerald-400'}`} />
                    </div>
                    <div className={`text-2xl font-bold ${analysis.risk_analysis.losses_risk > 6 ? 'text-red-400' : analysis.risk_analysis.losses_risk > 2 ? 'text-yellow-400' : 'text-emerald-400'}`}>
                      {analysis.risk_analysis.losses_risk}
                    </div>
                  </div>
                </div>
              </div>

              {(correlation || sharpe || benchmark) && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-slate-400">{t.correlation}</span>
                      <Activity className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div className="text-2xl font-bold text-white">
                      {correlation?.avg_correlation?.toFixed(2) ?? '-'}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Max: {correlation?.max_correlation?.toFixed(2) ?? '-'}
                    </div>
                    {correlation?.assessment && (
                      <div className="text-xs text-slate-300 mt-2">{correlation.assessment}</div>
                    )}
                  </div>

                  <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-slate-400">{t.sharpe}</span>
                      <Shield className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div className="text-2xl font-bold text-white">
                      {sharpe?.ratio?.toFixed(2) ?? '-'}
                    </div>
                    {sharpe?.assessment && (
                      <div className="text-xs text-slate-300 mt-1">{sharpe.assessment}</div>
                    )}
                    {sharpe?.volatility !== undefined && (
                      <div className="text-xs text-slate-500 mt-1">
                        Volatiliteetti: {sharpe.volatility.toFixed(2)}
                      </div>
                    )}
                  </div>

                  <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-slate-400">{t.benchmark}</span>
                      <TrendingUp className="w-5 h-5 text-purple-400" />
                    </div>
                    <div className={`text-2xl font-bold ${benchmark?.alpha && benchmark.alpha >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {benchmark?.alpha !== undefined ? `${benchmark.alpha >= 0 ? '+' : ''}${benchmark.alpha.toFixed(2)}%` : '-'}
                    </div>
                    {benchmark?.assessment && (
                      <div className="text-xs text-slate-300 mt-1">{benchmark.assessment}</div>
                    )}
                    {benchmark?.portfolio_return !== undefined && benchmark?.benchmark_return !== undefined && (
                      <div className="text-xs text-slate-500 mt-1">
                        Salkku {benchmark.portfolio_return.toFixed(2)}% vs S&P 500 {benchmark.benchmark_return.toFixed(2)}%
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-lg p-6">
                <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                  <BarChart3 className="w-6 h-6 text-blue-400" />
                  {t.performance}
                </h3>
                {analysis.performance?.message && (
                  <div className="text-xs text-slate-400 mb-4">{analysis.performance.message}</div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">{t.gainLoss}</div>
                    <div className={`text-2xl font-bold ${totalGainLossValue >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {formatPercent(totalGainLossPctValue)}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      {formatMoney(Math.abs(totalGainLossValue), reportingCurrency)}
                    </div>
                  </div>

                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">{t.bestPerformer}</div>
                    <div className="text-2xl font-bold text-emerald-400">
                      {analysis.performance?.best_performer?.ticker || bestPosition?.ticker || '-'}
                    </div>
                    <div className="text-xs text-emerald-400 mt-1">
                      {analysis.performance?.best_performer?.return !== undefined
                        ? formatPercent(analysis.performance.best_performer.return)
                        : bestPosition
                        ? formatPercent(bestPosition.gain_loss_pct)
                        : '-'}
                    </div>
                  </div>

                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">{t.worstPerformer}</div>
                    <div className="text-2xl font-bold text-red-400">
                      {analysis.performance?.worst_performer?.ticker || worstPosition?.ticker || '-'}
                    </div>
                    <div className="text-xs text-red-400 mt-1">
                      {analysis.performance?.worst_performer?.return !== undefined
                        ? formatPercent(analysis.performance.worst_performer.return)
                        : worstPosition
                        ? formatPercent(worstPosition.gain_loss_pct)
                        : '-'}
                    </div>
                  </div>

                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">{t.winRate}</div>
                    <div className="text-2xl font-bold text-white">
                      {analysis.performance?.win_rate !== undefined
                        ? `${analysis.performance.win_rate.toFixed(0)}%`
                        : analysis.positions.length
                        ? `${((analysis.positions.filter(p => p.gain_loss > 0).length / analysis.positions.length) * 100).toFixed(0)}%`
                        : '-'}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      {analysis.performance?.winners !== undefined && analysis.performance?.losers !== undefined
                        ? `${analysis.performance.winners}/${analysis.positions.length} voitollista`
                        : analysis.positions.length
                        ? `${analysis.positions.filter(p => p.gain_loss > 0).length}/${analysis.positions.length} voitollista`
                        : '-'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
                  <div>
                    <h3 className="text-white font-semibold">{t.performanceChart}</h3>
                    <p className="text-xs text-slate-400">{t.normalizedNote}</p>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    {(['3mo', '6mo', '1y'] as const).map((range) => (
                      <button
                        key={range}
                        onClick={() => setPerformanceRange(range)}
                        className={`px-3 py-1 rounded-full border transition ${
                          performanceRange === range
                            ? 'bg-cyan-600 text-white border-cyan-500'
                            : 'border-slate-700 text-slate-300 hover:text-white'
                        }`}
                      >
                        {range === '3mo' ? '3 kk' : range === '6mo' ? '6 kk' : '1 v'}
                      </button>
                    ))}
                  </div>
                </div>

                {performanceQuery.isLoading && (
                  <div className="text-sm text-slate-400">Haetaan kehityssarjaa...</div>
                )}
                {performanceQuery.isError && (
                  <div className="text-sm text-red-300">Kehityssarjan lataus epäonnistui.</div>
                )}

                {!performanceQuery.isLoading && performanceData.length === 0 && (
                  <div className="text-sm text-slate-400">
                    {performanceMessage || 'Ei kehityssarjaa saatavilla tälle salkulle.'}
                  </div>
                )}

                {performanceData.length > 0 && (
                  <>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300 mb-3">
                      {performanceSeriesKeys.map((key) => {
                        const config = lineConfig[key] || { label: key, color: '#94a3b8' };
                        return (
                          <span key={key} className="flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: config.color }} />
                            {config.label}
                          </span>
                        );
                      })}
                    </div>
                    <div className="h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={performanceData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                          <XAxis
                            dataKey="date"
                            tickFormatter={formatChartDate}
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                          />
                          <YAxis
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                            domain={['auto', 'auto']}
                            tickFormatter={(value) => Number(value).toFixed(0)}
                          />
                          <Tooltip
                            formatter={(value: number, name: string) => {
                              const config = lineConfig[name] || { label: name };
                              return [Number(value).toFixed(2), config.label];
                            }}
                            labelFormatter={(label) => `Päivä: ${formatChartDate(String(label))}`}
                            contentStyle={{
                              backgroundColor: '#0f172a',
                              border: '1px solid #334155',
                              borderRadius: '0.5rem',
                              color: '#e2e8f0',
                            }}
                          />
                          {performanceSeriesKeys.map((key) => {
                            const config = lineConfig[key] || { color: '#94a3b8' };
                            return (
                              <Line
                                key={key}
                                type="monotone"
                                dataKey={key}
                                stroke={config.color}
                                strokeWidth={config.width || 2}
                                strokeDasharray={config.dash}
                                dot={false}
                                activeDot={{ r: 3 }}
                                connectNulls
                              />
                            );
                          })}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </>
                )}
              </div>

              <div className="bg-gradient-to-br from-emerald-900/20 to-cyan-900/20 border border-emerald-500/30 rounded-lg p-6">
                <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                  <Brain className="w-6 h-6 text-emerald-400" />
                  {t.aiInsights}
                </h3>
                <div className="space-y-3">
                  {analysis.positions.map((position, idx) => {
                    const stopLoss = position.current_price * 0.92;
                    const takeProfit = position.current_price * 1.15;
                    const isWinning = position.gain_loss > 0;
                    const isLargePosition = position.weight > 20;

                    return (
                      <div key={idx} className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                              <span className="font-bold text-white text-lg">{position.ticker}</span>
                              <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                position.gain_loss >= 0 ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-red-500/20 text-red-300 border border-red-500/30'
                              }`}>
                                {position.gain_loss >= 0 ? 'VOITOLLA' : 'TAPPIOLLA'}
                              </span>
                              {isLargePosition && (
                                <span className="px-2 py-1 rounded text-xs font-semibold bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
                                  {position.weight.toFixed(1)}% salkusta
                                </span>
                              )}
                            </div>
                            <div className="text-sm text-slate-400">
                              {formatMoney(position.value, position.currency || primaryCurrency)}
                              <span className="mx-1 text-slate-500">|</span>
                              {formatPercent(position.gain_loss_pct)}
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                          <div className="bg-slate-800/50 rounded p-2">
                            <div className="text-xs text-slate-500">{t.entry}</div>
                            <div className="text-sm font-semibold text-white">{formatMoney(position.entry_price, position.currency || primaryCurrency)}</div>
                          </div>
                          <div className="bg-slate-800/50 rounded p-2">
                            <div className="text-xs text-slate-500">{t.current}</div>
                            <div className="text-sm font-semibold text-white">{formatMoney(position.current_price, position.currency || primaryCurrency)}</div>
                          </div>
                          <div className="bg-red-900/30 border border-red-500/30 rounded p-2">
                            <div className="text-xs text-red-400">{t.stopLoss}</div>
                            <div className="text-sm font-semibold text-red-300">{formatMoney(stopLoss, position.currency || primaryCurrency)}</div>
                          </div>
                          <div className="bg-emerald-900/30 border border-emerald-500/30 rounded p-2">
                            <div className="text-xs text-emerald-400">{t.takeProfit}</div>
                            <div className="text-sm font-semibold text-emerald-300">{formatMoney(takeProfit, position.currency || primaryCurrency)}</div>
                          </div>
                        </div>

                        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                          <div className="flex items-start gap-2">
                            <Target className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-blue-200">
                              <strong>AI-suositus:</strong>{' '}
                              {isLargePosition && isWinning ?
                                `Kotiuta osittain voittoja (${position.weight.toFixed(1)}% salkusta). Kevennä noin 15% tasolle.` :
                              isLargePosition && !isWinning ?
                                `Omistus on ${position.weight.toFixed(1)}% salkusta ja on tappiolla. Aseta tappioraja noin ${formatMoney(stopLoss, position.currency || primaryCurrency)} tasolle.` :
                              isWinning && position.gain_loss_pct > 15 ?
                                `Hyvä nousu! Harkitse voittojen kotiutusta tai liukuvaa tappiorajaa noin ${formatMoney(position.current_price * 0.95, position.currency || primaryCurrency)}.` :
                              !isWinning && position.gain_loss_pct < -10 ?
                                `Tappiolla ${Math.abs(position.gain_loss_pct).toFixed(1)}%. Arvioi uudelleen, tai keskimääräistä vain vahvalla näkemyksellä.` :
                                `Positio on kohtuullisesti mitoitettu (${position.weight.toFixed(1)}%). Seuraa riskitasoa.`
                              }
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                <h3 className="text-white font-semibold mb-3">{t.sectorBreakdown}</h3>
                <div className="space-y-3">
                  {analysis.diversification.sector_breakdown.map((sector, idx) => (
                    <div key={idx}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-slate-300">{sector.sector}</span>
                        <span className="text-sm font-semibold text-white">{sector.percentage.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2">
                        <div
                          className="bg-gradient-to-r from-cyan-600 to-blue-600 h-2 rounded-full transition-all"
                          style={{ width: `${sector.percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {analysis.rebalancing.length > 0 && (
                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    {t.rebalancing}
                  </h3>
                  <div className="space-y-2">
                    {analysis.rebalancing.map((rec, idx) => (
                      <div key={idx} className="p-3 bg-slate-900/50 rounded border border-slate-700/50">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-white">{rec.ticker}</span>
                          <span className={`px-2 py-1 rounded text-xs font-semibold border ${getActionColor(rec.action)}`}>
                            {getActionLabel(rec.action)}
                          </span>
                        </div>
                        <p className="text-sm text-slate-400">{rec.reason}</p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                          <span>Nykyinen: {rec.current_pct.toFixed(1)}%</span>
                          {rec.suggested_pct && <span>Suositus: {rec.suggested_pct.toFixed(1)}%</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Passiivisen tulon suunnittelija */}
              <div className="bg-gradient-to-br from-amber-900/20 to-yellow-900/20 border border-amber-500/30 rounded-lg p-6">
                <h3 className="text-white font-semibold mb-2 flex items-center gap-2">
                  <Wallet className="w-6 h-6 text-amber-400" />
                  {t.passiveIncome}
                </h3>
                <p className="text-sm text-slate-400 mb-4">{t.passiveIncomeDesc}</p>

                {(() => {
                  const dividends = analysis.dividends;
                  const currentAnnual = dividends?.total_expected_annual || 0;
                  const currentMonthly = currentAnnual / 12;
                  const targetAnnual = targetMonthlyIncome * 12;
                  const progress = targetAnnual > 0 ? Math.min((currentAnnual / targetAnnual) * 100, 100) : 0;
                  const toGo = Math.max(0, targetMonthlyIncome - currentMonthly);
                  const portfolioYield = dividends?.portfolio_yield || 0;
                  const neededInvestment = portfolioYield > 0 ? (toGo * 12) / (portfolioYield / 100) : 0;

                  // Get dividend-paying positions sorted by yield
                  const dividendPositions = analysis.positions
                    .filter(p => p.dividend_yield && p.dividend_yield > 0)
                    .sort((a, b) => (b.dividend_yield || 0) - (a.dividend_yield || 0));

                  return (
                    <>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                        <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
                          <div className="text-xs text-slate-500 mb-1">{t.currentMonthly}</div>
                          <div className="text-2xl font-bold text-emerald-400">
                            {formatMoney(currentMonthly, 'EUR')}
                          </div>
                          <div className="text-xs text-slate-500 mt-1">
                            ({formatMoney(currentAnnual, 'EUR')}/vuosi)
                          </div>
                        </div>

                        <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
                          <div className="text-xs text-slate-500 mb-1">{t.targetMonthly}</div>
                          <div className="flex items-center gap-2">
                            <input
                              type="number"
                              value={targetMonthlyIncome}
                              onChange={(e) => setTargetMonthlyIncome(Math.max(0, parseInt(e.target.value) || 0))}
                              className="w-24 px-2 py-1 bg-slate-800 border border-slate-600 rounded text-xl font-bold text-amber-400 text-center"
                            />
                            <span className="text-slate-400">€/kk</span>
                          </div>
                        </div>

                        <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
                          <div className="text-xs text-slate-500 mb-1">{t.toGoal}</div>
                          <div className="text-2xl font-bold text-cyan-400">
                            {toGo > 0 ? `+${formatMoney(toGo, 'EUR')}/kk` : '✓ Tavoite saavutettu!'}
                          </div>
                          {toGo > 0 && neededInvestment > 0 && (
                            <div className="text-xs text-slate-500 mt-1">
                              ≈ {formatMoney(neededInvestment, 'EUR', true)} lisäsijoitus
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Progress bar */}
                      <div className="mb-4">
                        <div className="flex justify-between text-xs text-slate-400 mb-1">
                          <span>Edistyminen</span>
                          <span>{progress.toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-3">
                          <div
                            className="bg-gradient-to-r from-amber-500 to-yellow-400 h-3 rounded-full transition-all"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                      </div>

                      {/* Dividend positions */}
                      {dividendPositions.length > 0 && (
                        <div className="mt-4">
                          <h4 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
                            <Coins className="w-4 h-4 text-amber-400" />
                            Osingonmaksajat salkussa
                          </h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                            {dividendPositions.slice(0, 6).map((pos, idx) => (
                              <div key={idx} className="flex items-center justify-between p-2 bg-slate-800/50 rounded border border-slate-700/50">
                                <div>
                                  <span className="font-semibold text-white text-sm">{pos.ticker.replace('.HE', '')}</span>
                                  <span className="text-xs text-slate-500 ml-2">{pos.sector}</span>
                                </div>
                                <div className="text-right">
                                  <div className="text-sm font-semibold text-amber-400">{pos.dividend_yield?.toFixed(1)}%</div>
                                  <div className="text-xs text-slate-500">
                                    ~{formatMoney((pos.expected_annual_dividend || 0) / 12, 'EUR')}/kk
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {dividendPositions.length === 0 && (
                        <div className="text-sm text-slate-500 text-center py-4">
                          {t.noDiv} - lisää osinko-osakkeita salkkuusi
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            </>
          )}

          {analyzePortfolio.isPending && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-8 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-600 mx-auto mb-4"></div>
              <p className="text-slate-400">{t.analyzing}</p>
            </div>
          )}

          {analyzePortfolio.isError && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 text-red-400">
                <AlertTriangle className="w-5 h-5" />
                <span>{t.analyzeError}</span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default PortfolioAnalyzerFi;


