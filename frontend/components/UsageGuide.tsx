"use client";

import React, { useState } from 'react';
import {
  HelpCircle, X,
  TrendingUp, Zap, Target, BarChart3,
  Newspaper, Users, Globe, Activity,
  Lightbulb, AlertTriangle, Info
} from 'lucide-react';

const UsageGuide = () => {
  const [isExpanded, setIsExpanded] = useState(false);

  const sections = [
    {
      icon: <BarChart3 className="w-4 h-4 text-blue-400" />,
      title: "Market Overview",
      description: "Real-time market sentiment and conditions"
    },
    {
      icon: <Target className="w-4 h-4 text-purple-400" />,
      title: "Hidden Gems",
      description: "Undervalued mid/small cap opportunities"
    },
    {
      icon: <Zap className="w-4 h-4 text-yellow-400" />,
      title: "Quick Wins",
      description: "Short-term momentum trades (1-3 days)"
    },
    {
      icon: <TrendingUp className="w-4 h-4 text-green-400" />,
      title: "AI Picks",
      description: "AI-scored stock recommendations (0-100)"
    },
    {
      icon: <Newspaper className="w-4 h-4 text-orange-400" />,
      title: "News Bombs",
      description: "High-impact market news by weight"
    },
    {
      icon: <Users className="w-4 h-4 text-pink-400" />,
      title: "Social Trending",
      description: "Reddit trending stocks & sentiment"
    },
    {
      icon: <Globe className="w-4 h-4 text-indigo-400" />,
      title: "Macro Indicators",
      description: "GDP, inflation, rates & economic data"
    }
  ];

  return (
    <>
      {/* Fixed Help Button - Bottom Right */}
      <div className="fixed bottom-4 right-4 z-50">
        {!isExpanded ? (
          // Collapsed - Small help button
          <button
            onClick={() => setIsExpanded(true)}
            className="bg-blue-600 hover:bg-blue-500 text-white p-3 rounded-full shadow-lg transition-all hover:scale-110"
            title="How to use this dashboard"
          >
            <HelpCircle className="w-5 h-5" />
          </button>
        ) : (
          // Expanded - Guide panel
          <div className="bg-slate-800/95 backdrop-blur-sm rounded-xl border border-slate-700/50 shadow-2xl w-80 max-h-96 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-3 border-b border-slate-700/50">
              <div className="flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-blue-400" />
                <span className="font-semibold text-white text-sm">Dashboard Guide</span>
              </div>
              <button
                onClick={() => setIsExpanded(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="overflow-y-auto max-h-72 p-3 space-y-3">
              {/* Quick Tips */}
              <div className="bg-blue-900/30 border border-blue-800/50 rounded-lg p-2">
                <div className="flex items-start gap-2">
                  <Lightbulb className="w-3 h-3 text-blue-400 mt-0.5 flex-shrink-0" />
                  <div className="text-xs">
                    <p className="text-blue-300 font-medium mb-1">Tips:</p>
                    <ul className="text-slate-300 space-y-0.5 list-disc list-inside">
                      <li>Scores 70+ = strong opportunity</li>
                      <li>Check multiple signals before trading</li>
                      <li>Data updates every 5-30 min</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Section Explanations */}
              <div className="space-y-2">
                {sections.map((section, index) => (
                  <div
                    key={index}
                    className="bg-slate-700/30 rounded-lg p-2 border border-slate-600/30"
                  >
                    <div className="flex items-center gap-2 mb-0.5">
                      {section.icon}
                      <span className="text-xs font-medium text-white">{section.title}</span>
                    </div>
                    <p className="text-xs text-slate-400 leading-tight">
                      {section.description}
                    </p>
                  </div>
                ))}
              </div>

              {/* Scoring System */}
              <div className="bg-slate-700/30 rounded-lg p-2 border border-slate-600/30">
                <div className="flex items-center gap-1 mb-1">
                  <Info className="w-3 h-3 text-slate-400" />
                  <span className="text-xs font-medium text-white">Scoring (0-100)</span>
                </div>
                <div className="grid grid-cols-2 gap-1 text-xs">
                  <div>
                    <span className="text-slate-400">Analysts:</span>
                    <span className="text-white ml-1">30pts</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Financials:</span>
                    <span className="text-white ml-1">35pts</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Market:</span>
                    <span className="text-white ml-1">20pts</span>
                  </div>
                  <div>
                    <span className="text-slate-400">News:</span>
                    <span className="text-white ml-1">15pts</span>
                  </div>
                </div>
              </div>

              {/* Risk Warning */}
              <div className="bg-yellow-900/30 border border-yellow-800/50 rounded-lg p-2">
                <div className="flex items-start gap-1">
                  <AlertTriangle className="w-3 h-3 text-yellow-400 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-yellow-300">
                    Analysis tools only. Do your own research.
                  </p>
                </div>
              </div>

              {/* Data Sources */}
              <div className="text-xs text-slate-500 text-center pt-1 border-t border-slate-700/50">
                Data: Finnhub • NewsAPI • Reddit • FRED
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default UsageGuide;
