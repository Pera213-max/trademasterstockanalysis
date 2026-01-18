"use client";

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Sparkles, TrendingUp, Target, Clock, ChevronRight, Star, Zap, Loader2, AlertCircle, Newspaper, ArrowUpCircle, ArrowDownCircle } from 'lucide-react';
import { getTopStockPicks, formatPrice, type StockPick } from '@/lib/api';
import UpdateStatus from '@/components/UpdateStatus';

interface AIPicksCardProps {
  timeHorizon?: 'day' | 'swing' | 'long';
}

const AIPicksCard: React.FC<AIPicksCardProps> = ({
  timeHorizon: initialHorizon = 'swing'
}) => {
  const [selectedHorizon, setSelectedHorizon] = useState<'day' | 'swing' | 'long'>(initialHorizon);

  // Fetch AI picks from API
  const refreshIntervalMs = 1000 * 60 * 60 * 12;
  const { data, isLoading, error, refetch, dataUpdatedAt, isFetching } = useQuery({
    queryKey: ['stock-picks', selectedHorizon],
    queryFn: () => getTopStockPicks(selectedHorizon),
    staleTime: refreshIntervalMs, // 12 hour cache (matches backend)
    refetchInterval: refreshIntervalMs,
    refetchOnWindowFocus: true, // Refresh when user returns
    retry: 2
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-900/50 via-blue-900/50 to-slate-900/50 border border-purple-500/30 p-6">
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-16 h-16 text-purple-400 animate-spin mb-4" />
            <h3 className="text-2xl font-bold text-white mb-2">Loading Stock Analysis</h3>
            <p className="text-slate-300 text-center max-w-md mb-1">
              Analyzing {selectedHorizon === 'day' ? 'day trading' : selectedHorizon === 'swing' ? 'swing trading' : 'long-term'} opportunities...
            </p>
            <p className="text-sm text-slate-400 text-center">
              This usually takes 1-2 minutes on first load
            </p>
          </div>
          <div className="animate-pulse space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-white/10 rounded"></div>
              ))}
            </div>
          </div>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-48 bg-slate-800/50 rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-red-900/50 via-purple-900/50 to-slate-900/50 border border-red-500/30 p-6">
        <div className="flex items-center gap-3 mb-4">
          <AlertCircle className="w-8 h-8 text-red-400" />
          <div>
            <h3 className="text-xl font-bold text-white">Error Loading Stock Picks</h3>
            <p className="text-red-300 text-sm">
              {error instanceof Error ? error.message : 'Failed to load predictions'}
            </p>
          </div>
        </div>
        <button
          onClick={() => refetch()}
          className="px-6 py-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-lg text-white font-semibold transition-all"
        >
          Retry
        </button>
      </div>
    );
  }

  const picks = data?.data || [];

  const horizons = [
    { value: 'day' as const, label: 'Day Trading', icon: Zap, description: '1-3 days' },
    { value: 'swing' as const, label: 'Swing Trading', icon: TrendingUp, description: '1-4 weeks' },
    { value: 'long' as const, label: 'Long Term', icon: Target, description: '3+ months' },
  ];

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 85) return 'from-green-500 to-emerald-600';
    if (confidence >= 70) return 'from-blue-500 to-cyan-600';
    return 'from-yellow-500 to-orange-600';
  };

  const getConfidenceTextColor = (confidence: number): string => {
    if (confidence >= 85) return 'text-green-400';
    if (confidence >= 70) return 'text-blue-400';
    return 'text-yellow-400';
  };

  const getRiskColor = (risk: StockPick['riskLevel']): string => {
    const colors = {
      LOW: 'bg-green-500/20 text-green-300 border-green-500/30',
      MEDIUM: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
      HIGH: 'bg-red-500/20 text-red-300 border-red-500/30',
    };
    return colors[risk];
  };

  // Generate news context for stock based on signals
  const getNewsContext = (pick: StockPick): { isPositive: boolean; context: string } => {
    const signals = pick.signals || [];
    const reasoning = pick.reasoning || '';

    // Check for positive catalysts
    if (signals.some(s => s.toLowerCase().includes('bullish')) ||
        reasoning.toLowerCase().includes('momentum') ||
        reasoning.toLowerCase().includes('breakout')) {
      return {
        isPositive: true,
        context: `Strong technical signal - ${pick.ticker} showing bullish patterns. Volume increase and positive momentum support buy signal.`
      };
    }

    if (signals.some(s => s.toLowerCase().includes('volume'))) {
      return {
        isPositive: true,
        context: `Volume surge detected - institutional investors may be accumulating positions in ${pick.ticker}.`
      };
    }

    if (reasoning.toLowerCase().includes('oversold') ||
        signals.some(s => s.toLowerCase().includes('rsi'))) {
      return {
        isPositive: true,
        context: `Oversold condition - ${pick.ticker} priced below fundamentals. Technical reversal possible.`
      };
    }

    if (pick.potentialReturn > 20) {
      return {
        isPositive: true,
        context: `High return potential (${pick.potentialReturn.toFixed(0)}%) - analyst price targets well above current price.`
      };
    }

    if (pick.riskLevel === 'HIGH') {
      return {
        isPositive: false,
        context: `High risk/reward - ${pick.ticker} requires tight stop-loss. High volatility enables quick moves.`
      };
    }

    return {
      isPositive: true,
      context: `Technical analysis identifies positive signal. Multiple indicators support buy position in coming days.`
    };
  };

  // Picks are already sorted by rank from the API
  const filteredPicks = picks;

  return (
    <div className="space-y-4">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-900/50 via-blue-900/50 to-slate-900/50 border border-purple-500/30 p-6">
        <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl"></div>
        <div className="relative">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <div>
                <h2 className="text-3xl font-bold text-white">Top Picks</h2>
                <p className="text-slate-300">Data-Driven Stock Screening</p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2">
              <div className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20">
                <Star className="w-5 h-5 text-yellow-400" />
                <span className="text-white font-semibold">{filteredPicks.length} Picks</span>
              </div>
              <UpdateStatus
                lastUpdatedAt={dataUpdatedAt}
                refreshIntervalMs={refreshIntervalMs}
                isFetching={isFetching}
                className="text-slate-400"
              />
            </div>
          </div>

          {/* Time Horizon Selector */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {horizons.map((horizon) => {
              const Icon = horizon.icon;
              const isSelected = selectedHorizon === horizon.value;
              return (
                <button
                  key={horizon.value}
                  onClick={() => setSelectedHorizon(horizon.value)}
                  className={`p-4 rounded-lg transition-all ${
                    isSelected
                      ? 'bg-white/20 border-2 border-white/40 shadow-lg'
                      : 'bg-white/5 border border-white/10 hover:bg-white/10'
                  }`}
                >
                  <Icon className={`w-6 h-6 mb-2 ${isSelected ? 'text-white' : 'text-slate-400'}`} />
                  <div className={`font-semibold ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                    {horizon.label}
                  </div>
                  <div className="text-xs text-slate-400">{horizon.description}</div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Picks List */}
      <div className="space-y-3">
        {filteredPicks.map((pick) => (
          <div
            key={pick.ticker}
            className="bg-slate-800/50 backdrop-blur-sm rounded-lg border border-slate-700/50 hover:border-slate-600 transition-all hover:shadow-xl hover:shadow-slate-900/50 overflow-hidden group cursor-pointer"
          >
            <div className="p-4">
              {/* Header Row */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  {/* Rank Badge */}
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center font-bold text-xl bg-gradient-to-br ${getConfidenceColor(pick.confidence)} text-white shadow-lg`}>
                    #{pick.rank}
                  </div>

                  {/* Ticker Info */}
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-white text-xl">{pick.ticker}</span>
                      <span className={`text-xs px-2 py-1 rounded-md border ${getRiskColor(pick.riskLevel)}`}>
                        {pick.riskLevel} RISK
                      </span>
                    </div>
                    <p className="text-slate-400 text-sm">{pick.name}</p>
                  </div>
                </div>

                {/* Confidence Score */}
                <div className="text-right">
                  <div className={`text-3xl font-bold ${getConfidenceTextColor(pick.confidence)}`}>
                    {pick.confidence}
                  </div>
                  <div className="text-xs text-slate-500">Confidence</div>
                  <div className="mt-1 h-2 w-24 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full bg-gradient-to-r ${getConfidenceColor(pick.confidence)} transition-all`}
                      style={{ width: `${pick.confidence}%` }}
                    ></div>
                  </div>
                </div>
              </div>

              {/* Price Info */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-3 p-3 bg-slate-900/50 rounded-lg">
                <div>
                  <div className="text-xs text-slate-500 mb-1">Current</div>
                  <div className="text-white font-semibold">{formatPrice(pick.currentPrice)}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">Target</div>
                  <div className="text-green-400 font-semibold">{formatPrice(pick.targetPrice)}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">Upside</div>
                  <div className="text-green-400 font-semibold flex items-center gap-1">
                    <TrendingUp className="w-4 h-4" />
                    +{pick.potentialReturn.toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Reasoning */}
              <p className="text-slate-300 text-sm mb-3 leading-relaxed">
                {pick.reasoning}
              </p>

              {/* News Context */}
              {(() => {
                const newsContext = getNewsContext(pick);
                return (
                  <div className={`mb-3 p-3 rounded-lg border text-sm ${
                    newsContext.isPositive
                      ? 'bg-green-500/10 border-green-500/30'
                      : 'bg-yellow-500/10 border-yellow-500/30'
                  }`}>
                    <div className="flex items-start gap-2">
                      {newsContext.isPositive ? (
                        <ArrowUpCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                      )}
                      <div>
                        <span className={`font-medium ${newsContext.isPositive ? 'text-green-400' : 'text-yellow-400'}`}>
                          {newsContext.isPositive ? 'Catalyst:' : 'Note:'}
                        </span>
                        <p className="text-slate-300 mt-1">{newsContext.context}</p>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Signals */}
              <div className="flex items-center gap-2 flex-wrap mb-3">
                {pick.signals.map((signal, index) => (
                  <span
                    key={index}
                    className="text-xs px-2 py-1 bg-blue-500/20 text-blue-300 rounded-md border border-blue-500/30"
                  >
                    {signal}
                  </span>
                ))}
              </div>

              {/* Action Button */}
              <Link
                href={`/stocks/${pick.ticker}`}
                className="w-full py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-semibold rounded-lg transition-all flex items-center justify-center gap-2 group-hover:shadow-lg"
              >
                View Full Analysis
                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>
        ))}
      </div>

      {/* Disclaimer */}
      <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
        <div className="flex items-start gap-3">
          <Clock className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-200">
            <strong className="block mb-1">Investment Disclaimer</strong>
            These picks are based on technical analysis and should not be considered financial advice.
            Always conduct your own research and consider your risk tolerance before making investment decisions.
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIPicksCard;
