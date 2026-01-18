"use client";

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Zap, Clock, ExternalLink, ChevronDown, Flame, AlertCircle, TrendingUp, TrendingDown, Newspaper, Scale, Calendar, ArrowUpCircle, ArrowDownCircle } from 'lucide-react';
import { getNewestNews, getNewsBombs, type NewsArticle } from '@/lib/api';
import { useWebSocket } from '@/lib/websocket';
import UpdateStatus from '@/components/UpdateStatus';

interface NewsBombsProps {
  maxItems?: number;
  defaultTab?: 'newest' | 'weighted';
  showDaysSelector?: boolean;
}

const NewsBombs: React.FC<NewsBombsProps> = ({
  maxItems = 20,
  defaultTab = 'newest',
  showDaysSelector = true
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'newest' | 'weighted'>(defaultTab);
  const [days, setDays] = useState(7);

  // Fetch newest news
  const refreshIntervalMs = 1000 * 60 * 5;
  const { data: newestData, isLoading: newestLoading, dataUpdatedAt: newestUpdatedAt, isFetching: newestFetching } = useQuery({
    queryKey: ['news-newest', days, maxItems],
    queryFn: () => getNewestNews(days, maxItems),
    staleTime: refreshIntervalMs, // 5 minutes
    refetchInterval: refreshIntervalMs,
  });

  // Fetch high-impact news bombs
  const { data: weightedData, isLoading: weightedLoading, dataUpdatedAt: weightedUpdatedAt, isFetching: weightedFetching } = useQuery({
    queryKey: ['news-bombs', days, maxItems],
    queryFn: () => getNewsBombs(maxItems, days),
    staleTime: refreshIntervalMs, // 5 minutes
    refetchInterval: refreshIntervalMs,
  });

  // WebSocket for real-time hot news
  const { data: wsNews } = useWebSocket('news');

  // Get current news based on active tab
  const currentNews = activeTab === 'newest'
    ? newestData?.data || []
    : weightedData?.data || [];

  const isLoading = activeTab === 'newest' ? newestLoading : weightedLoading;
  const lastUpdatedAt = activeTab === 'newest' ? newestUpdatedAt : weightedUpdatedAt;
  const isFetching = activeTab === 'newest' ? newestFetching : weightedFetching;

  // Loading state
  if (isLoading && currentNews.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Zap className="w-7 h-7 text-yellow-500" />
            News Bombs
          </h2>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-32 bg-slate-800/50 rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  const getTimeAgo = (timestamp: string): string => {
    const date = new Date(timestamp);
    const minutes = Math.floor((Date.now() - date.getTime()) / 60000);
    if (minutes < 1) return 'Juuri nyt';
    if (minutes < 60) return `${minutes}m sitten`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h sitten`;
    return `${Math.floor(hours / 24)}pv sitten`;
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      FDA_APPROVAL: 'bg-green-500/20 text-green-300 border-green-500/30',
      FDA: 'bg-green-500/20 text-green-300 border-green-500/30',
      EARNINGS_BEAT: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      EARNINGS_MISS: 'bg-red-500/20 text-red-300 border-red-500/30',
      EARNINGS: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
      MERGER: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      ACQUISITION: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      BANKRUPTCY: 'bg-red-500/20 text-red-300 border-red-500/30',
      BUYOUT: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
      TAKEOVER: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
      IPO: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      INVESTIGATION: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
      LAWSUIT: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
      RECALL: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
      GUIDANCE_RAISED: 'bg-teal-500/20 text-teal-300 border-teal-500/30',
      GUIDANCE_LOWERED: 'bg-pink-500/20 text-pink-300 border-pink-500/30',
      BREAKTHROUGH: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
      BREAKOUT: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
      ECONOMIC: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
      CRYPTO: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    };
    return colors[category] || 'bg-slate-500/20 text-slate-300 border-slate-500/30';
  };

  const getImpactColor = (impact: NewsArticle['impact']) => {
    const colors = {
      HIGH: 'text-red-400',
      MEDIUM: 'text-yellow-400',
      LOW: 'text-green-400',
    };
    return colors[impact];
  };

  const getWeightColor = (weight: number = 0) => {
    if (weight >= 140) return 'text-red-400 bg-red-500/20';
    if (weight >= 100) return 'text-orange-400 bg-orange-500/20';
    if (weight >= 70) return 'text-yellow-400 bg-yellow-500/20';
    return 'text-slate-400 bg-slate-500/20';
  };

  // Generate impact reasoning based on category
  const getImpactReasoning = (category: string): { isPositive: boolean; reason: string } => {
    const impacts: Record<string, { isPositive: boolean; reason: string }> = {
      FDA_APPROVAL: { isPositive: true, reason: 'FDA approval = new revenue stream and market cap increase' },
      MERGER: { isPositive: true, reason: 'Merger can bring synergies and growth' },
      ACQUISITION: { isPositive: true, reason: 'Acquisition expands business operations' },
      BANKRUPTCY: { isPositive: false, reason: 'Bankruptcy = shareholders lose investment' },
      BUYOUT: { isPositive: true, reason: 'Buyout usually at premium - stock rises' },
      TAKEOVER: { isPositive: true, reason: 'Takeover attempt raises stock price' },
      EARNINGS_BEAT: { isPositive: true, reason: 'Beat expectations = strong growth signal' },
      EARNINGS_MISS: { isPositive: false, reason: 'Missed earnings pressures stock downward' },
      IPO: { isPositive: true, reason: 'New listing brings visibility and capital' },
      INVESTIGATION: { isPositive: false, reason: 'Investigation brings uncertainty and risk' },
      LAWSUIT: { isPositive: false, reason: 'Lawsuit = potential damages and reputation risk' },
      RECALL: { isPositive: false, reason: 'Recall = costs and reputation damage' },
      GUIDANCE_RAISED: { isPositive: true, reason: 'Raised guidance = better than expected growth' },
      GUIDANCE_LOWERED: { isPositive: false, reason: 'Lowered guidance pressures valuation' },
      BREAKTHROUGH: { isPositive: true, reason: 'Breakthrough can disrupt the market' },
      ECONOMIC: { isPositive: true, reason: 'Economic news affects market sentiment' },
      CRYPTO: { isPositive: true, reason: 'Crypto news brings volatility' },
    };
    return impacts[category] || { isPositive: true, reason: 'Monitor news developments' };
  };

  const displayNews = currentNews.slice(0, maxItems);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Zap className="w-7 h-7 text-yellow-500" />
          News Bombs
        </h2>
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-slate-400">Live</span>
          </div>
          <UpdateStatus
            lastUpdatedAt={lastUpdatedAt}
            refreshIntervalMs={refreshIntervalMs}
            isFetching={isFetching}
            className="text-slate-400"
          />
        </div>
      </div>

      {/* Tab Buttons and Days Selector */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        {/* Tabs */}
        <div className="flex bg-slate-800/50 rounded-lg p-1 border border-slate-700/50">
          <button
            onClick={() => setActiveTab('newest')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === 'newest'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <Newspaper className="w-4 h-4" />
            Latest
          </button>
          <button
            onClick={() => setActiveTab('weighted')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === 'weighted'
                ? 'bg-orange-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <Scale className="w-4 h-4" />
            Weighted
          </button>
        </div>

        {/* Days Selector */}
        {showDaysSelector && (
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-slate-400" />
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
            >
              <option value={1}>1 day</option>
              <option value={3}>3 days</option>
              <option value={7}>7 days</option>
            </select>
          </div>
        )}
      </div>

      {/* Tab Description */}
      <div className="text-sm text-slate-400">
        {activeTab === 'newest' ? (
          <span className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Latest news in chronological order
          </span>
        ) : (
          <span className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Weighted news by importance (category, source, recency)
          </span>
        )}
      </div>

      {/* News Feed */}
      <div className="space-y-3">
        {displayNews.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            No news in selected time period
          </div>
        ) : (
          displayNews.map((item, index) => (
            <div
              key={item.id}
              className="bg-slate-800/50 backdrop-blur-sm rounded-lg border border-slate-700/50 hover:border-slate-600 transition-all hover:shadow-lg hover:shadow-slate-900/50 overflow-hidden"
            >
              <div className="p-4">
                {/* Header Row */}
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    {/* Rank for weighted */}
                    {activeTab === 'weighted' && (
                      <span className="text-xs font-bold text-slate-500 bg-slate-700/50 rounded px-2 py-1">
                        #{index + 1}
                      </span>
                    )}
                    {item.ticker && (
                      <span className="font-bold text-white text-lg px-3 py-1 bg-slate-700/50 rounded-md">
                        {item.ticker}
                      </span>
                    )}
                    <span className={`text-xs px-2 py-1 rounded-md border ${getCategoryColor(item.category)}`}>
                      {item.category.replace(/_/g, ' ')}
                    </span>
                    {item.isHot && (
                      <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-md bg-red-500/20 text-red-300 border border-red-500/30">
                        <Flame className="w-3 h-3" />
                        HOT
                      </span>
                    )}
                    <span className={`flex items-center gap-1 text-xs ${getImpactColor(item.impact)}`}>
                      <AlertCircle className="w-3 h-3" />
                      {item.impact}
                    </span>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <div className="flex items-center gap-2 text-slate-400 text-sm whitespace-nowrap">
                      <Clock className="w-4 h-4" />
                      {getTimeAgo(item.timestamp)}
                    </div>
                    {/* Weight score for weighted tab */}
                    {activeTab === 'weighted' && item.weight !== undefined && (
                      <div className={`text-xs px-2 py-0.5 rounded ${getWeightColor(item.weight)}`}>
                        Weight: {Math.round(item.weight)}
                      </div>
                    )}
                  </div>
                </div>

                {/* Headline */}
                <h3 className="text-white font-semibold text-lg mb-2 leading-tight">
                  {item.headline}
                </h3>

                {/* Summary - Expandable */}
                <div className="relative">
                  <p className={`text-slate-300 text-sm leading-relaxed transition-all ${
                    expandedId === item.id ? '' : 'line-clamp-2'
                  }`}>
                    {item.summary}
                  </p>
                </div>

                {/* Impact Reasoning */}
                {(() => {
                  const impact = getImpactReasoning(item.category);
                  return (
                    <div className={`mt-3 p-2 rounded-lg border text-xs ${
                      impact.isPositive
                        ? 'bg-green-500/10 border-green-500/30 text-green-400'
                        : 'bg-red-500/10 border-red-500/30 text-red-400'
                    }`}>
                      <div className="flex items-center gap-2">
                        {impact.isPositive ? (
                          <ArrowUpCircle className="w-4 h-4 flex-shrink-0" />
                        ) : (
                          <ArrowDownCircle className="w-4 h-4 flex-shrink-0" />
                        )}
                        <span className="font-medium">
                          {impact.isPositive ? 'Positive Impact:' : 'Negative Impact:'}
                        </span>
                      </div>
                      <p className="mt-1 text-slate-300">{impact.reason}</p>
                    </div>
                  );
                })()}

                {/* Source */}
                {item.source && (
                  <div className="mt-2 text-xs text-slate-500">
                    Source: {item.source}
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-700/50">
                  <button
                    onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                    className="flex items-center gap-1 text-sm text-slate-400 hover:text-white transition-colors"
                  >
                    <ChevronDown className={`w-4 h-4 transition-transform ${
                      expandedId === item.id ? 'rotate-180' : ''
                    }`} />
                    {expandedId === item.id ? 'Show less' : 'Read more'}
                  </button>
                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      Full article
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Stats */}
      {displayNews.length > 0 && (
        <div className="flex items-center justify-between text-sm text-slate-500 pt-2">
          <span>
            Showing {displayNews.length} articles
          </span>
          {activeTab === 'weighted' && (
            <span>
              Avg. weight: {Math.round(displayNews.reduce((sum, n) => sum + (n.weight || 0), 0) / displayNews.length)}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default NewsBombs;
