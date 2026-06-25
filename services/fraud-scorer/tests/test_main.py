from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_low_risk_transaction():
    response = client.post("/score", json={
        "card_last4": "1234",
        "amount": 100.0,
        "merchant": "amazon.com"
    })
    assert response.json()["risk"] == "low"
    assert response.json()["score"] < 40

def test_high_risk_blocked_merchant():
    response = client.post("/score", json={
        "card_last4": "1234",
        "amount": 100.0,
        "merchant": "shadystore.com"
    })
    assert response.json()["risk"] == "high"

def test_high_risk_amount():
    response = client.post("/score", json={
        "card_last4": "1234",
        "amount": 15000.0,
        "merchant": "amazon.com"
    })
    assert response.json()["risk"] == "high"

def test_medium_risk_amount():
    response = client.post("/score", json={
        "card_last4": "1234",
        "amount": 6000.0,
        "merchant": "amazon.com"
    })
    assert response.json()["risk"] == "medium"

def test_suspicious_card():
    response = client.post("/score", json={
        "card_last4": "0000",
        "amount": 100.0,
        "merchant": "amazon.com"
    })
    assert response.json()["score"] >= 40

def test_score_capped_at_100():
    response = client.post("/score", json={
        "card_last4": "0000",
        "amount": 15000.0,
        "merchant": "shadystore.com"
    })
    assert response.json()["score"] == 100
