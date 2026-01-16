# features/realtime_features.py
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "frauddb"),
    "user": os.getenv("DB_USER", "frauduser"),
    "password": os.getenv("DB_PASSWORD", "fraudpass"),
    "port": int(os.getenv("DB_PORT", "5432")),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def compute_and_upsert_features(transaction_id: str) -> dict:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # get base tx
            cur.execute("""
                SELECT transaction_id, user_id, device_id, merchant, merchant_category,
                       amount, country, timestamp
                FROM transactions
                WHERE transaction_id = %s;
            """, (transaction_id,))
            tx = cur.fetchone()
            if not tx:
                raise ValueError("Transaction not found")

            user_id = tx["user_id"]
            device_id = tx["device_id"]
            merchant = tx["merchant"]
            category = tx["merchant_category"]
            amount = float(tx["amount"])
            country = tx["country"]
            ts = tx["timestamp"]

            # velocity (5m/1h/24h) up to this tx timestamp
            cur.execute("""
                SELECT
                  COUNT(*) FILTER (WHERE timestamp >= %s - INTERVAL '5 minutes' AND timestamp <= %s)::int AS tx_count_5m,
                  COUNT(*) FILTER (WHERE timestamp >= %s - INTERVAL '1 hour' AND timestamp <= %s)::int AS tx_count_1h,
                  COUNT(*) FILTER (WHERE timestamp >= %s - INTERVAL '24 hours' AND timestamp <= %s)::int AS tx_count_24h
                FROM transactions
                WHERE user_id = %s;
            """, (ts, ts, ts, ts, ts, ts, user_id))
            vel = cur.fetchone()

            # user avg amount (up to now)
            cur.execute("""
                SELECT COALESCE(AVG(amount), 0)::float AS avg_amt
                FROM transactions
                WHERE user_id = %s AND timestamp <= %s;
            """, (user_id, ts))
            user_avg = float(cur.fetchone()["avg_amt"])
            amount_vs_avg = (amount / user_avg) if user_avg > 0 else 0.0

            # home_country
            cur.execute("SELECT home_country FROM users WHERE user_id = %s;", (user_id,))
            row = cur.fetchone()
            home = row["home_country"] if row else None
            is_foreign = (home is not None) and (country != home)

            # device reuse (# distinct users)
            cur.execute("""
                SELECT COUNT(DISTINCT user_id)::int AS cnt
                FROM transactions
                WHERE device_id = %s;
            """, (device_id,))
            device_user_count = int(cur.fetchone()["cnt"])

            # merchant fraud rate
            cur.execute("""
                SELECT CASE WHEN COUNT(*) = 0 THEN 0
                            ELSE (SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::float / COUNT(*)::float)
                       END AS rate
                FROM transactions
                WHERE merchant = %s;
            """, (merchant,))
            merchant_rate = float(cur.fetchone()["rate"])

            # category fraud rate
            cur.execute("""
                SELECT CASE WHEN COUNT(*) = 0 THEN 0
                            ELSE (SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::float / COUNT(*)::float)
                       END AS rate
                FROM transactions
                WHERE merchant_category = %s;
            """, (category,))
            category_rate = float(cur.fetchone()["rate"])

            feats = {
                "transaction_id": transaction_id,
                "tx_count_5m": int(vel["tx_count_5m"]),
                "tx_count_1h": int(vel["tx_count_1h"]),
                "tx_count_24h": int(vel["tx_count_24h"]),
                "user_avg_amount": float(user_avg),
                "amount_vs_user_avg": float(amount_vs_avg),
                "is_foreign_country": bool(is_foreign),
                "device_user_count": int(device_user_count),
                "merchant_fraud_rate": float(merchant_rate),
                "category_fraud_rate": float(category_rate),
            }

            # upsert into feature store
            cur.execute("""
                INSERT INTO transaction_features (
                    transaction_id,
                    tx_count_5m, tx_count_1h, tx_count_24h,
                    user_avg_amount, amount_vs_user_avg,
                    is_foreign_country, device_user_count,
                    merchant_fraud_rate, category_fraud_rate
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (transaction_id) DO UPDATE SET
                    tx_count_5m = EXCLUDED.tx_count_5m,
                    tx_count_1h = EXCLUDED.tx_count_1h,
                    tx_count_24h = EXCLUDED.tx_count_24h,
                    user_avg_amount = EXCLUDED.user_avg_amount,
                    amount_vs_user_avg = EXCLUDED.amount_vs_user_avg,
                    is_foreign_country = EXCLUDED.is_foreign_country,
                    device_user_count = EXCLUDED.device_user_count,
                    merchant_fraud_rate = EXCLUDED.merchant_fraud_rate,
                    category_fraud_rate = EXCLUDED.category_fraud_rate,
                    created_at = NOW();
            """, (
                transaction_id,
                feats["tx_count_5m"], feats["tx_count_1h"], feats["tx_count_24h"],
                feats["user_avg_amount"], feats["amount_vs_user_avg"],
                feats["is_foreign_country"], feats["device_user_count"],
                feats["merchant_fraud_rate"], feats["category_fraud_rate"],
            ))

        conn.commit()
        return feats

    finally:
        conn.close()
