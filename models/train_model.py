# models/train_model.py
import os
import joblib
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

DB_CONFIG = {
    "host": "localhost",
    "database": "frauddb",
    "user": "frauduser",
    "password": "fraudpass",
    "port": 5432,
}

FEATURE_COLS = [
    "tx_count_5m",
    "tx_count_1h",
    "tx_count_24h",
    "user_avg_amount",
    "amount_vs_user_avg",
    "is_foreign_country",
    "device_user_count",
    "merchant_fraud_rate",
    "category_fraud_rate",
]

def fetch_training_data():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                SELECT
                    f.transaction_id,
                    {", ".join("f."+c for c in FEATURE_COLS)},
                    t.is_fraud::int AS label
                FROM transaction_features f
                JOIN transactions t ON t.transaction_id = f.transaction_id;
            """)
            rows = cur.fetchall()

        X = []
        y = []
        for r in rows:
            X.append([float(r[c]) if c != "is_foreign_country" else (1.0 if r[c] else 0.0) for c in FEATURE_COLS])
            y.append(int(r["label"]))

        return np.array(X, dtype=float), np.array(y, dtype=int)

    finally:
        conn.close()

def main():
    X, y = fetch_training_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])

    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)

    auc = roc_auc_score(y_test, probs)
    print("ROC AUC:", round(float(auc), 4))
    print(classification_report(y_test, preds, digits=4))

    os.makedirs("models/artifacts", exist_ok=True)
    joblib.dump(
        {"model": model, "feature_cols": FEATURE_COLS},
        "models/artifacts/fraud_model.joblib"
    )
    print("Saved model to models/artifacts/fraud_model.joblib")

if __name__ == "__main__":
    main()

