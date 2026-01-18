'use client';

import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getApiBaseUrl } from '@/lib/api';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  AlertCircle,
  Target,
  BarChart3,
  Zap,
  Shield
} from 'lucide-react';
import UpdateStatus from '@/components/UpdateStatus';

interface MarketPulseProps {
  className?: string;
}

interface KeyIndicator {
  name: string;
  status: string;
  trend: 'up' | 'down' | 'flat';
}

const MarketPulse: React.FC<MarketPulseProps> = ({ className = '' }) => {
  // Fetch REAL market overview with auto-refresh
  const refreshIntervalMs = 1000 * 60 * 2;
  const { data: marketData, isLoading, dataUpdatedAt, isFetching } = useQuery({
    queryKey: ['market-overview'],
    queryFn: async () => {
      const response = await fetch(`${getApiBaseUrl()}/api/macro/market-overview`);
      if (!response.ok) throw new Error('Failed to fetch market overview');
      return response.json();
    },
    staleTime: refreshIntervalMs, // 2 min cache
    refetchInterval: refreshIntervalMs, // Auto-refresh every 2 minutes
    refetchOnWindowFocus: true, // Refresh when user returns to tab
  });

  // Extract real market data from API
  const marketSentiment = useMemo(() => {
    if (!marketData?.data?.sentiment) {
      return { score: 50, label: 'NEUTRAL', color: 'yellow', description: 'Loading...' };
    }
    return marketData.data.sentiment;
  }, [marketData]);

  // Risk level from API
  const riskLevel = useMemo(() => {
    if (!marketData?.data?.sentiment) {
      return { level: 'MEDIUM', color: 'yellow', icon: Activity };
    }
    const risk = marketData.data.sentiment.risk;
    const color = marketData.data.sentiment.risk_color;
    const icon = risk === 'HIGH' ? AlertCircle : risk === 'LOW' ? Shield : Activity;
    return { level: risk, color, icon };
  }, [marketData]);

  // Trading style from API
  const tradingStyle = useMemo(() => {
    if (!marketData?.data?.sentiment) {
      return { style: 'Balanced', icon: Target, color: 'yellow' };
    }
    const style = marketData.data.sentiment.trading_style;
    const icon = style.includes('Aggressive') ? Zap :
                 style.includes('Growth') ? TrendingUp :
                 style.includes('Conservative') || style.includes('Defensive') ? Shield : Target;
    const color = marketData.data.sentiment.color;
    return { style, icon, color };
  }, [marketData]);

  // Real sector data from API
  const keyIndicators = useMemo<KeyIndicator[]>(() => {
    if (!marketData?.data?.sectors || marketData.data.sectors.length === 0) {
      return [
        { name: 'Technology', status: 'Loading', trend: 'flat' as const },
        { name: 'Healthcare', status: 'Loading', trend: 'flat' as const },
        { name: 'Energy', status: 'Loading', trend: 'flat' as const },
      ];
    }
    // Get top 3 sectors
    return marketData.data.sectors.slice(0, 3).map((sector: any): KeyIndicator => ({
      name: sector.name,
      status: sector.status,
      trend: sector.trend
    }));
  }, [marketData]);

  const getSentimentColor = (color: string) => {
    const colors: Record<string, string> = {
      green: 'text-green-400 bg-green-900/30',
      lime: 'text-lime-400 bg-lime-900/30',
      yellow: 'text-yellow-400 bg-yellow-900/30',
      orange: 'text-orange-400 bg-orange-900/30',
      red: 'text-red-400 bg-red-900/30',
    };
    return colors[color] || colors.yellow;
  };

  const getRiskColor = (color: string) => {
    const colors: Record<string, string> = {
      green: 'text-green-400',
      yellow: 'text-yellow-400',
      red: 'text-red-400',
    };
    return colors[color] || colors.yellow;
  };

  if (isLoading) {
    return (
      <div className={`bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-lg p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-700 rounded w-48 mb-4"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const RiskIcon = riskLevel.icon;
  const StyleIcon = tradingStyle.icon;

  return (
    <div className={`bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600/20 rounded-lg">
            <BarChart3 className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Market Overview</h2>
            <p className="text-sm text-gray-400">Real-time market conditions</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <UpdateStatus
            lastUpdatedAt={dataUpdatedAt}
            refreshIntervalMs={refreshIntervalMs}
            isFetching={isFetching}
            className="text-gray-500"
          />
          {marketData?.data?.market_status && (
            <div className="text-xs text-gray-500">
              Status: <span className={`font-semibold ${
                marketData.data.market_status === 'open' ? 'text-green-400' :
                marketData.data.market_status === 'closed' ? 'text-red-400' :
                'text-yellow-400'
              }`}>
                {marketData.data.market_status.replace('-', ' ')}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Market Sentiment */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Market Sentiment</p>
            {marketSentiment.score >= 50 ? (
              <TrendingUp className="w-4 h-4 text-green-400" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-400" />
            )}
          </div>
          <div className={`inline-block px-3 py-1.5 rounded-full text-sm font-bold ${getSentimentColor(marketSentiment.color)}`}>
            {marketSentiment.label}
          </div>
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
              <span>Bearish</span>
              <span>Bullish</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-500 ${
                  marketSentiment.score >= 70 ? 'bg-green-500' :
                  marketSentiment.score >= 50 ? 'bg-lime-500' :
                  marketSentiment.score >= 30 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${marketSentiment.score}%` }}
              ></div>
            </div>
            <p className="text-center text-xs text-gray-500 mt-1">{marketSentiment.score}/100</p>
          </div>
        </div>

        {/* Risk Level */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Risk Level</p>
            <RiskIcon className={`w-4 h-4 ${getRiskColor(riskLevel.color)}`} />
          </div>
          <div className={`text-2xl font-bold ${getRiskColor(riskLevel.color)} mb-2`}>
            {riskLevel.level}
          </div>
          <p className="text-xs text-gray-400 leading-relaxed">
            VIX: {marketData?.data?.sentiment?.vix?.toFixed(1) || '--'} |
            {riskLevel.level === 'HIGH' && ' Volatile conditions'}
            {riskLevel.level === 'MEDIUM' && ' Moderate volatility'}
            {riskLevel.level === 'LOW' && ' Low volatility'}
          </p>
        </div>

        {/* Trading Style */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Recommended Style</p>
            <StyleIcon className={`w-4 h-4 ${getRiskColor(tradingStyle.color)}`} />
          </div>
          <div className="text-lg font-bold text-white mb-2">
            {tradingStyle.style}
          </div>
          <p className="text-xs text-gray-400 leading-relaxed">
            {marketData?.data?.sentiment?.advice?.substring(0, 60) || 'Market analysis in progress'}...
          </p>
        </div>

        {/* Sector Outlook */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Sector Outlook</p>
            <Target className="w-4 h-4 text-blue-400" />
          </div>
          <div className="space-y-2">
            {keyIndicators.map((indicator, idx) => (
              <div key={idx} className="flex items-center justify-between">
                <span className="text-sm text-gray-300">{indicator.name}</span>
                <div className="flex items-center gap-1">
                  <span className={`text-sm font-semibold ${
                    indicator.trend === 'up' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {indicator.status}
                  </span>
                  {indicator.trend === 'up' ? (
                    <TrendingUp className="w-3 h-3 text-green-400" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-red-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Analysis Summary */}
      <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/50">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-xs text-gray-400 mb-1">Sentiment</p>
            <p className={`text-lg font-bold ${
              marketSentiment.score >= 50 ? 'text-green-400' : 'text-red-400'
            }`}>
              {marketSentiment.score}/100
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">Risk Level</p>
            <p className={`text-lg font-bold ${getRiskColor(riskLevel.color)}`}>
              {riskLevel.level}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">VIX (Fear Index)</p>
            <p className="text-lg font-bold text-yellow-400">
              {marketData?.data?.sentiment?.vix?.toFixed(2) || '--'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">Positive Sectors</p>
            <p className="text-lg font-bold text-green-400">
              {marketData?.data?.sentiment?.positive_sectors || 0}/{marketData?.data?.sentiment?.total_sectors || 0}
            </p>
          </div>
        </div>
      </div>

      {/* Trading Recommendation */}
      <div className="mt-4 p-3 bg-blue-900/20 border border-blue-800/50 rounded-lg">
        <p className="text-sm text-blue-300">
          <span className="font-semibold">Today&apos;s Strategy:</span>{' '}
          {marketData?.data?.sentiment?.advice || 'Loading market strategy...'}
        </p>
        {marketData?.data?.sentiment?.description && (
          <p className="text-xs text-slate-400 mt-2">
            {marketData.data.sentiment.description}
          </p>
        )}
      </div>
    </div>
  );
};

export default MarketPulse;
