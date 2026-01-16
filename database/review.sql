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
