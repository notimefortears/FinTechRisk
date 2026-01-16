# api/main.py
from datetime import datetime
from typing import Optional, List

import psycopg2
import os
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field
from models.scoring import score_from_features
from features.realtime_features import compute_and_upsert_features
from models.scoring import score_with_reasons
import json
from fastapi.middleware.cors import CORSMiddleware



DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "frauddb"),
    "user": os.getenv("DB_USER", "frauduser"),
    "password": os.getenv("DB_PASSWORD", "fraudpass"),
    "port": int(os.getenv("DB_PORT", "5432")),
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)

app = FastAPI(title="Fraud Detection Platform API", version="0.1.0")


origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class TransactionOut(BaseModel):
    transaction_id: str
    user_id: str
    card_id: str
    device_id: str
    amount: float
    currency: str
    merchant: str
    merchant_category: str
    country: str
    timestamp: datetime
    is_fraud: bool
    fraud_reason: Optional[str] = None


class TransactionCreate(BaseModel):
    user_id: str
    card_id: str
    device_id: str
    amount: float = Field(gt=0)
    currency: str = "USD"
    merchant: str
    merchant_category: str
    country: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/transactions", response_model=List[TransactionOut])
def list_transactions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    is_fraud: Optional[bool] = None,
    user_id: Optional[str] = None,
    card_id: Optional[str] = None,
    merchant: Optional[str] = None,
):
    where = []
    params = {}

    if is_fraud is not None:
        where.append("is_fraud = %(is_fraud)s")
        params["is_fraud"] = is_fraud
    if user_id:
        where.append("user_id = %(user_id)s")
        params["user_id"] = user_id
    if card_id:
        where.append("card_id = %(card_id)s")
        params["card_id"] = card_id
    if merchant:
        where.append("merchant = %(merchant)s")
        params["merchant"] = merchant

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT transaction_id, user_id, card_id, device_id, amount, currency,
               merchant, merchant_category, country, timestamp, is_fraud, fraud_reason
        FROM transactions
        {where_sql}
        ORDER BY timestamp DESC
        LIMIT %(limit)s OFFSET %(offset)s;
    """
    params["limit"] = limit
    params["offset"] = offset

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return rows
    finally:
        conn.close()


@app.get("/transactions/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: str):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT transaction_id, user_id, card_id, device_id, amount, currency,
                       merchant, merchant_category, country, timestamp, is_fraud, fraud_reason
                FROM transactions
                WHERE transaction_id = %s;
                """,
                (transaction_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Transaction not found")
            return row
    finally:
        conn.close()


@app.get("/stats/fraud")
def fraud_stats():
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*)::int AS total FROM transactions;")
            total = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*)::int AS fraud FROM transactions WHERE is_fraud = true;")
            fraud = cur.fetchone()["fraud"]

            rate = (fraud / total) if total else 0.0
            return {"total": total, "fraud": fraud, "fraud_rate": rate}
    finally:
        conn.close()


