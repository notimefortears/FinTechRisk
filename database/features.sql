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
