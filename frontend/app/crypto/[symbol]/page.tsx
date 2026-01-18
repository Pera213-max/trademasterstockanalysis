"use client";

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import TradingChart from '@/components/TradingChart';
import NewsBombs from '@/components/NewsBombs';
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Users,
  Bitcoin,
  Globe,
  Layers,
  Target,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Zap,
  Shield,
  Link as LinkIcon,
  AlertCircle,
  Gauge
} from 'lucide-react';

interface CryptoData {
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  changePercent24h: number;
  volume24h: number;
  marketCap: number;
  marketCapRank: number;
  circulatingSupply: number;
  totalSupply: number;
  maxSupply: number | null;
  ath: number;
  athDate: string;
  atl: number;
  atlDate: string;
  category: string;
  description: string;
  website: string;
  blockchain: string;
  consensus: string;
  launchDate: string;
}

interface FearGreedData {
  value: number; // 0-100
  label: string;
  classification: string;
  lastUpdate: Date;
}

interface SentimentData {
  score: number; // -1 to 1
  label: string;
  mentions: {
    total: number;
    reddit: number;
    twitter: number;
    stocktwits: number;
  };
  trending: {
    last24h: number;
    last7d: number;
  };
}

interface OnChainMetrics {
  transactions24h: number;
  activeAddresses24h: number;
  averageTxFee: number;
  hashRate?: number; // For PoW coins
  stakingRate?: number; // For PoS coins
  holders: number;
  whaleConcentration: number;
}