@app.post("/transactions", response_model=TransactionOut)
def create_transaction(tx: TransactionCreate):
    # NOTE: for now, this endpoint only stores the transaction.
    # In the next step we will score it with ML + rules and set is_fraud/risk.
    import uuid

    transaction_id = f"tx_{uuid.uuid4().hex}"
    now = datetime.utcnow()

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO transactions (
                    transaction_id, user_id, card_id, device_id, amount, currency,
                    merchant, merchant_category, country, timestamp, is_fraud, fraud_reason
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, NULL)
                RETURNING transaction_id, user_id, card_id, device_id, amount, currency,
                          merchant, merchant_category, country, timestamp, is_fraud, fraud_reason;
                """,
                (
                    transaction_id,
                    tx.user_id,
                    tx.card_id,
                    tx.device_id,
                    tx.amount,
                    tx.currency,
                    tx.merchant,
                    tx.merchant_category,
                    tx.country,
                    now,
                ),
            )
            conn.commit()
            return cur.fetchone()
    finally:
        conn.close()
from psycopg2.extras import RealDictCursor

@app.get("/transactions/{transaction_id}/features")
def get_transaction_features(transaction_id: str):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM transaction_features WHERE transaction_id = %s;",
                (transaction_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Features not found for this transaction")
            return row
    finally:
        conn.close()

@app.get("/")
def root():
    return {"message": "Fraud Detection Platform API. Visit /docs"}

class ScoreResponse(BaseModel):
    transaction_id: str
    fraud_probability: float
    risk_score: int
    decision: str


@app.post("/score/{transaction_id}", response_model=ScoreResponse)
def score_transaction(transaction_id: str):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM transaction_features WHERE transaction_id = %s;", (transaction_id,))
            feats = cur.fetchone()
            if not feats:
                raise HTTPException(status_code=404, detail="Features not found for this transaction")

        prob = score_from_features(feats)
        risk_score = int(round(prob * 100))

        # simple decision policy (we’ll tune later)
        if risk_score >= 90:
            decision = "block"
        elif risk_score >= 60:
            decision = "manual_review"
        else:
            decision = "approve"

        return {
            "transaction_id": transaction_id,
            "fraud_probability": prob,
            "risk_score": risk_score,
            "decision": decision,
        }
    finally:
        conn.close()
class ScoreWithReasons(BaseModel):
    transaction_id: str
    fraud_probability: float
    risk_score: int
    decision: str
    reasons: list
@app.post("/transactions/score", response_model=ScoreWithReasons)
def create_and_score_transaction(tx: TransactionCreate):
    import uuid
    transaction_id = f"tx_{uuid.uuid4().hex}"
    now = datetime.utcnow()

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Ensure FK dimension rows exist
            cur.execute("""
                INSERT INTO users (user_id, home_country, account_age_days, avg_transaction_amount)
                VALUES (%s, %s, 30, 100.0)
                ON CONFLICT (user_id) DO NOTHING;
            """, (tx.user_id, tx.country))

            cur.execute("""
                INSERT INTO cards (card_id, user_id, issuer, is_stolen)
                VALUES (%s, %s, 'Visa', false)
                ON CONFLICT (card_id) DO NOTHING;
            """, (tx.card_id, tx.user_id))

            cur.execute("""
                INSERT INTO devices (device_id, device_type)
                VALUES (%s, 'mobile')
                ON CONFLICT (device_id) DO NOTHING;
            """, (tx.device_id,))

            # Insert transaction
            cur.execute("""
                INSERT INTO transactions (
                    transaction_id, user_id, card_id, device_id, amount, currency,
                    merchant, merchant_category, country, timestamp, is_fraud, fraud_reason
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, NULL);
            """, (
                transaction_id, tx.user_id, tx.card_id, tx.device_id, tx.amount, tx.currency,
                tx.merchant, tx.merchant_category, tx.country, now
            ))

        conn.commit()
    finally:
        conn.close()

    # Build features for this transaction
    feats = compute_and_upsert_features(transaction_id)

    # Score + explain
    prob, reasons = score_with_reasons(feats, top_k=3)
    risk_score = int(round(prob * 100))

    if risk_score >= 90:
        decision = "block"
    elif risk_score >= 60:
        decision = "manual_review"
    else:
        decision = "approve"

    # Store assessment
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO risk_assessments (transaction_id, fraud_probability, risk_score, decision, reasons)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (transaction_id) DO UPDATE SET
                    fraud_probability = EXCLUDED.fraud_probability,
                    risk_score = EXCLUDED.risk_score,
                    decision = EXCLUDED.decision,
                    reasons = EXCLUDED.reasons,
                    created_at = NOW();
            """, (transaction_id, float(prob), int(risk_score), decision, json.dumps(reasons)))
        conn.commit()
    finally:
        conn.close()

    return {
        "transaction_id": transaction_id,
        "fraud_probability": float(prob),
        "risk_score": int(risk_score),
        "decision": decision,
        "reasons": reasons,
    }
@app.get("/transactions/{transaction_id}/assessment")
def get_assessment(transaction_id: str):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM risk_assessments WHERE transaction_id = %s;", (transaction_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Assessment not found")
            return row
    finally:
        conn.close()
class ReviewActionIn(BaseModel):
    action: str  # "approve" or "reject"
    analyst: str = "analyst_1"
    notes: str | None = None
