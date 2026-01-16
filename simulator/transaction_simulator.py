# simulator/transaction_simulator.py

import random
import uuid
from datetime import datetime, timedelta
import json

# ---------------------------
# Fake domain data
# ---------------------------
COUNTRIES = ["US", "UK", "DE", "FR", "IN", "JP", "BR"]
MERCHANTS = [
    ("Amazon", "ecommerce"),
    ("Walmart", "retail"),
    ("Uber", "transport"),
    ("Netflix", "subscription"),
    ("Apple", "electronics"),
    ("Airbnb", "travel"),
    ("Binance", "crypto"),
]

DEVICES = ["mobile", "desktop", "tablet"]

# ---------------------------
# Entity generators
# ---------------------------

def generate_user(user_id):
    return {
        "user_id": f"user_{user_id}",
        "home_country": random.choice(COUNTRIES),
        "account_age_days": random.randint(10, 3000),
        "avg_transaction_amount": round(random.uniform(20, 200), 2),
    }

def generate_card(user_id):
    return {
        "card_id": f"card_{uuid.uuid4().hex[:8]}",
        "user_id": user_id,
        "issuer": random.choice(["Visa", "Mastercard", "Amex"]),
        "is_stolen": False
    }

def generate_device():
    return {
        "device_id": f"device_{uuid.uuid4().hex[:8]}",
        "device_type": random.choice(DEVICES)
    }

# ---------------------------
# Fraud patterns
# ---------------------------

def apply_fraud_patterns(transaction, user, card):
    fraud = False
    reason = None

    # 1. Stolen card used abroad
    if card["is_stolen"]:
        if transaction["country"] != user["home_country"]:
            fraud = True
            reason = "stolen_card_foreign_use"

    # 2. Very large transaction
    if transaction["amount"] > user["avg_transaction_amount"] * 6:
        fraud = True
        reason = "abnormally_large_amount"

    # 3. Crypto merchants higher risk
    if transaction["merchant_category"] == "crypto" and random.random() < 0.3:
        fraud = True
        reason = "high_risk_merchant"

    return fraud, reason

# ---------------------------
# Transaction generator
# ---------------------------

def generate_transaction(user, card, device, timestamp):
    merchant, category = random.choice(MERCHANTS)
    amount = round(random.uniform(1, user["avg_transaction_amount"] * 4), 2)
    country = random.choice(COUNTRIES)

    transaction = {
        "transaction_id": f"tx_{uuid.uuid4().hex}",
        "user_id": user["user_id"],
        "card_id": card["card_id"],
        "device_id": device["device_id"],
        "amount": amount,
        "currency": "USD",
        "merchant": merchant,
        "merchant_category": category,
        "country": country,
        "timestamp": timestamp.isoformat(),
    }

    is_fraud, fraud_reason = apply_fraud_patterns(transaction, user, card)

    transaction["is_fraud"] = is_fraud
    transaction["fraud_reason"] = fraud_reason

    return transaction

# ---------------------------
# Dataset generator
# ---------------------------

def generate_dataset(
    num_users=50,
    transactions_per_user=100,
    fraud_rate=0.05,
    output_file="transactions.json"
):
    users = [generate_user(i) for i in range(num_users)]
    cards = {}
    devices = {}

    for u in users:
        cards[u["user_id"]] = generate_card(u["user_id"])
        devices[u["user_id"]] = generate_device()

    # Mark some cards as stolen
    stolen_count = int(num_users * fraud_rate)
    stolen_users = random.sample(users, stolen_count)
    for u in stolen_users:
        cards[u["user_id"]]["is_stolen"] = True

    all_transactions = []
    now = datetime.utcnow()

    for user in users:
        card = cards[user["user_id"]]
        device = devices[user["user_id"]]

        start_time = now - timedelta(days=random.randint(1, 60))

        for i in range(transactions_per_user):
            tx_time = start_time + timedelta(minutes=i * random.randint(1, 60))
            tx = generate_transaction(user, card, device, tx_time)
            all_transactions.append(tx)

    random.shuffle(all_transactions)

    with open(output_file, "w") as f:
        json.dump(all_transactions, f, indent=2)

    print(f"Generated {len(all_transactions)} transactions")
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    generate_dataset(
        num_users=100,
        transactions_per_user=200,
        fraud_rate=0.08,
        output_file="transactions.json"
    )
