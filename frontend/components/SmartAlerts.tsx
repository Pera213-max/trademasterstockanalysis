"use client";

import React, { useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Bell, TrendingUp, TrendingDown, Volume2, Newspaper, Target,
  AlertTriangle, CheckCircle, Info, ArrowUpRight, ArrowDownRight, Zap
} from 'lucide-react';

import {
  addWatchlistItem,
  getSmartAlerts,
  getUniverseAlerts,
  getWatchlist,
  getWatchlistAlerts,
  loginUser,
  registerUser,
  removeWatchlistItem,
} from '@/lib/api';
import {
  clearAuthToken,
  clearStoredUser,
  getAuthToken,
  getStoredUser,
  setAuthToken,
  setStoredUser,
  type AuthUser,
} from '@/lib/auth';

const WATCHLIST_KEY = 'tm_watchlist';
const DEFAULT_WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'MSFT'];

const normalizeWatchlist = (items: string[]) => {
  const normalized = items
    .map((ticker) => ticker.trim().toUpperCase())
    .filter(Boolean);
  return Array.from(new Set(normalized));
};

interface Alert {
  type: string;
  severity: string;
  ticker: string;
  message: string;
  price?: number;
  change?: number;
  change_pct?: number;
  volume?: number;
  avg_volume?: number;
  headline?: string;
  timestamp: string;
}

type AlertScope = 'universe' | 'watchlist';

