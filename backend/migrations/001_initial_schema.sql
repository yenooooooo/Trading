-- ============================================
-- 코인 선물 자동매매 시스템 — 초기 DB 스키마
-- Supabase SQL Editor에서 실행
-- ============================================

-- --- UUID 확장 활성화 ---
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- 1. 사용자 테이블
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    nickname VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    settings JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE users IS '사용자 기본 정보';

-- ============================================
-- 2. 거래소 API 키 (AES-256 암호화 저장)
-- ============================================
CREATE TABLE exchange_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exchange VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    passphrase_encrypted TEXT,
    label VARCHAR(100),
    permissions JSONB DEFAULT '{"trade": true, "withdraw": false}'::jsonb,
    is_testnet BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE exchange_keys IS '거래소 API 키 (암호화 저장, 출금 권한 금지)';

CREATE INDEX idx_exchange_keys_user ON exchange_keys(user_id);

-- ============================================
-- 3. 전략 설정
-- ============================================
CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL,
    exchange_key_id UUID REFERENCES exchange_keys(id),
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    direction VARCHAR(10) DEFAULT 'both'
        CHECK (direction IN ('long', 'short', 'both')),
    leverage INTEGER DEFAULT 1
        CHECK (leverage >= 1 AND leverage <= 20),
    status VARCHAR(20) DEFAULT 'inactive'
        CHECK (status IN ('active', 'inactive', 'paused', 'error')),
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    risk_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ
);

COMMENT ON TABLE strategies IS '매매 전략 설정 (파라미터는 JSONB로 유연하게 관리)';
COMMENT ON COLUMN strategies.leverage IS '레버리지 (최대 20x 하드 리밋)';

CREATE INDEX idx_strategies_user ON strategies(user_id);
CREATE INDEX idx_strategies_status ON strategies(status);

-- ============================================
-- 4. 포지션
-- ============================================
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    strategy_id UUID REFERENCES strategies(id),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL
        CHECK (side IN ('long', 'short')),
    entry_price DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    size DECIMAL(20, 8) NOT NULL,
    leverage INTEGER NOT NULL
        CHECK (leverage >= 1 AND leverage <= 20),
    stop_loss DECIMAL(20, 8),
    take_profit JSONB,
    trailing_stop JSONB,
    unrealized_pnl DECIMAL(20, 8) DEFAULT 0,
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    fees_paid DECIMAL(20, 8) DEFAULT 0,
    funding_paid DECIMAL(20, 8) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'open'
        CHECK (status IN ('open', 'closed', 'liquidated')),
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    close_reason VARCHAR(50)
        CHECK (close_reason IN (
            'take_profit', 'stop_loss', 'trailing_stop',
            'manual', 'signal', 'risk_limit', NULL
        ))
);

COMMENT ON TABLE positions IS '매매 포지션 (금액은 DECIMAL 타입 필수)';

CREATE INDEX idx_positions_user ON positions(user_id);
CREATE INDEX idx_positions_strategy ON positions(strategy_id);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_symbol ON positions(symbol);

-- ============================================
-- 5. 주문
-- ============================================
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    strategy_id UUID REFERENCES strategies(id),
    position_id UUID REFERENCES positions(id),
    exchange VARCHAR(50) NOT NULL,
    exchange_order_id VARCHAR(100),
    symbol VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL
        CHECK (type IN ('market', 'limit', 'stop_market', 'stop_limit', 'trailing_stop')),
    side VARCHAR(10) NOT NULL
        CHECK (side IN ('buy', 'sell')),
    price DECIMAL(20, 8),
    amount DECIMAL(20, 8) NOT NULL,
    filled DECIMAL(20, 8) DEFAULT 0,
    avg_fill_price DECIMAL(20, 8),
    fee DECIMAL(20, 8) DEFAULT 0,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('pending', 'open', 'partially_filled', 'filled', 'cancelled', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE orders IS '주문 내역 (거래소 주문 ID 연동)';

CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_strategy ON orders(strategy_id);
CREATE INDEX idx_orders_position ON orders(position_id);
CREATE INDEX idx_orders_status ON orders(status);

-- ============================================
-- 6. 거래 체결 내역
-- ============================================
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    strategy_id UUID REFERENCES strategies(id),
    position_id UUID REFERENCES positions(id),
    order_id UUID REFERENCES orders(id),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL
        CHECK (side IN ('buy', 'sell')),
    price DECIMAL(20, 8) NOT NULL,
    amount DECIMAL(20, 8) NOT NULL,
    fee DECIMAL(20, 8) NOT NULL,
    fee_currency VARCHAR(20),
    realized_pnl DECIMAL(20, 8),
    executed_at TIMESTAMPTZ NOT NULL
);

