"use client";

import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  PieChart, TrendingUp, TrendingDown, AlertTriangle, CheckCircle,
  Shield, Activity, Briefcase, DollarSign, BarChart3, ArrowUpRight,
  ArrowDownRight, Info, Plus, X, Target, Zap, Brain, TrendingUpIcon,
  Calculator, AlertCircle, Gauge
} from 'lucide-react';
import { getApiBaseUrl, getProgramUniverseSummary, type ProgramUniverseSummary } from '@/lib/api';

interface PortfolioHolding {
  ticker: string;
  shares: number;
  avgPrice: number;
  currentPrice?: number;
}

interface PortfolioAnalysis {
  health_score: number;
  risk_analysis: {
    overall_risk: string;
    concentration_risk: number;
    volatility_risk: number;
    losses_risk: number;
    total_risk_score: number;
  };
  diversification: {
    score: number;
    status: string;
    sector_breakdown: Array<{
      sector: string;
      percentage: number;
      count: number;
    }>;
  };
  rebalancing: Array<{
    ticker: string;
    action: string;
    reason: string;
    current_pct: number;
    suggested_pct?: number;
  }>;
  positions: Array<{
    ticker: string;
    shares: number;
    entry_price: number;
    current_price: number;
    value: number;
    gain_loss: number;
    gain_loss_pct: number;
    weight: number;
    sector: string;
  }>;
  total_value: number;
  total_gain_loss: number;
  total_gain_loss_pct: number;
}

