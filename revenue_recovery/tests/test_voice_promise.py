"""Tests for POST /api/recovery-items/{item_id}/voice-promise and Hinglish promise extraction."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.hinglish_promise import HinglishPromiseExtractor


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _create_case(client: TestClient, customer_id: str = "cust_voice_test") -> str:
    payload = {
        "customer_id": customer_id,
        "amount_minor": 180000,
        "failure_reason": "soft_gateway_timeout",
        "payment_method": "upi",
    }
    resp = client.post("/api/recovery-items/create", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_voice_promise_demo_transcript_creates_promise_and_wait_decision(client: TestClient):
    """Target demo utterance extracts ₹12,000 promise and sets WAIT decision."""
    item_id = _create_case(client, customer_id="cust_voice_demo")
    transcript = "Abhi payment nahi ho pa raha hai, main 15 September ko 12000 rupees pay kar dungi."
    ref_date = "2026-09-04"

    resp = client.post(f"/api/recovery-items/{item_id}/voice-promise", json={
        "transcript": transcript,
        "reference_date": ref_date,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["extracted"]["intent"] == "promise_to_pay"
    assert data["extracted"]["amount_minor"] == 1200000
    assert data["extracted"]["promised_date"] == "2026-09-15"
    assert data["extracted"]["confidence"] >= 0.80
    assert data["promise_created"] is True
    assert data["promise"] is not None
    assert data["promise"]["recovery_item_id"] == item_id
    assert data["promise"]["promised_amount_minor"] == 1200000
    assert data["promise"]["status"] == "promised"
    assert data["decision"] == "WAIT"
    assert data["follow_up_date"] == "2026-09-15"

    # Confirm persistence via GET active promise endpoint
    promise_resp = client.get(f"/api/promises/by-item/{item_id}?active=true")
    assert promise_resp.status_code == 200
    promise_data = promise_resp.json()
    assert promise_data["promised_amount_minor"] == 1200000
    assert promise_data["promised_date"] == "2026-09-15"


def test_voice_promise_valid_hindi_transcript_creates_promise(client: TestClient):
    """Valid Hinglish transcript should extract a promise and create a PromiseRecord."""
    item_id = _create_case(client)
    transcript = "5 tareekh ko 50 hazaar transfer kar dunga"
    ref_date = str(date.today())

    resp = client.post(f"/api/recovery-items/{item_id}/voice-promise", json={
        "transcript": transcript,
        "reference_date": ref_date,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["extracted"]["intent"] == "promise_to_pay"
    assert data["extracted"]["amount_minor"] == 5000000
    assert data["extracted"]["promised_date"] == str(date.today() + timedelta(days=1))
    assert data["extracted"]["confidence"] >= 0.80
    assert data["extracted"]["source_text"] == transcript
    assert data["promise_created"] is True
    assert data["promise"] is not None
    assert data["promise"]["recovery_item_id"] == item_id
    assert data["promise"]["promised_amount_minor"] == 5000000
    assert data["promise"]["status"] == "promised"


def test_voice_promise_english_transcript_creates_promise(client: TestClient):
    """English transcript with amount and date should also work."""
    item_id = _create_case(client, customer_id="cust_voice_en")
    transcript = "I will pay 20000 rupees on Monday"

    resp = client.post(f"/api/recovery-items/{item_id}/voice-promise", json={
        "transcript": transcript,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["promise_created"] is True
    assert data["promise"] is not None
    assert data["promise"]["promised_amount_minor"] == 2000000


def test_voice_promise_missing_amount_returns_incomplete(client: TestClient):
    """Transcript with date but no amount should return incomplete promise, no promise record."""
    item_id = _create_case(client, customer_id="cust_voice_incomplete")
    transcript = "Kal clear kar dunga"

    resp = client.post(f"/api/recovery-items/{item_id}/voice-promise", json={
        "transcript": transcript,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["extracted"]["intent"] == "incomplete_promise"
    assert data["extracted"]["amount_minor"] is None
    assert data["promise_created"] is False
    assert data["promise"] is None


def test_voice_promise_missing_date_returns_incomplete(client: TestClient):
    """Transcript with amount but no date should return incomplete promise."""
    item_id = _create_case(client, customer_id="cust_voice_no_date")
    transcript = "Main 12000 rupees pay kar dunga"

    resp = client.post(f"/api/recovery-items/{item_id}/voice-promise", json={
        "transcript": transcript,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["extracted"]["intent"] == "incomplete_promise"
    assert data["extracted"]["amount_minor"] == 1200000
    assert data["extracted"]["promised_date"] is None
    assert data["promise_created"] is False
    assert data["promise"] is None


def test_voice_promise_no_payment_intent_returns_ambiguous(client: TestClient):
    """Transcript without payment intent should be ambiguous."""
    item_id = _create_case(client, customer_id="cust_voice_ambiguous")
    transcript = "Hello, how are you doing today?"

    resp = client.post(f"/api/recovery-items/{item_id}/voice-promise", json={
        "transcript": transcript,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["extracted"]["intent"] == "ambiguous"
    assert data["promise_created"] is False
    assert data["promise"] is None


def test_voice_promise_missing_item_returns_404(client: TestClient):
    """Non-existent item_id should return 404."""
    resp = client.post("/api/recovery-items/nonexistent_item_999/voice-promise", json={
        "transcript": "Monday ko payment karunga",
    })
    assert resp.status_code == 404
    assert "not found" in resp.json()["error"].lower()


def test_voice_promise_empty_transcript_returns_400(client: TestClient):
    """Empty transcript should return 400."""
    item_id = _create_case(client, customer_id="cust_voice_empty")
    resp = client.post(f"/api/recovery-items/{item_id}/voice-promise", json={
        "transcript": "   ",
    })
    assert resp.status_code == 400
    assert "transcript" in resp.json()["error"].lower()


def test_voice_promise_fixed_transcript_amount_date_match():
    """Unit test: fixed transcript should extract exact amount and date."""
    extractor = HinglishPromiseExtractor()
    ref = date(2026, 8, 1)
    result = extractor.extract("Monday ko clear kar dunga ₹20,000", reference_date=ref)

    assert result.intent == "promise_to_pay"
    assert result.amount_minor == 2000000
    assert result.promised_date == "2026-08-03"
    assert result.confidence >= 0.80
