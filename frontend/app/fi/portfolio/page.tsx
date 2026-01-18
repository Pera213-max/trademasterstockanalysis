"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowLeft, PieChart, Plus, Trash2, BarChart3,
  AlertTriangle, Shield, Loader2, ChevronRight,
  Sparkles, X, Save, RotateCcw
} from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';

interface Holding {
  ticker: string;
  shares: number;
  avgCost: number;
}

interface Position {
  ticker: string;
  name: string;
  shares: number;
  currentPrice: number;
  currentValue: number;
  avgCost: number | null;
  costBasis: number | null;
  gainLoss: number | null;
  gainLossPct: number | null;
  sector: string;
  beta: number;
  dividendYield: number;
  weight: number;
}

interface SectorAllocation {
  sector: string;
  value: number;
  weight: number;
}

interface PortfolioMetrics {
  beta: number;
  dividendYield: number;
  diversificationScore: number;
  riskLevel: string;
  positionCount: number;
  sectorCount: number;
}

interface BenchmarkComparison {
  name: string;
  beta: number;
  dividendYield: number;
  comparison: {
    betaDiff: number;
    betaLabel: string;
    dividendDiff: number;
    dividendLabel: string;
  };
}

interface PortfolioAnalysis {
  totalValue: number;
  totalCost: number | null;
  totalGainLoss: number | null;
  totalGainLossPct: number | null;
  positions: Position[];
  sectors: SectorAllocation[];
  metrics: PortfolioMetrics;
  benchmark?: BenchmarkComparison;
  recommendations: string[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Suositut suomalaiset osakkeet nopeaan lisäykseen
const POPULAR_STOCKS = [
  { ticker: 'NOKIA', name: 'Nokia' },
  { ticker: 'NDA-FI', name: 'Nordea' },
  { ticker: 'FORTUM', name: 'Fortum' },
  { ticker: 'SAMPO', name: 'Sampo' },
  { ticker: 'NESTE', name: 'Neste' },
  { ticker: 'UPM', name: 'UPM' },
  { ticker: 'STORA ENSO R', name: 'Stora Enso' },
  { ticker: 'ELISA', name: 'Elisa' },
  { ticker: 'KONE', name: 'Kone' },
  { ticker: 'ORION B', name: 'Orion' },
];

const STORAGE_KEY = 'trademaster_fi_portfolio';

export default function FiPortfolioPage() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [analysis, setAnalysis] = useState<PortfolioAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showQuickAdd, setShowQuickAdd] = useState(false);

