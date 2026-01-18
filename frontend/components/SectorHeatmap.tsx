'use client';

import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getSectorPicks } from '@/lib/api';
import { TrendingUp, TrendingDown, Cpu, Zap, Heart, Building2, ShoppingCart, type LucideIcon } from 'lucide-react';

interface SectorHeatmapProps {
  className?: string;
}

const SectorHeatmap: React.FC<SectorHeatmapProps> = ({ className = '' }) => {
  // Fetch data for all sectors
  const sectors = ['tech', 'energy', 'healthcare', 'finance', 'consumer'] as const;

  const sectorQueries = useQuery({
    queryKey: ['sector-heatmap'],
    queryFn: async () => {
      // Fetch top pick from each sector
      const results = await Promise.all(
        sectors.map(async (sector) => {
          try {
            const data = await getSectorPicks(sector, undefined, 'swing', 1);
            const pick = data.data[0];
            return {
              sector,
              performance: pick?.potentialReturn || 0,
              ticker: pick?.ticker || 'N/A',
              price: pick?.currentPrice || 0,
              confidence: pick?.confidence || 0,
            };
          } catch (error) {
            return {
              sector,
              performance: 0,
              ticker: 'N/A',
              price: 0,
              confidence: 0,
            };
          }
        })
      );
      return results;
    },
    staleTime: 1000 * 60 * 15, // 15 minutes
  });

  const sectorData = sectorQueries.data || [];

  // Sector metadata
  const sectorMeta: Record<string, { label: string; Icon: LucideIcon; color: string }> = {
    tech: { label: 'Technology', Icon: Cpu, color: 'blue' },
    energy: { label: 'Energy', Icon: Zap, color: 'yellow' },
    healthcare: { label: 'Healthcare', Icon: Heart, color: 'green' },
    finance: { label: 'Finance', Icon: Building2, color: 'indigo' },
    consumer: { label: 'Consumer', Icon: ShoppingCart, color: 'purple' },
  };

  const getPerformanceColor = (performance: number) => {
    if (performance >= 15)
      return 'bg-green-600 border-green-500 text-white';
    if (performance >= 10)
      return 'bg-green-700 border-green-600 text-white';
    if (performance >= 5)
      return 'bg-green-800 border-green-700 text-green-100';
    if (performance >= 2)
      return 'bg-green-900 border-green-800 text-green-200';
    if (performance >= 0)
      return 'bg-gray-800 border-gray-700 text-gray-300';
    if (performance >= -2)
      return 'bg-red-900 border-red-800 text-red-200';
    if (performance >= -5)
      return 'bg-red-800 border-red-700 text-red-100';
    if (performance >= -10)
      return 'bg-red-700 border-red-600 text-white';
    return 'bg-red-600 border-red-500 text-white';
  };

  const getPerformanceIntensity = (performance: number) => {
    const abs = Math.abs(performance);
    if (abs >= 15) return 'font-bold text-xl';
    if (abs >= 10) return 'font-bold text-lg';
    if (abs >= 5) return 'font-semibold text-base';
    return 'font-medium text-sm';
  };

  if (sectorQueries.isLoading) {
    return (
      <div className={`bg-gray-900 border border-gray-800 rounded-lg p-6 ${className}`}>
        <h2 className="text-xl font-bold text-white mb-4">Sector Heatmap</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {sectors.map((sector) => (
            <div
              key={sector}
              className="aspect-square bg-gray-800 rounded-lg animate-pulse"
            ></div>
          ))}
        </div>
      </div>
    );
  }

  if (sectorQueries.isError) {
    return (
      <div className={`bg-gray-900 border border-gray-800 rounded-lg p-6 ${className}`}>
        <h2 className="text-xl font-bold text-white mb-4">Sector Heatmap</h2>
        <p className="text-red-400">Failed to load sector data</p>
      </div>
    );
  }

  return (
    <div className={`bg-gray-900 border border-gray-800 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white">Sector Heatmap</h2>
          <p className="text-sm text-gray-400 mt-1">Top pick performance by sector</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-600 rounded"></div>
            <span>Bullish</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-gray-700 rounded"></div>
            <span>Neutral</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-600 rounded"></div>
            <span>Bearish</span>
          </div>
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {sectorData.map((data) => {
          const meta = sectorMeta[data.sector as keyof typeof sectorMeta];
          const colorClass = getPerformanceColor(data.performance);
          const intensityClass = getPerformanceIntensity(data.performance);

          return (
            <div
              key={data.sector}
              className={`relative aspect-square rounded-lg border-2 p-4 flex flex-col items-center justify-center
                transition-all duration-200 hover:scale-105 cursor-pointer group ${colorClass}`}
            >
              {/* Sector Icon */}
              <div className="mb-2">
                <meta.Icon className="w-10 h-10" />
              </div>

              {/* Sector Name */}
              <h3 className="text-sm font-semibold text-center mb-1">{meta.label}</h3>

              {/* Performance */}
              <div className={`flex items-center gap-1 ${intensityClass}`}>
                {data.performance >= 0 ? (
                  <TrendingUp className="w-4 h-4" />
                ) : (
                  <TrendingDown className="w-4 h-4" />
                )}
                <span>
                  {data.performance >= 0 ? '+' : ''}
                  {data.performance.toFixed(1)}%
                </span>
              </div>

              {/* Ticker */}
              <div className="text-xs opacity-75 mt-1">{data.ticker}</div>

              {/* Hover details */}
              <div
                className="absolute inset-0 bg-black/90 rounded-lg p-3 opacity-0 group-hover:opacity-100
                transition-opacity duration-200 flex flex-col justify-center text-xs space-y-1"
              >
                <div className="text-center">
                  <p className="font-bold text-white">{data.ticker}</p>
                  <p className="text-gray-300">
                    ${data.price.toFixed(2)}
                  </p>
                  <p className="text-gray-400 mt-2">
                    Confidence: {data.confidence}/100
                  </p>
                  <p
                    className={`mt-1 font-semibold ${
                      data.performance >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {data.performance >= 0 ? '+' : ''}
                    {data.performance.toFixed(2)}% Potential
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Stats */}
      <div className="mt-6 pt-4 border-t border-gray-800">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center text-sm">
          <div>
            <p className="text-gray-400 mb-1">Best Performer</p>
            <p className="text-green-400 font-semibold">
              {sectorData.reduce((best, curr) =>
                curr.performance > best.performance ? curr : best,
                sectorData[0]
              )?.sector.toUpperCase() || 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-gray-400 mb-1">Worst Performer</p>
            <p className="text-red-400 font-semibold">
              {sectorData.reduce((worst, curr) =>
                curr.performance < worst.performance ? curr : worst,
                sectorData[0]
              )?.sector.toUpperCase() || 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-gray-400 mb-1">Avg Performance</p>
            <p className="text-white font-semibold">
              {sectorData.length > 0
                ? (
                    sectorData.reduce((sum, s) => sum + s.performance, 0) /
                    sectorData.length
                  ).toFixed(1)
                : '0'}
              %
            </p>
          </div>
          <div>
            <p className="text-gray-400 mb-1">Bullish Sectors</p>
            <p className="text-blue-400 font-semibold">
              {sectorData.filter((s) => s.performance >= 5).length}/{sectorData.length}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SectorHeatmap;