const PortfolioAnalyzer: React.FC = () => {
  const [showAddHolding, setShowAddHolding] = useState(false);
  const [analysisScope, setAnalysisScope] = useState<'program' | 'portfolio'>('program');
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([
    { ticker: 'AAPL', shares: 10, avgPrice: 150 },
    { ticker: 'NVDA', shares: 5, avgPrice: 400 },
    { ticker: 'MSFT', shares: 8, avgPrice: 350 },
  ]);

  const [newHolding, setNewHolding] = useState<PortfolioHolding>({
    ticker: '',
    shares: 0,
    avgPrice: 0,
  });

  const programSummaryQuery = useQuery({
    queryKey: ['program-universe-summary'],
    queryFn: getProgramUniverseSummary,
    enabled: analysisScope === 'program',
  });

  const programSummary = programSummaryQuery.data?.data as ProgramUniverseSummary | undefined;

  // Analyze portfolio mutation
  const analyzePortfolio = useMutation({
    mutationFn: async (portfolioHoldings: PortfolioHolding[]) => {
      // Transform to backend format (avgPrice -> avg_cost)
      const backendHoldings = portfolioHoldings.map(h => ({
        ticker: h.ticker,
        shares: h.shares,
        avg_cost: h.avgPrice
      }));

      const response = await fetch(`${getApiBaseUrl()}/api/portfolio/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ holdings: backendHoldings }),
      });
      if (!response.ok) throw new Error('Failed to analyze portfolio');
      return response.json();
    },
  });

  const analysis = analyzePortfolio.data?.data as PortfolioAnalysis | undefined;

  const handleAnalyze = () => {
    analyzePortfolio.mutate(holdings);
  };

  const handleAddHolding = () => {
    if (newHolding.ticker && newHolding.shares > 0 && newHolding.avgPrice > 0) {
      setHoldings([...holdings, newHolding]);
      setNewHolding({ ticker: '', shares: 0, avgPrice: 0 });
      setShowAddHolding(false);
    }
  };

  const handleRemoveHolding = (index: number) => {
    setHoldings(holdings.filter((_, i) => i !== index));
  };

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-400 bg-green-900/30 border-green-500/50';
    if (score >= 60) return 'text-yellow-400 bg-yellow-900/30 border-yellow-500/50';
    return 'text-red-400 bg-red-900/30 border-red-500/50';
  };

  const getRiskColor = (risk: string) => {
    if (risk === 'LOW') return 'text-green-400';
    if (risk === 'MEDIUM') return 'text-yellow-400';
    return 'text-red-400';
  };

  const getActionColor = (action: string) => {
    const colors: Record<string, string> = {
      'TRIM': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
      'HOLD': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
      'ADD': 'bg-green-500/20 text-green-300 border-green-500/30',
      'REVIEW': 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
      'TAKE_PROFITS': 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    };
    return colors[action] || 'bg-slate-500/20 text-slate-300 border-slate-500/30';
  };

  const formatSectorLabel = (value: string) => {
    if (!value) return 'Other';
    if (value === 'other') return 'Other';
    return value.charAt(0).toUpperCase() + value.slice(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-600/20 rounded-lg">
            <PieChart className="w-7 h-7 text-purple-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Portfolio Analyzer</h2>
            <p className="text-sm text-slate-400">Comprehensive portfolio health analysis</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-slate-900/60 border border-slate-700 rounded-full p-1 text-xs">
            <button
              onClick={() => setAnalysisScope('program')}
              className={`px-3 py-1 rounded-full transition ${
                analysisScope === 'program'
                  ? 'bg-purple-600 text-white'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              Program Universe
            </button>
            <button
              onClick={() => setAnalysisScope('portfolio')}
              className={`px-3 py-1 rounded-full transition ${
                analysisScope === 'portfolio'
                  ? 'bg-purple-600 text-white'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              My Portfolio
            </button>
          </div>

          {analysisScope === 'portfolio' && (
            <button
              onClick={() => setShowAddHolding(!showAddHolding)}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg flex items-center gap-2 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Holding
            </button>
          )}
        </div>
      </div>

      {analysisScope === 'program' && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white font-semibold">Program Universe</h3>
            <span className="text-sm text-slate-400">
              {programSummary ? `${programSummary.total_stocks} stocks` : 'Loading...'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            Coverage across all program stocks. Switch to My Portfolio for personalized analysis.
          </p>

          {programSummaryQuery.isLoading && (
            <p className="text-sm text-slate-400">Loading universe summary...</p>
          )}

          {programSummary && (
            <div className="space-y-3">
              {programSummary.sector_breakdown.map((sector) => (
                <div key={sector.sector}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-300">{formatSectorLabel(sector.sector)}</span>
                    <span className="text-sm font-semibold text-white">
                      {sector.percentage.toFixed(1)}% ({sector.count})
                    </span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-purple-600 to-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${sector.percentage}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {programSummaryQuery.isError && (
            <p className="text-xs text-red-300 mt-3">Failed to load program universe summary.</p>
          )}
        </div>
      )}

      {analysisScope === 'portfolio' && (
        <>
          {/* Add Holding Form */}
          {showAddHolding && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
              <h3 className="text-white font-semibold mb-3">Add New Holding</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <input
                  type="text"
                  placeholder="Ticker (e.g., AAPL)"
                  value={newHolding.ticker}
                  onChange={(e) => setNewHolding({ ...newHolding, ticker: e.target.value.toUpperCase() })}
                  className="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
                />
                <input
                  type="number"
                  placeholder="Shares"
                  value={newHolding.shares || ''}
                  onChange={(e) => setNewHolding({ ...newHolding, shares: parseFloat(e.target.value) || 0 })}
                  className="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
                />
                <input
                  type="number"
                  placeholder="Avg Price"
                  value={newHolding.avgPrice || ''}
                  onChange={(e) => setNewHolding({ ...newHolding, avgPrice: parseFloat(e.target.value) || 0 })}
                  className="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
                />
                <button
                  onClick={handleAddHolding}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
                >
                  Add
                </button>
              </div>
            </div>
          )}

          {/* Current Holdings */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
            <h3 className="text-white font-semibold mb-3">Current Holdings ({holdings.length})</h3>
            <div className="space-y-2">
              {holdings.map((holding, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-slate-900/50 rounded border border-slate-700/50">
                  <div className="flex items-center gap-4">
                    <span className="font-bold text-white">{holding.ticker}</span>
                    <span className="text-slate-400">{holding.shares} shares @ ${holding.avgPrice.toFixed(2)}</span>
                  </div>
                  <button
                    onClick={() => handleRemoveHolding(index)}
                    className="p-1 hover:bg-red-500/20 rounded text-red-400 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
            <button
              onClick={handleAnalyze}
              disabled={analyzePortfolio.isPending || holdings.length === 0}
              className="mt-4 w-full px-4 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors"
            >
              {analyzePortfolio.isPending ? 'Analyzing...' : 'Analyze Portfolio'}
            </button>
          </div>

          {/* Analysis Results */}
          {analysis && (
            <>
          {/* Portfolio Overview */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className={`rounded-lg p-4 border ${getHealthColor(analysis.health_score)}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm opacity-80">Health Score</span>
                <Shield className="w-5 h-5" />
              </div>
              <div className="text-3xl font-bold">{analysis.health_score}/100</div>
              <div className="text-xs mt-1 opacity-80">
                {analysis.health_score >= 80 ? 'Excellent' : analysis.health_score >= 60 ? 'Good' : 'Needs Attention'}
              </div>
            </div>

            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-400">Total Value</span>
                <DollarSign className="w-5 h-5 text-slate-400" />
              </div>
              <div className="text-3xl font-bold text-white">${analysis.total_value.toLocaleString()}</div>
              <div className={`text-xs mt-1 flex items-center gap-1 ${analysis.total_gain_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {analysis.total_gain_loss >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                {analysis.total_gain_loss >= 0 ? '+' : ''}{analysis.total_gain_loss_pct.toFixed(2)}%
              </div>
            </div>

            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-400">Risk Level</span>
                <AlertTriangle className={`w-5 h-5 ${getRiskColor(analysis.risk_analysis.overall_risk)}`} />
              </div>
              <div className={`text-2xl font-bold ${getRiskColor(analysis.risk_analysis.overall_risk)}`}>
                {analysis.risk_analysis.overall_risk}
              </div>
              <div className="text-xs mt-1 text-slate-400">
                Score: {analysis.risk_analysis.total_risk_score}/100
              </div>
            </div>

            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-400">Diversification</span>
                <Activity className="w-5 h-5 text-slate-400" />
              </div>
              <div className="text-2xl font-bold text-white">{analysis.diversification.score}/100</div>
              <div className="text-xs mt-1 text-slate-400">
                {analysis.diversification.status}
              </div>
            </div>
          </div>

          {/* Positions Table */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
            <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
              <Briefcase className="w-5 h-5" />
              Positions
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700 text-slate-400 text-sm">
                    <th className="text-left py-2">Ticker</th>
                    <th className="text-right py-2">Shares</th>
                    <th className="text-right py-2">Entry</th>
                    <th className="text-right py-2">Current</th>
                    <th className="text-right py-2">Value</th>
                    <th className="text-right py-2">Gain/Loss</th>
                    <th className="text-right py-2">Weight</th>
                    <th className="text-left py-2">Sector</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.positions.map((position, idx) => (
                    <tr key={idx} className="border-b border-slate-700/50 text-sm">
                      <td className="py-3 font-bold text-white">{position.ticker}</td>
                      <td className="text-right text-slate-300">{position.shares}</td>
                      <td className="text-right text-slate-300">${position.entry_price.toFixed(2)}</td>
                      <td className="text-right text-slate-300">${position.current_price.toFixed(2)}</td>
                      <td className="text-right text-white font-semibold">${position.value.toLocaleString()}</td>
                      <td className={`text-right font-semibold ${position.gain_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {position.gain_loss >= 0 ? '+' : ''}{position.gain_loss_pct.toFixed(2)}%
                      </td>
                      <td className="text-right text-slate-300">{position.weight.toFixed(1)}%</td>
                      <td className="text-slate-400">{position.sector}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Risk Analysis Breakdown */}
          <div className="bg-gradient-to-br from-red-900/20 to-orange-900/20 border border-red-500/30 rounded-lg p-6">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Gauge className="w-6 h-6 text-red-400" />
              Risk Analysis Breakdown
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-400">Concentration Risk</span>
                  <AlertTriangle className={`w-4 h-4 ${analysis.risk_analysis.concentration_risk > 70 ? 'text-red-400' : analysis.risk_analysis.concentration_risk > 40 ? 'text-yellow-400' : 'text-green-400'}`} />
                </div>
                <div className={`text-2xl font-bold ${analysis.risk_analysis.concentration_risk > 70 ? 'text-red-400' : analysis.risk_analysis.concentration_risk > 40 ? 'text-yellow-400' : 'text-green-400'}`}>
                  {analysis.risk_analysis.concentration_risk}/100
                </div>
                <div className="mt-2 w-full bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${analysis.risk_analysis.concentration_risk > 70 ? 'bg-red-500' : analysis.risk_analysis.concentration_risk > 40 ? 'bg-yellow-500' : 'bg-green-500'}`}
                    style={{ width: `${analysis.risk_analysis.concentration_risk}%` }}
                  ></div>
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  {analysis.risk_analysis.concentration_risk > 70 ? 'Too concentrated - diversify!' : analysis.risk_analysis.concentration_risk > 40 ? 'Moderate concentration' : 'Well diversified'}
                </p>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-400">Volatility Risk</span>
                  <Activity className={`w-4 h-4 ${analysis.risk_analysis.volatility_risk > 70 ? 'text-red-400' : analysis.risk_analysis.volatility_risk > 40 ? 'text-yellow-400' : 'text-green-400'}`} />
                </div>
                <div className={`text-2xl font-bold ${analysis.risk_analysis.volatility_risk > 70 ? 'text-red-400' : analysis.risk_analysis.volatility_risk > 40 ? 'text-yellow-400' : 'text-green-400'}`}>
                  {analysis.risk_analysis.volatility_risk}/100
                </div>
                <div className="mt-2 w-full bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${analysis.risk_analysis.volatility_risk > 70 ? 'bg-red-500' : analysis.risk_analysis.volatility_risk > 40 ? 'bg-yellow-500' : 'bg-green-500'}`}
                    style={{ width: `${analysis.risk_analysis.volatility_risk}%` }}
                  ></div>
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  {analysis.risk_analysis.volatility_risk > 70 ? 'High volatility portfolio' : analysis.risk_analysis.volatility_risk > 40 ? 'Moderate volatility' : 'Low volatility'}
                </p>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-400">Unrealized Loss Risk</span>
                  <TrendingDown className={`w-4 h-4 ${analysis.risk_analysis.losses_risk > 70 ? 'text-red-400' : analysis.risk_analysis.losses_risk > 40 ? 'text-yellow-400' : 'text-green-400'}`} />
                </div>
                <div className={`text-2xl font-bold ${analysis.risk_analysis.losses_risk > 70 ? 'text-red-400' : analysis.risk_analysis.losses_risk > 40 ? 'text-yellow-400' : 'text-green-400'}`}>
                  {analysis.risk_analysis.losses_risk}/100
                </div>
                <div className="mt-2 w-full bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${analysis.risk_analysis.losses_risk > 70 ? 'bg-red-500' : analysis.risk_analysis.losses_risk > 40 ? 'bg-yellow-500' : 'bg-green-500'}`}
                    style={{ width: `${analysis.risk_analysis.losses_risk}%` }}
                  ></div>
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  {analysis.risk_analysis.losses_risk > 70 ? 'Significant unrealized losses' : analysis.risk_analysis.losses_risk > 40 ? 'Some positions underwater' : 'Most positions profitable'}
                </p>
              </div>
            </div>
          </div>

          {/* Advanced Performance Metrics */}
          <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-lg p-6">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-6 h-6 text-blue-400" />
              Performance Metrics
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Total Return</div>
                <div className={`text-2xl font-bold ${analysis.total_gain_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {analysis.total_gain_loss >= 0 ? '+' : ''}{analysis.total_gain_loss_pct.toFixed(2)}%
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  ${Math.abs(analysis.total_gain_loss).toLocaleString()}
                </div>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Best Performer</div>
                <div className="text-2xl font-bold text-green-400">
                  {analysis.positions.reduce((best, pos) => pos.gain_loss_pct > best.gain_loss_pct ? pos : best).ticker}
                </div>
                <div className="text-xs text-green-400 mt-1">
                  +{analysis.positions.reduce((best, pos) => pos.gain_loss_pct > best.gain_loss_pct ? pos : best).gain_loss_pct.toFixed(2)}%
                </div>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Worst Performer</div>
                <div className="text-2xl font-bold text-red-400">
                  {analysis.positions.reduce((worst, pos) => pos.gain_loss_pct < worst.gain_loss_pct ? pos : worst).ticker}
                </div>
                <div className="text-xs text-red-400 mt-1">
                  {analysis.positions.reduce((worst, pos) => pos.gain_loss_pct < worst.gain_loss_pct ? pos : worst).gain_loss_pct.toFixed(2)}%
                </div>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Win Rate</div>
                <div className="text-2xl font-bold text-white">
                  {((analysis.positions.filter(p => p.gain_loss > 0).length / analysis.positions.length) * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {analysis.positions.filter(p => p.gain_loss > 0).length}/{analysis.positions.length} winning
                </div>
              </div>
            </div>
          </div>

          {/* Position-Specific Recommendations */}
          <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-lg p-6">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Brain className="w-6 h-6 text-green-400" />
              AI Position Analysis
            </h3>
            <div className="space-y-3">
              {analysis.positions.map((position, idx) => {
                const stopLoss = position.current_price * 0.92; // 8% stop loss
                const takeProfit = position.current_price * 1.15; // 15% take profit
                const isWinning = position.gain_loss > 0;
                const isLargePosition = position.weight > 20;

                return (
                  <div key={idx} className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-bold text-white text-lg">{position.ticker}</span>
                          <span className={`px-2 py-1 rounded text-xs font-semibold ${
                            position.gain_loss >= 0 ? 'bg-green-500/20 text-green-300 border border-green-500/30' : 'bg-red-500/20 text-red-300 border border-red-500/30'
                          }`}>
                            {position.gain_loss >= 0 ? 'PROFIT' : 'LOSS'}
                          </span>
                          {isLargePosition && (
                            <span className="px-2 py-1 rounded text-xs font-semibold bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
                              {position.weight.toFixed(1)}% of portfolio
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-slate-400">
                          ${position.value.toLocaleString()} • {position.gain_loss >= 0 ? '+' : ''}{position.gain_loss_pct.toFixed(2)}%
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                      <div className="bg-slate-800/50 rounded p-2">
                        <div className="text-xs text-slate-500">Entry Price</div>
                        <div className="text-sm font-semibold text-white">${position.entry_price.toFixed(2)}</div>
                      </div>
                      <div className="bg-slate-800/50 rounded p-2">
                        <div className="text-xs text-slate-500">Current Price</div>
                        <div className="text-sm font-semibold text-white">${position.current_price.toFixed(2)}</div>
                      </div>
                      <div className="bg-red-900/30 border border-red-500/30 rounded p-2">
                        <div className="text-xs text-red-400">Stop Loss (8%)</div>
                        <div className="text-sm font-semibold text-red-300">${stopLoss.toFixed(2)}</div>
                      </div>
                      <div className="bg-green-900/30 border border-green-500/30 rounded p-2">
                        <div className="text-xs text-green-400">Take Profit (15%)</div>
                        <div className="text-sm font-semibold text-green-300">${takeProfit.toFixed(2)}</div>
                      </div>
                    </div>

                    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                      <div className="flex items-start gap-2">
                        <Target className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-blue-200">
                          <strong>AI Recommendation:</strong>{' '}
                          {isLargePosition && isWinning ?
                            `Consider taking partial profits on ${position.ticker}. It represents ${position.weight.toFixed(1)}% of your portfolio. Trim to 15% to reduce concentration risk.` :
                          isLargePosition && !isWinning ?
                            `${position.ticker} is ${position.weight.toFixed(1)}% of portfolio but down ${Math.abs(position.gain_loss_pct).toFixed(1)}%. Set stop loss at $${stopLoss.toFixed(2)} (-8%) to limit downside.` :
                          isWinning && position.gain_loss_pct > 15 ?
                            `Excellent performance! Consider taking profits or setting trailing stop at $${(position.current_price * 0.95).toFixed(2)} to lock in gains.` :
                          !isWinning && position.gain_loss_pct < -10 ?
                            `Down ${Math.abs(position.gain_loss_pct).toFixed(1)}%. Review fundamentals. Consider cutting if story has changed, or average down if conviction remains strong.` :
                            `Position sized appropriately at ${position.weight.toFixed(1)}%. Monitor for entry/exit opportunities.`
                          }
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Sector Diversification */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
            <h3 className="text-white font-semibold mb-3">Sector Breakdown</h3>
            <div className="space-y-3">
              {analysis.diversification.sector_breakdown.map((sector, idx) => (
                <div key={idx}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-300">{sector.sector}</span>
                    <span className="text-sm font-semibold text-white">{sector.percentage.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-purple-600 to-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${sector.percentage}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Rebalancing Recommendations */}
          {analysis.rebalancing.length > 0 && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
              <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Rebalancing Recommendations
              </h3>
              <div className="space-y-2">
                {analysis.rebalancing.map((rec, idx) => (
                  <div key={idx} className="p-3 bg-slate-900/50 rounded border border-slate-700/50">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-white">{rec.ticker}</span>
                      <span className={`px-2 py-1 rounded text-xs font-semibold border ${getActionColor(rec.action)}`}>
                        {rec.action}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400">{rec.reason}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                      <span>Current: {rec.current_pct.toFixed(1)}%</span>
                      {rec.suggested_pct && <span>Suggested: {rec.suggested_pct.toFixed(1)}%</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Loading State */}
      {analyzePortfolio.isPending && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-slate-400">Analyzing your portfolio...</p>
        </div>
      )}

      {/* Error State */}
      {analyzePortfolio.isError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle className="w-5 h-5" />
            <span>Failed to analyze portfolio. Please try again.</span>
          </div>
        </div>
      )}
        </>
      )}
    </div>
  );
};

export default PortfolioAnalyzer;
