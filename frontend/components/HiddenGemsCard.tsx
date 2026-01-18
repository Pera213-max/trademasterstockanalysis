'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { getHiddenGems, HiddenGemPick, Timeframe, formatPrice, formatLargeNumber } from '@/lib/api';
import { TrendingUp, Gem, ChevronRight, BarChart3 } from 'lucide-react';
import UpdateStatus from '@/components/UpdateStatus';

interface HiddenGemsCardProps {
  className?: string;
}

const HiddenGemsCard: React.FC<HiddenGemsCardProps> = ({ className = '' }) => {
  const [timeframe, setTimeframe] = useState<Timeframe>('swing');

  const refreshIntervalMs = 1000 * 60 * 60 * 3;
  const { data, isLoading, isError, dataUpdatedAt, isFetching } = useQuery({
    queryKey: ['hidden-gems', timeframe],
    queryFn: async () => {
      const response = await getHiddenGems(timeframe, 5);
      console.log('Hidden Gems response:', response);
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
          <Gem className="w-6 h-6 text-purple-500 animate-pulse" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Hidden Gems</h2>
        </div>
        <div className="flex flex-col items-center justify-center py-8 mb-4">
          <BarChart3 className="w-12 h-12 text-purple-500 animate-bounce mb-3" />
          <p className="text-gray-700 dark:text-gray-300 font-semibold mb-1">Discovering Hidden Gems...</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Finding undervalued stocks (1-2 min)</p>
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
          <Gem className="w-6 h-6 text-purple-500" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Hidden Gems</h2>
        </div>
        <p className="text-red-500 dark:text-red-400">Failed to load hidden gems</p>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="flex items-center gap-2">
          <Gem className="w-6 h-6 text-purple-500" />
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Hidden Gems</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">High-potential stocks others miss</p>
          </div>
        </div>
        <UpdateStatus
          lastUpdatedAt={dataUpdatedAt}
          refreshIntervalMs={refreshIntervalMs}
          isFetching={isFetching}
          className="text-gray-500 dark:text-gray-400"
        />
      </div>

      {/* Timeframe Selector */}
      <div className="flex gap-2 mb-4">
        {[
          { value: 'day' as Timeframe, label: 'Day' },
          { value: 'swing' as Timeframe, label: 'Swing' },
          { value: 'long' as Timeframe, label: 'Long' },
        ].map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setTimeframe(value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              timeframe === value
                ? 'bg-purple-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Info Banner */}
      <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4 mb-4">
        <div className="flex items-start gap-3">
          <Gem className="w-5 h-5 text-purple-600 dark:text-purple-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-semibold text-purple-900 dark:text-purple-100 mb-1">What are Hidden Gems?</p>
            <p className="text-purple-800 dark:text-purple-300">
              Mid/small-cap stocks ($500M-$10B) with high revenue growth (&gt;30%), low analyst coverage,
              and strong technical patterns. These are stocks most people miss before they break out.
            </p>
          </div>
        </div>
      </div>

      {/* Picks List */}
      <div className="space-y-3">
        {picks.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No hidden gems found for this timeframe
          </div>
        ) : (
          picks.map((pick) => {
            const breakdown = pick.breakdown ?? pick.scoreBreakdown;

            return (
              <div
                key={pick.ticker}
                className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20
                  border border-purple-200 dark:border-purple-800 rounded-lg p-4 hover:shadow-lg
                  transition-all duration-200 group cursor-pointer"
              >
              {/* Header Row */}
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-purple-600 text-white text-xs font-bold">
                      {pick.rank}
                    </span>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white">{pick.ticker}</h3>
                    <span className="text-xs font-semibold px-2 py-1 rounded-full bg-purple-600 text-white">
                      {pick.category}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                    <span>{formatPrice(pick.currentPrice)}</span>
                    <span>-</span>
                    <span className={pick.potentialReturn >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                      {pick.potentialReturn >= 0 ? '+' : ''}{pick.potentialReturn.toFixed(1)}% potential
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-1 mb-1">
                    <BarChart3 className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                    <span className="text-lg font-bold text-gray-900 dark:text-white">{pick.confidence}</span>
                  </div>
                  <div className={`text-xs font-semibold px-2 py-1 rounded ${
                    pick.riskLevel === 'LOW'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : pick.riskLevel === 'MEDIUM'
                      ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                      : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  }`}>
                    {pick.riskLevel}
                  </div>
                </div>
              </div>

              {/* Fundamental Stats */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
                <div className="bg-white/50 dark:bg-gray-800/50 rounded p-2">
                  <p className="text-xs text-gray-600 dark:text-gray-400">Market Cap</p>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">
                    {formatLargeNumber(pick.marketCap)}
                  </p>
                </div>
                <div className="bg-white/50 dark:bg-gray-800/50 rounded p-2">
                  <p className="text-xs text-gray-600 dark:text-gray-400">Revenue Growth</p>
                  <p className="text-sm font-semibold text-green-600 dark:text-green-400">
                    +{pick.revenueGrowth.toFixed(0)}%
                  </p>
                </div>
                <div className="bg-white/50 dark:bg-gray-800/50 rounded p-2">
                  <p className="text-xs text-gray-600 dark:text-gray-400">Target</p>
                  <p className="text-sm font-semibold text-purple-600 dark:text-purple-400">
                    {formatPrice(pick.targetPrice)}
                  </p>
                </div>
              </div>

              {/* Enhanced Score Breakdown */}
              <div className="bg-white/50 dark:bg-gray-800/50 rounded p-3 mb-3">
                <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Enhanced Score Breakdown</p>
                {breakdown ? (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Technical:</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{breakdown.technical}/30</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Momentum:</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{breakdown.momentum}/30</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Volume:</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{breakdown.volume}/25</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Trend:</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{breakdown.trend}/20</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-purple-600 dark:text-purple-400 font-semibold">Hidden Gem:</span>
                      <span className="font-bold text-purple-600 dark:text-purple-400">{breakdown.hidden_gem}/20</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-blue-600 dark:text-blue-400 font-semibold">Smart Money:</span>
                      <span className="font-bold text-blue-600 dark:text-blue-400">{breakdown.smart_money}/15</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 dark:text-gray-400">Score breakdown unavailable</p>
                )}
              </div>

              {/* Reasoning */}
              <div className="mb-3">
                <p className="text-sm text-gray-700 dark:text-gray-300">{pick.reasoning}</p>
              </div>

              {/* Signals */}
              <div className="flex flex-wrap gap-2 mb-3">
                {pick.signals.map((signal, index) => (
                  <span
                    key={index}
                    className="text-xs px-2 py-1 rounded-full bg-purple-100 dark:bg-purple-900/30
                      text-purple-700 dark:text-purple-300 font-medium"
                  >
                    {signal}
                  </span>
                ))}
                {pick.volumeSurge && (
                  <span className="text-xs px-2 py-1 rounded-full bg-orange-100 dark:bg-orange-900/30
                    text-orange-700 dark:text-orange-300 font-medium flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" />
                    Volume Surge
                  </span>
                )}
              </div>

              {/* View Details Link */}
              <div className="flex items-center justify-between pt-3 border-t border-purple-200 dark:border-purple-800">
                <span className="text-xs text-gray-600 dark:text-gray-400">
                  Timeframe: <span className="font-semibold">{pick.timeHorizon}</span>
                </span>
                <Link
                  href={`/stocks/${pick.ticker}`}
                  className="flex items-center gap-1 text-sm font-medium text-purple-600 dark:text-purple-400
                  hover:text-purple-700 dark:hover:text-purple-300 transition-colors group-hover:gap-2"
                >
                  View Full Analysis
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          );
        })
        )}
      </div>

      {/* Footer Note */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800">
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
          Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
};

export default HiddenGemsCard;
