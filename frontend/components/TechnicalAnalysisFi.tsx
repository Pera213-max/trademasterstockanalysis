"use client";

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  Target,
  AlertTriangle,
  Search,
  ArrowUpCircle,
  ArrowDownCircle,
  MinusCircle,
} from 'lucide-react';
import { getFiTechnicals, FiTechnicals } from '@/lib/api';

const t = {
  title: 'Tekninen analyysi',
  subtitle: 'RSI, MACD, Bollinger-nauhat ja liukuvat keskiarvot',
  search: 'Hae osake (esim. NOKIA)',
  analyze: 'Analysoi',
  loading: 'Ladataan...',
  error: 'Teknistä analyysiä ei voitu ladata.',
  noData: 'Ei riittävästi historiadataa analyysiin.',
  rsi: 'RSI (Relative Strength Index)',
  macd: 'MACD',
  bollinger: 'Bollinger-nauhat',
  sma: 'Liukuvat keskiarvot',
  signals: 'Signaalit',
  summary: 'Yhteenveto',
  price: 'Hinta',
  upper: 'Yläreuna',
  middle: 'Keskiarvo',
  lower: 'Alareuna',
  position: 'Sijainti nauhalla',
  trend: 'Trendi',
  verdict: 'Suositus',
};

const getRsiColor = (value: number | null) => {
  if (value === null) return 'text-slate-400';
  if (value < 30) return 'text-emerald-400';
  if (value > 70) return 'text-red-400';
  if (value < 40) return 'text-yellow-400';
  if (value > 60) return 'text-cyan-400';
  return 'text-slate-300';
};

const getRsiLabel = (signal: string | null) => {
  const labels: Record<string, string> = {
    YLIMYYTY: 'Ylimyyty (Osta)',
    YLIOSTETTU: 'Yliostettu (Myy)',
    NEUTRAALI: 'Neutraali',
    HEIKKO: 'Heikko',
    VAHVA: 'Vahva',
  };
  return labels[signal || ''] || signal || '-';
};

const getMacdLabel = (signal: string | null) => {
  const labels: Record<string, string> = {
    BULLISH_CROSSOVER: 'Nouseva risteämä',
    BEARISH_CROSSOVER: 'Laskeva risteämä',
    BULLISH: 'Nouseva',
    BEARISH: 'Laskeva',
  };
  return labels[signal || ''] || signal || '-';
};

const getTrendLabel = (trend: string | null) => {
  const labels: Record<string, string> = {
    VAHVA_NOUSU: 'Vahva nousutrendi',
    VAHVA_LASKU: 'Vahva laskutrendi',
    NOUSU: 'Nousutrendi',
    LASKU: 'Laskutrendi',
  };
  return labels[trend || ''] || trend || '-';
};

const getTrendIcon = (trend: string | null) => {
  if (trend?.includes('NOUSU')) {
    return <TrendingUp className="w-5 h-5 text-emerald-400" />;
  }
  if (trend?.includes('LASKU')) {
    return <TrendingDown className="w-5 h-5 text-red-400" />;
  }
  return <MinusCircle className="w-5 h-5 text-slate-400" />;
};

const getVerdictStyle = (verdict: string) => {
  if (verdict === 'OSTA') return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50';
  if (verdict === 'MYY') return 'bg-red-500/20 text-red-300 border-red-500/50';
  if (verdict?.includes('OSTA')) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  if (verdict?.includes('MYY')) return 'bg-red-500/10 text-red-400 border-red-500/30';
  return 'bg-slate-500/20 text-slate-300 border-slate-500/50';
};

