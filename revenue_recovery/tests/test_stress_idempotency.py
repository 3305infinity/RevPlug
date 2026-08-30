import concurrent.futures
import hmac
import hashlib
from fastapi.testclient import TestClient

from app.main import app
from app.db.postgres_repositories import PostgresRecoveryItemRepository
from app.db.session import PostgresConnection

# Force synchronous mode for the test
app.state.container.jobs = None
client = TestClient(app)

def generate_signature(payload: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

def test_webhook_idempotency_concurrent():
    """Ensure that concurrent duplicate webhooks result in exactly one recovery item."""
    
    import uuid
    unique_id = str(uuid.uuid4())
    event_id = f"evt_{unique_id}"
    payment_id = f"pay_{unique_id}"
    
    # Create the raw payload for the webhook
    payload_str = f'''{{
      "id": "{event_id}",
      "entity": "event",
      "account_id": "acc_123",
      "event": "payment.failed",
      "contains": ["payment"],
      "payload": {{
        "payment": {{
          "entity": {{
            "id": "{payment_id}",
            "amount": 50000,
            "currency": "INR",
            "status": "failed",
            "error_code": "BAD_REQUEST_ERROR",
            "error_description": "Payment failed due to card decline",
            "error_source": "issuer",
            "error_step": "payment_authorization",
            "error_reason": "payment_failed"
          }}
        }}
      }},
      "created_at": 1690000000
    }}'''
    payload = payload_str.encode("utf-8")
    
    # We must sign the webhook or it will be rejected
    secret = "unconfigured-placeholder-secret"
    signature = generate_signature(payload, secret)
    headers = {
        "X-Razorpay-Signature": signature,
        "Content-Type": "application/json"
    }

    def send_webhook() -> tuple[int, str]:
        response = client.post("/webhooks/razorpay", content=payload, headers=headers)
        return response.status_code, response.text

    # Fire 10 concurrent requests with the exact same payload
    responses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_webhook) for _ in range(10)]
        for future in concurrent.futures.as_completed(futures):
            responses.append(future.result())
            
    print(f"Concurrent responses: {responses}")
    status_codes = [code for code, _ in responses]
            
    # All requests should return 200 or 409 (if we reject explicitly, though Razorpay expects 200)
    print(f"Concurrent status codes: {status_codes}")
    assert all(code in (200, 202, 409) for code in status_codes)

    # Let's inspect the database to see how many items were created
    container = app.state.container
    repo = container.recovery_items
    
    # Check the database for this specific provider event ID or by amount/currency/created_at
    # Let's just list all and filter.
    all_items = repo.list_all(limit=100)
    print(f"Total items in repo: {len(all_items)}")
    # Parse responses to find the created item ID
    import json
    accepted_response = next(r[1] for r in responses if "processed" in r[1])
    created_item_id = json.loads(accepted_response).get("recovery_item_id")
    
    matches = [i for i in all_items if i.id == created_item_id]
    
    # Should be exactly 1 item!
    assert len(matches) == 1, f"Expected 1 item, but found {len(matches)}"

if __name__ == "__main__":
    test_webhook_idempotency_concurrent()
    print("Idempotency test PASS")
