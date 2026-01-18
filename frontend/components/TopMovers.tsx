"use client";

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Activity, Loader2, AlertCircle } from 'lucide-react';
import { getStockMovers, getCryptoMovers, formatPrice, formatPercent, type Mover } from '@/lib/api';

const TopMovers: React.FC = () => {
  const [tab, setTab] = useState<'stocks' | 'crypto'>('stocks');

  // Fetch stock movers
  const stocksQuery = useQuery({
    queryKey: ['stock-movers'],
    queryFn: getStockMovers,
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: tab === 'stocks',
  });

  // Fetch crypto movers
  const cryptoQuery = useQuery({
    queryKey: ['crypto-movers'],
    queryFn: getCryptoMovers,
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: tab === 'crypto',
  });

  const query = tab === 'stocks' ? stocksQuery : cryptoQuery;
  const { data, isLoading, error } = query;
  const formatVolume = (volume: number): string => {
    if (volume >= 1e9) return `${(volume / 1e9).toFixed(2)}B`;
    if (volume >= 1e6) return `${(volume / 1e6).toFixed(2)}M`;
    if (volume >= 1e3) return `${(volume / 1e3).toFixed(2)}K`;
    return volume.toString();
  };

  const formatPriceValue = (price: number): string => {
    return price >= 1 ? price.toFixed(2) : price.toFixed(4);
  };

  const MoverCard = ({ mover, isGainer }: { mover: Mover; isGainer: boolean }) => (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-lg p-4 border border-slate-700/50 hover:border-slate-600 transition-all hover:shadow-lg hover:shadow-slate-900/50 group cursor-pointer">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white text-lg">{mover.ticker}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              mover.type === 'crypto'
                ? 'bg-purple-500/20 text-purple-300'
                : 'bg-blue-500/20 text-blue-300'
            }`}>
              {mover.type === 'crypto' ? 'CRYPTO' : 'STOCK'}
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1 truncate">{mover.name}</p>
        </div>
        {isGainer ? (
          <TrendingUp className="text-green-500 w-6 h-6 group-hover:scale-110 transition-transform" />
        ) : (
          <TrendingDown className="text-red-500 w-6 h-6 group-hover:scale-110 transition-transform" />
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-baseline justify-between">
          <span className="text-2xl font-bold text-white">
            ${formatPriceValue(mover.price)}
          </span>
          <div className="text-right">
            <div className={`text-lg font-semibold ${isGainer ? 'text-green-500' : 'text-red-500'}`}>
              {formatPercent(mover.changePercent)}
            </div>
            <div className={`text-sm ${isGainer ? 'text-green-400/70' : 'text-red-400/70'}`}>
              {mover.change >= 0 ? '+' : ''}${Math.abs(mover.change).toFixed(2)}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 pt-2 border-t border-slate-700/50">
          <Activity className="w-4 h-4 text-slate-500" />
          <span className="text-slate-400 text-sm">Volume:</span>
          <span className="text-slate-300 text-sm font-medium ml-auto">
            {formatVolume(mover.volume)}
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <TrendingUp className="w-7 h-7 text-green-500" />
          Most Interesting Moves
        </h2>

        {/* Tab Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setTab('stocks')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === 'stocks'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
            }`}
          >
            Stocks
          </button>
          <button
            onClick={() => setTab('crypto')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === 'crypto'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
            }`}
          >
            Crypto
          </button>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <Loader2 className="w-10 h-10 animate-spin text-blue-600" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-6 h-6 text-red-400" />
            <div>
              <h3 className="font-semibold text-red-300">Error loading movers</h3>
              <p className="text-sm text-red-400">
                {error instanceof Error ? error.message : 'Failed to fetch data'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Data */}
      {data && !isLoading && (
        <>
          {/* Gainers Section */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="h-1 w-12 bg-gradient-to-r from-green-500 to-green-400 rounded-full"></div>
              <h3 className="text-xl font-semibold text-green-400">Notable Gainers</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {data.data.gainers.slice(0, 5).map((mover: Mover) => (
                <MoverCard key={mover.ticker} mover={mover} isGainer={true} />
              ))}
            </div>
          </div>

          {/* Losers Section */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="h-1 w-12 bg-gradient-to-r from-red-500 to-red-400 rounded-full"></div>
              <h3 className="text-xl font-semibold text-red-400">Notable Decliners</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {data.data.losers.slice(0, 5).map((mover: Mover) => (
                <MoverCard key={mover.ticker} mover={mover} isGainer={false} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default TopMovers;
