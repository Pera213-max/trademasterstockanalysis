'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { getQuickWins, QuickWinPick, formatPrice } from '@/lib/api';
import { Zap, TrendingUp, Activity, BarChart3, ChevronRight, Clock } from 'lucide-react';
import UpdateStatus from '@/components/UpdateStatus';

interface QuickWinsCardProps {
  className?: string;
}

const QuickWinsCard: React.FC<QuickWinsCardProps> = ({ className = '' }) => {
  const refreshIntervalMs = 1000 * 60 * 60 * 3;
  const { data, isLoading, isError, dataUpdatedAt, isFetching } = useQuery({
    queryKey: ['quick-wins'],
    queryFn: async () => {
      const response = await getQuickWins(5);
      console.log('Quick Wins response:', response);
      return response;
    },
    staleTime: refreshIntervalMs,
    refetchInterval: refreshIntervalMs
  });

  const picks = data?.data || [];

  if (isLoading) {
    return (
      <div className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6 ${className}`}>
        <div className="flex items-center gap-2 mb-6">
          <Zap className="w-6 h-6 text-yellow-500 animate-pulse" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Quick Wins</h2>
        </div>
        <div className="flex flex-col items-center justify-center py-8 mb-4">
          <Activity className="w-12 h-12 text-yellow-500 animate-spin mb-3" />
          <p className="text-gray-700 dark:text-gray-300 font-semibold mb-1">Scanning for Quick Wins...</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Analyzing high-volume opportunities (1-2 min)</p>
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 animate-pulse h-24"></div>
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <Zap className="w-6 h-6 text-yellow-500" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Quick Wins</h2>
        </div>
        <p className="text-red-500 dark:text-red-400">Failed to load quick wins</p>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Zap className="w-6 h-6 text-yellow-500" />
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Quick Wins</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">Day trading opportunities</p>
          </div>
        </div>
        <UpdateStatus
          lastUpdatedAt={dataUpdatedAt}
          refreshIntervalMs={refreshIntervalMs}
          isFetching={isFetching}
          className="text-gray-600 dark:text-gray-400"
        />
      </div>

      {/* Info Banner */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-4">
        <div className="flex items-start gap-3">
          <Zap className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-semibold text-yellow-900 dark:text-yellow-100 mb-1">What are Quick Wins?</p>
            <p className="text-yellow-800 dark:text-yellow-300">
              High-volume, liquid stocks with strong short-term momentum, volume surges, and elevated volatility.
              Perfect for active day traders looking for fast moves.
            </p>
            <p className="text-yellow-700 dark:text-yellow-400 text-xs mt-2 font-semibold">
              HIGH RISK: Day trading involves significant risk. Only trade with capital you can afford to lose.
            </p>
          </div>
        </div>
      </div>

      {/* Picks List */}
      <div className="space-y-3">
        {picks.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No quick win opportunities found right now
          </div>
        ) : (
          picks.map((pick) => {
            const breakdown = pick.breakdown ?? pick.scoreBreakdown;

            return (
              <div
                key={pick.ticker}
                className="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20
                  border-2 border-yellow-300 dark:border-yellow-700 rounded-lg p-4 hover:shadow-lg
                  transition-all duration-200 group cursor-pointer relative overflow-hidden"
              >
              {/* Animated pulse effect for high confidence */}
              {pick.confidence >= 80 && (
                <div className="absolute inset-0 bg-gradient-to-r from-yellow-400/10 to-orange-400/10 animate-pulse"></div>
              )}

              <div className="relative z-10">
                {/* Header Row */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-yellow-500 text-white text-xs font-bold">
                        {pick.rank}
                      </span>
                      <h3 className="text-lg font-bold text-gray-900 dark:text-white">{pick.ticker}</h3>
                      <span className="text-xs font-semibold px-2 py-1 rounded-full bg-yellow-500 text-white flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        QUICK WIN
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <span className="font-semibold">{formatPrice(pick.currentPrice)}</span>
                      <span>-&gt;</span>
                      <span className="font-semibold text-green-600 dark:text-green-400">
                        {formatPrice(pick.targetPrice)}
                      </span>
                      <span className="text-green-600 dark:text-green-400 font-bold">
                        (+{pick.potentialReturn.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1 mb-1">
                      <Activity className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                      <span className="text-lg font-bold text-gray-900 dark:text-white">{pick.confidence}</span>
                    </div>
                    <div className="text-xs font-semibold px-2 py-1 rounded bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                      {pick.riskLevel}
                    </div>
                  </div>
                </div>

                {/* Key Metrics */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
                  <div className="bg-white/60 dark:bg-gray-800/60 rounded p-2">
                    <div className="flex items-center gap-1 mb-1">
                      <TrendingUp className="w-3 h-3 text-green-600 dark:text-green-400" />
                      <p className="text-xs text-gray-600 dark:text-gray-400">Momentum</p>
                    </div>
                    <p className="text-sm font-bold text-green-600 dark:text-green-400">
                      +{pick.momentum.toFixed(2)}%
                    </p>
                  </div>
                  <div className="bg-white/60 dark:bg-gray-800/60 rounded p-2">
                    <div className="flex items-center gap-1 mb-1">
                      <BarChart3 className="w-3 h-3 text-orange-600 dark:text-orange-400" />
                      <p className="text-xs text-gray-600 dark:text-gray-400">Volume</p>
                    </div>
                    <p className="text-sm font-bold text-orange-600 dark:text-orange-400">
                      {pick.volumeRatio.toFixed(1)}x
                    </p>
                  </div>
                  <div className="bg-white/60 dark:bg-gray-800/60 rounded p-2">
                    <div className="flex items-center gap-1 mb-1">
                      <Clock className="w-3 h-3 text-blue-600 dark:text-blue-400" />
                      <p className="text-xs text-gray-600 dark:text-gray-400">Timeframe</p>
                    </div>
                    <p className="text-sm font-bold text-blue-600 dark:text-blue-400">
                      {pick.timeHorizon}
                    </p>
                  </div>
                </div>

                {/* Enhanced Score Breakdown */}
                <div className="bg-white/60 dark:bg-gray-800/60 rounded p-3 mb-3">
                  <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Score Breakdown</p>
                  {breakdown ? (
                    <div className="space-y-1">
                      {/* Base scores */}
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-blue-500 h-full rounded-full transition-all duration-500"
                            style={{ width: `${(breakdown.technical / 30) * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-20 text-right">
                          Tech: {breakdown.technical}/30
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-green-500 h-full rounded-full transition-all duration-500"
                            style={{ width: `${(breakdown.momentum / 30) * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-20 text-right">
                          Mom: {breakdown.momentum}/30
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-orange-500 h-full rounded-full transition-all duration-500"
                            style={{ width: `${(breakdown.volume / 25) * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-20 text-right">
                          Vol: {breakdown.volume}/25
                        </span>
                      </div>
                      {/* Bonus: Quick Win */}
                      {breakdown.quick_win > 0 && (
                        <div className="flex items-center gap-2 pt-1 border-t border-gray-300 dark:border-gray-600">
                          <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-yellow-500 h-full rounded-full transition-all duration-500"
                              style={{ width: `${(breakdown.quick_win / 15) * 100}%` }}
                            ></div>
                          </div>
                          <span className="text-xs font-bold text-yellow-600 dark:text-yellow-400 w-20 text-right">
                            Quick: {breakdown.quick_win}/15
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-500 dark:text-gray-400">Score breakdown unavailable</p>
                  )}
                </div>

                {/* Reasoning */}
                <div className="mb-3">
                  <p className="text-sm text-gray-700 dark:text-gray-300 font-medium">{pick.reasoning}</p>
                </div>

                {/* Signals */}
                <div className="flex flex-wrap gap-2 mb-3">
                  {pick.signals.map((signal, index) => (
                    <span
                      key={index}
                      className="text-xs px-2 py-1 rounded-full bg-yellow-100 dark:bg-yellow-900/30
                        text-yellow-700 dark:text-yellow-300 font-medium"
                    >
                      {signal}
                    </span>
                  ))}
                </div>

                {/* View Analysis Link */}
                <Link
                  href={`/stocks/${pick.ticker}`}
                  className="w-full bg-slate-800 hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600
                    text-white font-semibold py-2 px-4 rounded-lg transition-all duration-200
                    flex items-center justify-center gap-2 border border-slate-600 dark:border-slate-500
                    hover:border-yellow-500 dark:hover:border-yellow-500"
                >
                  View Full Analysis
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
            </div>
          );
        })
        )}
      </div>

      {/* Footer Warning */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3">
          <p className="text-xs text-red-700 dark:text-red-300 font-semibold">
            Day Trading Disclaimer: Quick wins are high-risk opportunities. These picks are meant for experienced
            day traders only. Always use stop-losses and never risk more than you can afford to lose. Past performance
            does not guarantee future results.
          </p>
        </div>
      </div>
    </div>
  );
};

export default QuickWinsCard;
