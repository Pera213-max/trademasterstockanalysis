"use client";

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { TrendingDown, Target, Clock, ChevronRight, Star, Zap, AlertCircle, RefreshCw, AlertTriangle, ArrowDownCircle } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/api';

interface ShortPick {
  ticker: string;
  name: string;
  rank: number;
  confidence: number;
  currentPrice: number;
  targetPrice: number;
  potentialReturn: number;
  reasoning: string;
  signals: string[];
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  sector?: string;
  breakdown?: {
    fundamental_weakness?: number;
    technical_bearish?: number;
    negative_sentiment?: number;
    momentum_reversal?: number;
    volume_distribution?: number;
  };
  squeeze_risk?: {
    risk: string;
    daysToCover?: number;
    shortInterest?: number;
  };
}

interface ShortPicksCardProps {
  timeHorizon?: 'day' | 'swing' | 'long';
}

const ShortPicksCard: React.FC<ShortPicksCardProps> = ({
  timeHorizon: initialHorizon = 'swing'
}) => {
  const [selectedHorizon, setSelectedHorizon] = useState<'day' | 'swing' | 'long'>(initialHorizon);

  // Fetch short picks from API
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['short-picks', selectedHorizon],
    queryFn: async () => {
      const response = await fetch(`${getApiBaseUrl()}/api/stocks/short-opportunities?timeframe=${selectedHorizon}&limit=10`);
      if (!response.ok) {
        throw new Error('Failed to fetch short picks');
      }
      return response.json();
    },
    staleTime: 1000 * 60 * 60, // 1 hour cache
    retry: 2,
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-red-900/50 via-orange-900/50 to-slate-900/50 border border-red-500/30 p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-white/20 rounded w-1/3"></div>
            <div className="h-4 bg-white/20 rounded w-2/3"></div>
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

  // Error state - Show friendly message instead of error
  if (error) {
    return (
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-red-900/50 via-orange-900/50 to-slate-900/50 border border-yellow-500/30 p-6">
        <div className="flex items-center gap-3 mb-4">
          <TrendingDown className="w-8 h-8 text-yellow-400" />
          <div>
            <h3 className="text-xl font-bold text-white">Short Picks</h3>
            <p className="text-slate-300 text-sm">
              Short opportunities analysis is currently being updated
            </p>
          </div>
        </div>
        <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700">
          <p className="text-slate-400 text-sm">
            ℹ️ The short picks analysis system is currently processing market data.
            This feature analyzes stocks for potential short opportunities based on technical
            and fundamental weakness indicators. Check back soon!
          </p>
        </div>
      </div>
    );
  }

  const picks = data?.data || [];

  const horizons = [
    { value: 'day' as const, label: 'Day Trading', icon: Zap, description: '1-3 days' },
    { value: 'swing' as const, label: 'Swing Trading', icon: TrendingDown, description: '1-4 weeks' },
    { value: 'long' as const, label: 'Long Term', icon: Target, description: '3+ months' },
  ];

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 85) return 'from-red-500 to-orange-600';
    if (confidence >= 70) return 'from-orange-500 to-yellow-600';
    return 'from-yellow-500 to-amber-600';
  };

  const getConfidenceTextColor = (confidence: number): string => {
    if (confidence >= 85) return 'text-red-400';
    if (confidence >= 70) return 'text-orange-400';
    return 'text-yellow-400';
  };

  const getRiskColor = (risk: ShortPick['riskLevel']): string => {
    const colors = {
      LOW: 'bg-green-500/20 text-green-300 border-green-500/30',
      MEDIUM: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
      HIGH: 'bg-red-500/20 text-red-300 border-red-500/30',
    };
    return colors[risk];
  };

  const formatPrice = (price: number): string => {
    return `$${price.toFixed(2)}`;
  };

  return (
    <div className="space-y-4">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-red-900/50 via-orange-900/50 to-slate-900/50 border border-red-500/30 p-6">
        <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/10 rounded-full blur-3xl"></div>
        <div className="relative">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-red-500 to-orange-600 rounded-xl">
                <TrendingDown className="w-8 h-8 text-white" />
              </div>
              <div>
                <h2 className="text-3xl font-bold text-white">Short Picks</h2>
                <p className="text-slate-300">Data-Driven Short Opportunities</p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2">
              <div className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20">
                <Star className="w-5 h-5 text-red-400" />
                <span className="text-white font-semibold">{picks.length} Opportunities</span>
              </div>
              <div className="flex items-center gap-1 text-xs text-slate-400">
                <RefreshCw className="w-3 h-3" />
                <span>Updates every 1h</span>
              </div>
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
        {picks.length === 0 ? (
          <div className="text-center py-12 text-slate-400 bg-slate-800/30 rounded-lg border border-slate-700">
            <TrendingDown className="w-12 h-12 mx-auto mb-3 text-slate-600" />
            <p className="text-lg font-medium">No short opportunities found</p>
            <p className="text-sm mt-2">Market conditions may not favor short positions right now</p>
          </div>
        ) : (
          picks.map((pick: ShortPick) => (
            <div
              key={pick.ticker}
              className="bg-slate-800/50 backdrop-blur-sm rounded-lg border border-slate-700/50 hover:border-red-600/50 transition-all hover:shadow-xl hover:shadow-red-900/20 overflow-hidden group cursor-pointer"
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
                        {pick.squeeze_risk && pick.squeeze_risk.risk === 'HIGH' && (
                          <span className="text-xs px-2 py-1 rounded-md bg-yellow-500/20 text-yellow-300 border border-yellow-500/30 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            SQUEEZE RISK
                          </span>
                        )}
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
                    <div className="text-red-400 font-semibold">{formatPrice(pick.targetPrice)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Downside</div>
                    <div className="text-red-400 font-semibold flex items-center gap-1">
                      <TrendingDown className="w-4 h-4" />
                      {pick.potentialReturn.toFixed(1)}%
                    </div>
                  </div>
                </div>

                {/* Reasoning */}
                <p className="text-slate-300 text-sm mb-3 leading-relaxed">
                  {pick.reasoning}
                </p>

                {/* Short Context */}
                <div className="mb-3 p-3 rounded-lg border bg-red-500/10 border-red-500/30 text-sm">
                  <div className="flex items-start gap-2">
                    <ArrowDownCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-medium text-red-400">Short Opportunity:</span>
                      <p className="text-slate-300 mt-1">
                        {pick.confidence >= 80
                          ? `Strong bearish signals indicate potential decline. Consider short position with proper risk management.`
                          : `Moderate bearish indicators suggest downward pressure. Use appropriate position sizing.`
                        }
                      </p>
                    </div>
                  </div>
                </div>

                {/* Signals */}
                <div className="flex items-center gap-2 flex-wrap mb-3">
                  {pick.signals.map((signal, index) => (
                    <span
                      key={index}
                      className="text-xs px-2 py-1 bg-red-500/20 text-red-300 rounded-md border border-red-500/30"
                    >
                      {signal}
                    </span>
                  ))}
                </div>

                {/* Action Button */}
                <Link
                  href={`/stocks/${pick.ticker}`}
                  className="w-full py-2 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white font-semibold rounded-lg transition-all flex items-center justify-center gap-2 group-hover:shadow-lg"
                >
                  View Full Analysis
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Disclaimer */}
      <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-red-200">
            <strong className="block mb-1">Short Selling Risk Warning</strong>
            Short selling involves unlimited risk potential. Always use stop-losses, monitor short squeeze indicators,
            and never risk more than you can afford to lose. This is not financial advice.
          </div>
        </div>
      </div>
    </div>
  );
};

export default ShortPicksCard;