  // Lataa tallennettu salkku
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setHoldings(parsed);
        }
      } catch (e) {
        // ignore
      }
    }
  }, []);

  // Tallenna salkku automaattisesti
  useEffect(() => {
    if (holdings.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(holdings));
    }
  }, [holdings]);

  const addHolding = (ticker?: string) => {
    const newHolding = { ticker: ticker || '', shares: 0, avgCost: 0 };
    setHoldings([...holdings, newHolding]);
    setShowQuickAdd(false);
  };

  const removeHolding = (index: number) => {
    const updated = holdings.filter((_, i) => i !== index);
    setHoldings(updated);
    if (updated.length === 0) {
      localStorage.removeItem(STORAGE_KEY);
      setAnalysis(null);
    }
  };

  const clearPortfolio = () => {
    setHoldings([]);
    setAnalysis(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  const updateHolding = (index: number, field: keyof Holding, value: string | number) => {
    const updated = [...holdings];
    if (field === 'ticker') {
      updated[index][field] = (value as string).toUpperCase();
    } else {
      updated[index][field] = Number(value) || 0;
    }
    setHoldings(updated);
  };

  const loadExamplePortfolio = () => {
    setHoldings([
      { ticker: 'NOKIA', shares: 500, avgCost: 4.20 },
      { ticker: 'NDA-FI', shares: 200, avgCost: 10.50 },
      { ticker: 'FORTUM', shares: 100, avgCost: 14.00 },
      { ticker: 'SAMPO', shares: 50, avgCost: 38.00 },
      { ticker: 'NESTE', shares: 30, avgCost: 45.00 },
    ]);
    setAnalysis(null);
  };

  const analyzePortfolio = async () => {
    const validHoldings = holdings.filter(h => h.ticker && h.shares > 0);
    if (validHoldings.length === 0) {
      setError('Lisää vähintään yksi osake salkkuun.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/fi/portfolio/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          holdings: validHoldings.map(h => ({
            ticker: h.ticker,
            shares: h.shares,
            avgCost: h.avgCost > 0 ? h.avgCost : null
          }))
        })
      });

      const data = await response.json();
      if (data.success) {
        setAnalysis(data.data);
      } else {
        setError('Analyysi epäonnistui. Tarkista tickerit.');
      }
    } catch (err) {
      setError('Verkkovirhe. Yritä uudelleen.');
    } finally {
      setLoading(false);
    }
  };

  const formatEur = (value: number) => {
    return new Intl.NumberFormat('fi-FI', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2
    }).format(value);
  };

  const formatPercent = (value: number) => {
    const prefix = value >= 0 ? '+' : '';
    return `${prefix}${value.toFixed(2).replace('.', ',')}%`;
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'LOW': return 'text-emerald-400 bg-emerald-500/20 border-emerald-500/30';
      case 'MEDIUM': return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30';
      case 'HIGH': return 'text-red-400 bg-red-500/20 border-red-500/30';
      default: return 'text-slate-400 bg-slate-500/20 border-slate-500/30';
    }
  };

  const getRiskLabel = (level: string) => {
    switch (level) {
      case 'LOW': return 'Matala';
      case 'MEDIUM': return 'Keskitaso';
      case 'HIGH': return 'Korkea';
      default: return level;
    }
  };

  const sectorColors = [
    'bg-cyan-500', 'bg-purple-500', 'bg-emerald-500', 'bg-orange-500',
    'bg-pink-500', 'bg-blue-500', 'bg-yellow-500', 'bg-red-500'
  ];

  const hasValidHoldings = holdings.some(h => h.ticker && h.shares > 0);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-[2400px] mx-auto px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40 py-4 2xl:py-6">
          <div className="flex items-center justify-between gap-4 2xl:gap-6 flex-wrap">
            <div className="flex items-center gap-3 2xl:gap-5">
              <Link
                href="/fi/dashboard"
                className="flex items-center gap-2 2xl:gap-3 text-sm 2xl:text-2xl text-slate-300 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-4 h-4 2xl:w-6 2xl:h-6" />
                Takaisin
              </Link>
              <div className="flex items-center gap-2 2xl:gap-4">
                <div className="p-2 2xl:p-3 rounded-lg 2xl:rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                  <PieChart className="w-5 h-5 2xl:w-8 2xl:h-8 text-emerald-400" />
                </div>
                <div>
                  <h1 className="text-xl 2xl:text-4xl font-semibold text-white">Salkkuanalyysi</h1>
                  <p className="text-xs 2xl:text-base text-slate-400">Suomalaiset osakkeet</p>
                </div>
              </div>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="max-w-[2400px] mx-auto px-3 sm:px-4 md:px-6 lg:px-8 xl:px-12 2xl:px-40 py-4 sm:py-6 md:py-10 2xl:py-16">
        <div className="max-w-5xl 2xl:max-w-6xl mx-auto space-y-4 sm:space-y-6 2xl:space-y-10">

          {/* Tyhjä tila - näytä aloitusohje */}
          {holdings.length === 0 && !analysis && (
            <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-3xl p-5 sm:p-8 2xl:p-12 text-center">
              <div className="w-12 h-12 sm:w-16 sm:h-16 2xl:w-24 2xl:h-24 mx-auto mb-3 sm:mb-4 2xl:mb-6 rounded-full bg-cyan-500/20 flex items-center justify-center">
                <PieChart className="w-6 h-6 sm:w-8 sm:h-8 2xl:w-12 2xl:h-12 text-cyan-400" />
              </div>
              <h2 className="text-lg sm:text-xl 2xl:text-4xl font-semibold text-white mb-2 2xl:mb-4">Analysoi salkkusi</h2>
              <p className="text-slate-400 text-sm sm:text-base 2xl:text-2xl mb-4 sm:mb-6 2xl:mb-10 max-w-md 2xl:max-w-2xl mx-auto">
                Lisää osakkeesi ja näe salkun hajauttaminen, riskitaso ja suositukset parempaan hajautukseen.
              </p>
              <div className="flex flex-col sm:flex-row justify-center gap-2 sm:gap-3 2xl:gap-5">
                <button
                  onClick={loadExamplePortfolio}
                  className="flex items-center justify-center gap-2 2xl:gap-3 px-4 sm:px-5 2xl:px-8 py-2 sm:py-2.5 2xl:py-4 bg-cyan-600 hover:bg-cyan-500 rounded-lg 2xl:rounded-xl text-xs sm:text-sm 2xl:text-2xl font-semibold text-white transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-6 2xl:h-6" />
                  Kokeile esimerkkisalkulla
                </button>
                <button
                  onClick={() => addHolding()}
                  className="flex items-center justify-center gap-2 2xl:gap-3 px-4 sm:px-5 2xl:px-8 py-2 sm:py-2.5 2xl:py-4 bg-slate-700 hover:bg-slate-600 rounded-lg 2xl:rounded-xl text-xs sm:text-sm 2xl:text-2xl font-medium text-white transition-colors"
                >
                  <Plus className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-6 2xl:h-6" />
                  Lisää oma salkku
                </button>
              </div>
            </div>
          )}

          {/* Input Form - näytä vain jos on osakkeita */}
          {holdings.length > 0 && (
            <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-3xl p-3 sm:p-5 2xl:p-10">
              <div className="flex items-center justify-between mb-3 sm:mb-4 2xl:mb-8">
                <h2 className="text-base sm:text-lg 2xl:text-4xl font-semibold text-white flex items-center gap-2 2xl:gap-4">
                  <BarChart3 className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8 text-cyan-400" />
                  Salkun osakkeet
                </h2>
                <div className="flex items-center gap-2">
                  {holdings.length > 0 && (
                    <button
                      onClick={clearPortfolio}
                      className="flex items-center gap-1 sm:gap-1.5 2xl:gap-2 px-2 sm:px-3 2xl:px-4 py-1 sm:py-1.5 2xl:py-2 text-[10px] sm:text-xs 2xl:text-base text-slate-400 hover:text-red-400 transition-colors"
                    >
                      <RotateCcw className="w-2.5 h-2.5 sm:w-3 sm:h-3 2xl:w-5 2xl:h-5" />
                      Tyhjennä
                    </button>
                  )}
                </div>
              </div>

              <div className="space-y-2 2xl:space-y-4">
                {holdings.map((holding, index) => (
                  <div key={index} className="flex flex-wrap sm:flex-nowrap gap-1.5 sm:gap-2 2xl:gap-4 items-center bg-slate-800/50 rounded-lg 2xl:rounded-xl p-1.5 sm:p-2 2xl:p-4">
                    <input
                      type="text"
                      value={holding.ticker}
                      onChange={(e) => updateHolding(index, 'ticker', e.target.value)}
                      placeholder="NOKIA"
                      className="flex-1 min-w-[70px] 2xl:min-w-[150px] bg-slate-900/50 border border-slate-700 rounded 2xl:rounded-lg px-2 sm:px-3 2xl:px-4 py-1.5 sm:py-2 2xl:py-3 text-xs sm:text-sm 2xl:text-2xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                    />
                    <div className="flex items-center gap-1 2xl:gap-2">
                      <input
                        type="number"
                        value={holding.shares || ''}
                        onChange={(e) => updateHolding(index, 'shares', e.target.value)}
                        placeholder="100"
                        className="w-14 sm:w-20 2xl:w-32 bg-slate-900/50 border border-slate-700 rounded 2xl:rounded-lg px-1.5 sm:px-2 2xl:px-4 py-1.5 sm:py-2 2xl:py-3 text-xs sm:text-sm 2xl:text-2xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 text-right"
                      />
                      <span className="text-[10px] sm:text-xs 2xl:text-base text-slate-500">kpl</span>
                    </div>
                    <div className="flex items-center gap-1 2xl:gap-2">
                      <input
                        type="number"
                        step="0.01"
                        value={holding.avgCost || ''}
                        onChange={(e) => updateHolding(index, 'avgCost', e.target.value)}
                        placeholder="0"
                        className="w-14 sm:w-20 2xl:w-32 bg-slate-900/50 border border-slate-700 rounded 2xl:rounded-lg px-1.5 sm:px-2 2xl:px-4 py-1.5 sm:py-2 2xl:py-3 text-xs sm:text-sm 2xl:text-2xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 text-right"
                      />
                      <span className="text-[10px] sm:text-xs 2xl:text-base text-slate-500">€</span>
                    </div>
                    <button
                      onClick={() => removeHolding(index)}
                      className="p-1.5 sm:p-2 2xl:p-3 text-slate-500 hover:text-red-400 transition-colors"
                    >
                      <X className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-6 2xl:h-6" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Lisää osake */}
              <div className="mt-3 2xl:mt-6 relative">
                <button
                  onClick={() => setShowQuickAdd(!showQuickAdd)}
                  className="flex items-center gap-2 2xl:gap-3 px-3 2xl:px-5 py-2 2xl:py-3 text-sm 2xl:text-2xl text-slate-400 hover:text-cyan-400 transition-colors"
                >
                  <Plus className="w-4 h-4 2xl:w-6 2xl:h-6" />
                  Lisää osake
                </button>

                {showQuickAdd && (
                  <div className="absolute left-0 top-full mt-1 z-10 bg-slate-800 border border-slate-700 rounded-lg 2xl:rounded-xl p-3 2xl:p-5 shadow-xl w-72 2xl:w-96">
                    <div className="text-xs 2xl:text-base text-slate-400 mb-2 2xl:mb-4">Suositut osakkeet:</div>
                    <div className="flex flex-wrap gap-1.5 2xl:gap-3 mb-3 2xl:mb-5">
                      {POPULAR_STOCKS.map((stock) => (
                        <button
                          key={stock.ticker}
                          onClick={() => addHolding(stock.ticker)}
                          className="px-2 2xl:px-4 py-1 2xl:py-2 text-xs 2xl:text-base bg-slate-700 hover:bg-cyan-600 rounded 2xl:rounded-lg text-slate-300 hover:text-white transition-colors"
                        >
                          {stock.name}
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={() => addHolding()}
                      className="w-full px-3 2xl:px-5 py-1.5 2xl:py-3 text-xs 2xl:text-base bg-slate-700 hover:bg-slate-600 rounded 2xl:rounded-lg text-slate-300 transition-colors"
                    >
                      Tyhjä rivi
                    </button>
                  </div>
                )}
              </div>

              {/* Analysoi-nappi */}
              <div className="mt-3 sm:mt-4 2xl:mt-8 pt-3 sm:pt-4 2xl:pt-8 border-t border-slate-700/50">
                <button
                  onClick={analyzePortfolio}
                  disabled={loading || !hasValidHoldings}
                  className="w-full flex items-center justify-center gap-2 2xl:gap-3 px-4 sm:px-6 2xl:px-10 py-2.5 sm:py-3 2xl:py-5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 rounded-lg 2xl:rounded-xl text-xs sm:text-sm 2xl:text-2xl font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-6 2xl:h-6 animate-spin" />
                      Analysoidaan...
                    </>
                  ) : (
                    <>
                      <ChevronRight className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-6 2xl:h-6" />
                      Analysoi salkku
                    </>
                  )}
                </button>
                {!hasValidHoldings && holdings.length > 0 && (
                  <p className="text-[10px] sm:text-xs 2xl:text-base text-slate-500 text-center mt-2 2xl:mt-4">
                    Lisää vähintään ticker ja kappalemäärä
                  </p>
                )}
              </div>

              {error && (
                <div className="mt-4 2xl:mt-6 p-3 2xl:p-5 bg-red-500/20 border border-red-500/30 rounded-lg 2xl:rounded-xl text-red-300 text-sm 2xl:text-xl">
                  {error}
                </div>
              )}
            </div>
          )}

          {/* Analysis Results */}
          {analysis && (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3 2xl:gap-6">
                <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-4 2xl:p-8">
                  <div className="text-[10px] sm:text-xs 2xl:text-xl text-slate-400 mb-0.5 sm:mb-1 2xl:mb-3">Salkun arvo</div>
                  <div className="text-base sm:text-xl 2xl:text-5xl font-bold text-white">{formatEur(analysis.totalValue)}</div>
                </div>
                {analysis.totalGainLoss !== null && (
                  <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-4 2xl:p-8">
                    <div className="text-[10px] sm:text-xs 2xl:text-xl text-slate-400 mb-0.5 sm:mb-1 2xl:mb-3">Tuotto</div>
                    <div className={`text-base sm:text-xl 2xl:text-5xl font-bold ${analysis.totalGainLoss >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {formatPercent(analysis.totalGainLossPct!)}
                    </div>
                    <div className={`text-[10px] sm:text-xs 2xl:text-xl ${analysis.totalGainLoss >= 0 ? 'text-emerald-400/70' : 'text-red-400/70'}`}>
                      {formatEur(analysis.totalGainLoss)}
                    </div>
                  </div>
                )}
                <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-4 2xl:p-8">
                  <div className="text-[10px] sm:text-xs 2xl:text-xl text-slate-400 mb-0.5 sm:mb-1 2xl:mb-3">Osinkotuotto</div>
                  <div className="text-base sm:text-xl 2xl:text-5xl font-bold text-cyan-400">{analysis.metrics.dividendYield.toFixed(2).replace('.', ',')}%</div>
                </div>
                <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-4 2xl:p-8">
                  <div className="text-[10px] sm:text-xs 2xl:text-xl text-slate-400 mb-0.5 sm:mb-1 2xl:mb-3">Riski</div>
                  <div className={`inline-block px-1.5 sm:px-2 2xl:px-4 py-0.5 2xl:py-2 rounded 2xl:rounded-lg text-xs sm:text-sm 2xl:text-2xl font-semibold border ${getRiskColor(analysis.metrics.riskLevel)}`}>
                    {getRiskLabel(analysis.metrics.riskLevel)}
                  </div>
                  <div className="text-[10px] sm:text-xs 2xl:text-xl text-slate-500 mt-0.5 sm:mt-1 2xl:mt-3">Beta {analysis.metrics.beta.toFixed(2).replace('.', ',')}</div>
                </div>
              </div>

              {/* Metrics & Sectors */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 2xl:gap-8">
                {/* Diversification */}
                <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-3xl p-3 sm:p-5 2xl:p-10">
                  <h3 className="text-xs sm:text-sm 2xl:text-3xl font-semibold text-white mb-2 sm:mb-3 2xl:mb-6 flex items-center gap-1.5 sm:gap-2 2xl:gap-4">
                    <Shield className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-7 2xl:h-7 text-emerald-400" />
                    Hajauttaminen
                  </h3>
                  <div className="mb-2 sm:mb-3 2xl:mb-6">
                    <div className="flex justify-between text-[10px] sm:text-xs 2xl:text-xl mb-1 2xl:mb-3">
                      <span className="text-slate-400">Hajautuspisteet</span>
                      <span className="text-white font-semibold">{analysis.metrics.diversificationScore}/100</span>
                    </div>
                    <div className="h-1.5 sm:h-2 2xl:h-4 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${analysis.metrics.diversificationScore >= 70 ? 'bg-emerald-500' : analysis.metrics.diversificationScore >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                        style={{ width: `${analysis.metrics.diversificationScore}%` }}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 sm:gap-3 2xl:gap-6 text-xs sm:text-sm 2xl:text-2xl">
                    <div className="bg-slate-800/50 rounded-lg 2xl:rounded-xl p-1.5 sm:p-2 2xl:p-5">
                      <div className="text-slate-400 text-[10px] sm:text-xs 2xl:text-base">Osakkeita</div>
                      <div className="text-white font-semibold 2xl:text-4xl">{analysis.metrics.positionCount}</div>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg 2xl:rounded-xl p-1.5 sm:p-2 2xl:p-5">
                      <div className="text-slate-400 text-[10px] sm:text-xs 2xl:text-base">Toimialoja</div>
                      <div className="text-white font-semibold 2xl:text-4xl">{analysis.metrics.sectorCount}</div>
                    </div>
                  </div>
                </div>

                {/* Sector Allocation */}
                <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-3xl p-3 sm:p-5 2xl:p-10">
                  <h3 className="text-xs sm:text-sm 2xl:text-3xl font-semibold text-white mb-2 sm:mb-3 2xl:mb-6 flex items-center gap-1.5 sm:gap-2 2xl:gap-4">
                    <PieChart className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-7 2xl:h-7 text-purple-400" />
                    Toimialajako
                  </h3>
                  <div className="space-y-1.5 sm:space-y-2 2xl:space-y-4">
                    {analysis.sectors.slice(0, 5).map((sector, i) => (
                      <div key={sector.sector}>
                        <div className="flex items-center justify-between text-xs sm:text-sm 2xl:text-2xl mb-0.5 sm:mb-1 2xl:mb-2">
                          <div className="flex items-center gap-1.5 sm:gap-2 2xl:gap-3">
                            <div className={`w-1.5 h-1.5 sm:w-2 sm:h-2 2xl:w-4 2xl:h-4 rounded-full ${sectorColors[i % sectorColors.length]}`} />
                            <span className="text-slate-300 truncate text-[11px] sm:text-sm 2xl:text-xl">{sector.sector}</span>
                          </div>
                          <span className="text-white font-medium text-[11px] sm:text-sm 2xl:text-2xl">{sector.weight.toFixed(1).replace('.', ',')}%</span>
                        </div>
                        <div className="h-1 2xl:h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${sectorColors[i % sectorColors.length]}`}
                            style={{ width: `${sector.weight}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Benchmark Comparison */}
              {analysis.benchmark && (
                <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-3xl p-3 sm:p-5 2xl:p-10">
                  <h3 className="text-xs sm:text-sm 2xl:text-3xl font-semibold text-white mb-3 sm:mb-4 2xl:mb-8 flex items-center gap-1.5 sm:gap-2 2xl:gap-4">
                    <BarChart3 className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-7 2xl:h-7 text-cyan-400" />
                    Vertailu: {analysis.benchmark.name}
                  </h3>
                  <div className="grid grid-cols-2 gap-2 sm:gap-4 2xl:gap-8">
                    {/* Beta comparison */}
                    <div className="bg-slate-800/50 rounded-lg 2xl:rounded-xl p-2 sm:p-3 2xl:p-6">
                      <div className="text-[10px] sm:text-xs 2xl:text-xl text-slate-400 mb-1.5 sm:mb-2 2xl:mb-4">Beta (riski)</div>
                      <div className="flex items-end justify-between">
                        <div>
                          <div className="text-sm sm:text-lg 2xl:text-4xl font-semibold text-white">{analysis.metrics.beta.toFixed(2).replace('.', ',')}</div>
                          <div className="text-[10px] sm:text-xs 2xl:text-base text-slate-500">Salkkusi</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm sm:text-lg 2xl:text-4xl font-semibold text-slate-400">{analysis.benchmark.beta.toFixed(2).replace('.', ',')}</div>
                          <div className="text-[10px] sm:text-xs 2xl:text-base text-slate-500">{analysis.benchmark.name}</div>
                        </div>
                      </div>
                      <div className={`mt-1.5 sm:mt-2 2xl:mt-4 text-[10px] sm:text-xs 2xl:text-base px-1.5 sm:px-2 2xl:px-4 py-0.5 sm:py-1 2xl:py-2 rounded 2xl:rounded-lg inline-block ${
                        analysis.benchmark.comparison.betaDiff < 0
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : analysis.benchmark.comparison.betaDiff > 0
                            ? 'bg-orange-500/20 text-orange-400'
                            : 'bg-slate-700 text-slate-400'
                      }`}>
                        {analysis.benchmark.comparison.betaLabel}
                      </div>
                    </div>
                    {/* Dividend comparison */}
                    <div className="bg-slate-800/50 rounded-lg 2xl:rounded-xl p-2 sm:p-3 2xl:p-6">
                      <div className="text-[10px] sm:text-xs 2xl:text-xl text-slate-400 mb-1.5 sm:mb-2 2xl:mb-4">Osinkotuotto</div>
                      <div className="flex items-end justify-between">
                        <div>
                          <div className="text-sm sm:text-lg 2xl:text-4xl font-semibold text-white">{analysis.metrics.dividendYield.toFixed(2).replace('.', ',')}%</div>
                          <div className="text-[10px] sm:text-xs 2xl:text-base text-slate-500">Salkkusi</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm sm:text-lg 2xl:text-4xl font-semibold text-slate-400">{analysis.benchmark.dividendYield.toFixed(1).replace('.', ',')}%</div>
                          <div className="text-[10px] sm:text-xs 2xl:text-base text-slate-500">{analysis.benchmark.name}</div>
                        </div>
                      </div>
                      <div className={`mt-1.5 sm:mt-2 2xl:mt-4 text-[10px] sm:text-xs 2xl:text-base px-1.5 sm:px-2 2xl:px-4 py-0.5 sm:py-1 2xl:py-2 rounded 2xl:rounded-lg inline-block ${
                        analysis.benchmark.comparison.dividendDiff > 0
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : analysis.benchmark.comparison.dividendDiff < 0
                            ? 'bg-orange-500/20 text-orange-400'
                            : 'bg-slate-700 text-slate-400'
                      }`}>
                        {analysis.benchmark.comparison.dividendLabel}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {analysis.recommendations.length > 0 && (
                <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-3xl p-3 sm:p-5 2xl:p-10">
                  <h3 className="text-xs sm:text-sm 2xl:text-3xl font-semibold text-white mb-2 sm:mb-3 2xl:mb-6 flex items-center gap-1.5 sm:gap-2 2xl:gap-4">
                    <AlertTriangle className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-7 2xl:h-7 text-yellow-400" />
                    Suositukset
                  </h3>
                  <ul className="space-y-1.5 sm:space-y-2 2xl:space-y-4">
                    {analysis.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-1.5 sm:gap-2 2xl:gap-4 text-xs sm:text-sm 2xl:text-2xl text-slate-300">
                        <span className="text-yellow-400 mt-0.5">•</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Positions Table */}
              <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-3xl p-3 sm:p-5 2xl:p-10 overflow-x-auto">
                <h3 className="text-xs sm:text-sm 2xl:text-3xl font-semibold text-white mb-2 sm:mb-3 2xl:mb-6">Positiot</h3>
                <table className="w-full text-xs sm:text-sm 2xl:text-2xl">
                  <thead>
                    <tr className="text-slate-400 text-[10px] sm:text-xs 2xl:text-xl border-b border-slate-700/50">
                      <th className="text-left py-1.5 sm:py-2 2xl:py-4 pr-2 sm:pr-3 2xl:pr-6">Osake</th>
                      <th className="text-right py-1.5 sm:py-2 2xl:py-4 px-1 sm:px-2 2xl:px-4">Kpl</th>
                      <th className="text-right py-1.5 sm:py-2 2xl:py-4 px-1 sm:px-2 2xl:px-4 hidden sm:table-cell">Hinta</th>
                      <th className="text-right py-1.5 sm:py-2 2xl:py-4 px-1 sm:px-2 2xl:px-4">Arvo</th>
                      <th className="text-right py-1.5 sm:py-2 2xl:py-4 px-1 sm:px-2 2xl:px-4">Tuotto</th>
                      <th className="text-right py-1.5 sm:py-2 2xl:py-4 px-1 sm:px-2 2xl:px-4">Paino</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.positions.map((pos) => (
                      <tr key={pos.ticker} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                        <td className="py-1.5 sm:py-2 2xl:py-5 pr-2 sm:pr-3 2xl:pr-6">
                          <Link href={`/fi/stocks/${pos.ticker}`} className="hover:text-cyan-400 transition-colors">
                            <div className="font-medium text-white text-xs sm:text-sm 2xl:text-2xl">{pos.ticker}</div>
                            <div className="text-[10px] sm:text-xs 2xl:text-base text-slate-400 truncate max-w-[80px] sm:max-w-[120px] 2xl:max-w-[200px]">{pos.name}</div>
                          </Link>
                        </td>
                        <td className="text-right py-1.5 sm:py-2 2xl:py-5 px-1 sm:px-2 2xl:px-4 text-slate-300">{pos.shares}</td>
                        <td className="text-right py-1.5 sm:py-2 2xl:py-5 px-1 sm:px-2 2xl:px-4 text-slate-300 hidden sm:table-cell">{formatEur(pos.currentPrice)}</td>
                        <td className="text-right py-1.5 sm:py-2 2xl:py-5 px-1 sm:px-2 2xl:px-4 text-white font-medium">{formatEur(pos.currentValue)}</td>
                        <td className="text-right py-1.5 sm:py-2 2xl:py-5 px-1 sm:px-2 2xl:px-4">
                          {pos.gainLossPct !== null ? (
                            <span className={pos.gainLossPct >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                              {formatPercent(pos.gainLossPct)}
                            </span>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                        <td className="text-right py-1.5 sm:py-2 2xl:py-5 px-1 sm:px-2 2xl:px-4 text-cyan-400">{pos.weight.toFixed(1).replace('.', ',')}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

        </div>
      </main>
    </div>
  );
}