const SmartAlerts: React.FC = () => {
  const [watchlist, setWatchlist] = useState<string[]>(DEFAULT_WATCHLIST);
  const [newTicker, setNewTicker] = useState('');
  const [watchlistReady, setWatchlistReady] = useState(false);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [watchlistBusy, setWatchlistBusy] = useState(false);
  const [alertScope, setAlertScope] = useState<AlertScope>('universe');
  const [authToken, setAuthTokenState] = useState<string | null>(null);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authUsername, setAuthUsername] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const lastAutoScanKey = useRef<string | null>(null);

  const loadLocalWatchlist = () => {
    const storedList = localStorage.getItem(WATCHLIST_KEY);
    if (storedList) {
      try {
        const parsed = JSON.parse(storedList);
        if (Array.isArray(parsed)) {
          setWatchlist(normalizeWatchlist(parsed));
          setWatchlistReady(true);
          return;
        }
      } catch {
        // Ignore malformed watchlist values.
      }
    }
    setWatchlist(DEFAULT_WATCHLIST);
    setWatchlistReady(true);
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const token = getAuthToken();
    const storedUser = getStoredUser();
    if (token) {
      setAuthTokenState(token);
    }
    if (storedUser) {
      setAuthUser(storedUser);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    let cancelled = false;
    setWatchlistReady(false);
    setWatchlistError(null);

    if (!authToken) {
      loadLocalWatchlist();
      return;
    }

    const loadWatchlist = async () => {
      try {
        const response = await getWatchlist();
        if (cancelled) return;
        const items = response.data.items || [];
        setWatchlist(items.map((item) => item.ticker));
        setWatchlistReady(true);
      } catch {
        if (cancelled) return;
        clearAuthToken();
        clearStoredUser();
        setAuthTokenState(null);
        setAuthUser(null);
        loadLocalWatchlist();
      }
    };

    loadWatchlist();
    return () => {
      cancelled = true;
    };
  }, [authToken]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!watchlistReady) return;
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(watchlist));
  }, [watchlist, watchlistReady]);

  // Get alerts mutation
  const getAlerts = useMutation({
    mutationFn: async ({ scope, tickers }: { scope: AlertScope; tickers: string[] }) => {
      if (scope === 'universe') {
        return getUniverseAlerts();
      }
      const token = getAuthToken();
      if (token) {
        return getWatchlistAlerts();
      }
      return getSmartAlerts(tickers);
    },
  });

  useEffect(() => {
    if (!watchlistReady) return;
    if (alertScope === 'watchlist' && watchlist.length === 0) return;
    const watchlistKey = watchlist.join(',');
    const autoScanKey = `${alertScope}:${alertScope === 'watchlist' ? watchlistKey : 'all'}`;
    if (lastAutoScanKey.current === autoScanKey) return;
    lastAutoScanKey.current = autoScanKey;
    getAlerts.mutate({ scope: alertScope, tickers: watchlist });
  }, [alertScope, watchlist, watchlistReady, getAlerts]);

  const alertPayload = getAlerts.data?.data as { alerts: Alert[]; total_scanned?: number } | undefined;
  const alerts = alertPayload?.alerts as Alert[] | undefined;
  const universeTotal = alertPayload?.total_scanned as number | undefined;
  const scanLabel = alertScope === 'universe'
    ? (universeTotal ? `${universeTotal} stocks` : 'program universe')
    : `${watchlist.length} stocks`;
  const noAlertScopeLabel = alertScope === 'universe' ? 'program universe' : 'watchlist';

  const handleScan = () => {
    getAlerts.mutate({ scope: alertScope, tickers: watchlist });
  };

  const handleAuthSubmit = async () => {
    if (!authEmail || !authPassword) {
      setAuthError('Email and password are required.');
      return;
    }
    if (authMode === 'register' && authPassword.length < 8) {
      setAuthError('Password must be at least 8 characters.');
      return;
    }
    setAuthError(null);
    setAuthBusy(true);
    try {
      const response = authMode === 'login'
        ? await loginUser(authEmail, authPassword)
        : await registerUser(authEmail, authPassword, authUsername || undefined);
      const payload = response.data;
      setAuthToken(payload.token);
      setStoredUser(payload.user);
      setAuthTokenState(payload.token);
      setAuthUser(payload.user);
      setAuthPassword('');
    } catch {
      setAuthError('Authentication failed. Check your credentials.');
    } finally {
      setAuthBusy(false);
    }
  };

  const handleLogout = () => {
    clearAuthToken();
    clearStoredUser();
    setAuthTokenState(null);
    setAuthUser(null);
  };

  const handleAddTicker = async () => {
    const trimmed = newTicker.trim().toUpperCase();
    if (!trimmed) return;
    setWatchlistError(null);
    setWatchlistBusy(true);
    try {
      if (authToken) {
        await addWatchlistItem(trimmed);
      }
      const nextList = normalizeWatchlist([...watchlist, trimmed]);
      setWatchlist(nextList);
      setNewTicker('');
    } catch {
      setWatchlistError('Failed to add ticker to watchlist.');
    } finally {
      setWatchlistBusy(false);
    }
  };

  const handleRemoveTicker = async (ticker: string) => {
    setWatchlistError(null);
    setWatchlistBusy(true);
    try {
      if (authToken) {
        await removeWatchlistItem(ticker);
      }
      setWatchlist(watchlist.filter(t => t !== ticker));
    } catch {
      setWatchlistError('Failed to remove ticker from watchlist.');
    } finally {
      setWatchlistBusy(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      'HIGH': 'bg-red-500/20 text-red-300 border-red-500/50',
      'MEDIUM': 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50',
      'LOW': 'bg-blue-500/20 text-blue-300 border-blue-500/50',
    };
    return colors[severity] || 'bg-slate-500/20 text-slate-300 border-slate-500/50';
  };

  const getAlertIcon = (type: string) => {
    const icons: Record<string, React.ReactNode> = {
      'PRICE_SPIKE': <TrendingUp className="w-5 h-5" />,
      'PRICE_DROP': <TrendingDown className="w-5 h-5" />,
      'VOLUME_SPIKE': <Volume2 className="w-5 h-5" />,
      'NEWS_IMPACT': <Newspaper className="w-5 h-5" />,
      '52W_HIGH': <ArrowUpRight className="w-5 h-5" />,
      '52W_LOW': <ArrowDownRight className="w-5 h-5" />,
      'TECHNICAL_BREAKOUT': <ArrowUpRight className="w-5 h-5" />,
      'TECHNICAL_OVERSOLD': <ArrowDownRight className="w-5 h-5" />,
    };
    return icons[type] || <Bell className="w-5 h-5" />;
  };

  const getAlertColor = (type: string) => {
    const colors: Record<string, string> = {
      'PRICE_SPIKE': 'text-green-400',
      'PRICE_DROP': 'text-red-400',
      'VOLUME_SPIKE': 'text-purple-400',
      'NEWS_IMPACT': 'text-blue-400',
      '52W_HIGH': 'text-green-400',
      '52W_LOW': 'text-red-400',
      'TECHNICAL_BREAKOUT': 'text-green-400',
      'TECHNICAL_OVERSOLD': 'text-red-400',
    };
    return colors[type] || 'text-slate-400';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-yellow-600/20 rounded-lg relative">
            <Bell className="w-7 h-7 text-yellow-400" />
            {alerts && alerts.length > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs text-white flex items-center justify-center font-bold">
                {alerts.length}
              </span>
            )}
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Smart Alerts</h2>
            <p className="text-sm text-slate-400">AI-powered market anomaly detection</p>
          </div>
        </div>
        <button
          onClick={handleScan}
          disabled={getAlerts.isPending || (alertScope === 'watchlist' && watchlist.length === 0)}
          className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-2 transition-colors"
        >
          <Zap className="w-4 h-4" />
          {getAlerts.isPending
            ? 'Scanning...'
            : alertScope === 'universe'
              ? 'Scan Universe'
              : 'Scan Watchlist'}
        </button>
      </div>

      <div className="flex items-center gap-2 text-xs">
        <span className="text-slate-400">Scope:</span>
        <div className="flex items-center gap-1 bg-slate-900/60 border border-slate-700 rounded-full p-1">
          <button
            onClick={() => setAlertScope('universe')}
            className={`px-3 py-1 rounded-full transition ${
              alertScope === 'universe'
                ? 'bg-blue-600 text-white'
                : 'text-slate-300 hover:text-white'
            }`}
          >
            Program Universe
          </button>
          <button
            onClick={() => setAlertScope('watchlist')}
            className={`px-3 py-1 rounded-full transition ${
              alertScope === 'watchlist'
                ? 'bg-blue-600 text-white'
                : 'text-slate-300 hover:text-white'
            }`}
          >
            Watchlist
          </button>
        </div>
      </div>

      {/* Watchlist Management */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h3 className="text-white font-semibold">Watchlist ({watchlist.length})</h3>
            <p className="text-xs text-slate-400">
              {authToken ? 'Synced to your account' : 'Stored locally in this browser'}
            </p>
            {alertScope === 'universe' && (
              <p className="text-xs text-slate-500 mt-1">
                Universe scan covers {scanLabel}. Switch to Watchlist to scan only your picks.
              </p>
            )}
          </div>
          {authToken && (
            <button
              onClick={handleLogout}
              className="text-xs text-slate-300 hover:text-white border border-slate-600 rounded px-2 py-1"
            >
              Sign out
            </button>
          )}
        </div>

        {authToken && authUser && (
          <div className="mb-3 text-xs text-slate-300">
            Signed in as {authUser.email}
          </div>
        )}

        {!authToken && (
          <div className="mb-4 bg-slate-900/60 border border-slate-700 rounded-lg p-3">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h4 className="text-sm font-semibold text-white">
                  {authMode === 'login' ? 'Sign in to sync' : 'Create an account'}
                </h4>
                <p className="text-xs text-slate-400">
                  {authMode === 'login'
                    ? 'Save watchlists and alerts across devices.'
                    : 'Use an email and password to enable sync.'}
                </p>
              </div>
              <button
                onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
                className="text-xs text-blue-300 hover:text-blue-200"
              >
                {authMode === 'login' ? 'Create account' : 'Use existing'}
              </button>
            </div>

            {authMode === 'register' && (
              <input
                type="text"
                placeholder="Username (optional)"
                value={authUsername}
                onChange={(e) => setAuthUsername(e.target.value)}
                className="w-full px-3 py-2 mb-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
              />
            )}
            <input
              type="email"
              placeholder="Email"
              value={authEmail}
              onChange={(e) => setAuthEmail(e.target.value)}
              className="w-full px-3 py-2 mb-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
            />
            <input
              type="password"
              placeholder="Password"
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
              className="w-full px-3 py-2 mb-3 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
            />
            <button
              onClick={handleAuthSubmit}
              disabled={authBusy}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 text-white rounded transition-colors"
            >
              {authBusy ? 'Please wait...' : authMode === 'login' ? 'Sign in' : 'Create account'}
            </button>
            {authError && (
              <p className="text-xs text-red-300 mt-2">{authError}</p>
            )}
          </div>
        )}

        {/* Add Ticker */}
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            placeholder="Add ticker (e.g., AAPL)"
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === 'Enter' && handleAddTicker()}
            className="flex-1 px-3 py-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
            disabled={watchlistBusy}
          />
          <button
            onClick={handleAddTicker}
            disabled={watchlistBusy}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 text-white rounded transition-colors"
          >
            {watchlistBusy ? '...' : 'Add'}
          </button>
        </div>
        {watchlistError && (
          <p className="text-xs text-red-300 mb-3">{watchlistError}</p>
        )}

        {/* Ticker List */}
        <div className="flex flex-wrap gap-2">
          {watchlist.map((ticker) => (
            <div
              key={ticker}
              className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-full flex items-center gap-2 group"
            >
              <span className="text-white font-semibold">{ticker}</span>
              <button
                onClick={() => handleRemoveTicker(ticker)}
                disabled={watchlistBusy}
                className="text-slate-400 hover:text-red-400 transition-colors"
              >
                x
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Alert Types Legend */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { type: 'PRICE_SPIKE', label: 'Price Spike', icon: TrendingUp, color: 'text-green-400' },
          { type: 'PRICE_DROP', label: 'Price Drop', icon: TrendingDown, color: 'text-red-400' },
          { type: 'VOLUME_SPIKE', label: 'Volume Surge', icon: Volume2, color: 'text-purple-400' },
          { type: 'NEWS_IMPACT', label: 'Major News', icon: Newspaper, color: 'text-blue-400' },
          { type: '52W_HIGH', label: '52W High', icon: ArrowUpRight, color: 'text-green-400' },
          { type: '52W_LOW', label: '52W Low', icon: ArrowDownRight, color: 'text-red-400' },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.type} className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
              <Icon className={`w-4 h-4 ${item.color} mb-1`} />
              <div className="text-xs text-slate-300">{item.label}</div>
            </div>
          );
        })}
      </div>

      {/* Alerts List */}
      {alerts && alerts.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-white font-semibold flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
            Active Alerts ({alerts.length})
          </h3>

          {alerts.map((alert, idx) => (
            <div
              key={idx}
              className={`bg-slate-800/50 border rounded-lg p-4 ${getSeverityColor(alert.severity)}`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-3">
                  <div className={getAlertColor(alert.type)}>
                    {getAlertIcon(alert.type)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-lg">{alert.ticker}</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${getSeverityColor(alert.severity)}`}>
                        {alert.severity}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>

                {alert.price && (
                  <div className="text-right">
                    <div className="text-white font-bold">${alert.price.toFixed(2)}</div>
                    {alert.change_pct !== undefined && (
                      <div className={`text-sm font-semibold ${alert.change_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {alert.change_pct >= 0 ? '+' : ''}{alert.change_pct.toFixed(2)}%
                      </div>
                    )}
                  </div>
                )}
              </div>

              <p className="text-slate-300 mb-3">{alert.message}</p>

              {alert.headline && (
                <div className="bg-slate-900/50 rounded p-2 border border-slate-700/50">
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <Newspaper className="w-3 h-3" />
                    <span className="text-slate-300">{alert.headline}</span>
                  </div>
                </div>
              )}

              {alert.volume && alert.avg_volume && (
                <div className="flex items-center gap-4 mt-3 text-xs text-slate-400">
                  <div>
                    <span className="text-slate-500">Volume:</span> {(alert.volume / 1000000).toFixed(2)}M
                  </div>
                  <div>
                    <span className="text-slate-500">Avg:</span> {(alert.avg_volume / 1000000).toFixed(2)}M
                  </div>
                  <div>
                    <span className="text-slate-500">Ratio:</span> {(alert.volume / alert.avg_volume).toFixed(1)}x
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* No Alerts */}
      {alerts && alerts.length === 0 && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-6 text-center">
          <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-3" />
          <h3 className="text-white font-semibold mb-1">All Clear!</h3>
          <p className="text-slate-400 text-sm">No unusual activity detected in your {noAlertScopeLabel}</p>
        </div>
      )}

      {/* Loading State */}
      {getAlerts.isPending && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-600 mx-auto mb-4"></div>
          <p className="text-slate-400">Scanning {scanLabel} for unusual activity...</p>
        </div>
      )}

      {/* Error State */}
      {getAlerts.isError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle className="w-5 h-5" />
            <span>Failed to scan for alerts. Please try again.</span>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-400 mt-0.5" />
          <div>
            <h4 className="text-blue-300 font-semibold mb-1">How Smart Alerts Work</h4>
            <p className="text-sm text-blue-200/80">
              {alertScope === 'universe'
                ? 'Our AI scans the full program universe for:'
                : 'Our AI monitors your watchlist for:'}
              <span className="block mt-1">- Price spikes &gt;5% (unusual movements)</span>
              <span className="block">- Volume surges &gt;2x average (increased interest)</span>
              {alertScope === 'watchlist' && (
                <span className="block">- Breaking news with major impact</span>
              )}
              <span className="block">- 52-week highs/lows (key technical levels)</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SmartAlerts;
