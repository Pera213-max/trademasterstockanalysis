'use client';

import React from 'react';
import { TrendingUp, TrendingDown, Target, Award, BarChart3, CheckCircle } from 'lucide-react';

interface BacktestResultsProps {
  className?: string;
}

const BacktestResults: React.FC<BacktestResultsProps> = ({ className = '' }) => {
  // Mock historical performance data
  // In production, this would come from backend API tracking past predictions
  const backtestData = {
    period: '30 Days',
    totalPicks: 45,
    successfulPicks: 32,
    successRate: 71.1,
    averageReturn: 8.4,
    bestPick: {
      ticker: 'NVDA',
      return: 24.5,
      date: '2025-10-15',
    },
    worstPick: {
      ticker: 'META',
      return: -5.2,
      date: '2025-10-22',
    },
    byTimeframe: [
      { timeframe: 'Day Trade', picks: 15, success: 9, avgReturn: 2.1 },
      { timeframe: 'Swing', picks: 20, success: 15, avgReturn: 9.8 },
      { timeframe: 'Long Term', picks: 10, success: 8, avgReturn: 14.2 },
    ],
    recentPicks: [
      { ticker: 'AAPL', predicted: 10.5, actual: 12.3, status: 'success' },
      { ticker: 'TSLA', predicted: 15.0, actual: 18.2, status: 'success' },
      { ticker: 'AMD', predicted: 8.0, actual: 6.1, status: 'partial' },
      { ticker: 'GOOGL', predicted: 12.0, actual: -2.1, status: 'miss' },
    ],
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-900/30 text-green-400 border-green-800';
      case 'partial':
        return 'bg-yellow-900/30 text-yellow-400 border-yellow-800';
      case 'miss':
        return 'bg-red-900/30 text-red-400 border-red-800';
      default:
        return 'bg-gray-800 text-gray-400 border-gray-700';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4" />;
      case 'partial':
        return <TrendingUp className="w-4 h-4" />;
      case 'miss':
        return <TrendingDown className="w-4 h-4" />;
      default:
        return null;
    }
  };

  return (
    <div className={`bg-gray-900 border border-gray-800 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-600/20 rounded-lg">
            <BarChart3 className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">AI Picks Performance</h2>
            <p className="text-sm text-gray-400">Historical backtest results ({backtestData.period})</p>
          </div>
        </div>
        <div className="bg-purple-900/30 px-3 py-1.5 rounded-lg border border-purple-800/50">
          <span className="text-sm font-semibold text-purple-300">
            {backtestData.successRate}% Win Rate
          </span>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {/* Total Picks */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <p className="text-xs text-gray-400 mb-1 uppercase tracking-wide">Total Picks</p>
          <p className="text-2xl font-bold text-white">{backtestData.totalPicks}</p>
          <p className="text-xs text-gray-500 mt-1">Last {backtestData.period}</p>
        </div>

        {/* Successful Picks */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <p className="text-xs text-gray-400 mb-1 uppercase tracking-wide">Successful</p>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-bold text-green-400">{backtestData.successfulPicks}</p>
            <CheckCircle className="w-5 h-5 text-green-400" />
          </div>
          <p className="text-xs text-green-500 mt-1">{backtestData.successRate.toFixed(1)}% win rate</p>
        </div>

        {/* Average Return */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <p className="text-xs text-gray-400 mb-1 uppercase tracking-wide">Avg Return</p>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-bold text-blue-400">+{backtestData.averageReturn}%</p>
            <TrendingUp className="w-5 h-5 text-blue-400" />
          </div>
          <p className="text-xs text-gray-500 mt-1">Per pick</p>
        </div>

        {/* Best Pick */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <p className="text-xs text-gray-400 mb-1 uppercase tracking-wide">Best Pick</p>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-bold text-yellow-400">+{backtestData.bestPick.return}%</p>
            <Award className="w-5 h-5 text-yellow-400" />
          </div>
          <p className="text-xs text-yellow-500 mt-1">{backtestData.bestPick.ticker}</p>
        </div>
      </div>

      {/* Performance by Timeframe */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-white mb-3">Performance by Timeframe</h3>
        <div className="space-y-3">
          {backtestData.byTimeframe.map((tf, idx) => {
            const successRate = (tf.success / tf.picks) * 100;
            return (
              <div key={idx} className="bg-gray-800/30 rounded-lg p-3 border border-gray-700/50">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="text-sm font-semibold text-white">{tf.timeframe}</p>
                    <p className="text-xs text-gray-400">
                      {tf.success}/{tf.picks} picks successful
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-green-400">+{tf.avgReturn}%</p>
                    <p className="text-xs text-gray-400">{successRate.toFixed(0)}% win rate</p>
                  </div>
                </div>
                {/* Progress Bar */}
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full transition-all"
                    style={{ width: `${successRate}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Picks Performance */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-3">Recent Picks Performance</h3>
        <div className="space-y-2">
          {backtestData.recentPicks.map((pick, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between bg-gray-800/30 rounded-lg p-3 border border-gray-700/50"
            >
              <div className="flex items-center gap-3">
                <div className={`px-2 py-1 rounded border ${getStatusColor(pick.status)}`}>
                  {getStatusIcon(pick.status)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{pick.ticker}</p>
                  <p className="text-xs text-gray-400">Predicted: +{pick.predicted}%</p>
                </div>
              </div>
              <div className="text-right">
                <p
                  className={`text-sm font-bold ${
                    pick.actual >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {pick.actual >= 0 ? '+' : ''}
                  {pick.actual.toFixed(1)}%
                </p>
                <p className="text-xs text-gray-400">Actual</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Disclaimer */}
      <div className="mt-6 pt-4 border-t border-gray-800">
        <p className="text-xs text-gray-500 leading-relaxed">
          <span className="font-semibold text-gray-400">Disclaimer:</span> Past performance does
          not guarantee future results. Backtest results are based on historical data and do not
          account for execution costs, slippage, or market conditions. Always conduct your own
          research and consider your risk tolerance before trading.
        </p>
      </div>
    </div>
  );
};

export default BacktestResults;