export default function CryptoDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = (params.symbol as string)?.toUpperCase();

  const [cryptoData, setCryptoData] = useState<CryptoData | null>(null);
  const [fearGreed, setFearGreed] = useState<FearGreedData | null>(null);
  const [sentiment, setSentiment] = useState<SentimentData | null>(null);
  const [onChain, setOnChain] = useState<OnChainMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCryptoData = async () => {
      try {
        // TODO: Replace with actual API call
        // const response = await fetch(`/api/crypto/${symbol}`);
        // const data = await response.json();

        // Mock data
        const mockData: CryptoData = {
          symbol: symbol,
          name: getCryptoName(symbol),
          price: getCryptoPrice(symbol),
          change24h: 2850.50,
          changePercent24h: 4.32,
          volume24h: 28500000000,
          marketCap: 1342000000000,
          marketCapRank: 1,
          circulatingSupply: 19650000,
          totalSupply: 21000000,
          maxSupply: 21000000,
          ath: 69000,
          athDate: '2021-11-10',
          atl: 67.81,
          atlDate: '2013-07-06',
          category: 'Cryptocurrency',
          description: getCryptoDescription(symbol),
          website: 'https://bitcoin.org',
          blockchain: getBlockchain(symbol),
          consensus: getConsensus(symbol),
          launchDate: getLaunchDate(symbol),
        };

        const mockFearGreed: FearGreedData = {
          value: 68,
          label: 'Greed',
          classification: 'GREED',
          lastUpdate: new Date(),
        };

        const mockSentiment: SentimentData = {
          score: 0.72,
          label: 'Very Bullish',
          mentions: {
            total: 28450,
            reddit: 15200,
            twitter: 11500,
            stocktwits: 1750,
          },
          trending: {
            last24h: 312.5,
            last7d: 145.8,
          },
        };

        const mockOnChain: OnChainMetrics = {
          transactions24h: 285420,
          activeAddresses24h: 892450,
          averageTxFee: 2.35,
          hashRate: symbol === 'BTC' ? 450.5 : undefined,
          stakingRate: symbol === 'ETH' ? 28.5 : undefined,
          holders: 48250000,
          whaleConcentration: 42.5,
        };

        setCryptoData(mockData);
        setFearGreed(mockFearGreed);
        setSentiment(mockSentiment);
        setOnChain(mockOnChain);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching crypto data:', error);
        setLoading(false);
      }
    };

    if (symbol) {
      fetchCryptoData();
    }
  }, [symbol]);

  const getCryptoName = (symbol: string): string => {
    const names: Record<string, string> = {
      'BTC': 'Bitcoin',
      'ETH': 'Ethereum',
      'BNB': 'Binance Coin',
      'SOL': 'Solana',
      'ADA': 'Cardano',
      'DOGE': 'Dogecoin',
      'MATIC': 'Polygon',
      'DOT': 'Polkadot',
    };
    return names[symbol] || symbol;
  };

  const getCryptoPrice = (symbol: string): number => {
    const prices: Record<string, number> = {
      'BTC': 68500,
      'ETH': 3850,
      'BNB': 585,
      'SOL': 145,
      'ADA': 0.62,
      'DOGE': 0.085,
      'MATIC': 0.92,
      'DOT': 7.45,
    };
    return prices[symbol] || 100;
  };

  const getCryptoDescription = (symbol: string): string => {
    const descriptions: Record<string, string> = {
      'BTC': 'Bitcoin is the first decentralized cryptocurrency, created in 2009. It operates on a peer-to-peer network without central authority.',
      'ETH': 'Ethereum is a decentralized platform for smart contracts and decentralized applications (dApps), powered by its native cryptocurrency Ether.',
      'SOL': 'Solana is a high-performance blockchain supporting builders around the world creating crypto apps that scale.',
    };
    return descriptions[symbol] || 'Leading cryptocurrency with innovative blockchain technology.';
  };

  const getBlockchain = (symbol: string): string => {
    const blockchains: Record<string, string> = {
      'BTC': 'Bitcoin',
      'ETH': 'Ethereum',
      'BNB': 'BNB Chain',
      'SOL': 'Solana',
      'ADA': 'Cardano',
      'DOGE': 'Dogecoin',
      'MATIC': 'Polygon',
      'DOT': 'Polkadot',
    };
    return blockchains[symbol] || 'Custom';
  };

  const getConsensus = (symbol: string): string => {
    const consensus: Record<string, string> = {
      'BTC': 'Proof of Work (PoW)',
      'ETH': 'Proof of Stake (PoS)',
      'BNB': 'Proof of Staked Authority',
      'SOL': 'Proof of History + PoS',
      'ADA': 'Ouroboros PoS',
      'DOGE': 'Proof of Work (PoW)',
    };
    return consensus[symbol] || 'Hybrid';
  };

  const getLaunchDate = (symbol: string): string => {
    const dates: Record<string, string> = {
      'BTC': 'January 2009',
      'ETH': 'July 2015',
      'BNB': 'July 2017',
      'SOL': 'March 2020',
      'ADA': 'September 2017',
      'DOGE': 'December 2013',
    };
    return dates[symbol] || 'Unknown';
  };

  const formatNumber = (num: number): string => {
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    if (num >= 1e3) return `${(num / 1e3).toFixed(2)}K`;
    return num.toString();
  };

  const formatSupply = (num: number): string => {
    if (num >= 1e9) return `${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `${(num / 1e6).toFixed(2)}M`;
    if (num >= 1e3) return `${(num / 1e3).toFixed(2)}K`;
    return num.toFixed(2);
  };

  const getFearGreedColor = (value: number): string => {
    if (value >= 75) return 'text-green-400';
    if (value >= 55) return 'text-yellow-400';
    if (value >= 45) return 'text-orange-400';
    if (value >= 25) return 'text-red-400';
    return 'text-red-600';
  };

  const getFearGreedBg = (value: number): string => {
    if (value >= 75) return 'bg-green-500/20 border-green-500/30';
    if (value >= 55) return 'bg-yellow-500/20 border-yellow-500/30';
    if (value >= 45) return 'bg-orange-500/20 border-orange-500/30';
    if (value >= 25) return 'bg-red-500/20 border-red-500/30';
    return 'bg-red-600/20 border-red-600/30';
  };

  const getFearGreedGradient = (value: number): string => {
    if (value >= 75) return 'from-green-500 to-emerald-500';
    if (value >= 55) return 'from-yellow-500 to-orange-400';
    if (value >= 45) return 'from-orange-500 to-orange-600';
    if (value >= 25) return 'from-red-500 to-red-600';
    return 'from-red-600 to-red-700';
  };

  const getSentimentColor = (score: number): string => {
    if (score > 0.5) return 'text-green-400';
    if (score > 0) return 'text-green-300';
    if (score > -0.5) return 'text-red-300';
    return 'text-red-400';
  };

  const getSentimentBgColor = (score: number): string => {
    if (score > 0.5) return 'bg-green-500/20 border-green-500/30';
    if (score > 0) return 'bg-green-500/10 border-green-500/20';
    if (score > -0.5) return 'bg-red-500/10 border-red-500/20';
    return 'bg-red-500/20 border-red-500/30';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-16 h-16 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading {symbol} data...</p>
        </div>
      </div>
    );
  }

  if (!cryptoData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <p className="text-slate-400">Failed to load crypto data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => router.back()}
              className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              Back
            </button>

            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-sm text-slate-400">Crypto Market</div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-white font-semibold text-sm">24/7 Trading</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Crypto Header */}
          <div className="bg-gradient-to-br from-orange-900/20 via-slate-800/50 to-slate-800/50 backdrop-blur-sm rounded-xl border border-orange-500/20 p-6">
            <div className="flex items-start justify-between flex-wrap gap-4">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-orange-500/20 rounded-lg">
                    <Bitcoin className="w-8 h-8 text-orange-400" />
                  </div>
                  <h1 className="text-4xl font-bold text-white">{symbol}</h1>
                  <span className="px-3 py-1 bg-slate-700/50 text-slate-300 rounded-md text-sm">
                    Rank #{cryptoData.marketCapRank}
                  </span>
                  <span className="px-3 py-1 bg-orange-500/20 text-orange-300 rounded-md text-sm border border-orange-500/30">
                    {cryptoData.category}
                  </span>
                </div>
                <p className="text-xl text-slate-300 mb-1">{cryptoData.name}</p>
                <p className="text-sm text-slate-500">{cryptoData.blockchain} • {cryptoData.consensus}</p>
              </div>

              <div className="text-right">
                <div className="text-5xl font-bold text-white mb-2">
                  ${cryptoData.price.toFixed(cryptoData.price < 1 ? 4 : 2)}
                </div>
                <div className={`flex items-center justify-end gap-2 text-xl ${
                  cryptoData.change24h >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {cryptoData.change24h >= 0 ? (
                    <TrendingUp className="w-6 h-6" />
                  ) : (
                    <TrendingDown className="w-6 h-6" />
                  )}
                  <span>
                    {cryptoData.change24h >= 0 ? '+' : ''}{cryptoData.change24h.toFixed(2)} ({cryptoData.changePercent24h.toFixed(2)}%)
                  </span>
                </div>
                <div className="text-sm text-slate-500 mt-1">24h Change</div>
              </div>
            </div>
          </div>

          {/* Trading Chart - Large */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6" style={{ minHeight: '60vh' }}>
            <TradingChart ticker={symbol} />
          </div>

          {/* Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column - Crypto Info */}
            <div className="space-y-6">
              {/* Market Statistics */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
                <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <DollarSign className="w-6 h-6 text-green-500" />
                  Market Statistics
                </h2>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-slate-900/50 rounded-lg">
                    <span className="text-slate-400">Market Cap</span>
                    <span className="text-white font-semibold">{formatNumber(cryptoData.marketCap)}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-slate-900/50 rounded-lg">
                    <span className="text-slate-400">24h Volume</span>
                    <span className="text-white font-semibold">{formatNumber(cryptoData.volume24h)}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-slate-900/50 rounded-lg">
                    <span className="text-slate-400">Circulating Supply</span>
                    <span className="text-white font-semibold">{formatSupply(cryptoData.circulatingSupply)} {symbol}</span>
                  </div>
                  {cryptoData.maxSupply && (
                    <div className="flex justify-between items-center p-3 bg-slate-900/50 rounded-lg">
                      <span className="text-slate-400">Max Supply</span>
                      <span className="text-white font-semibold">{formatSupply(cryptoData.maxSupply)} {symbol}</span>
                    </div>
                  )}
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-slate-400 text-sm">Supply Progress</span>
                      <span className="text-slate-400 text-sm">
                        {((cryptoData.circulatingSupply / (cryptoData.maxSupply || cryptoData.totalSupply)) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-orange-500 to-orange-400"
                        style={{ width: `${(cryptoData.circulatingSupply / (cryptoData.maxSupply || cryptoData.totalSupply)) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Price Extremes */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
                <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <Target className="w-6 h-6 text-blue-500" />
                  Price Extremes
                </h2>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-slate-400">All-Time High</span>
                      <span className="text-green-400 font-semibold">${cryptoData.ath.toLocaleString()}</span>
                    </div>
                    <div className="text-xs text-slate-500">{new Date(cryptoData.athDate).toLocaleDateString()}</div>
                    <div className="text-sm text-red-400 mt-1">
                      -{((1 - cryptoData.price / cryptoData.ath) * 100).toFixed(1)}% from ATH
                    </div>
                  </div>
                  <div className="border-t border-slate-700 pt-4">
                    <div className="flex justify-between mb-2">
                      <span className="text-slate-400">All-Time Low</span>
                      <span className="text-red-400 font-semibold">${cryptoData.atl.toFixed(2)}</span>
                    </div>
                    <div className="text-xs text-slate-500">{new Date(cryptoData.atlDate).toLocaleDateString()}</div>
                    <div className="text-sm text-green-400 mt-1">
                      +{((cryptoData.price / cryptoData.atl - 1) * 100).toFixed(0)}% from ATL
                    </div>
                  </div>
                </div>
              </div>

              {/* About */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
                <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <Globe className="w-6 h-6 text-purple-500" />
                  About {cryptoData.name}
                </h2>
                <p className="text-slate-300 text-sm leading-relaxed mb-4">{cryptoData.description}</p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-slate-500 mb-1">Launch Date</div>
                    <div className="text-white">{cryptoData.launchDate}</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-500 mb-1">Website</div>
                    <a
                      href={cryptoData.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-sm"
                    >
                      <LinkIcon className="w-3 h-3" />
                      Visit
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column - Fear & Greed + Sentiment */}
            <div className="space-y-6">
              {/* Fear & Greed Index */}
              {fearGreed && (
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
                  <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <Gauge className="w-6 h-6 text-yellow-500" />
                    Fear & Greed Index
                  </h2>

                  <div className={`p-6 rounded-lg border mb-4 ${getFearGreedBg(fearGreed.value)}`}>
                    <div className="text-center mb-4">
                      <div className={`text-6xl font-bold ${getFearGreedColor(fearGreed.value)} mb-2`}>
                        {fearGreed.value}
                      </div>
                      <div className={`text-2xl font-semibold ${getFearGreedColor(fearGreed.value)}`}>
                        {fearGreed.label}
                      </div>
                    </div>

                    {/* Gauge Visualization */}
                    <div className="relative h-3 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`absolute h-full bg-gradient-to-r ${getFearGreedGradient(fearGreed.value)} transition-all`}
                        style={{ width: `${fearGreed.value}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-xs text-slate-500 mt-2">
                      <span>Extreme Fear</span>
                      <span>Neutral</span>
                      <span>Extreme Greed</span>
                    </div>
                  </div>

                  <div className="text-sm text-slate-400 space-y-2">
                    <p>The Fear & Greed Index measures market sentiment from 0 (Extreme Fear) to 100 (Extreme Greed).</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2 bg-red-500/10 rounded">0-25: Extreme Fear</div>
                      <div className="p-2 bg-orange-500/10 rounded">25-45: Fear</div>
                      <div className="p-2 bg-yellow-500/10 rounded">45-55: Neutral</div>
                      <div className="p-2 bg-green-500/10 rounded">55-100: Greed</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Social Sentiment */}
              {sentiment && (
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
                  <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <MessageSquare className="w-6 h-6 text-cyan-500" />
                    Social Sentiment
                  </h2>

                  <div className={`p-6 rounded-lg border mb-4 ${getSentimentBgColor(sentiment.score)}`}>
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <div className="text-sm text-slate-400 mb-1">Overall Sentiment</div>
                        <div className={`text-3xl font-bold ${getSentimentColor(sentiment.score)}`}>
                          {sentiment.label}
                        </div>
                      </div>
                      {sentiment.score >= 0 ? (
                        <ThumbsUp className={`w-12 h-12 ${getSentimentColor(sentiment.score)}`} />
                      ) : (
                        <ThumbsDown className={`w-12 h-12 ${getSentimentColor(sentiment.score)}`} />
                      )}
                    </div>

                    <div className="relative h-4 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`absolute h-full ${sentiment.score >= 0 ? 'bg-green-500' : 'bg-red-500'}`}
                        style={{
                          width: `${Math.abs(sentiment.score) * 100}%`,
                          left: sentiment.score >= 0 ? '50%' : `${50 - Math.abs(sentiment.score) * 50}%`
                        }}
                      ></div>
                      <div className="absolute left-1/2 top-0 h-full w-px bg-white/50"></div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                      <span className="text-slate-400">Total Mentions</span>
                      <span className="text-white font-semibold">{sentiment.mentions.total.toLocaleString()}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="p-3 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                        <div className="text-xs text-orange-400 mb-1">Reddit</div>
                        <div className="text-white font-semibold">{formatNumber(sentiment.mentions.reddit)}</div>
                      </div>
                      <div className="p-3 bg-sky-500/10 border border-sky-500/30 rounded-lg">
                        <div className="text-xs text-sky-400 mb-1">Twitter</div>
                        <div className="text-white font-semibold">{formatNumber(sentiment.mentions.twitter)}</div>
                      </div>
                      <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
                        <div className="text-xs text-green-400 mb-1">StockTwits</div>
                        <div className="text-white font-semibold">{formatNumber(sentiment.mentions.stocktwits)}</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* On-Chain Metrics */}
          {onChain && (
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Layers className="w-6 h-6 text-purple-500" />
                On-Chain Metrics
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-5 h-5 text-yellow-400" />
                    <span className="text-slate-400">Transactions 24h</span>
                  </div>
                  <div className="text-2xl font-bold text-white">{onChain.transactions24h.toLocaleString()}</div>
                  <div className="text-sm text-green-400 mt-1">+12.5% vs avg</div>
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Users className="w-5 h-5 text-blue-400" />
                    <span className="text-slate-400">Active Addresses</span>
                  </div>
                  <div className="text-2xl font-bold text-white">{onChain.activeAddresses24h.toLocaleString()}</div>
                  <div className="text-sm text-green-400 mt-1">+8.2% vs avg</div>
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign className="w-5 h-5 text-green-400" />
                    <span className="text-slate-400">Avg Tx Fee</span>
                  </div>
                  <div className="text-2xl font-bold text-white">${onChain.averageTxFee.toFixed(2)}</div>
                  <div className="text-sm text-red-400 mt-1">-15.3% vs avg</div>
                </div>

                {onChain.hashRate && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Shield className="w-5 h-5 text-orange-400" />
                      <span className="text-slate-400">Hash Rate</span>
                    </div>
                    <div className="text-2xl font-bold text-white">{onChain.hashRate} EH/s</div>
                    <div className="text-sm text-green-400 mt-1">All-time high</div>
                  </div>
                )}

                {onChain.stakingRate && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Target className="w-5 h-5 text-purple-400" />
                      <span className="text-slate-400">Staking Rate</span>
                    </div>
                    <div className="text-2xl font-bold text-white">{onChain.stakingRate}%</div>
                    <div className="text-sm text-slate-400 mt-1">of supply staked</div>
                  </div>
                )}

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Users className="w-5 h-5 text-cyan-400" />
                    <span className="text-slate-400">Total Holders</span>
                  </div>
                  <div className="text-2xl font-bold text-white">{formatNumber(onChain.holders)}</div>
                  <div className="text-sm text-green-400 mt-1">Growing</div>
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Activity className="w-5 h-5 text-red-400" />
                    <span className="text-slate-400">Whale Concentration</span>
                  </div>
                  <div className="text-2xl font-bold text-white">{onChain.whaleConcentration}%</div>
                  <div className="text-sm text-yellow-400 mt-1">Top 100 addresses</div>
                </div>
              </div>
            </div>
          )}

          {/* News Section */}
          <div>
            <NewsBombs maxItems={5} />
          </div>
        </div>
      </main>
    </div>
  );
}
