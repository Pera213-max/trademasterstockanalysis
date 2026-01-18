"use client";

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Newspaper, Clock, ExternalLink, ChevronDown, Flame,
  AlertCircle, TrendingUp, Scale, BarChart3, Calendar
} from 'lucide-react';
import { getStockNewsAnalysis, type NewsArticle } from '@/lib/api';

interface StockNewsAnalysisProps {
  ticker: string;
  maxItems?: number;
}

const StockNewsAnalysis: React.FC<StockNewsAnalysisProps> = ({
  ticker,
  maxItems = 5
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'newest' | 'weighted'>('weighted');
  const [days, setDays] = useState(7);

  // Fetch stock news analysis
  const { data, isLoading, error } = useQuery({
    queryKey: ['stock-news-analysis', ticker, days],
    queryFn: () => getStockNewsAnalysis(ticker, days),
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: !!ticker,
  });

  const analysis = data?.data;

  // Loading state
  if (isLoading) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Newspaper className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">News Analysis</h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-slate-700/50 rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error || !analysis) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Newspaper className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">News Analysis</h3>
        </div>
        <p className="text-slate-400 text-sm">No news available</p>
      </div>
    );
  }

  const getTimeAgo = (timestamp: string): string => {
    const date = new Date(timestamp);
    const minutes = Math.floor((Date.now() - date.getTime()) / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      FDA_APPROVAL: 'bg-green-500/20 text-green-300 border-green-500/30',
      EARNINGS_BEAT: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      EARNINGS_MISS: 'bg-red-500/20 text-red-300 border-red-500/30',
      MERGER: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      ACQUISITION: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      BANKRUPTCY: 'bg-red-500/20 text-red-300 border-red-500/30',
      IPO: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      INVESTIGATION: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
      LAWSUIT: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
      BREAKTHROUGH: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
      ECONOMIC: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
      CRYPTO: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    };
    return colors[category] || 'bg-slate-500/20 text-slate-300 border-slate-500/30';
  };

  const getImpactColor = (impact: string) => {
    const colors: Record<string, string> = {
      HIGH: 'text-red-400',
      MEDIUM: 'text-yellow-400',
      LOW: 'text-green-400',
    };
    return colors[impact] || 'text-slate-400';
  };

  const getWeightColor = (weight: number = 0) => {
    if (weight >= 140) return 'text-red-400 bg-red-500/20';
    if (weight >= 100) return 'text-orange-400 bg-orange-500/20';
    if (weight >= 70) return 'text-yellow-400 bg-yellow-500/20';
    return 'text-slate-400 bg-slate-500/20';
  };

  const currentNews = activeTab === 'newest'
    ? analysis.newest
    : analysis.weighted;
  const displayNews = currentNews.slice(0, maxItems);

  // Calculate news score for display (0-100)
  const newsScore = Math.min(100, Math.round((analysis.avg_weight / 170) * 100));

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Newspaper className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">News Analysis</h3>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="bg-slate-700/50 border border-slate-600/50 rounded px-2 py-1 text-xs text-white"
        >
          <option value={1}>1d</option>
          <option value={3}>3d</option>
          <option value={7}>7d</option>
        </select>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <div className="bg-slate-700/30 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-white">{analysis.total_articles}</div>
          <div className="text-xs text-slate-400">Articles</div>
        </div>
        <div className="bg-slate-700/30 rounded-lg p-3 text-center">
          <div className={`text-2xl font-bold ${
            newsScore >= 70 ? 'text-green-400' :
            newsScore >= 40 ? 'text-yellow-400' : 'text-slate-400'
          }`}>
            {newsScore}
          </div>
          <div className="text-xs text-slate-400">News score</div>
        </div>
        <div className="bg-slate-700/30 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-blue-400">
            {Math.round(analysis.avg_weight)}
          </div>
          <div className="text-xs text-slate-400">Avg. weight</div>
        </div>
      </div>

      {/* Category Distribution */}
      {Object.keys(analysis.categories).length > 0 && (
        <div className="mb-4">
          <div className="text-xs text-slate-400 mb-2 flex items-center gap-1">
            <BarChart3 className="w-3 h-3" />
            Categories
          </div>
          <div className="flex flex-wrap gap-1">
            {Object.entries(analysis.categories).map(([cat, count]) => (
              <span
                key={cat}
                className={`text-xs px-2 py-0.5 rounded border ${getCategoryColor(cat)}`}
              >
                {cat.replace(/_/g, ' ')} ({count})
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex bg-slate-700/30 rounded-lg p-1 mb-4">
        <button
          onClick={() => setActiveTab('weighted')}
          className={`flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded text-xs font-medium transition-all ${
            activeTab === 'weighted'
              ? 'bg-orange-600 text-white'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Scale className="w-3 h-3" />
          Weighted
        </button>
        <button
          onClick={() => setActiveTab('newest')}
          className={`flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded text-xs font-medium transition-all ${
            activeTab === 'newest'
              ? 'bg-blue-600 text-white'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Clock className="w-3 h-3" />
          Newest
        </button>
      </div>

      {/* News List */}
      <div className="space-y-3">
        {displayNews.length === 0 ? (
          <div className="text-center py-4 text-slate-400 text-sm">
            No news
          </div>
        ) : (
          displayNews.map((item, index) => (
            <div
              key={item.id}
              className="bg-slate-700/30 rounded-lg p-3 border border-slate-600/30 hover:border-slate-500/50 transition-colors"
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-1.5 flex-wrap">
                  {activeTab === 'weighted' && (
                    <span className="text-xs font-bold text-slate-500">
                      #{index + 1}
                    </span>
                  )}
                  <span className={`text-xs px-1.5 py-0.5 rounded border ${getCategoryColor(item.category)}`}>
                    {item.category.replace(/_/g, ' ')}
                  </span>
                  {item.isHot && (
                    <Flame className="w-3 h-3 text-red-400" />
                  )}
                </div>
                <div className="flex flex-col items-end gap-0.5">
                  <span className="text-xs text-slate-400">
                    {getTimeAgo(item.timestamp)}
                  </span>
                  {activeTab === 'weighted' && item.weight && (
                    <span className={`text-xs px-1.5 py-0.5 rounded ${getWeightColor(item.weight)}`}>
                      {Math.round(item.weight)}
                    </span>
                  )}
                </div>
              </div>

              {/* Headline */}
              <h4 className="text-sm font-medium text-white mb-1 leading-snug">
                {item.headline}
              </h4>

              {/* Summary */}
              <p className={`text-xs text-slate-400 leading-relaxed ${
                expandedId === item.id ? '' : 'line-clamp-2'
              }`}>
                {item.summary}
              </p>

              {/* Actions */}
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-600/30">
                <button
                  onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                  className="flex items-center gap-1 text-xs text-slate-400 hover:text-white transition-colors"
                >
                  <ChevronDown className={`w-3 h-3 transition-transform ${
                    expandedId === item.id ? 'rotate-180' : ''
                  }`} />
                  {expandedId === item.id ? 'Show less' : 'Read more'}
                </button>
                {item.url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    Read
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default StockNewsAnalysis;