@app.get("/review/queue")
def review_queue(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    ra.transaction_id,
                    ra.risk_score,
                    ra.fraud_probability,
                    ra.decision,
                    ra.created_at,
                    t.user_id,
                    t.amount,
                    t.merchant,
                    t.country,
                    t.timestamp
                FROM risk_assessments ra
                JOIN transactions t ON t.transaction_id = ra.transaction_id
                WHERE ra.decision = 'manual_review'
                ORDER BY ra.created_at DESC
                LIMIT %s OFFSET %s;
            """, (limit, offset))
            return cur.fetchall()
    finally:
        conn.close()
@app.get("/review/case/{transaction_id}")
def review_case(transaction_id: str):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM transactions WHERE transaction_id=%s;", (transaction_id,))
            tx = cur.fetchone()
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")

            cur.execute("SELECT * FROM transaction_features WHERE transaction_id=%s;", (transaction_id,))
            feats = cur.fetchone()

            cur.execute("SELECT * FROM risk_assessments WHERE transaction_id=%s;", (transaction_id,))
            assess = cur.fetchone()

            cur.execute("""
                SELECT id, action, analyst, notes, created_at
                FROM review_actions
                WHERE transaction_id=%s
                ORDER BY created_at DESC;
            """, (transaction_id,))
            history = cur.fetchall()

            return {"transaction": tx, "features": feats, "assessment": assess, "review_history": history}
    finally:
        conn.close()
@app.post("/review/case/{transaction_id}/action")
def submit_review_action(transaction_id: str, body: ReviewActionIn):
    if body.action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # ensure assessment exists
            cur.execute("SELECT decision FROM risk_assessments WHERE transaction_id=%s;", (transaction_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Assessment not found for transaction")

            # store analyst decision
            cur.execute("""
                INSERT INTO review_actions (transaction_id, action, analyst, notes)
                VALUES (%s, %s, %s, %s)
                RETURNING id, transaction_id, action, analyst, notes, created_at;
            """, (transaction_id, body.action, body.analyst, body.notes))

            action_row = cur.fetchone()

            # optional: write back “confirmed fraud” when rejected
            # (in real fintech this may be "chargeback/confirmed fraud" later,
            # but for your showcase this is great.)
            if body.action == "reject":
                cur.execute("""
                    UPDATE transactions
                    SET is_fraud = true, fraud_reason = 'confirmed_by_review'
                    WHERE transaction_id = %s;
                """, (transaction_id,))

            # update assessment decision for auditability
            new_decision = "block" if body.action == "reject" else "approve"
            cur.execute("""
                UPDATE risk_assessments
                SET decision = %s
                WHERE transaction_id = %s;
            """, (new_decision, transaction_id))

        conn.commit()
        return action_row
    finally:
        conn.close()
@app.get("/monitoring/summary")
def monitoring_summary():
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                  COUNT(*)::int AS total,
                  SUM(CASE WHEN decision='approve' THEN 1 ELSE 0 END)::int AS approve,
                  SUM(CASE WHEN decision='manual_review' THEN 1 ELSE 0 END)::int AS manual_review,
                  SUM(CASE WHEN decision='block' THEN 1 ELSE 0 END)::int AS block
                FROM risk_assessments
                WHERE created_at >= NOW() - INTERVAL '24 hours';
            """)
            return cur.fetchone()
    finally:
        conn.close()


@app.get("/monitoring/score_buckets")
def monitoring_score_buckets():
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                  CASE
                    WHEN risk_score >= 90 THEN '90-100'
                    WHEN risk_score >= 60 THEN '60-89'
                    WHEN risk_score >= 30 THEN '30-59'
                    ELSE '0-29'
                  END AS bucket,
                  COUNT(*)::int AS count
                FROM risk_assessments
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY bucket
                ORDER BY bucket;
            """)
            return cur.fetchall()
    finally:
        conn.close()


@app.get("/monitoring/top_merchants")
def monitoring_top_merchants(limit: int = Query(10, ge=1, le=50)):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                  t.merchant,
                  COUNT(*)::int AS tx_count,
                  AVG(ra.risk_score)::float AS avg_risk,
                  SUM(CASE WHEN ra.decision='block' THEN 1 ELSE 0 END)::int AS blocks,
                  SUM(CASE WHEN ra.decision='manual_review' THEN 1 ELSE 0 END)::int AS reviews
                FROM risk_assessments ra
                JOIN transactions t ON t.transaction_id = ra.transaction_id
                WHERE ra.created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY t.merchant
                ORDER BY avg_risk DESC
                LIMIT %s;
            """, (limit,))
            return cur.fetchall()
    finally:
        conn.close()
