CREATE TABLE IF NOT EXISTS risk_assessments (
    transaction_id TEXT PRIMARY KEY REFERENCES transactions(transaction_id),
    fraud_probability FLOAT NOT NULL,
    risk_score INT NOT NULL,
    decision TEXT NOT NULL,
    reasons JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_assessments_created_at ON risk_assessments(created_at);
