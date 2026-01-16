# ingestion/ingest_transactions.py

import json
import psycopg2
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "database": "frauddb",
    "user": "frauduser",
    "password": "fraudpass"
}

def connect():
    return psycopg2.connect(**DB_CONFIG)

def ingest(transactions_file):
    conn = connect()
    cur = conn.cursor()

    with open(transactions_file, "r") as f:
        transactions = json.load(f)

    users = {}
    cards = {}
    devices = {}

    # Build dimension tables from transaction data
    for tx in transactions:
        users[tx["user_id"]] = {
            "user_id": tx["user_id"],
            "home_country": tx["country"],  # approximation for now
            "account_age_days": 365,
            "avg_transaction_amount": 100.0
        }

        cards[tx["card_id"]] = {
            "card_id": tx["card_id"],
            "user_id": tx["user_id"],
            "issuer": "Visa",
            "is_stolen": False
        }

        devices[tx["device_id"]] = {
            "device_id": tx["device_id"],
            "device_type": "mobile"
        }

    # Insert users
    for u in users.values():
        cur.execute("""
            INSERT INTO users (user_id, home_country, account_age_days, avg_transaction_amount)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING;
        """, (u["user_id"], u["home_country"], u["account_age_days"], u["avg_transaction_amount"]))

    # Insert cards
    for c in cards.values():
        cur.execute("""
            INSERT INTO cards (card_id, user_id, issuer, is_stolen)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (card_id) DO NOTHING;
        """, (c["card_id"], c["user_id"], c["issuer"], c["is_stolen"]))

    # Insert devices
    for d in devices.values():
        cur.execute("""
            INSERT INTO devices (device_id, device_type)
            VALUES (%s, %s)
            ON CONFLICT (device_id) DO NOTHING;
        """, (d["device_id"], d["device_type"]))

    # Insert transactions
    for tx in transactions:
        cur.execute("""
            INSERT INTO transactions (
                transaction_id, user_id, card_id, device_id, amount, currency,
                merchant, merchant_category, country, timestamp,
                is_fraud, fraud_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (transaction_id) DO NOTHING;
        """, (
            tx["transaction_id"],
            tx["user_id"],
            tx["card_id"],
            tx["device_id"],
            tx["amount"],
            tx["currency"],
            tx["merchant"],
            tx["merchant_category"],
            tx["country"],
            datetime.fromisoformat(tx["timestamp"]),
            tx["is_fraud"],
            tx["fraud_reason"]
        ))

    conn.commit()
    cur.close()
    conn.close()

    print(f"Ingested {len(transactions)} transactions into PostgreSQL")


if __name__ == "__main__":
    # Path is relative to project root
    ingest("simulator/transactions.json")
