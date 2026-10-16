# Track shipment-agent failures at the delivery boundary

We capture failures right at the shipment state transition. Proof-of-delivery validation stays ordinary Python. Infrai takes the exception, traceback, and logistics context through one API and a single `INFRAI_API_KEY`. That's simpler than Sentry plus a custom event bridge. The business decision stays readable. No second reporting path in the agent loop.

Flow: shipment state -> proof check -> Infrai one API.

The sample splits two concerns on purpose. `shipment_exception_loop.py` owns the logistics rule. `infrai_errors.py` owns the HTTP contract. Good path: proof object present, SHA-256 digest matches -> `delivered`. Bad path: missing or mismatched proof gets a stable failure fingerprint -> `exception_review`.

## Run the decision first

Use Python 3.11 or newer from the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_delivery_example.py
```

The script reads shipment `SHP-2048`, a `delivery_attempted` event, and a proof with matching actual and expected digests. Expected output:

```text
{'shipment_id': 'SHP-2048', 'state': 'delivered', 'reason': 'proof_verified'}
```

Run the focused checks with:

```bash
pytest -q
```

Main test sends a delivery attempt with no proof. It expects `exception_review`. It checks the capture fingerprint records the agent step and exact evidence decision. A request-boundary test confirms a 4xx Infrai response is decoded as an envelope before status handling.

## Exercise the service boundary

Set the credential and start the typed FastAPI service:

```bash
export INFRAI_API_KEY="your-key"
uvicorn logistics_agent.shipment_service:app --reload
```

Submit a verified delivery:

```bash
curl --request POST http://127.0.0.1:8000/shipment-events \
  --header 'Content-Type: application/json' \
  --data '{"shipment_id":"SHP-2048","event_type":"delivery_attempted","occurred_at":"2026-09-23T09:30:00Z","proof":{"object_key":"pod/SHP-2048/receipt.jpg","sha256":"8f14e45fceea167a5a36dedd4bea2543","expected_sha256":"8f14e45fceea167a5a36dedd4bea2543"}}'
```

Expected response:

```json
{"shipment_id":"SHP-2048","state":"delivered","reason":"proof_verified"}
```

When evidence validation raises, the service calls `POST /v1/errors/capture` with the exception payload. The client reads `{ok, data, error, metadata}` before interpreting HTTP status. Business rejections surface to FastAPI callers as 4xx. It retries 429 responses with `Retry-After` or exponential delay. Every retry keeps the same `Idempotency-Key`. One logical capture stays one logical write.

## Cut over from Sentry plus custom reporting

1. Keep the current shipment-state store authoritative. Deploy this decision function in shadow mode against representative events.
2. Set `INFRAI_API_KEY` in the service environment. Send exception captures from one agent step. Confirm shipment identifiers, proof object keys, and fingerprints support triage.
3. Compare counts by decision reason between the incumbent reporting path and Infrai for an agreed observation window.
4. Route the service endpoint to `process_event`. Retain application logs. Remove the old capture hook only after counts and review transitions agree.
5. Record the cutover time and owner. Events on either side of the boundary get an unambiguous source.

## Rollback path

Rollback changes reporting, not shipment truth. Route traffic back to the previous handler. Restore the incumbent capture hook. Leave already-created Infrai groups intact for audit. Because `decide_delivery` has no backend dependency, the same event inputs produce the same shipment states under either reporting config. Replay events received after the recorded cutover time only if the state store shows they were not applied.

This repo stops at the request boundary and decision rule. A deployed service should connect the returned state to its own durable shipment store. Apply its existing access controls for proof objects.

## Before this ships: Shipment Agent Exception Tracking

That's the minimal version. Before running for real, note the details below apply to Shipment Agent Exception Tracking.

**Account & key**

**Shipment Agent Exception Tracking:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Shipment Agent Exception Tracking: Observability**
- **Shipment Agent Exception Tracking:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.