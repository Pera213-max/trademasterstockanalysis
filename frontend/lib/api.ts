/**
 * API Client for OsakedataX
 * Central location for all API calls to the backend
 */

import { getAuthToken } from './auth';

const DEFAULT_API_PORT = '8000';
const FALLBACK_API_BASE_URL = `http://localhost:${DEFAULT_API_PORT}`;
const LONG_REQUEST_TIMEOUT_MS = 2 * 60 * 60 * 1000;

const normalizeApiBaseUrl = (value: string) => {
  const trimmed = value.trim().replace(/\/+$/, '');
  return trimmed.endsWith('/api') ? trimmed.slice(0, -4) : trimmed;
};

const resolveEnvApiBaseUrl = () => {
  const envBaseUrl = process.env.NEXT_PUBLIC_API_URL;
  const trimmed = envBaseUrl ? envBaseUrl.trim() : '';
  return trimmed ? normalizeApiBaseUrl(trimmed) : undefined;
};

const resolveApiPort = (value?: string) => {
  if (!value) return DEFAULT_API_PORT;
  try {
    return new URL(value).port || DEFAULT_API_PORT;
  } catch {
    return DEFAULT_API_PORT;
  }
};

const isLocalhostHost = (value: string) => value === 'localhost' || value === '127.0.0.1';

export const getApiBaseUrl = () => {
  const envBaseUrl = resolveEnvApiBaseUrl();
  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location;
    if (!envBaseUrl) {
      if (isLocalhostHost(hostname)) {
        return `${protocol}//${hostname}:${DEFAULT_API_PORT}`;
      }
      return port ? `${protocol}//${hostname}:${port}` : `${protocol}//${hostname}`;
    }
    const normalizedEnv = normalizeApiBaseUrl(envBaseUrl);
    const envIsLocal = normalizedEnv.includes('localhost') || normalizedEnv.includes('127.0.0.1');
    if (envIsLocal && !isLocalhostHost(hostname)) {
      return port ? `${protocol}//${hostname}:${port}` : `${protocol}//${hostname}`;
    }
    return normalizedEnv;
  }
  return envBaseUrl || FALLBACK_API_BASE_URL;
};

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  cached?: boolean;
}

export interface AuthUser {
  id: number;
  email: string;
  username?: string | null;
}

export interface AuthPayload {
  token: string;
  user: AuthUser;
}

type ApiCallOptions = RequestInit & { timeoutMs?: number };

// Helper function for API calls
async function apiCall<T>(endpoint: string, options: ApiCallOptions = {}): Promise<T> {
  const authToken = getAuthToken();
  const { timeoutMs, ...fetchOptions } = options;
  const shouldTimeout = Boolean(timeoutMs) && !fetchOptions.signal;
  const controller = shouldTimeout ? new AbortController() : null;
  const signal = fetchOptions.signal ?? controller?.signal;
  const timeoutId = shouldTimeout
    ? setTimeout(() => controller?.abort(), timeoutMs)
    : null;

  try {
    const headers = new Headers(fetchOptions.headers);
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    if (authToken) {
      headers.set('Authorization', `Bearer ${authToken}`);
    }

    const response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
      headers,
      ...fetchOptions,
      signal,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface MajorNewsEvent {
  category: string;
  impact: 'LOW' | 'MEDIUM' | 'HIGH' | 'VERY HIGH';
  sentiment: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
  headline: string;
  summary: string;
  source: string;
  url: string;
  timestamp: number;
  date: string;
  reason: string;
}

export interface NewsSummary {
  total_major_events: number;
  category_breakdown: Record<string, number>;
  most_impactful_event: MajorNewsEvent | null;
  recent_events: MajorNewsEvent[];
}

export interface AiScoreBreakdown {
  recommendations: number;
  financials: number;
  market_position: number;
  news_activity: number;
}

export interface StockPick {
  rank: number;
  ticker: string;
  name?: string;
  company?: string;
  sector?: string;
  currentPrice: number;
  targetPrice: number;
  potentialReturn: number;
  confidence: number;
  timeHorizon: 'DAY' | 'SWING' | 'LONG';
  reasoning: string;
  signals: string[];
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  breakdown?: AiScoreBreakdown | BaseScoreBreakdown;
  major_news?: MajorNewsEvent[];
  news_summary?: NewsSummary;
}

export interface Fundamentals {
  marketCap?: number;
  peRatio?: number;
  forwardPE?: number;
  dividendYield?: number;
  dividendAmount?: number;
  eps?: number;
  beta?: number;
  revenue?: number;
  profitMargin?: number;
  debtToEquity?: number;
  roe?: number;
  roic?: number;
  bookValue?: number;
  priceToBook?: number;
  revenueGrowth?: number;
  earningsGrowth?: number;
  evEbit?: number;
  evEbitda?: number;
  enterpriseValue?: number;
}

export interface FiRankedStock {
  ticker: string;
  name: string;
  sector: string;
  score: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  price: number;
  change: number;
  return3m: number | null;
  return12m: number | null;
  volatility: number | null;
  peRatio?: number | null;
  pbRatio?: number | null;
  dividendYield?: number | null;
  dividendAmount?: number | null;
  evEbit?: number | null;
  roic?: number | null;
  beta?: number | null;
  marketCap?: number | null;
}

export interface BaseScoreBreakdown {
  technical: number;
  momentum: number;
  volume: number;
  trend: number;
}

export interface EnhancedScoreBreakdown extends BaseScoreBreakdown {
  hidden_gem: number;
  smart_money: number;
  quick_win: number;
}

export interface SectorPick extends StockPick {
  sector: string;
  theme: string;
  breakdown?: BaseScoreBreakdown;
  scoreBreakdown?: BaseScoreBreakdown;
  fundamentals?: Fundamentals;
}

export type Sector = 'tech' | 'energy' | 'healthcare' | 'finance' | 'consumer';
export type Theme = 'growth' | 'value' | 'esg';
export type Timeframe = 'day' | 'swing' | 'long';

export interface Mover {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  type: 'stock' | 'crypto';
}

export interface SocialTrend {
  ticker: string;
  mentions: number;
  sentiment: number;
  platform: string;
  trending: boolean;
}

export interface NewsArticle {
  id: string;
  ticker?: string;
  headline: string;
  summary: string;
  timestamp: string;
  category: string;
  isHot: boolean;
  impact: 'LOW' | 'MEDIUM' | 'HIGH';
  url: string;
  source?: string;
  weight?: number;
}

export interface StockNewsAnalysis {
  ticker: string;
  period_days: number;
  total_articles: number;
  avg_weight: number;
  categories: Record<string, number>;
  newest: NewsArticle[];
  weighted: NewsArticle[];
}

export interface CalendarEvent {
  date: string;
  ticker?: string;
  company?: string;
  eventType: string;
  description: string;
  expectedImpact: string;
  time?: string;
}

export interface MacroIndicator {
  label: string;
  value: number | string;
  change?: number;
  changePercent?: number;
  impact: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
  unit?: string;
}

// ============================================================================
// AUTH API
// ============================================================================

export async function registerUser(email: string, password: string, username?: string) {
  return apiCall<ApiResponse<AuthPayload>>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, username }),
  });
}

