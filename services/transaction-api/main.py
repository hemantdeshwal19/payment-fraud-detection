from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import httpx
import os

app = FastAPI()

API_KEY = os.getenv("API_KEY")
FRAUD_SCORER_URL = os.getenv("FRAUD_SCORER_URL", "http://localhost:8001")

class Transaction(BaseModel):
    card_last4: str
    amount: float
    merchant: str

def verify_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/transaction")
async def process_transaction(txn: Transaction, x_api_key: str = Header(...)):
    verify_key(x_api_key)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{FRAUD_SCORER_URL}/score",
            json=txn.model_dump()
        )
    
    result = await  response.json()
    
    if result["risk"] == "high":
        raise HTTPException(status_code=403, detail="Transaction blocked — high fraud risk")
    
    return {"status": "approved", "fraud_score": result["score"]}
