"use client";

import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Shield, TrendingUp, TrendingDown, Calculator, Target,
  AlertTriangle, CheckCircle, DollarSign, Percent, Activity,
  BarChart3, Award, Info
} from 'lucide-react';
import { getApiBaseUrl } from '@/lib/api';

interface TrackRecord {
  total_picks: number;
  winning_picks: number;
  losing_picks: number;
  win_rate: number;
  avg_return: number;
  performance_level: string;
}

interface PositionSizeResult {
  recommended_shares: number;
  position_value: number;
  risk_amount: number;
  max_loss_per_share: number;
}

interface StopLossResult {
  conservative: number;
  moderate: number;
  aggressive: number;
  recommendations: {
    conservative: string;
    moderate: string;
    aggressive: string;
  };
}

const RiskManagement: React.FC = () => {
  // Track Record State
  const [trades, setTrades] = useState<Array<{ ticker: string; return: number }>>([
    { ticker: 'AAPL', return: 12.5 },
    { ticker: 'NVDA', return: -5.2 },
    { ticker: 'TSLA', return: 8.7 },
  ]);
  const [newTicker, setNewTicker] = useState('');
  const [newReturn, setNewReturn] = useState('');

  // Position Sizing State
  const [accountValue, setAccountValue] = useState('10000');
  const [riskPerTrade, setRiskPerTrade] = useState('2');
  const [entryPrice, setEntryPrice] = useState('');
  const [stopPrice, setStopPrice] = useState('');

  // Stop Loss State
  const [slEntryPrice, setSlEntryPrice] = useState('');
  const [slAccountValue, setSlAccountValue] = useState('10000');
  const [positionSize, setPositionSize] = useState('100');

  // Track Record Mutation
  const getTrackRecord = useMutation({
    mutationFn: async (tradesList: Array<{ ticker: string; return: number }>) => {
      // Convert 'return' to 'return_pct' for backend compatibility
      const trades = tradesList.map(t => ({
        ticker: t.ticker,
        return_pct: t.return
      }));

      const response = await fetch(`${getApiBaseUrl()}/api/portfolio/track-record-simple`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trades }),
      });
      if (!response.ok) throw new Error('Failed to calculate track record');
      return response.json();
    },
  });

  // Position Size Mutation
  const calculatePositionSize = useMutation({
    mutationFn: async (params: {
      account_value: number;
      risk_per_trade: number;
      entry_price: number;
      stop_loss_price: number;
    }) => {
      const response = await fetch(`${getApiBaseUrl()}/api/portfolio/position-size`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (!response.ok) throw new Error('Failed to calculate position size');
      return response.json();
    },
  });

  // Stop Loss Mutation
  const calculateStopLoss = useMutation({
    mutationFn: async (params: {
      entry_price: number;
      account_value: number;
      position_size: number;
    }) => {
      const response = await fetch(`${getApiBaseUrl()}/api/portfolio/stop-loss-simple`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (!response.ok) throw new Error('Failed to calculate stop loss');
      return response.json();
    },
  });

  const trackRecord = getTrackRecord.data?.data as TrackRecord | undefined;
  const positionSizeResult = calculatePositionSize.data?.data as PositionSizeResult | undefined;
  const stopLossResult = calculateStopLoss.data?.data as StopLossResult | undefined;

  const handleAddTrade = () => {
    if (newTicker && newReturn) {
      const newTrade = {
        ticker: newTicker.toUpperCase(),
        return: parseFloat(newReturn),
      };
      const updatedTrades = [...trades, newTrade];
      setTrades(updatedTrades);
      setNewTicker('');
      setNewReturn('');
      getTrackRecord.mutate(updatedTrades);
    }
  };

  const handleRemoveTrade = (index: number) => {
    const updatedTrades = trades.filter((_, i) => i !== index);
    setTrades(updatedTrades);
    if (updatedTrades.length > 0) {
      getTrackRecord.mutate(updatedTrades);
    }
  };

  const handleCalculateTrackRecord = () => {
    getTrackRecord.mutate(trades);
  };

  const handleCalculatePositionSize = () => {
    const params = {
      account_value: parseFloat(accountValue),
      risk_per_trade: parseFloat(riskPerTrade),
      entry_price: parseFloat(entryPrice),
      stop_loss_price: parseFloat(stopPrice),
    };
    calculatePositionSize.mutate(params);
  };

  const handleCalculateStopLoss = () => {
    const params = {
      entry_price: parseFloat(slEntryPrice),
      account_value: parseFloat(slAccountValue),
      position_size: parseFloat(positionSize),
    };
    calculateStopLoss.mutate(params);
  };

  const getPerformanceColor = (level: string) => {
    const colors: Record<string, string> = {
      'EXCELLENT': 'text-green-400 bg-green-900/30 border-green-500/50',
      'GOOD': 'text-lime-400 bg-lime-900/30 border-lime-500/50',
      'AVERAGE': 'text-yellow-400 bg-yellow-900/30 border-yellow-500/50',
      'POOR': 'text-orange-400 bg-orange-900/30 border-orange-500/50',
      'VERY_POOR': 'text-red-400 bg-red-900/30 border-red-500/50',
    };
    return colors[level] || colors['AVERAGE'];
  };

  const getPerformanceIcon = (level: string) => {
    if (level === 'EXCELLENT' || level === 'GOOD') return <Award className="w-6 h-6" />;
    if (level === 'AVERAGE') return <Activity className="w-6 h-6" />;
    return <AlertTriangle className="w-6 h-6" />;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-purple-600/20 rounded-lg">
          <Shield className="w-7 h-7 text-purple-400" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-white">Risk Management</h2>
          <p className="text-sm text-slate-400">Track performance & manage position sizing</p>
        </div>
      </div>

      {/* Track Record Section */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-white font-semibold flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-400" />
            Trading Track Record
          </h3>
          <button
            onClick={handleCalculateTrackRecord}
            disabled={getTrackRecord.isPending || trades.length === 0}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm"
          >
            {getTrackRecord.isPending ? 'Calculating...' : 'Calculate Stats'}
          </button>
        </div>

        {/* Add Trade Form */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <input
            type="text"
            placeholder="Ticker (e.g., AAPL)"
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
            className="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
          />
          <input
            type="number"
            placeholder="Return %"
            value={newReturn}
            onChange={(e) => setNewReturn(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddTrade()}
            className="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
          />
          <button
            onClick={handleAddTrade}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
          >
            Add Trade
          </button>
        </div>

        {/* Trades List */}
        <div className="space-y-2 mb-4">
          {trades.map((trade, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between bg-slate-900 border border-slate-700 rounded p-3"
            >
              <div className="flex items-center gap-3">
                <span className="font-bold text-white">{trade.ticker}</span>
                <span className={`font-semibold ${trade.return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {trade.return >= 0 ? '+' : ''}{trade.return.toFixed(2)}%
                </span>
              </div>
              <button
                onClick={() => handleRemoveTrade(idx)}
                className="text-slate-400 hover:text-red-400 transition-colors"
              >
                ×
              </button>
            </div>
          ))}
        </div>

        {/* Track Record Results */}
        {trackRecord && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-4 h-4 text-blue-400" />
                <p className="text-xs text-slate-400 uppercase">Win Rate</p>
              </div>
              <p className={`text-2xl font-bold ${trackRecord.win_rate >= 60 ? 'text-green-400' : trackRecord.win_rate >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                {trackRecord.win_rate.toFixed(1)}%
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {trackRecord.winning_picks}W / {trackRecord.losing_picks}L
              </p>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-purple-400" />
                <p className="text-xs text-slate-400 uppercase">Avg Return</p>
              </div>
              <p className={`text-2xl font-bold ${trackRecord.avg_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {trackRecord.avg_return >= 0 ? '+' : ''}{trackRecord.avg_return.toFixed(2)}%
              </p>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4 text-cyan-400" />
                <p className="text-xs text-slate-400 uppercase">Total Picks</p>
              </div>
              <p className="text-2xl font-bold text-white">{trackRecord.total_picks}</p>
            </div>

            <div className={`rounded-lg p-4 border ${getPerformanceColor(trackRecord.performance_level)}`}>
              <div className="flex items-center gap-2 mb-2">
                {getPerformanceIcon(trackRecord.performance_level)}
                <p className="text-xs uppercase">Performance</p>
              </div>
              <p className="text-lg font-bold">
                {trackRecord.performance_level.replace('_', ' ')}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Position Sizing Calculator */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <Calculator className="w-5 h-5 text-green-400" />
          Position Size Calculator
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm text-slate-400 mb-2">Account Value ($)</label>
            <input
              type="number"
              value={accountValue}
              onChange={(e) => setAccountValue(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Risk Per Trade (%)</label>
            <input
              type="number"
              value={riskPerTrade}
              onChange={(e) => setRiskPerTrade(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Entry Price ($)</label>
            <input
              type="number"
              value={entryPrice}
              onChange={(e) => setEntryPrice(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Stop Loss Price ($)</label>
            <input
              type="number"
              value={stopPrice}
              onChange={(e) => setStopPrice(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white"
            />
          </div>
        </div>

        <button
          onClick={handleCalculatePositionSize}
          disabled={calculatePositionSize.isPending || !entryPrice || !stopPrice}
          className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
        >
          {calculatePositionSize.isPending ? 'Calculating...' : 'Calculate Position Size'}
        </button>

        {/* Position Size Results */}
        {positionSizeResult && (
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-green-900/30 border border-green-500/50 rounded-lg p-4">
              <p className="text-xs text-green-400 mb-1 uppercase">Recommended Shares</p>
              <p className="text-2xl font-bold text-green-300">{positionSizeResult.recommended_shares}</p>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
              <p className="text-xs text-slate-400 mb-1 uppercase">Position Value</p>
              <p className="text-2xl font-bold text-white">${positionSizeResult.position_value.toFixed(2)}</p>
            </div>

            <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-4">
              <p className="text-xs text-red-400 mb-1 uppercase">Risk Amount</p>
              <p className="text-2xl font-bold text-red-300">${positionSizeResult.risk_amount.toFixed(2)}</p>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
              <p className="text-xs text-slate-400 mb-1 uppercase">Max Loss/Share</p>
              <p className="text-2xl font-bold text-slate-300">${positionSizeResult.max_loss_per_share.toFixed(2)}</p>
            </div>
          </div>
        )}
      </div>

      {/* Stop Loss Calculator */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-orange-400" />
          Stop Loss Calculator
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm text-slate-400 mb-2">Entry Price ($)</label>
            <input
              type="number"
              value={slEntryPrice}
              onChange={(e) => setSlEntryPrice(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Account Value ($)</label>
            <input
              type="number"
              value={slAccountValue}
              onChange={(e) => setSlAccountValue(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Position Size (shares)</label>
            <input
              type="number"
              value={positionSize}
              onChange={(e) => setPositionSize(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white"
            />
          </div>
        </div>

        <button
          onClick={handleCalculateStopLoss}
          disabled={calculateStopLoss.isPending || !slEntryPrice}
          className="w-full px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
        >
          {calculateStopLoss.isPending ? 'Calculating...' : 'Calculate Stop Loss Levels'}
        </button>

        {/* Stop Loss Results */}
        {stopLossResult && (
          <div className="mt-6 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-green-900/30 border border-green-500/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-green-400 uppercase font-semibold">Conservative</p>
                  <CheckCircle className="w-4 h-4 text-green-400" />
                </div>
                <p className="text-2xl font-bold text-green-300 mb-2">${stopLossResult.conservative.toFixed(2)}</p>
                <p className="text-xs text-green-200/80">{stopLossResult.recommendations.conservative}</p>
              </div>

              <div className="bg-yellow-900/30 border border-yellow-500/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-yellow-400 uppercase font-semibold">Moderate</p>
                  <Activity className="w-4 h-4 text-yellow-400" />
                </div>
                <p className="text-2xl font-bold text-yellow-300 mb-2">${stopLossResult.moderate.toFixed(2)}</p>
                <p className="text-xs text-yellow-200/80">{stopLossResult.recommendations.moderate}</p>
              </div>

              <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-red-400 uppercase font-semibold">Aggressive</p>
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                </div>
                <p className="text-2xl font-bold text-red-300 mb-2">${stopLossResult.aggressive.toFixed(2)}</p>
                <p className="text-xs text-red-200/80">{stopLossResult.recommendations.aggressive}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-400 mt-0.5" />
          <div>
            <h4 className="text-blue-300 font-semibold mb-1">Risk Management Best Practices</h4>
            <p className="text-sm text-blue-200/80">
              <span className="block mt-1">• Never risk more than 1-2% of your account on a single trade</span>
              <span className="block">• Always use stop losses to protect your capital</span>
              <span className="block">• Position size based on your risk tolerance and account size</span>
              <span className="block">• Track your performance to identify strengths and weaknesses</span>
              <span className="block">• Conservative stops (8-10%) for volatile stocks, tighter for stable stocks</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskManagement;
