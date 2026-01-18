"use client";

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MessageSquare, TrendingUp, Twitter, ThumbsUp, ThumbsDown, Users, Loader2, RefreshCw, Flame, ArrowUp, ArrowDown } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { getSocialTrending, type SocialTrend } from '@/lib/api';
import { useWebSocket } from '@/lib/websocket';

const SocialTrending: React.FC = () => {
  const [liveData, setLiveData] = useState<SocialTrend[]>([]);

  // Fetch initial social trending data
  const { data, isLoading, error } = useQuery({
    queryKey: ['social-trending'],
    queryFn: () => getSocialTrending(10),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // WebSocket for real-time updates
  const { data: wsData, isConnected } = useWebSocket('social');

  // Update live data when WebSocket receives new data
  useEffect(() => {
    if (wsData && 'platform' in wsData && 'mentions' in wsData && 'sentiment' in wsData) {
      // Map SocialUpdate to SocialTrend format
      const socialTrend: SocialTrend = {
        ticker: wsData.ticker,
        mentions: wsData.mentions,
        sentiment: wsData.sentiment,
        platform: wsData.platform,
        trending: 'spike' in wsData ? wsData.spike : false
      };

      setLiveData((prev) => {
        const updated = [...prev];
        const index = updated.findIndex((item) => item.ticker === socialTrend.ticker);
        if (index >= 0) {
          updated[index] = { ...updated[index], ...socialTrend };
        } else {
          updated.unshift(socialTrend);
        }
        return updated.slice(0, 10);
      });
    }
  }, [wsData]);

  // Initialize live data from API
  useEffect(() => {
    if (data?.data) {
      setLiveData(data.data);
    }
  }, [data]);

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <MessageSquare className="w-7 h-7 text-blue-500" />
            Social Trending
          </h2>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-24 bg-slate-800/50 rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  const formatMentions = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getSentimentColor = (sentiment: number): string => {
    if (sentiment > 0.5) return 'text-green-400';
    if (sentiment > 0) return 'text-green-300';
    if (sentiment > -0.5) return 'text-red-300';
    return 'text-red-400';
  };

  const getSentimentBgColor = (sentiment: number): string => {
    if (sentiment > 0.5) return 'bg-green-500/20 border-green-500/30';
    if (sentiment > 0) return 'bg-green-500/10 border-green-500/20';
    if (sentiment > -0.5) return 'bg-red-500/10 border-red-500/20';
    return 'bg-red-500/20 border-red-500/30';
  };

  const getSentimentLabel = (sentiment: number): string => {
    if (sentiment > 0.7) return 'Very Bullish';
    if (sentiment > 0.3) return 'Bullish';
    if (sentiment > -0.3) return 'Neutral';
    if (sentiment > -0.7) return 'Bearish';
    return 'Very Bearish';
  };

  const getSentimentIcon = (sentiment: number) => {
    return sentiment >= 0 ? (
      <ThumbsUp className="w-4 h-4" />
    ) : (
      <ThumbsDown className="w-4 h-4" />
    );
  };

  const getSparklineColor = (sentiment: number): string => {
    return sentiment >= 0 ? '#10b981' : '#ef4444';
  };

  // Generate detailed market impact analysis
  const getMarketImpact = (trend: SocialTrend): { discussion: string; impact: string; emoji: string } => {
    const mentionK = Math.round((trend.mentions || 0) / 1000);
    const sentiment = isNaN(trend.sentiment) ? 0 : trend.sentiment;

    // High volume + very bullish
    if (mentionK > 50 && sentiment > 0.7) {
      return {
        emoji: "↗↗",
        discussion: `MASSIVE retail hype (${mentionK}K mentions). WSB army rallying hard.`,
        impact: "BULLISH IMPACT: Heavy retail buying pressure incoming. Expect 5-15% short-term pump. Watch for profit-taking on resistance."
      };
    }
    // High volume + bullish
    else if (mentionK > 20 && sentiment > 0.4) {
      return {
        emoji: "↗",
        discussion: `Strong retail interest (${mentionK}K mentions). Buying momentum building.`,
        impact: "BUYING PRESSURE: Retail accumulation phase. Could push stock 3-8% higher. Monitor options activity and short interest."
      };
    }
    // High volume + bearish
    else if (mentionK > 20 && sentiment < -0.3) {
      return {
        emoji: "↘↘",
        discussion: `Heavy bearish discussion (${mentionK}K mentions). Warning signals spreading.`,
        impact: "BEARISH PRESSURE: Retail selling/shorting sentiment. Risk of 4-10% decline. Check for fundamental catalysts driving fear."
      };
    }
    // Moderate volume + very bullish
    else if (sentiment > 0.6) {
      return {
        emoji: "↗",
        discussion: `Bullish buzz growing (${mentionK}K mentions). Early momentum spotted.`,
        impact: "EARLY OPPORTUNITY: Community finding this before mainstream. Potential 5-12% move if volume confirms. Good risk/reward."
      };
    }
    // Moderate volume + bearish
    else if (sentiment < -0.4) {
      return {
        emoji: "↘",
        discussion: `Bearish warnings (${mentionK}K mentions). Community skeptical.`,
        impact: "CAUTION ADVISED: Negative sentiment spreading. May see 3-7% pullback. Consider reducing exposure or wait for reversal."
      };
    }
    // Neutral but high activity
    else if (mentionK > 30) {
      return {
        emoji: "↕",
        discussion: `Hot debate (${mentionK}K mentions). Bulls vs bears fighting.`,
        impact: "HIGH VOLATILITY: Community divided. Expect big swings ±5-10%. Perfect for day traders, risky for holders."
      };
    }
    // Low/moderate positive
    else if (sentiment > 0.2) {
      return {
        emoji: "→",
        discussion: `Moderate interest (${mentionK}K mentions). Some bullish chatter.`,
        impact: "MILD BULLISH: Steady retail interest. May drift 2-4% higher. Not strong catalyst yet, watch for volume spike."
      };
    }
    // Default
    else {
      return {
        emoji: "•",
        discussion: `Active discussion (${mentionK}K mentions). Mixed sentiment.`,
        impact: "MONITORING: Neutral community view. Stock likely trades sideways. Wait for clearer signal before entry."
      };
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <MessageSquare className="w-7 h-7 text-blue-500" />
          Reddit Trending
        </h2>
        <div className="flex items-center gap-3">
          {isConnected && (
            <div className="flex items-center gap-2 text-green-500 text-sm">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              Live
            </div>
          )}
          <div className="flex items-center gap-1 text-xs text-slate-500">
            <RefreshCw className="w-3 h-3" />
            5min
          </div>
        </div>
      </div>

      {error && (
        <div className="text-red-400 p-3 bg-red-500/10 rounded-lg border border-red-500/30 text-sm">
          Virhe ladattaessa trendejä
        </div>
      )}

      {/* Trending List */}
      <div className="space-y-3">
        {liveData.slice(0, 8).map((trend, index) => {
          const impact = getMarketImpact(trend);
          return (
            <div
              key={trend.ticker}
              className="p-4 hover:bg-slate-800/50 rounded-lg border border-slate-700/50 hover:border-slate-600 transition-all cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{impact.emoji}</span>
                  <span className="text-xs text-slate-500">#{index + 1}</span>
                  <span className="font-bold text-white text-lg">{trend.ticker}</span>
                  {index < 3 && <Flame className="w-4 h-4 text-orange-400 animate-pulse" />}
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold flex items-center gap-1 ${
                    trend.sentiment > 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {trend.sentiment > 0 ? (
                      <><ArrowUp className="w-3 h-3" /> Bullish</>
                    ) : (
                      <><ArrowDown className="w-3 h-3" /> Bearish</>
                    )}
                  </span>
                </div>
              </div>

              {/* Discussion Context */}
              <div className="text-xs text-slate-300 mb-2 bg-slate-800/30 p-2 rounded">
                <strong>Discussion:</strong> {impact.discussion}
              </div>

              {/* Market Impact Analysis */}
              <div className={`text-xs p-3 rounded-lg border mb-2 ${
                trend.sentiment > 0.5 ? 'bg-green-500/10 border-green-500/30 text-green-200' :
                trend.sentiment < -0.3 ? 'bg-red-500/10 border-red-500/30 text-red-200' :
                'bg-yellow-500/10 border-yellow-500/30 text-yellow-200'
              }`}>
                <div className="font-semibold mb-1">Market Impact:</div>
                {impact.impact}
              </div>

              {/* Stats */}
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">
                  {formatMentions(trend.mentions)} mentions · r/wallstreetbets
                </span>
                <span className={`px-2 py-0.5 rounded font-medium ${
                  trend.sentiment > 0
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-red-500/20 text-red-400'
                }`}>
                  {isNaN(trend.sentiment) ? '0' : Math.round(Math.abs(trend.sentiment) * 100)}% {trend.sentiment > 0 ? 'bullish' : 'bearish'}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Info */}
      <div className="text-xs text-slate-500 text-center pt-2">
        Data: r/wallstreetbets, r/stocks, r/investing
      </div>
    </div>
  );
};

export default SocialTrending;