COMMENT ON TABLE trades IS '실제 체결된 거래 내역';

CREATE INDEX idx_trades_user ON trades(user_id);
CREATE INDEX idx_trades_strategy ON trades(strategy_id);
CREATE INDEX idx_trades_executed ON trades(executed_at DESC);

-- ============================================
-- 7. 백테스트 결과
-- ============================================
CREATE TABLE backtests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    strategy_id UUID REFERENCES strategies(id),
    parameters JSONB NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_balance DECIMAL(20, 8) NOT NULL,
    results JSONB NOT NULL DEFAULT '{}'::jsonb,
    trades_data JSONB,
    equity_curve JSONB,
    status VARCHAR(20) DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

COMMENT ON TABLE backtests IS '백테스트 실행 결과 및 거래 데이터';

CREATE INDEX idx_backtests_user ON backtests(user_id);
CREATE INDEX idx_backtests_strategy ON backtests(strategy_id);

-- ============================================
-- 8. 일일 성과 스냅샷
-- ============================================
CREATE TABLE daily_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    strategy_id UUID REFERENCES strategies(id),
    date DATE NOT NULL,
    starting_balance DECIMAL(20, 8),
    ending_balance DECIMAL(20, 8),
    realized_pnl DECIMAL(20, 8),
    unrealized_pnl DECIMAL(20, 8),
    fees DECIMAL(20, 8),
    funding DECIMAL(20, 8),
    trade_count INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    max_drawdown DECIMAL(10, 4),
    UNIQUE(user_id, strategy_id, date)
);

COMMENT ON TABLE daily_performance IS '일일 성과 기록 (대시보드 차트용)';

CREATE INDEX idx_daily_perf_user_date ON daily_performance(user_id, date DESC);

-- ============================================
-- 9. 시장 데이터 (OHLCV)
-- ============================================
CREATE TABLE market_data (
    id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    open DECIMAL(20, 8),
    high DECIMAL(20, 8),
    low DECIMAL(20, 8),
    close DECIMAL(20, 8),
    volume DECIMAL(20, 8)
);

COMMENT ON TABLE market_data IS 'OHLCV 캔들 데이터 (백테스트 및 차트용)';

CREATE INDEX idx_market_data_lookup
    ON market_data(exchange, symbol, interval, time DESC);

-- ============================================
-- 10. 알림 설정
-- ============================================
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL
        CHECK (type IN ('pnl', 'price', 'risk', 'error', 'trade')),
    conditions JSONB NOT NULL,
    channels JSONB NOT NULL DEFAULT '{"telegram": false, "discord": false}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE alert_rules IS '알림 규칙 설정 (조건 + 채널)';

CREATE INDEX idx_alert_rules_user ON alert_rules(user_id);

-- ============================================
-- 11. 알림 로그
-- ============================================
CREATE TABLE alert_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    alert_rule_id UUID REFERENCES alert_rules(id),
    event_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    channel VARCHAR(20) NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    is_read BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE alert_logs IS '발송된 알림 기록';

CREATE INDEX idx_alert_logs_user ON alert_logs(user_id, sent_at DESC);

-- ============================================
-- updated_at 자동 갱신 함수
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- strategies 테이블에 트리거 적용
CREATE TRIGGER trigger_strategies_updated_at
    BEFORE UPDATE ON strategies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- orders 테이블에 트리거 적용
CREATE TRIGGER trigger_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- users 테이블에 트리거 적용
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- RLS (Row Level Security) 활성화
-- 각 사용자는 자신의 데이터만 접근 가능
-- ============================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE exchange_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtests ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_logs ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 완료 확인
-- ============================================
SELECT
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS size
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
ORDER BY table_name;
