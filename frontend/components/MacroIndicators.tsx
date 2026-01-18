"use client";

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, DollarSign, Activity, Briefcase, Home, Globe, Loader2, AlertCircle } from 'lucide-react';
import { getMacroIndicators, type MacroIndicator } from '@/lib/api';
import UpdateStatus from '@/components/UpdateStatus';

const MacroIndicators: React.FC = () => {
  // Fetch macro indicators from API with 5min cache and auto-refresh
  const refreshIntervalMs = 1000 * 60 * 5;
  const { data, isLoading, error, dataUpdatedAt, isFetching } = useQuery({
    queryKey: ['macro-indicators'],
    queryFn: getMacroIndicators,
    staleTime: refreshIntervalMs, // 5 min cache (matches backend TTL)
    refetchInterval: refreshIntervalMs, // Auto-refresh every 5 minutes (active tab only)
    refetchOnWindowFocus: true, // Refresh when user returns to tab
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Globe className="w-7 h-7 text-cyan-500" />
            Macro Indicators
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="h-48 bg-slate-800/50 rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-6 h-6 text-red-400" />
          <div>
            <h3 className="font-semibold text-red-300">Error loading macro indicators</h3>
            <p className="text-sm text-red-400">
              {error instanceof Error ? error.message : 'Failed to fetch macro data'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const indicators = Array.isArray(data?.data) ? data.data : [];

  // Map indicator labels to icons (simplified mapping)
  const getIcon = (label: string = '') => {
    if (!label) return Globe;
    const lowerLabel = label.toLowerCase();
    if (lowerLabel.includes('fed') || lowerLabel.includes('rate') || lowerLabel.includes('dollar')) return DollarSign;
    if (lowerLabel.includes('cpi') || lowerLabel.includes('pmi') || lowerLabel.includes('vix')) return Activity;
    if (lowerLabel.includes('employment') || lowerLabel.includes('jobs') || lowerLabel.includes('unemployment')) return Briefcase;
    if (lowerLabel.includes('gdp') || lowerLabel.includes('growth')) return TrendingUp;
    if (lowerLabel.includes('housing') || lowerLabel.includes('retail')) return Home;
    return Globe;
  };

  const toFiniteNumber = (value: number | null | undefined): number | null => {
    if (typeof value !== 'number') return null;
    return Number.isFinite(value) ? value : null;
  };

  const formatValue = (value: number | string | null | undefined, unit?: string): string => {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'string') return value || 'N/A';
    const safeValue = toFiniteNumber(value);
    if (safeValue === null) return 'N/A';
    if (!unit) return safeValue.toFixed(2);
    if (unit === '$') return `$${safeValue.toFixed(2)}`;
    if (unit === '%') return `${safeValue.toFixed(2)}%`;
    if (unit === 'M') return `${safeValue.toFixed(3)}M`;
    return `${safeValue.toFixed(2)}${unit}`;
  };

  const getImpactColor = (impact: MacroIndicator['impact']): string => {
    const colors = {
      POSITIVE: 'from-green-500/20 to-emerald-500/20 border-green-500/30',
      NEGATIVE: 'from-red-500/20 to-rose-500/20 border-red-500/30',
      NEUTRAL: 'from-slate-500/20 to-slate-600/20 border-slate-500/30',
    };
    return colors[impact];
  };

  const getImpactBadgeColor = (impact: MacroIndicator['impact']): string => {
    const colors = {
      POSITIVE: 'bg-green-500/20 text-green-300 border-green-500/30',
      NEGATIVE: 'bg-red-500/20 text-red-300 border-red-500/30',
      NEUTRAL: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
    };
    return colors[impact];
  };

  const getTrendIcon = (change: number) => {
    if (change > 0) return <TrendingUp className="w-5 h-5 text-green-500" />;
    if (change < 0) return <TrendingDown className="w-5 h-5 text-red-500" />;
    return <Activity className="w-5 h-5 text-slate-500" />;
  };

  const getTrendColor = (change?: number): string => {
    if (!change) return 'text-slate-400';
    if (change > 0) return 'text-green-400';
    if (change < 0) return 'text-red-400';
    return 'text-slate-400';
  };

  if (indicators.length === 0) {
    return (
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-6 text-center">
        <h3 className="text-white font-semibold mb-1">Macro Indicators</h3>
        <p className="text-sm text-slate-400">No macro data available yet. Please refresh.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Globe className="w-7 h-7 text-cyan-500" />
          Macro Indicators
        </h2>
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-slate-400">Live Data</span>
          </div>
          <UpdateStatus
            lastUpdatedAt={dataUpdatedAt}
            refreshIntervalMs={refreshIntervalMs}
            isFetching={isFetching}
            className="text-slate-400"
          />
        </div>
      </div>

      {/* Indicators Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {indicators.map((indicator, idx) => {
          const displayName = indicator.label || 'N/A';
          const Icon = getIcon(displayName);
          const change = toFiniteNumber(indicator.change) ?? 0;
          const changePercent = toFiniteNumber(indicator.changePercent) ?? 0;
          const value = indicator.value;

          return (
            <div
              key={idx}
              className={`bg-gradient-to-br ${getImpactColor(indicator.impact)} backdrop-blur-sm rounded-lg border p-4 hover:shadow-lg hover:shadow-slate-900/50 transition-all cursor-pointer group`}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-slate-700/50 rounded-lg">
                    <Icon className="w-5 h-5 text-slate-300" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-white font-semibold text-sm">
                      {displayName}
                    </h3>
                  </div>
                </div>
                {getTrendIcon(change)}
              </div>

              {/* Current Value */}
              <div className="mb-3">
                <div className="text-3xl font-bold text-white mb-1">
                  {formatValue(value, indicator.unit)}
                </div>
                {change !== 0 && (
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-semibold ${getTrendColor(change)}`}>
                      {change > 0 ? '+' : ''}{typeof value === 'number' ? formatValue(Math.abs(change), indicator.unit) : change}
                    </span>
                    {changePercent !== 0 && (
                      <span className={`text-xs ${getTrendColor(change)}`}>
                        ({changePercent > 0 ? '+' : ''}{changePercent.toFixed(2)}%)
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Impact Badge */}
              <div className={`text-xs px-2 py-1 rounded-md border inline-flex items-center gap-1 ${getImpactBadgeColor(indicator.impact)}`}>
                {indicator.impact === 'POSITIVE' && <TrendingUp className="w-3 h-3" />}
                {indicator.impact === 'NEGATIVE' && <TrendingDown className="w-3 h-3" />}
                {indicator.impact === 'NEUTRAL' && <Activity className="w-3 h-3" />}
                {indicator.impact} Impact
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-green-400 mb-1">Positive Indicators</div>
              <div className="text-2xl font-bold text-green-300">
                {indicators.filter(i => i.impact === 'POSITIVE').length}
              </div>
            </div>
            <TrendingUp className="w-8 h-8 text-green-500/50" />
          </div>
        </div>

        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-red-400 mb-1">Negative Indicators</div>
              <div className="text-2xl font-bold text-red-300">
                {indicators.filter(i => i.impact === 'NEGATIVE').length}
              </div>
            </div>
            <TrendingDown className="w-8 h-8 text-red-500/50" />
          </div>
        </div>

        <div className="bg-slate-500/10 border border-slate-500/30 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400 mb-1">Neutral Indicators</div>
              <div className="text-2xl font-bold text-slate-300">
                {indicators.filter(i => i.impact === 'NEUTRAL').length}
              </div>
            </div>
            <Activity className="w-8 h-8 text-slate-500/50" />
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="text-center text-sm text-slate-500">
        Data sources: Federal Reserve, Bureau of Labor Statistics, CME Group
      </div>
    </div>
  );
};

export default MacroIndicators;
