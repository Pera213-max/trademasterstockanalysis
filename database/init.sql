-- TradeMaster Pro Database Initialization Script
-- PostgreSQL Database Schema

-- Create database (if using docker-compose, database is created automatically)
-- CREATE DATABASE trademaster;

-- Connect to the database
\c trademaster;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For fuzzy text search

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- 1. Users Table
-- Stores user account information
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- 2. Watchlists Table
-- Stores user watchlists for stocks and crypto
CREATE TABLE IF NOT EXISTS watchlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('stock', 'crypto', 'index', 'etf')),
    notes TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, ticker, type)
);

-- 3. Price History Table
-- Stores OHLCV (Open, High, Low, Close, Volume) data
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('stock', 'crypto')),
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume BIGINT,
    quote_volume DECIMAL(20, 2), -- For crypto (volume in USDT)
    trades INTEGER, -- Number of trades
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ticker, type, timestamp)
);

-- 4. Social Mentions Table
-- Stores social media mentions and sentiment data
CREATE TABLE IF NOT EXISTS social_mentions (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('reddit', 'twitter', 'stocktwits', 'discord')),
    mentions INTEGER DEFAULT 0,
    sentiment_score DECIMAL(5, 3) CHECK (sentiment_score BETWEEN -1 AND 1),
    sentiment_label VARCHAR(30), -- e.g., 'Bullish', 'Bearish', 'Neutral'
    bullish_count INTEGER DEFAULT 0,
    bearish_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ticker, platform, timestamp)
);

-- 5. News Articles Table
-- Stores news articles with sentiment analysis
CREATE TABLE IF NOT EXISTS news_articles (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    title TEXT NOT NULL,
    summary TEXT,
    url VARCHAR(500) UNIQUE,
    source VARCHAR(100),
    author VARCHAR(200),
    published_at TIMESTAMP NOT NULL,
    category VARCHAR(50), -- e.g., 'EARNINGS', 'FDA', 'MERGER', 'BREAKOUT'
    sentiment DECIMAL(5, 3) CHECK (sentiment BETWEEN -1 AND 1),
    sentiment_label VARCHAR(30),
    is_bomb BOOLEAN DEFAULT FALSE, -- Breaking news / high impact
    impact_level VARCHAR(20) CHECK (impact_level IN ('LOW', 'MEDIUM', 'HIGH')),
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. AI Predictions Table
-- Stores AI-generated stock/crypto predictions
CREATE TABLE IF NOT EXISTS ai_predictions (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('stock', 'crypto')),
    prediction_type VARCHAR(20) NOT NULL CHECK (prediction_type IN ('day', 'swing', 'long')),
    current_price DECIMAL(20, 8) NOT NULL,
    target_price DECIMAL(20, 8) NOT NULL,
    potential_return DECIMAL(10, 2),
    strength_score DECIMAL(5, 2) CHECK (strength_score BETWEEN 0 AND 100),
    confidence DECIMAL(5, 2) CHECK (confidence BETWEEN 0 AND 100),
    reasoning TEXT,
    signals JSONB, -- Array of signals
    technical_score DECIMAL(5, 2),
    momentum_score DECIMAL(5, 2),
    volume_score DECIMAL(5, 2),
    trend_score DECIMAL(5, 2),
    risk_level VARCHAR(20) CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP, -- When prediction becomes stale
    accuracy DECIMAL(5, 2), -- Backfilled after outcome is known
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- ADDITIONAL TABLES
-- ============================================================================

-- Portfolios Table
-- Stores user portfolio information
CREATE TABLE IF NOT EXISTS portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_value DECIMAL(20, 2) DEFAULT 0.00,
    cash_balance DECIMAL(20, 2) DEFAULT 0.00,
    initial_balance DECIMAL(20, 2) DEFAULT 10000.00,
    total_return DECIMAL(10, 2) DEFAULT 0.00,
    total_return_percent DECIMAL(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trades Table
-- Stores user trading history
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('stock', 'crypto')),
    trade_type VARCHAR(10) NOT NULL CHECK (trade_type IN ('buy', 'sell')),
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    total_value DECIMAL(20, 2) NOT NULL,
    fee DECIMAL(20, 2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'cancelled', 'failed')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Positions Table
-- Stores current user positions
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('stock', 'crypto')),
    quantity DECIMAL(20, 8) NOT NULL,
    average_price DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    total_cost DECIMAL(20, 2) NOT NULL,
    current_value DECIMAL(20, 2),
    unrealized_pnl DECIMAL(20, 2),
    unrealized_pnl_percent DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, ticker, type)
);

-- Alerts Table
-- Stores user price alerts and notifications
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('stock', 'crypto')),
    alert_type VARCHAR(30) NOT NULL CHECK (alert_type IN ('price_above', 'price_below', 'percent_change', 'volume_spike')),
    target_price DECIMAL(20, 8),
    target_percent DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT TRUE,
    triggered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Economic Indicators Table