export async function loginUser(email: string, password: string) {
  return apiCall<ApiResponse<AuthPayload>>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser() {
  return apiCall<ApiResponse<AuthUser>>('/api/auth/me');
}

export interface WatchlistItem {
  ticker: string;
  type: string;
  notes?: string | null;
  added_at?: string | null;
}

export async function getWatchlist() {
  return apiCall<ApiResponse<{ items: WatchlistItem[] }>>('/api/watchlist');
}

export async function addWatchlistItem(ticker: string, type: string = 'stock', notes?: string) {
  return apiCall<ApiResponse<WatchlistItem>>('/api/watchlist', {
    method: 'POST',
    body: JSON.stringify({ ticker, type, notes }),
  });
}

export async function removeWatchlistItem(ticker: string, type: string = 'stock') {
  const params = new URLSearchParams({ type });
  return apiCall<ApiResponse<{ removed: boolean; ticker: string; type: string }>>(
    `/api/watchlist/${ticker}?${params.toString()}`,
    { method: 'DELETE' },
  );
}

export async function getWatchlistAlerts() {
  return apiCall<ApiResponse<{ total: number; alerts: Alert[] }>>('/api/watchlist/alerts', {
    timeoutMs: 20000,
  });
}

export async function getWatchlistSummary() {
  return apiCall<ApiResponse<any>>('/api/watchlist/summary');
}

// ============================================================================
// STOCKS API
// ============================================================================

export async function getTopStockPicks(
  timeframe: 'day' | 'swing' | 'long' = 'swing',
  forceRefresh: boolean = false
) {
  const params = new URLSearchParams();
  params.append('timeframe', timeframe);
  if (forceRefresh) params.append('force_refresh', 'true');
  return apiCall<ApiResponse<StockPick[]>>(`/api/stocks/top-picks?${params.toString()}`, {
    timeoutMs: LONG_REQUEST_TIMEOUT_MS,
  });
}

export async function getSectorPicks(
  sector?: Sector,
  theme?: Theme,
  timeframe: Timeframe = 'swing',
  limit: number = 5
) {
  const params = new URLSearchParams();
  if (sector) params.append('sector', sector);
  if (theme) params.append('theme', theme);
  params.append('timeframe', timeframe);
  params.append('limit', limit.toString());

  return apiCall<ApiResponse<SectorPick[]>>(`/api/stocks/picks?${params.toString()}`, {
    timeoutMs: LONG_REQUEST_TIMEOUT_MS,
  });
}

export interface HiddenGemPick extends StockPick {
  category: string;
  marketCap: number;
  revenueGrowth: number;
  volumeSurge: boolean;
  breakdown?: EnhancedScoreBreakdown;
  scoreBreakdown?: EnhancedScoreBreakdown;
}

export interface QuickWinPick extends StockPick {
  category: string;
  volumeRatio: number;
  momentum: number;
  breakdown?: EnhancedScoreBreakdown;
  scoreBreakdown?: EnhancedScoreBreakdown;
}

export async function getHiddenGems(
  timeframe: Timeframe = 'swing',
  limit: number = 10,
  forceRefresh: boolean = false
) {
  const params = new URLSearchParams();
  params.append('timeframe', timeframe);
  params.append('limit', limit.toString());
  if (forceRefresh) params.append('force_refresh', 'true');

  return apiCall<ApiResponse<HiddenGemPick[]>>(`/api/stocks/hidden-gems?${params.toString()}`, {
    timeoutMs: LONG_REQUEST_TIMEOUT_MS,
  });
}

export async function getQuickWins(limit: number = 10, forceRefresh: boolean = false) {
  const params = new URLSearchParams();
  params.append('limit', limit.toString());
  if (forceRefresh) params.append('force_refresh', 'true');

  return apiCall<ApiResponse<QuickWinPick[]>>(`/api/stocks/quick-wins?${params.toString()}`, {
    timeoutMs: LONG_REQUEST_TIMEOUT_MS,
  });
}

export async function getStockMovers() {
  return apiCall<ApiResponse<{ gainers: Mover[]; losers: Mover[] }>>('/api/stocks/movers');
}

export async function getStockDetails(ticker: string) {
  return apiCall<ApiResponse<any>>(`/api/stocks/${ticker}`);
}

export async function getStockNews(ticker: string) {
  return apiCall<ApiResponse<NewsArticle[]>>(`/api/stocks/${ticker}/news`);
}

export async function getStockSentiment(ticker: string) {
  return apiCall<ApiResponse<any>>(`/api/stocks/${ticker}/sentiment`);
}

// ============================================================================
// CRYPTO API
// ============================================================================

export async function getCryptoMovers() {
  return apiCall<ApiResponse<{ gainers: Mover[]; losers: Mover[] }>>('/api/crypto/movers');
}

export async function getCryptoDetails(symbol: string) {
  return apiCall<ApiResponse<any>>(`/api/crypto/${symbol}`);
}

// ============================================================================
// SOCIAL API
// ============================================================================

export async function getSocialTrending(limit: number = 10) {
  return apiCall<ApiResponse<SocialTrend[]>>(`/api/social/trending?limit=${limit}`);
}

// ============================================================================
// NEWS API
// ============================================================================

export async function getNewsBombs(limit: number = 20, days: number = 7) {
  return apiCall<ApiResponse<NewsArticle[]>>(`/api/news/bombs?limit=${limit}&days=${days}`);
}

export async function getCategorizedNews(
  sortBy: 'newest' | 'weighted' = 'newest',
  days: number = 7,
  limit: number = 20,
  ticker?: string
) {
  const params = new URLSearchParams({
    sort_by: sortBy,
    days: days.toString(),
    limit: limit.toString(),
  });
  if (ticker) params.append('ticker', ticker);
  return apiCall<ApiResponse<NewsArticle[]>>(`/api/news/categorized?${params}`);
}

export async function getNewestNews(days: number = 7, limit: number = 10) {
  return apiCall<ApiResponse<NewsArticle[]>>(`/api/news/newest?days=${days}&limit=${limit}`);
}

export async function getWeightedNews(days: number = 7, limit: number = 10) {
  return apiCall<ApiResponse<NewsArticle[]>>(`/api/news/weighted?days=${days}&limit=${limit}`);
}

export async function getStockNewsAnalysis(ticker: string, days: number = 7) {
  return apiCall<ApiResponse<StockNewsAnalysis>>(`/api/news/stock/${ticker}?days=${days}`);
}

// ============================================================================
// MACRO API
// ============================================================================

export async function getMacroIndicators() {
  return apiCall<ApiResponse<MacroIndicator[]>>('/api/macro/indicators');
}

export async function getUpcomingEvents(days: number = 30) {
  return apiCall<ApiResponse<CalendarEvent[]>>(`/api/macro/events/upcoming?days=${days}`);
}

// ============================================================================
// PORTFOLIO API
// ============================================================================

export interface PortfolioHolding {
  ticker: string;
  shares: number;
  avgPrice: number;
  currentPrice?: number;
}

export interface PortfolioHealth {
  score: number;
  level: string;
  issues: string[];
}

export interface RiskAnalysis {
  overall_risk: string;
  concentration_risk: number;
  volatility_risk: number;
  unrealized_losses: number;
}

export interface DiversificationScore {
  score: number;
  sector_breakdown: Record<string, number>;
  recommendations: string[];
}

export interface Recommendation {
  ticker: string;
  action: string;
  reasoning: string;
  priority: string;
}

export interface PortfolioAnalysis {
  total_value: number;
  total_cost: number;
  unrealized_pl: number;
  unrealized_pl_pct: number;
  health: PortfolioHealth;
  risk: RiskAnalysis;
  diversification: DiversificationScore;
  positions: Array<{
    ticker: string;
    shares: number;
    avg_price: number;
    current_price: number;
    total_value: number;
    unrealized_pl: number;
    unrealized_pl_pct: number;
    weight: number;
  }>;
  recommendations: Recommendation[];
}

export interface Alert {
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

export interface UniverseAlerts {
  total_scanned: number;
  total_alerts: number;
  alerts: Alert[];
  generated_at: string;
}

export interface ProgramUniverseSummary {
  total_stocks: number;
  sector_breakdown: Array<{
    sector: string;
    count: number;
    percentage: number;
  }>;
  as_of: string;
}

export interface TrackRecord {
  total_picks: number;
  winning_picks: number;
  losing_picks: number;
  win_rate: number;
  avg_return: number;
  performance_level: string;
}

export interface PositionSizeResult {
  recommended_shares: number;
  position_value: number;
  risk_amount: number;
  max_loss_per_share: number;
}

export interface StopLossResult {
  conservative: number;
  moderate: number;
  aggressive: number;
  recommendations: {
    conservative: string;
    moderate: string;
    aggressive: string;
  };
}

export async function analyzePortfolio(holdings: PortfolioHolding[]) {
  return apiCall<ApiResponse<PortfolioAnalysis>>('/api/portfolio/analyze', {
    method: 'POST',
    body: JSON.stringify({ holdings }),
  });
}

export async function getSmartAlerts(tickers: string[]) {
  return apiCall<ApiResponse<{ alerts: Alert[] }>>('/api/portfolio/alerts', {
    method: 'POST',
    body: JSON.stringify({ tickers }),
    timeoutMs: 20000,
  });
}

export async function getUniverseAlerts(limit: number = 20, forceRefresh: boolean = false) {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (forceRefresh) params.append('force_refresh', 'true');
  return apiCall<ApiResponse<UniverseAlerts>>(
    `/api/portfolio/alerts/universe?${params.toString()}`,
    { timeoutMs: 60000 }
  );
}

export async function getProgramUniverseSummary() {
  return apiCall<ApiResponse<ProgramUniverseSummary>>('/api/portfolio/universe/summary');
}

export async function getTrackRecord(trades: Array<{ ticker: string; return: number }>) {
  return apiCall<ApiResponse<TrackRecord>>('/api/portfolio/track-record', {
    method: 'POST',
    body: JSON.stringify({ trades }),
  });
}

export async function calculatePositionSize(params: {
  account_value: number;
  risk_per_trade: number;
  entry_price: number;
  stop_loss_price: number;
}) {
  return apiCall<ApiResponse<PositionSizeResult>>('/api/portfolio/position-size', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function calculateStopLoss(params: {
  entry_price: number;
  account_value: number;
  position_size: number;
}) {
  return apiCall<ApiResponse<StopLossResult>>('/api/portfolio/stop-loss', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

// ============================================================================
// CHART DATA API
// ============================================================================

export interface PriceData {
  time?: number;
  timestamp?: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export async function getPriceHistory(
  ticker: string,
  timeframe: '1d' | '1h' | '15m' = '1d',
  limit: number = 100
) {
  return apiCall<ApiResponse<PriceData[]>>(
    `/api/stocks/chart/${ticker}?timeframe=${timeframe}&limit=${limit}`
  );
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

export function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price);
}

export function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatLargeNumber(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
  return `$${value.toFixed(2)}`;
}

/**
 * Fetch stock data from backend API
 */
export async function fetchStockData(ticker: string) {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/stocks/${ticker}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    // Error handled silently
    throw error;
  }
}

/**
 * Fetch market prices
 */
export async function fetchMarketPrices() {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/market/prices`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    // Error handled silently
    throw error;
  }
}

/**
 * Fetch market trends
 */
export async function fetchMarketTrends() {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/market/trends`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    // Error handled silently
    throw error;
  }
}

/**
 * Fetch AI predictions
 */
export async function fetchPredictions() {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/analytics/predictions`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    // Error handled silently
    throw error;
  }
}

/**
 * Fetch portfolio data
 */
export async function fetchPortfolio() {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/portfolio`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    // Error handled silently
    throw error;
  }
}

/**
 * Create a new trade
 */
export async function createTrade(tradeData: any) {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/trades`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(tradeData),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    // Error handled silently
    throw error;
  }
}

/**
 * Fetch crypto data from backend API
 */
export async function fetchCryptoData(symbol: string) {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/crypto/${symbol}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    // Error handled silently
    throw error;
  }
}

/**
 * Fetch crypto market data
 */
export async function fetchCryptoMarket() {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/crypto/market`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    // Error handled silently
    throw error;
  }
}

/**
 * Fetch Fear & Greed Index
 */
export async function fetchFearGreedIndex() {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/crypto/fear-greed`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    // Error handled silently
    throw error;
  }
}

// ============================================================================
// FINLAND (NASDAQ HELSINKI) API
// ============================================================================

export interface FiStock {
  ticker: string;
  name: string;
  sector: string;
  newsUrl?: string;
}

export interface FiQuote {
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
  previousClose: number;
  high: number;
  low: number;
  open: number;
  currency: string;
  exchange: string;
  timestamp: string;
}

export interface FiHistoryPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface FiMetrics {
  volatility: number | null;
  maxDrawdown: number | null;
  sharpeRatio: number | null;
  return3m: number | null;
  return12m: number | null;
}

export interface FiFundamentals {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  exchange: string;
  currency: string;
  marketCap: number;
  peRatio: number | null;
  forwardPE: number | null;
  pegRatio: number | null;
  priceToBook: number | null;
  dividendYield: number | null;
  profitMargins: number | null;
  revenueGrowth: number | null;
  earningsGrowth: number | null;
  returnOnEquity: number | null;
  returnOnAssets: number | null;
  roic: number | null;
  debtToEquity: number | null;
  beta: number | null;
  fiftyTwoWeekHigh: number | null;
  fiftyTwoWeekLow: number | null;
  averageVolume: number | null;
  enterpriseValue: number | null;
  ebit: number | null;
  evEbit: number | null;
  timestamp: string;
}

export interface FiScoreComponents {
  momentum: number;
  risk: number;
  fundamentals: number;
}

export interface FiNewsEvent {
  id: number;
  ticker?: string | null;
  company?: string | null;
  event_type: string;
  title: string;
  summary?: string | null;
  source?: string | null;
  source_url?: string | null;
  published_at?: string | null;
  impact?: string | null;
  sentiment?: string | null;
  analysis?: any;
}

export interface FiEventSummary {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  mixed: number;
  last_updated: string;
}

export interface FiInsight {
  id: number;
  ticker: string;
  insight_type: string;
  title: string;
  summary?: string | null;
  bullets?: string[];
  impact?: string | null;
  sentiment?: string | null;
  key_metrics?: Array<{ label: string; value: string; unit?: string }>;
  risks?: string[];
  watch_items?: string[];
  provider?: string | null;
  model?: string | null;
  language?: string | null;
  created_at?: string | null;
}

export interface FiAnalysis {
  ticker: string;
  name: string;
  sector: string;
  exchange: string;
  currency: string;
  quote: FiQuote | null;
  fundamentals: FiFundamentals | null;
  metrics: FiMetrics;
  score: number;
  scoreComponents: FiScoreComponents;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  explanations: string[];
  newsEvents?: FiNewsEvent[];
  eventSummary?: FiEventSummary | null;
  newsPageUrl?: string | null;
  irUrl?: string | null;
  irNewsUrl?: string | null;
  rankPosition?: number | null;
  rankTotal?: number | null;
  sectorBenchmarks?: {
    sector: string;
    sampleCount: number;
    medians: Record<string, number | null>;
    values: Record<string, number | null>;
  } | null;
  fundamentalInsight?: FiInsight | null;
  timestamp: string;
}

export interface FiRankedStock {
  ticker: string;
  name: string;
  sector: string;
  score: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  price: number;
  change: number;
  return3m: number | null;
  return12m: number | null;
  volatility: number | null;
}

export interface FiScreenerResponse {
  success: boolean;
  filters_applied?: Record<string, any>;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  total_matches: number;
  returned: number;
  offset: number;
  data: FiRankedStock[];
}

export interface FiMover {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
}

export interface FiUniverse {
  exchange: string;
  currency: string;
  country: string;
  totalCount: number;
  sectors: Record<string, number>;
  blueChips: string[];
  stocks: FiStock[];
}

/**
 * Get Finnish stock universe (all Nasdaq Helsinki stocks)
 */
export async function getFiUniverse() {
  return apiCall<{ success: boolean } & FiUniverse>('/api/fi/universe');
}

/**
 * Get current quote for a Finnish stock
 */
export async function getFiQuote(ticker: string) {
  return apiCall<{ success: boolean; data: FiQuote }>(`/api/fi/quote/${ticker}`);
}

/**
 * Get historical data for a Finnish stock
 */
export async function getFiHistory(
  ticker: string,
  range: string = '1y',
  interval: string = '1d'
) {
  const params = new URLSearchParams({ range, interval });
  return apiCall<{
    success: boolean;
    ticker: string;
    range: string;
    interval: string;
    count: number;
    data: FiHistoryPoint[];
  }>(`/api/fi/history/${ticker}?${params}`);
}

/**
 * Get comprehensive analysis for a Finnish stock
 */
export async function getFiAnalysis(ticker: string) {
  return apiCall<{ success: boolean; data: FiAnalysis }>(`/api/fi/analysis/${ticker}`);
}

export interface FiTechnicals {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  rsi: {
    value: number | null;
    signal: string | null;
    period: number;
  } | null;
  macd: {
    value: number | null;
    signal_line: number | null;
    histogram: number | null;
    signal: string | null;
  } | null;
  bollinger: {
    upper: number | null;
    middle: number | null;
    lower: number | null;
    position: number | null;
    signal: string | null;
    period: number;
  } | null;
  sma: {
    sma20: number | null;
    sma50: number | null;
    sma200: number | null;
    trend: string | null;
  } | null;
  signals: Array<{
    type: string;
    signal: 'BUY' | 'SELL';
    text: string;
  }>;
  summary: {
    verdict: string;
    text: string;
  } | null;
}

/**
 * Get technical analysis (RSI, MACD, Bollinger, SMA) for a Finnish stock
 */
export async function getFiTechnicals(ticker: string) {
  return apiCall<{ success: boolean; data: FiTechnicals }>(`/api/fi/technicals/${ticker}`);
}

/**
 * Get top-ranked Finnish stocks by AI score
 */
export async function getFiRankings(limit: number = 50) {
  const params = new URLSearchParams({ limit: limit.toString() });
  return apiCall<{ success: boolean; count: number; data: FiRankedStock[] }>(
    `/api/fi/rank?${params}`
  );
}

/**
 * Get top gainers and losers for Finnish stocks
 */
export async function getFiMovers(limit: number = 10) {
  const params = new URLSearchParams({ limit: limit.toString() });
  return apiCall<{ success: boolean; gainers: FiMover[]; losers: FiMover[] }>(
    `/api/fi/movers?${params}`
  );
}

/**
 * Momentum stock data
 */
export interface FiMomentumStock {
  ticker: string;
  name: string;
  price: number;
  weeklyReturn: number;
  volume: number;
  avgVolume: number;
  volumeRatio: number;
  rsi: number | null;
}

export interface FiMomentumData {
  weekly_gainers: FiMomentumStock[];
  weekly_losers: FiMomentumStock[];
  unusual_volume: FiMomentumStock[];
  overbought: FiMomentumStock[];
  oversold: FiMomentumStock[];
  updated_at: string | null;
}

/**
 * Get weekly momentum data for Finnish stocks
 */
export async function getFiMomentum(limit: number = 10) {
  const params = new URLSearchParams({ limit: limit.toString() });
  return apiCall<{ success: boolean } & FiMomentumData>(
    `/api/fi/momentum?${params}`
  );
}

/**
 * Potential stock data
 */
export interface FiPotentialStock {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  potentialScore: number;
  reasons: string[];
  peRatio: number | null;
  pbRatio: number | null;
  dividendYield: number;
  return3m: number | null;
  return12m: number | null;
  roe: number | null;
  revenueGrowth: number | null;
  riskLevel: string;
}

/**
 * Get stocks with highest potential by timeframe
 */
export async function getFiPotential(timeframe: 'short' | 'medium' | 'long' = 'short', limit: number = 10) {
  const params = new URLSearchParams({ timeframe, limit: limit.toString() });
  return apiCall<{ success: boolean; timeframe: string; total: number; data: FiPotentialStock[] }>(
    `/api/fi/potential?${params}`
  );
}

/**
 * Get sector breakdown for Finnish stocks
 */
export async function getFiSectors() {
  return apiCall<{ success: boolean; data: Array<{ sector: string; count: number }> }>(
    '/api/fi/sectors'
  );
}

/**
 * Screen Finnish stocks (supports sorting by score asc/desc)
 */
export async function getFiScreener(params?: {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
  sector?: string;
  market?: string;
}) {
  const query = new URLSearchParams();
  if (params?.sort_by) query.set('sort_by', params.sort_by);
  if (params?.sort_order) query.set('sort_order', params.sort_order);
  if (params?.limit !== undefined) query.set('limit', params.limit.toString());
  if (params?.offset !== undefined) query.set('offset', params.offset.toString());
  if (params?.sector) query.set('sector', params.sector);
  if (params?.market) query.set('market', params.market);

  return apiCall<FiScreenerResponse>(`/api/fi/screener${query.toString() ? `?${query}` : ''}`);
}

/**
 * Get basic stock info for a Finnish stock
 */
export async function getFiStockInfo(ticker: string) {
  return apiCall<{ success: boolean; data: FiStock }>(`/api/fi/stock/${ticker}`);
}

/**
 * Get Finnish disclosure/news events
 */
export async function getFiEvents(params?: {
  ticker?: string;
  types?: string;
  limit?: number;
  offset?: number;
  include_analysis?: boolean;
}) {
  const searchParams = new URLSearchParams();
  if (params?.ticker) searchParams.append('ticker', params.ticker);
  if (params?.types) searchParams.append('types', params.types);
  if (params?.limit) searchParams.append('limit', params.limit.toString());
  if (params?.offset) searchParams.append('offset', params.offset.toString());
  if (params?.include_analysis === false) searchParams.append('include_analysis', 'false');

  const query = searchParams.toString();
  return apiCall<{ success: boolean; count: number; data: FiNewsEvent[] }>(
    `/api/fi/events${query ? `?${query}` : ''}`
  );
}

/**
 * Get significant Finnish events for dashboard (filtered, no duplicates)
 */
export async function getFiSignificantEvents(days: number = 7, limit: number = 10) {
  const params = new URLSearchParams({ days: days.toString(), limit: limit.toString() });
  return apiCall<{ success: boolean; count: number; data: FiNewsEvent[] }>(
    `/api/fi/events/significant?${params}`
  );
}

/**
 * Finnish macro indicator type
 */
export interface FiMacroIndicator {
  code: string;
  name: string;
  symbol: string;
  price: number | null;
  change: number | null;
  changePercent: number | null;
  previousClose: number | null;
}

export interface FiMacroData {
  indices: FiMacroIndicator[];
  currencies: FiMacroIndicator[];
  rates: FiMacroIndicator[];
  timestamp: string;
}

/**
 * Get Finnish and Eurozone macro indicators
 */
export async function getFiMacro() {
  return apiCall<{ success: boolean; data: FiMacroData }>('/api/fi/macro');
}

/**
 * Get macro indicator history
 */
export async function getFiMacroHistory(code: string, period: string = '1y', interval: string = '1d') {
  return apiCall<{ success: boolean; data: any }>(`/api/fi/macro/${encodeURIComponent(code)}/history?period=${period}&interval=${interval}`);
}

/**
 * Precious metal type
 */
export interface FiMetal {
  symbol: string;
  code: string;
  name: string;
  name_en: string;
  unit: string;
  description: string;
  price: number;
  previousClose: number | null;
  change: number;
  changePercent: number;
  high: number | null;
  low: number | null;
  open: number | null;
  fiftyTwoWeekHigh: number | null;
  fiftyTwoWeekLow: number | null;
  fiftyDayAverage: number | null;
  twoHundredDayAverage: number | null;
  volume: number | null;
}

export interface FiMetalHistory {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface FiMetalDetail extends FiMetal {
  history: FiMetalHistory[];
  timestamp: string;
}

export interface FiMetalsOverview {
  metals: FiMetal[];
  timestamp: string;
}

/**
 * Get precious metals overview (gold, silver)
 */
export async function getFiMetals() {
  return apiCall<{ success: boolean; data: FiMetalsOverview }>('/api/fi/metals');
}

/**
 * Get detailed data for a specific metal including history
 */
export async function getFiMetalDetail(code: string) {
  return apiCall<{ success: boolean; data: FiMetalDetail }>(`/api/fi/metals/${code}`);
}

/**
 * Get metal price history
 */
export async function getFiMetalHistory(code: string, period: string = '1y', interval: string = '1d') {
  const params = new URLSearchParams({ period, interval });
  return apiCall<{ success: boolean; data: FiMetalHistory[] }>(`/api/fi/metals/${code}/history?${params}`);
}

/**
 * IR headline type
 */
export interface FiIrHeadline {
  title: string;
  url?: string | null;
  date?: string | null;
}

/**
 * Get latest headlines from company IR page
 */
export async function getFiIrHeadlines(ticker: string, limit: number = 5) {
  const params = new URLSearchParams({ limit: limit.toString() });
  return apiCall<{ success: boolean; ticker: string; count: number; data: FiIrHeadline[] }>(
    `/api/fi/ir-headlines/${ticker}?${params}`
  );
}

// ============================================================================
// UNITED STATES (NYSE/NASDAQ) API
// ============================================================================

export interface UsStock {
  ticker: string;
  name: string;
  sector: string;
  index: string[];  // ["SP500", "NASDAQ100"]
}

export interface UsQuote {
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
  previousClose: number;
  high: number;
  low: number;
  open: number;
  currency: string;
  exchange: string;
  timestamp: string;
}

export interface UsHistoryPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface UsMetrics {
  volatility: number | null;
  maxDrawdown: number | null;
  sharpeRatio: number | null;
  return3m: number | null;
  return12m: number | null;
}

export interface UsFundamentals {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  exchange: string;
  currency: string;
  marketCap: number;
  peRatio: number | null;
  forwardPE: number | null;
  pegRatio: number | null;
  priceToBook: number | null;
  dividendYield: number | null;
  profitMargins: number | null;
  revenueGrowth: number | null;
  earningsGrowth: number | null;
  returnOnEquity: number | null;
  returnOnAssets: number | null;
  roic: number | null;
  debtToEquity: number | null;
  beta: number | null;
  fiftyTwoWeekHigh: number | null;
  fiftyTwoWeekLow: number | null;
  averageVolume: number | null;
  enterpriseValue: number | null;
  ebit: number | null;
  evEbit: number | null;
  timestamp: string;
}

export interface UsScoreComponents {
  momentum: number;
  risk: number;
  fundamentals: number;
}

export interface UsAnalysis {
  ticker: string;
  name: string;
  sector: string;
  exchange: string;
  currency: string;
  index: string[];
  quote: UsQuote | null;
  fundamentals: UsFundamentals | null;
  metrics: UsMetrics;
  score: number;
  scoreComponents: UsScoreComponents;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  explanations: string[];
  rankPosition?: number | null;
  rankTotal?: number | null;
  sectorBenchmarks?: {
    sector: string;
    sampleCount: number;
    medians: Record<string, number | null>;
    values: Record<string, number | null>;
  } | null;
  timestamp: string;
}

export interface UsRankedStock {
  ticker: string;
  name: string;
  sector: string;
  score: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  price: number;
  change: number;
  return3m: number | null;
  return12m: number | null;
  volatility: number | null;
  peRatio?: number | null;
  pbRatio?: number | null;
  dividendYield?: number | null;
  dividendAmount?: number | null;
  evEbit?: number | null;
  roic?: number | null;
  beta?: number | null;
  marketCap?: number | null;
  index?: string[];
}

export interface UsScreenerResponse {
  success: boolean;
  filters_applied?: Record<string, any>;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  total_matches: number;
  returned: number;
  offset: number;
  data: UsRankedStock[];
}

export interface UsMover {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
}

export interface UsUniverse {
  exchange: string;
  currency: string;
  country: string;
  totalCount: number;
  sp500Count: number;
  nasdaq100Count: number;
  sectors: Record<string, number>;
  blueChips: string[];
  stocks: UsStock[];
}

export interface UsMomentumStock {
  ticker: string;
  name: string;
  price: number;
  weeklyReturn: number;
  volume: number;
  avgVolume: number;
  volumeRatio: number;
  rsi: number | null;
}

export interface UsMomentumData {
  weekly_gainers: UsMomentumStock[];
  weekly_losers: UsMomentumStock[];
  unusual_volume: UsMomentumStock[];
  overbought: UsMomentumStock[];
  oversold: UsMomentumStock[];
  updated_at: string | null;
}

export interface UsPotentialStock {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  potentialScore: number;
  reasons: string[];
  peRatio: number | null;
  pbRatio: number | null;
  dividendYield: number;
  return3m: number | null;
  return12m: number | null;
  roe: number | null;
  revenueGrowth: number | null;
  riskLevel: string;
  index?: string[];
}

export interface UsMacroIndicator {
  code: string;
  name: string;
  symbol: string;
  price: number | null;
  change: number | null;
  changePercent: number | null;
  previousClose: number | null;
}

export interface UsMacroData {
  indices: UsMacroIndicator[];
  currencies: UsMacroIndicator[];
  rates: UsMacroIndicator[];
  commodities: UsMacroIndicator[];
  timestamp: string;
}

export interface UsTechnicals {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  rsi: {
    value: number | null;
    signal: string | null;
    period: number;
  } | null;
  macd: {
    value: number | null;
    signal_line: number | null;
    histogram: number | null;
    signal: string | null;
  } | null;
  bollinger: {
    upper: number | null;
    middle: number | null;
    lower: number | null;
    position: number | null;
    signal: string | null;
    period: number;
  } | null;
  sma: {
    sma20: number | null;
    sma50: number | null;
    sma200: number | null;
    trend: string | null;
  } | null;
  signals: Array<{
    type: string;
    signal: 'BUY' | 'SELL';
    text: string;
  }>;
  summary: {
    verdict: string;
    text: string;
  } | null;
}

/**
 * Get US stock universe (S&P 500 + NASDAQ 100)
 */
export async function getUsUniverse() {
  return apiCall<{ success: boolean } & UsUniverse>('/api/us/universe');
}

/**
 * Get current quote for a US stock
 */
export async function getUsQuote(ticker: string) {
  return apiCall<{ success: boolean; data: UsQuote }>(`/api/us/quote/${ticker}`);
}

/**
 * Get historical data for a US stock
 */
export async function getUsHistory(
  ticker: string,
  range: string = '1y',
  interval: string = '1d'
) {
  const params = new URLSearchParams({ range, interval });
  return apiCall<{
    success: boolean;
    ticker: string;
    range: string;
    interval: string;
    count: number;
    data: UsHistoryPoint[];
  }>(`/api/us/history/${ticker}?${params}`);
}

/**
 * Get comprehensive analysis for a US stock
 */
export async function getUsAnalysis(ticker: string) {
  return apiCall<{ success: boolean; data: UsAnalysis }>(`/api/us/analysis/${ticker}`);
}

/**
 * Get technical analysis (RSI, MACD, Bollinger, SMA) for a US stock
 */
export async function getUsTechnicals(ticker: string) {
  return apiCall<{ success: boolean; data: UsTechnicals }>(`/api/us/technicals/${ticker}`);
}

/**
 * Get top-ranked US stocks by AI score
 */
export async function getUsRankings(limit: number = 50) {
  const params = new URLSearchParams({ limit: limit.toString() });
  return apiCall<{ success: boolean; count: number; data: UsRankedStock[] }>(
    `/api/us/rank?${params}`
  );
}

/**
 * Get top gainers and losers for US stocks
 */
export async function getUsMovers(limit: number = 10) {
  const params = new URLSearchParams({ limit: limit.toString() });
  return apiCall<{ success: boolean; gainers: UsMover[]; losers: UsMover[] }>(
    `/api/us/movers?${params}`
  );
}

/**
 * Get weekly momentum data for US stocks
 */
export async function getUsMomentum(limit: number = 10) {
  const params = new URLSearchParams({ limit: limit.toString() });
  return apiCall<{ success: boolean } & UsMomentumData>(
    `/api/us/momentum?${params}`
  );
}

/**
 * Get US stocks with highest potential by timeframe
 */
export async function getUsPotential(timeframe: 'short' | 'medium' | 'long' = 'short', limit: number = 10) {
  const params = new URLSearchParams({ timeframe, limit: limit.toString() });
  return apiCall<{ success: boolean; timeframe: string; total: number; data: UsPotentialStock[] }>(
    `/api/us/potential?${params}`
  );
}

/**
 * Get sector breakdown for US stocks
 */
export async function getUsSectors() {
  return apiCall<{ success: boolean; data: Array<{ sector: string; count: number }> }>(
    '/api/us/sectors'
  );
}

/**
 * Screen US stocks with index filter (SP500, NASDAQ100, ALL)
 */
export async function getUsScreener(params?: {
  index?: string;  // SP500, NASDAQ100, or ALL
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
  sector?: string;
  min_dividend_yield?: number;
  max_pe?: number;
  min_pe?: number;
  max_volatility?: number;
  min_return_12m?: number;
  min_return_3m?: number;
  min_market_cap?: number;
  risk_level?: string;
}) {
  const query = new URLSearchParams();
  if (params?.index) query.set('index', params.index);
  if (params?.sort_by) query.set('sort_by', params.sort_by);
  if (params?.sort_order) query.set('sort_order', params.sort_order);
  if (params?.limit !== undefined) query.set('limit', params.limit.toString());
  if (params?.offset !== undefined) query.set('offset', params.offset.toString());
  if (params?.sector) query.set('sector', params.sector);
  if (params?.min_dividend_yield !== undefined) query.set('min_dividend_yield', params.min_dividend_yield.toString());
  if (params?.max_pe !== undefined) query.set('max_pe', params.max_pe.toString());
  if (params?.min_pe !== undefined) query.set('min_pe', params.min_pe.toString());
  if (params?.max_volatility !== undefined) query.set('max_volatility', params.max_volatility.toString());
  if (params?.min_return_12m !== undefined) query.set('min_return_12m', params.min_return_12m.toString());
  if (params?.min_return_3m !== undefined) query.set('min_return_3m', params.min_return_3m.toString());
  if (params?.min_market_cap !== undefined) query.set('min_market_cap', params.min_market_cap.toString());
  if (params?.risk_level) query.set('risk_level', params.risk_level);

  return apiCall<UsScreenerResponse>(`/api/us/screener${query.toString() ? `?${query}` : ''}`);
}

/**
 * Get basic stock info for a US stock
 */
export async function getUsStockInfo(ticker: string) {
  return apiCall<{ success: boolean; data: UsStock }>(`/api/us/stock/${ticker}`);
}

/**
 * Get US macro indicators (S&P 500, NASDAQ, VIX, Treasury, etc.)
 */
export async function getUsMacro() {
  return apiCall<{ success: boolean; data: UsMacroData }>('/api/us/macro');
}

/**
 * Get US macro indicator history
 */
export async function getUsMacroHistory(code: string, period: string = '1y', interval: string = '1d') {
  return apiCall<{ success: boolean; data: any }>(`/api/us/macro/${encodeURIComponent(code)}/history?period=${period}&interval=${interval}`);
}

// Helper for formatting USD prices
export function formatUsdPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price);
}

// Helper for formatting large USD numbers
export function formatLargeUsdNumber(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
  return `$${value.toFixed(2)}`;
}
