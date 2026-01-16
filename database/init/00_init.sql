CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    home_country TEXT,
    account_age_days INT,
    avg_transaction_amount FLOAT
);

CREATE TABLE IF NOT EXISTS cards (
    card_id TEXT PRIMARY KEY,
    user_id TEXT,
    issuer TEXT,
    is_stolen BOOLEAN,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    device_type TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id TEXT,
    card_id TEXT,
    device_id TEXT,
    amount FLOAT,
    currency TEXT,
    merchant TEXT,
    merchant_category TEXT,
    country TEXT,
    timestamp TIMESTAMP,
    is_fraud BOOLEAN,
    fraud_reason TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (card_id) REFERENCES cards(card_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_transactions_card ON transactions(card_id);
CREATE INDEX idx_transactions_fraud ON transactions(is_fraud);
CREATE TABLE IF NOT EXISTS transaction_features (
    transaction_id TEXT PRIMARY KEY REFERENCES transactions(transaction_id),

    -- velocity features
    tx_count_5m INT NOT NULL,
    tx_count_1h INT NOT NULL,
    tx_count_24h INT NOT NULL,

    -- amount/behavior
    user_avg_amount FLOAT NOT NULL,
    amount_vs_user_avg FLOAT NOT NULL,

    -- geo/device/merchant signals
    is_foreign_country BOOLEAN NOT NULL,
    device_user_count INT NOT NULL,
    merchant_fraud_rate FLOAT NOT NULL,
    category_fraud_rate FLOAT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_features_created_at ON transaction_features(created_at);
CREATE TABLE IF NOT EXISTS risk_assessments (
    transaction_id TEXT PRIMARY KEY REFERENCES transactions(transaction_id),
    fraud_probability FLOAT NOT NULL,
    risk_score INT NOT NULL,
    decision TEXT NOT NULL,
    reasons JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_assessments_created_at ON risk_assessments(created_at);
CREATE TABLE IF NOT EXISTS review_actions (
    id BIGSERIAL PRIMARY KEY,
    transaction_id TEXT NOT NULL REFERENCES transactions(transaction_id),
    action TEXT NOT NULL CHECK (action IN ('approve', 'reject')),
    analyst TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_actions_tx ON review_actions(transaction_id);
CREATE INDEX IF NOT EXISTS idx_review_actions_created ON review_actions(created_at);
