from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

BLOCKED_MERCHANTS = {"shadystore.com", "fraudshop.net"}
HIGH_RISK_AMOUNT = 10000.0
MEDIUM_RISK_AMOUNT = 5000.0

class Transaction(BaseModel):
    card_last4: str
    amount: float
    merchant: str

def calculate_score(txn: Transaction) -> tuple[int, str]:
    score = 0

    if txn.merchant in BLOCKED_MERCHANTS:
        score += 80

    if txn.amount >= HIGH_RISK_AMOUNT:
        score += 60
    elif txn.amount >= MEDIUM_RISK_AMOUNT:
        score += 30

    if txn.card_last4 in {"0000", "9999"}:
        score += 40

    score = min(score, 100)

    if score >= 60:
        risk = "high"
    elif score >= 30:
        risk = "medium"
    else:
        risk = "low"

    return score, risk

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/score")
def score_transaction(txn: Transaction):
    score, risk = calculate_score(txn)
    return {"score": score, "risk": risk}
# test
