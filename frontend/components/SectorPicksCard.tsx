'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getSectorPicks, SectorPick, Sector, Theme, Timeframe } from '@/lib/api';
import { TrendingUp, TrendingDown, Target, Activity, DollarSign, Cpu, Zap, Heart, Building2, ShoppingCart, Leaf, type LucideIcon } from 'lucide-react';

interface SectorPicksCardProps {
  defaultSector?: Sector;
  defaultTheme?: Theme;
  defaultTimeframe?: Timeframe;
}

const SectorPicksCard: React.FC<SectorPicksCardProps> = ({
  defaultSector,
  defaultTheme,
  defaultTimeframe = 'swing'
}) => {
  const [selectedSector, setSelectedSector] = useState<Sector | undefined>(defaultSector);
  const [selectedTheme, setSelectedTheme] = useState<Theme | undefined>(defaultTheme);
  const [selectedTimeframe, setSelectedTimeframe] = useState<Timeframe>(defaultTimeframe);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['sector-picks', selectedSector, selectedTheme, selectedTimeframe],
    queryFn: () => getSectorPicks(selectedSector, selectedTheme, selectedTimeframe, 5),
    staleTime: 1000 * 60 * 60 * 12, // 12 hours
    retry: 2,
  });

  const sectors: { value: Sector; label: string; Icon: LucideIcon }[] = [
    { value: 'tech', label: 'Technology', Icon: Cpu },
    { value: 'energy', label: 'Energy', Icon: Zap },
    { value: 'healthcare', label: 'Healthcare', Icon: Heart },
    { value: 'finance', label: 'Finance', Icon: Building2 },
    { value: 'consumer', label: 'Consumer', Icon: ShoppingCart },
  ];

  const themes: { value: Theme; label: string; Icon: LucideIcon }[] = [
    { value: 'growth', label: 'Growth', Icon: TrendingUp },
    { value: 'value', label: 'Value', Icon: DollarSign },
    { value: 'esg', label: 'ESG', Icon: Leaf },
  ];

  const timeframes: { value: Timeframe; label: string }[] = [
    { value: 'day', label: 'Day Trade' },
    { value: 'swing', label: 'Swing' },
    { value: 'long', label: 'Long Term' },
  ];

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'LOW':
        return 'text-green-400';
      case 'MEDIUM':
        return 'text-yellow-400';
      case 'HIGH':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const getReturnColor = (returnPercent: number) => {
    return returnPercent >= 0 ? 'text-green-400' : 'text-red-400';
  };

  if (isLoading) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">Sector Picks</h2>
          <div className="animate-pulse bg-gray-700 h-6 w-24 rounded"></div>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="animate-pulse bg-gray-800 h-20 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <div className="text-center py-8">
          <p className="text-red-400 mb-4">Failed to load sector picks</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const picks = data?.data || [];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white">Sector Picks</h2>
          <p className="text-sm text-gray-400 mt-1">
            Top-scored picks by sector and theme
          </p>
        </div>
        {data?.cached && (
          <span className="text-xs text-blue-400 bg-blue-900/30 px-2 py-1 rounded">
            Cached
          </span>
        )}
      </div>

      {/* Sector Tabs */}
      <div className="mb-4">
        <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">Sector</p>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedSector(undefined)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              selectedSector === undefined
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            All
          </button>
          {sectors.map((sector) => (
            <button
              key={sector.value}
              onClick={() => setSelectedSector(sector.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition flex items-center gap-1.5 ${
                selectedSector === sector.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              <sector.Icon className="w-4 h-4" /> {sector.label}
            </button>
          ))}
        </div>
      </div>

      {/* Theme Tabs */}
      <div className="mb-4">
        <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">Theme</p>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedTheme(undefined)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              selectedTheme === undefined
                ? 'bg-purple-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            General
          </button>
          {themes.map((theme) => (
            <button
              key={theme.value}
              onClick={() => setSelectedTheme(theme.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition flex items-center gap-1.5 ${
                selectedTheme === theme.value
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              <theme.Icon className="w-4 h-4" /> {theme.label}
            </button>
          ))}
        </div>
      </div>

      {/* Timeframe Tabs */}
      <div className="mb-6">
        <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">Timeframe</p>
        <div className="flex gap-2">
          {timeframes.map((tf) => (
            <button
              key={tf.value}
              onClick={() => setSelectedTimeframe(tf.value)}
              className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition ${
                selectedTimeframe === tf.value
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Picks List */}
      {picks.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-400">No picks available for this selection</p>
          <p className="text-sm text-gray-500 mt-2">Try a different sector or theme</p>
        </div>
      ) : (
        <div className="space-y-3">
          {picks.map((pick) => {
            const breakdown = pick.breakdown ?? pick.scoreBreakdown;

            return (
              <div
                key={pick.ticker}
                className="bg-gray-800 rounded-lg p-4 hover:bg-gray-750 transition border border-gray-700 hover:border-gray-600"
              >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="bg-blue-900/30 text-blue-400 rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">
                    #{pick.rank}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-bold text-white">{pick.ticker}</h3>
                      <span className="text-xs text-gray-400 bg-gray-700 px-2 py-0.5 rounded">
                        {pick.sector}
                      </span>
                      {pick.theme !== 'general' && (
                        <span className="text-xs text-purple-400 bg-purple-900/30 px-2 py-0.5 rounded">
                          {pick.theme}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-400 mt-1">{pick.reasoning}</p>
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-lg font-bold ${getReturnColor(pick.potentialReturn)}`}>
                    {pick.potentialReturn > 0 ? '+' : ''}
                    {pick.potentialReturn.toFixed(1)}%
                  </div>
                  <div className="flex items-center gap-1 text-xs text-gray-400 mt-1">
                    <Activity className="w-3 h-3" />
                    <span className={getRiskColor(pick.riskLevel)}>{pick.riskLevel}</span>
                  </div>
                </div>
              </div>

              {/* Price Info */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-3">
                <div>
                  <p className="text-xs text-gray-400 mb-1">Current</p>
                  <p className="text-sm font-semibold text-white flex items-center gap-1">
                    <DollarSign className="w-3 h-3" />
                    {pick.currentPrice.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 mb-1">Target</p>
                  <p className="text-sm font-semibold text-green-400 flex items-center gap-1">
                    <Target className="w-3 h-3" />
                    {pick.targetPrice.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 mb-1">Confidence</p>
                  <p className="text-sm font-semibold text-blue-400">{pick.confidence}/100</p>
                </div>
              </div>

              {/* Signals */}
              <div className="flex flex-wrap gap-1.5">
                {pick.signals.map((signal, idx) => (
                  <span
                    key={idx}
                    className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded"
                  >
                    {signal}
                  </span>
                ))}
              </div>

              {/* Breakdown (if available) */}
              {breakdown && (
                <div className="mt-3 pt-3 border-t border-gray-700">
                  <p className="text-xs text-gray-400 mb-2">Score Breakdown</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    <div>
                      <p className="text-gray-500">Tech</p>
                      <p className="text-white font-semibold">{breakdown.technical}/30</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Mom</p>
                      <p className="text-white font-semibold">{breakdown.momentum}/30</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Vol</p>
                      <p className="text-white font-semibold">{breakdown.volume}/20</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Trend</p>
                      <p className="text-white font-semibold">{breakdown.trend}/20</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Fundamentals (if available) */}
              {pick.fundamentals && Object.keys(pick.fundamentals).length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-700">
                  <p className="text-xs text-gray-400 mb-2">Fundamentals</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                    {pick.fundamentals.peRatio && (
                      <div>
                        <p className="text-gray-500">P/E Ratio</p>
                        <p className="text-white font-semibold">{pick.fundamentals.peRatio.toFixed(2)}</p>
                      </div>
                    )}
                    {pick.fundamentals.marketCap && (
                      <div>
                        <p className="text-gray-500">Market Cap</p>
                        <p className="text-white font-semibold">
                          ${(pick.fundamentals.marketCap / 1e9).toFixed(1)}B
                        </p>
                      </div>
                    )}
                    {pick.fundamentals.dividendYield && (
                      <div>
                        <p className="text-gray-500">Div Yield</p>
                        <p className="text-white font-semibold">
                          {(pick.fundamentals.dividendYield * 100).toFixed(2)}%
                        </p>
                      </div>
                    )}
                    {pick.fundamentals.beta && (
                      <div>
                        <p className="text-gray-500">Beta</p>
                        <p className="text-white font-semibold">{pick.fundamentals.beta.toFixed(2)}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
        </div>
      )}

      {/* Summary */}
      <div className="mt-4 pt-4 border-t border-gray-800 text-center">
        <p className="text-xs text-gray-500">
          Showing top {picks.length} picks |{' '}
          <span className="text-gray-400">
            {selectedSector ? sectors.find((s) => s.value === selectedSector)?.label : 'All Sectors'} |{' '}
            {selectedTheme ? themes.find((t) => t.value === selectedTheme)?.label : 'General'} |{' '}
            {timeframes.find((t) => t.value === selectedTimeframe)?.label}
          </span>
        </p>
      </div>
    </div>
  );
};

export default SectorPicksCard;