const TechnicalAnalysisFi: React.FC = () => {
  const searchParams = useSearchParams();
  const initialTicker = searchParams.get('ticker')?.toUpperCase() || 'NOKIA';

  const [ticker, setTicker] = useState(initialTicker);
  const [searchTicker, setSearchTicker] = useState(initialTicker);

  // Update when URL params change
  useEffect(() => {
    const urlTicker = searchParams.get('ticker')?.toUpperCase();
    if (urlTicker && urlTicker !== searchTicker) {
      setTicker(urlTicker);
      setSearchTicker(urlTicker);
    }
  }, [searchParams]);

  const techQuery = useQuery({
    queryKey: ['fi-technicals', searchTicker],
    queryFn: () => getFiTechnicals(searchTicker),
    enabled: !!searchTicker,
    staleTime: 5 * 60 * 1000,
  });

  const data = techQuery.data?.data;

  const handleSearch = () => {
    if (ticker.trim()) {
      setSearchTicker(ticker.trim().toUpperCase());
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-600/20 rounded-lg">
            <Activity className="w-7 h-7 text-purple-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">{t.title}</h2>
            <p className="text-sm text-slate-400">{t.subtitle}</p>
          </div>
        </div>

        {/* Search */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder={t.search}
              className="pl-9 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none w-48"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={techQuery.isFetching}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-700 text-white rounded-lg transition-colors"
          >
            {techQuery.isFetching ? t.loading : t.analyze}
          </button>
        </div>
      </div>

      {/* Error */}
      {techQuery.isError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-center gap-2 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <span>{t.error}</span>
        </div>
      )}

      {/* Loading */}
      {techQuery.isLoading && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4" />
          <p className="text-slate-400">{t.loading}</p>
        </div>
      )}

      {/* Results */}
      {data && (
        <>
          {/* Stock Header */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-white">{data.name}</h3>
                <p className="text-sm text-slate-400">{data.ticker} • {data.sector}</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-white">{data.price?.toFixed(2)} €</div>
                {data.summary && (
                  <div className={`inline-block px-3 py-1 rounded-full text-sm font-semibold border ${getVerdictStyle(data.summary.verdict)}`}>
                    {data.summary.verdict}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Summary */}
          {data.summary && (
            <div className="bg-gradient-to-r from-purple-900/30 to-indigo-900/30 border border-purple-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Target className="w-6 h-6 text-purple-400 flex-shrink-0 mt-1" />
                <div>
                  <h4 className="text-lg font-semibold text-white mb-1">{t.summary}</h4>
                  <p className="text-slate-300">{data.summary.text}</p>
                </div>
              </div>
            </div>
          )}

          {/* Signals */}
          {data.signals && data.signals.length > 0 && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
              <h4 className="text-white font-semibold mb-3 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
                {t.signals}
              </h4>
              <div className="space-y-2">
                {data.signals.map((signal, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center gap-2 p-2 rounded ${
                      signal.signal === 'BUY'
                        ? 'bg-emerald-500/10 border border-emerald-500/30'
                        : 'bg-red-500/10 border border-red-500/30'
                    }`}
                  >
                    {signal.signal === 'BUY' ? (
                      <ArrowUpCircle className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <ArrowDownCircle className="w-5 h-5 text-red-400" />
                    )}
                    <span className="text-sm text-slate-200">{signal.text}</span>
                    <span className={`ml-auto text-xs px-2 py-0.5 rounded ${
                      signal.signal === 'BUY' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'
                    }`}>
                      {signal.type}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Indicators Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* RSI */}
            {data.rsi && (
              <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                <h4 className="text-white font-semibold mb-3 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-cyan-400" />
                  {t.rsi}
                </h4>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Arvo ({data.rsi.period} päivää)</span>
                    <span className={`text-2xl font-bold ${getRsiColor(data.rsi.value)}`}>
                      {data.rsi.value?.toFixed(1) ?? '-'}
                    </span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-3 relative overflow-hidden">
                    <div className="absolute inset-y-0 left-0 w-[30%] bg-emerald-500/30" />
                    <div className="absolute inset-y-0 left-[30%] w-[40%] bg-slate-600/50" />
                    <div className="absolute inset-y-0 left-[70%] w-[30%] bg-red-500/30" />
                    {data.rsi.value && (
                      <div
                        className="absolute top-0 bottom-0 w-1 bg-white rounded"
                        style={{ left: `${Math.min(100, Math.max(0, data.rsi.value))}%` }}
                      />
                    )}
                  </div>
                  <div className="flex justify-between text-xs text-slate-500">
                    <span>0 (Ylimyyty)</span>
                    <span>50</span>
                    <span>100 (Yliostettu)</span>
                  </div>
                  <div className="text-center">
                    <span className={`px-3 py-1 rounded-full text-sm ${getRsiColor(data.rsi.value)} bg-slate-700/50`}>
                      {getRsiLabel(data.rsi.signal)}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* MACD */}
            {data.macd && (
              <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                <h4 className="text-white font-semibold mb-3 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-purple-400" />
                  {t.macd}
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">MACD</span>
                    <span className={`font-semibold ${(data.macd.value ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {data.macd.value?.toFixed(4) ?? '-'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Signaalilinja</span>
                    <span className="text-slate-300">{data.macd.signal_line?.toFixed(4) ?? '-'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Histogrammi</span>
                    <span className={`font-semibold ${(data.macd.histogram ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {data.macd.histogram?.toFixed(4) ?? '-'}
                    </span>
                  </div>
                  <div className="pt-2 border-t border-slate-700">
                    <div className="flex items-center justify-center gap-2">
                      {data.macd.signal?.includes('BULLISH') ? (
                        <TrendingUp className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <TrendingDown className="w-5 h-5 text-red-400" />
                      )}
                      <span className={data.macd.signal?.includes('BULLISH') ? 'text-emerald-400' : 'text-red-400'}>
                        {getMacdLabel(data.macd.signal)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Bollinger Bands */}
            {data.bollinger && (
              <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                <h4 className="text-white font-semibold mb-3 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-amber-400" />
                  {t.bollinger}
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">{t.upper}</span>
                    <span className="text-red-300">{data.bollinger.upper?.toFixed(2) ?? '-'} €</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">{t.middle}</span>
                    <span className="text-slate-300">{data.bollinger.middle?.toFixed(2) ?? '-'} €</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">{t.lower}</span>
                    <span className="text-emerald-300">{data.bollinger.lower?.toFixed(2) ?? '-'} €</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">{t.price}</span>
                    <span className="text-white font-semibold">{data.price?.toFixed(2)} €</span>
                  </div>
                  <div className="pt-2">
                    <div className="text-xs text-slate-500 mb-1">{t.position}</div>
                    <div className="w-full bg-slate-700 rounded-full h-2 relative">
                      <div
                        className="absolute top-0 bottom-0 w-2 h-2 bg-amber-400 rounded-full -translate-x-1/2"
                        style={{ left: `${Math.min(100, Math.max(0, data.bollinger.position ?? 50))}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-slate-500 mt-1">
                      <span>Alaraja</span>
                      <span>{data.bollinger.position?.toFixed(0)}%</span>
                      <span>Yläraja</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* SMA */}
            {data.sma && (
              <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                <h4 className="text-white font-semibold mb-3 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-blue-400" />
                  {t.sma}
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">SMA 20</span>
                    <span className={data.price > (data.sma.sma20 ?? 0) ? 'text-emerald-400' : 'text-red-400'}>
                      {data.sma.sma20?.toFixed(2) ?? '-'} €
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">SMA 50</span>
                    <span className={data.price > (data.sma.sma50 ?? 0) ? 'text-emerald-400' : 'text-red-400'}>
                      {data.sma.sma50?.toFixed(2) ?? '-'} €
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">SMA 200</span>
                    <span className={data.price > (data.sma.sma200 ?? 0) ? 'text-emerald-400' : 'text-red-400'}>
                      {data.sma.sma200?.toFixed(2) ?? '-'} €
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">{t.price}</span>
                    <span className="text-white font-semibold">{data.price?.toFixed(2)} €</span>
                  </div>
                  <div className="pt-2 border-t border-slate-700">
                    <div className="flex items-center justify-center gap-2">
                      {getTrendIcon(data.sma.trend)}
                      <span className={data.sma.trend?.includes('NOUSU') ? 'text-emerald-400' : data.sma.trend?.includes('LASKU') ? 'text-red-400' : 'text-slate-400'}>
                        {getTrendLabel(data.sma.trend)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default TechnicalAnalysisFi;