-- Stores macro economic data
CREATE TABLE IF NOT EXISTS economic_indicators (
    id SERIAL PRIMARY KEY,
    indicator_name VARCHAR(100) NOT NULL,
    indicator_code VARCHAR(50) UNIQUE NOT NULL, -- e.g., 'DFF', 'CPIAUCSL'
    value DECIMAL(20, 4),
    change_percent DECIMAL(10, 2),
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(50) DEFAULT 'FRED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (indicator_code, timestamp)
);

-- Market Indices Table
-- Stores major market indices (SPY, QQQ, DXY, VIX)
CREATE TABLE IF NOT EXISTS market_indices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    value DECIMAL(20, 4) NOT NULL,
    change DECIMAL(20, 4),
    change_percent DECIMAL(10, 2),
    high_52w DECIMAL(20, 4),
    low_52w DECIMAL(20, 4),
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, timestamp)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Watchlists indexes
CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlists_ticker ON watchlists(ticker);
CREATE INDEX IF NOT EXISTS idx_watchlists_type ON watchlists(type);
CREATE INDEX IF NOT EXISTS idx_watchlists_added_at ON watchlists(added_at);

-- Price history indexes (critical for performance)
CREATE INDEX IF NOT EXISTS idx_price_history_ticker ON price_history(ticker);
CREATE INDEX IF NOT EXISTS idx_price_history_type ON price_history(type);
CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_ticker_timestamp ON price_history(ticker, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_type_timestamp ON price_history(type, timestamp DESC);

-- Social mentions indexes
CREATE INDEX IF NOT EXISTS idx_social_mentions_ticker ON social_mentions(ticker);
CREATE INDEX IF NOT EXISTS idx_social_mentions_platform ON social_mentions(platform);
CREATE INDEX IF NOT EXISTS idx_social_mentions_timestamp ON social_mentions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_social_mentions_ticker_timestamp ON social_mentions(ticker, timestamp DESC);

-- News articles indexes
CREATE INDEX IF NOT EXISTS idx_news_articles_ticker ON news_articles(ticker);
CREATE INDEX IF NOT EXISTS idx_news_articles_published_at ON news_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_category ON news_articles(category);
CREATE INDEX IF NOT EXISTS idx_news_articles_is_bomb ON news_articles(is_bomb) WHERE is_bomb = TRUE;
CREATE INDEX IF NOT EXISTS idx_news_articles_ticker_published ON news_articles(ticker, published_at DESC);
-- Full-text search index for news titles
CREATE INDEX IF NOT EXISTS idx_news_articles_title_trgm ON news_articles USING gin(title gin_trgm_ops);

-- AI predictions indexes
CREATE INDEX IF NOT EXISTS idx_ai_predictions_ticker ON ai_predictions(ticker);
CREATE INDEX IF NOT EXISTS idx_ai_predictions_type ON ai_predictions(type);
CREATE INDEX IF NOT EXISTS idx_ai_predictions_prediction_type ON ai_predictions(prediction_type);
CREATE INDEX IF NOT EXISTS idx_ai_predictions_predicted_at ON ai_predictions(predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_predictions_strength_score ON ai_predictions(strength_score DESC);
CREATE INDEX IF NOT EXISTS idx_ai_predictions_ticker_predicted ON ai_predictions(ticker, predicted_at DESC);

-- Trades indexes
CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_user_ticker ON trades(user_id, ticker);

-- Positions indexes
CREATE INDEX IF NOT EXISTS idx_positions_user_id ON positions(user_id);
CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions(ticker);

-- Alerts indexes
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_ticker ON alerts(ticker);
CREATE INDEX IF NOT EXISTS idx_alerts_is_active ON alerts(is_active) WHERE is_active = TRUE;

-- Economic indicators indexes
CREATE INDEX IF NOT EXISTS idx_economic_indicators_code ON economic_indicators(indicator_code);
CREATE INDEX IF NOT EXISTS idx_economic_indicators_timestamp ON economic_indicators(timestamp DESC);

-- Market indices indexes
CREATE INDEX IF NOT EXISTS idx_market_indices_symbol ON market_indices(symbol);
CREATE INDEX IF NOT EXISTS idx_market_indices_timestamp ON market_indices(timestamp DESC);

-- ============================================================================
-- TRIGGERS AND FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at columns
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portfolios_updated_at
    BEFORE UPDATE ON portfolios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_news_articles_updated_at
    BEFORE UPDATE ON news_articles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate position values
CREATE OR REPLACE FUNCTION update_position_values()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.current_price IS NOT NULL THEN
        NEW.current_value = NEW.quantity * NEW.current_price;
        NEW.unrealized_pnl = NEW.current_value - NEW.total_cost;
        IF NEW.total_cost > 0 THEN
            NEW.unrealized_pnl_percent = (NEW.unrealized_pnl / NEW.total_cost) * 100;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER calculate_position_values
    BEFORE INSERT OR UPDATE ON positions
    FOR EACH ROW
    EXECUTE FUNCTION update_position_values();

-- ============================================================================
-- SAMPLE DATA (Development)
-- ============================================================================

-- Insert sample users
INSERT INTO users (email, username, hashed_password, is_verified)
VALUES
    ('demo@trademaster.pro', 'demo_user', '$2b$12$demo_hashed_password_here', TRUE),
    ('test@trademaster.pro', 'test_trader', '$2b$12$test_hashed_password_here', TRUE),
    ('admin@trademaster.pro', 'admin', '$2b$12$admin_hashed_password_here', TRUE)
ON CONFLICT (email) DO NOTHING;

-- Insert sample portfolios
INSERT INTO portfolios (user_id, total_value, cash_balance, initial_balance)
SELECT id, 10000.00, 10000.00, 10000.00
FROM users
WHERE email IN ('demo@trademaster.pro', 'test@trademaster.pro')
ON CONFLICT (user_id) DO NOTHING;

-- Insert sample watchlists
INSERT INTO watchlists (user_id, ticker, type)
SELECT
    u.id,
    ticker,
    'stock'
FROM users u
CROSS JOIN (VALUES ('NVDA'), ('AAPL'), ('MSFT'), ('GOOGL'), ('TSLA')) AS tickers(ticker)
WHERE u.email = 'demo@trademaster.pro'
ON CONFLICT (user_id, ticker, type) DO NOTHING;

INSERT INTO watchlists (user_id, ticker, type)
SELECT
    u.id,
    ticker,
    'crypto'
FROM users u
CROSS JOIN (VALUES ('BTC'), ('ETH'), ('SOL')) AS tickers(ticker)
WHERE u.email = 'demo@trademaster.pro'
ON CONFLICT (user_id, ticker, type) DO NOTHING;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View for latest prices
CREATE OR REPLACE VIEW latest_prices AS
SELECT DISTINCT ON (ticker, type)
    ticker,
    type,
    timestamp,
    close AS price,
    volume,
    (close - open) AS change,
    ((close - open) / NULLIF(open, 0) * 100) AS change_percent
FROM price_history
ORDER BY ticker, type, timestamp DESC;

-- View for trending stocks (social mentions)
CREATE OR REPLACE VIEW trending_stocks AS
SELECT
    ticker,
    SUM(mentions) AS total_mentions,
    AVG(sentiment_score) AS avg_sentiment,
    MAX(timestamp) AS last_updated
FROM social_mentions
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY ticker
ORDER BY total_mentions DESC
LIMIT 50;

-- View for hot news
CREATE OR REPLACE VIEW hot_news AS
SELECT *
FROM news_articles
WHERE is_bomb = TRUE
ORDER BY published_at DESC
LIMIT 100;

-- ============================================================================
-- GRANTS AND PERMISSIONS
-- ============================================================================

-- Grant permissions to application user (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trademaster_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trademaster_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO trademaster_app;

-- ============================================================================
-- CLEANUP AND MAINTENANCE FUNCTIONS
-- ============================================================================

-- Function to cleanup old price history (keep last 2 years)
CREATE OR REPLACE FUNCTION cleanup_old_price_history()
RETURNS void AS $$
BEGIN
    DELETE FROM price_history
    WHERE timestamp < NOW() - INTERVAL '2 years';
END;
$$ language 'plpgsql';

-- Function to cleanup old social mentions (keep last 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_social_mentions()
RETURNS void AS $$
BEGIN
    DELETE FROM social_mentions
    WHERE timestamp < NOW() - INTERVAL '90 days';
END;
$$ language 'plpgsql';

-- Function to cleanup old news articles (keep last 1 year)
CREATE OR REPLACE FUNCTION cleanup_old_news()
RETURNS void AS $$
BEGIN
    DELETE FROM news_articles
    WHERE published_at < NOW() - INTERVAL '1 year'
    AND is_bomb = FALSE;
END;
$$ language 'plpgsql';

-- ============================================================================
-- ANALYTICS QUERIES (Examples)
-- ============================================================================

-- Example: Get user portfolio performance
-- SELECT
--     u.username,
--     p.total_value,
--     p.cash_balance,
--     p.total_return,
--     p.total_return_percent,
--     COUNT(pos.id) AS num_positions
-- FROM users u
-- JOIN portfolios p ON u.id = p.user_id
-- LEFT JOIN positions pos ON u.id = pos.user_id
-- WHERE u.email = 'demo@trademaster.pro'
-- GROUP BY u.id, p.id;

-- Example: Get top AI predictions
-- SELECT *
-- FROM ai_predictions
-- WHERE predicted_at > NOW() - INTERVAL '24 hours'
-- ORDER BY strength_score DESC, confidence DESC
-- LIMIT 10;

COMMIT;

-- End of initialization script
