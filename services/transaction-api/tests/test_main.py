from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import os
os.environ["API_KEY"] = "test-key"
os.environ["FRAUD_SCORER_URL"] = "http://mock-scorer"

from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_missing_api_key():
    response = client.post("/transaction", json={
        "card_last4": "1234",
        "amount": 100.0,
        "merchant": "amazon.com"
    })
    assert response.status_code == 422

def test_invalid_api_key():
    response = client.post("/transaction",
        json={"card_last4": "1234", "amount": 100.0, "merchant": "amazon.com"},
        headers={"x-api-key": "wrong-key"}
    )
    assert response.status_code == 401

def test_approved_transaction():
    mock_response = AsyncMock()
    mock_response.json.return_value = {"score": 10, "risk": "low"}

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        response = client.post("/transaction",
            json={"card_last4": "1234", "amount": 100.0, "merchant": "amazon.com"},
            headers={"x-api-key": "test-key"}
        )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

def test_blocked_high_risk_transaction():
    mock_response = AsyncMock()
    mock_response.json.return_value = {"score": 90, "risk": "high"}

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        response = client.post("/transaction",
            json={"card_last4": "1234", "amount": 100.0, "merchant": "shadystore.com"},
            headers={"x-api-key": "test-key"}
        )
    assert response.status_code == 403
