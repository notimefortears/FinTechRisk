#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
N="${1:-5}"

echo "Creating $N manual_review-ish transactions..."

for i in $(seq 1 "$N"); do
  user="demo_user_review_$i"
  card="demo_card_review_$i"
  device="device_df2397fe"   # reuse to raise risk features a bit
  amount="800.00"            # tends to land in manual_review band in your setup
  country="JP"

  curl -s -X POST "$API_BASE/transactions/score" \
    -H "Content-Type: application/json" \
    -d "{
      \"user_id\":\"$user\",
      \"card_id\":\"$card\",
      \"device_id\":\"$device\",
      \"amount\": $amount,
      \"currency\":\"USD\",
      \"merchant\":\"Binance\",
      \"merchant_category\":\"crypto\",
      \"country\":\"$country\"
    }" | python -m json.tool | sed 's/^/  /'

  echo "----"
done

echo "Done. Open the dashboard queue."

