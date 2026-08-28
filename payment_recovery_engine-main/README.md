# Payment Recovery Engine

> Tested reference implementation for deterministic payment-failure classification, bounded retry policy, idempotent state transitions, and n8n operations.

**Status:** Validated reference implementation — not a production or client deployment
**Stack:** Python 3.11 · FastAPI · PostgreSQL 16 · n8n · Stripe test mode · Docker

This repository demonstrates the safety boundaries of a recurring-payment recovery system. It does not claim a recovery rate, revenue outcome, time saving, production SLA, or client result.

## Architecture

```text
Stripe webhook (exact raw bytes)
        ↓
Python ingress: signature verification + provider normalization
        ↓
deterministic policy + state transition
        ↓
PostgreSQL event / retry / notification ledgers
        ↓
n8n: schedules, provider calls, email, operational reports
```

Python owns business rules. n8n remains useful for orchestration and credentials, but does not classify declines or calculate retry schedules. See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).

## Implemented and tested

- exact-raw-body Stripe HMAC verification, multiple `v1` signatures, and timestamp tolerance;
- provider-code normalization separated from policy;
- explicit decisions containing retry permission, next retry, budget, notification, manual review, reason, and policy version;
- bounded schedules for insufficient-funds and temporary-processing failures;
- no unattended retry for expired/invalid methods, authentication, security/fraud, hard declines, or unknown codes;
- duplicate-event and notification suppression;
- terminal recovery/cancellation states that clear future retries;
- thread-safe reference transitions for concurrent/replayed events;
- PostgreSQL atomic/reclaimable retry leases with `FOR UPDATE SKIP LOCKED`, unique idempotency keys, and optimistic terminal updates;
- inactive, credential-free n8n imports for internal intake, persistence, notifications, retry work, and reporting;
- Python, artifact, service, concurrency, and PostgreSQL integration tests;
- Ruff, GitHub Actions, Docker, and Docker Compose reproducibility.

The in-memory `RecoveryStore` is a testable state-machine reference. Production persistence belongs in PostgreSQL; it must not be replaced with process memory.

## Conservative policy defaults

| Normalized category | Automatic retry | Default action |
|---|---:|---|
| Insufficient funds | Up to 3 | 48h, 120h, then 168h after each observed failure |
| Temporary processing | Up to 3 | 1h, 6h, then 24h |
| Expired/invalid payment method | No | Notify for secure payment-method update |
| Authentication required | No | Request customer authentication |
| Security/fraud signal | No | Internal manual review; do not disclose provider signal |
| Hard decline / unknown | No | Manual review or customer action |

These are repository policy choices, not universal network rules. Validate them against contracts, jurisdiction, customer terms, and current provider guidance before deployment.

## Quick verification

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install '.[dev]'
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
```

Run Python plus a disposable PostgreSQL 16 database:

```bash
docker compose up --build --abort-on-container-exit --exit-code-from tests
```

Run the service locally:

```bash
export STRIPE_WEBHOOK_SECRET=whsec_from_a_test_mode_endpoint
.venv/bin/python -m payment_recovery
```

Full configuration and test-mode instructions are in [`docs/CONFIGURATION.md`](./docs/CONFIGURATION.md) and [`docs/TESTING.md`](./docs/TESTING.md).

## Stripe behavior validated for this pass

The implementation was checked against current Stripe documentation for [webhook signatures](https://docs.stripe.com/webhooks/signature), [decline codes](https://docs.stripe.com/declines/codes), and [test-mode payment methods](https://docs.stripe.com/testing?testing-method=payment-methods). Notably, `do_not_honor` is an unspecified issuer decline, not proof of fraud; `fraudulent`, `lost_card`, and `stolen_card` are security-sensitive and are not automatically retried here.

## Evidence status

| Claim | Evidence |
|---|---|
| Deterministic policy and state machine | **Implemented and tested** |
| PostgreSQL schema and retry claim | **Executed and tested on PostgreSQL 16** |
| n8n workflow artifacts | **Implemented; static import-contract tested** |
| Stripe test-mode semantics | **Checked against current official documentation** |
| Synthetic recovery benchmark | **Not performed** |
| Production/client outcomes | **Not established** |
| Historical 28–35%, 3×, or dollar claims | **Not reproduced and not claimed** |

See [`docs/EVIDENCE.md`](./docs/EVIDENCE.md) for the claim policy and [`docs/RELIABILITY.md`](./docs/RELIABILITY.md) for remaining deployment controls.

## Limitations

- No live Stripe endpoint or customer billing environment was exercised.
- n8n JSON structure and safety contracts are automated; an authenticated n8n import/execution remains deployment acceptance work.
- The service's reference in-memory store is intentionally non-durable; a deployed adapter must commit the verified event and state transition in PostgreSQL before acknowledging work.
- No synthetic outcome simulation was added because policy behavior can be tested directly without inventing a recovery probability.

## License

MIT. See [`LICENSE`](./LICENSE).

Built by **Ugo Chukwu / Etherlabs**.
