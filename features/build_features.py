# features/build_features.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor


DB_CONFIG = {
    "host": "localhost",
    "database": "frauddb",
    "user": "frauduser",
    "password": "fraudpass",
    "port": 5432,
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def ensure_user_home_country(conn):
    """
    Earlier ingestion used an approximation for users.home_country.
    Now we correct it properly: set home_country = most frequent transaction country per user.
    This makes 'foreign country' feature meaningful.
    """
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE users u
            SET home_country = sub.country
            FROM (
                SELECT user_id, country
                FROM (
                    SELECT user_id, country,
                           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY COUNT(*) DESC) AS rn
                    FROM transactions
                    GROUP BY user_id, country
                ) ranked
                WHERE rn = 1
            ) sub
            WHERE u.user_id = sub.user_id;
        """)
    conn.commit()


def fetch_transactions_missing_features(conn, limit: int = 2000) -> List[Dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT t.transaction_id, t.user_id, t.device_id, t.merchant, t.merchant_category,
                   t.amount, t.country, t.timestamp
            FROM transactions t
            LEFT JOIN transaction_features f ON f.transaction_id = t.transaction_id
            WHERE f.transaction_id IS NULL
            ORDER BY t.timestamp ASC
            LIMIT %s;
            """,
            (limit,),
        )
        return cur.fetchall()


def compute_velocity_counts(conn, transaction_id: str) -> Dict[str, int]:
    """
    Compute velocity based on the transaction's timestamp and user_id.
    We'll do this in one SQL call for realism.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            WITH base AS (
              SELECT user_id, timestamp
              FROM transactions
              WHERE transaction_id = %s
            )
            SELECT
              (SELECT COUNT(*)::int FROM transactions t, base b
               WHERE t.user_id = b.user_id AND t.timestamp >= b.timestamp - INTERVAL '5 minutes'
                 AND t.timestamp <= b.timestamp) AS tx_count_5m,
              (SELECT COUNT(*)::int FROM transactions t, base b
               WHERE t.user_id = b.user_id AND t.timestamp >= b.timestamp - INTERVAL '1 hour'
                 AND t.timestamp <= b.timestamp) AS tx_count_1h,
              (SELECT COUNT(*)::int FROM transactions t, base b
               WHERE t.user_id = b.user_id AND t.timestamp >= b.timestamp - INTERVAL '24 hours'
                 AND t.timestamp <= b.timestamp) AS tx_count_24h;
            """,
            (transaction_id,),
        )
        return cur.fetchone()


def compute_user_avg_amount(conn, user_id: str, up_to_ts: datetime) -> float:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(AVG(amount), 0)::float
            FROM transactions
            WHERE user_id = %s AND timestamp <= %s;
            """,
            (user_id, up_to_ts),
        )
        return float(cur.fetchone()[0])


def compute_device_user_count(conn, device_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(DISTINCT user_id)::int
            FROM transactions
            WHERE device_id = %s;
            """,
            (device_id,),
        )
        return int(cur.fetchone()[0])


def compute_merchant_fraud_rate(conn, merchant: str) -> float:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              CASE WHEN COUNT(*) = 0 THEN 0
                   ELSE (SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::float / COUNT(*)::float)
              END AS rate
            FROM transactions
            WHERE merchant = %s;
            """,
            (merchant,),
        )
        return float(cur.fetchone()[0])


def compute_category_fraud_rate(conn, category: str) -> float:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              CASE WHEN COUNT(*) = 0 THEN 0
                   ELSE (SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::float / COUNT(*)::float)
              END AS rate
            FROM transactions
            WHERE merchant_category = %s;
            """,
            (category,),
        )
        return float(cur.fetchone()[0])


def compute_is_foreign(conn, user_id: str, tx_country: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT home_country FROM users WHERE user_id = %s;", (user_id,))
        row = cur.fetchone()
        home = row[0] if row else None
    return (home is not None) and (tx_country != home)


def upsert_features(conn, transaction_id: str, feats: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO transaction_features (
                transaction_id,
                tx_count_5m, tx_count_1h, tx_count_24h,
                user_avg_amount, amount_vs_user_avg,
                is_foreign_country, device_user_count,
                merchant_fraud_rate, category_fraud_rate
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
            """,
            (
                transaction_id,
                feats["tx_count_5m"],
                feats["tx_count_1h"],
                feats["tx_count_24h"],
                feats["user_avg_amount"],
                feats["amount_vs_user_avg"],
                feats["is_foreign_country"],
                feats["device_user_count"],
                feats["merchant_fraud_rate"],
                feats["category_fraud_rate"],
            ),
        )
    conn.commit()


def build_features_batch(limit: int = 2000) -> int:
    conn = get_conn()
    try:
        ensure_user_home_country(conn)

        rows = fetch_transactions_missing_features(conn, limit=limit)
        if not rows:
            print("No transactions missing features.")
            return 0

        for r in rows:
            tx_id = r["transaction_id"]
            user_id = r["user_id"]
            device_id = r["device_id"]
            merchant = r["merchant"]
            category = r["merchant_category"]
            amount = float(r["amount"])
            country = r["country"]
            ts = r["timestamp"]

            velocity = compute_velocity_counts(conn, tx_id)
            user_avg = compute_user_avg_amount(conn, user_id, ts)
            amount_vs_avg = amount / user_avg if user_avg > 0 else 0.0
            is_foreign = compute_is_foreign(conn, user_id, country)
            device_users = compute_device_user_count(conn, device_id)
            merch_rate = compute_merchant_fraud_rate(conn, merchant)
            cat_rate = compute_category_fraud_rate(conn, category)

            feats = {
                **velocity,
                "user_avg_amount": user_avg,
                "amount_vs_user_avg": amount_vs_avg,
                "is_foreign_country": is_foreign,
                "device_user_count": device_users,
                "merchant_fraud_rate": merch_rate,
                "category_fraud_rate": cat_rate,
            }

            upsert_features(conn, tx_id, feats)

        print(f"Built features for {len(rows)} transactions.")
        return len(rows)

    finally:
        conn.close()


if __name__ == "__main__":
    build_features_batch(limit=5000)
