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
