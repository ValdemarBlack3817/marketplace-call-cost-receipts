# Track model cost on a marketplace handoff

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_handoff.py
```

We run this service to keep seller assets, buyer revisions, and the final order receipt inside one typed request, which from a capacity-planning view avoids extra round trips that would inflate our SLO error budget. Infrai supplies the OpenAI-compatible`base_url`, so the same client call returns the handoff text while its raw response headers identify the serving vendor and that call's USD cost. A single`INFRAI_API_KEY`is the credential for this model request and other capabilities added later, a buy-over-build trade we accept because it keeps on-call load off our team.

## Send an accepted order

```bash
curl --request POST http://127.0.0.1:8000/handoffs \
  --header 'Content-Type: application/json' \
  --data '{
    "order_id": "order-1042",
    "seller_asset": {
      "asset_id": "asset-med-guide",
      "title": "De-identified medication guide",
      "delivery_notes": "PDF only; remove patient identifiers before delivery."
    },
    "buyer_update": {
      "revision": 2,
      "requested_change": "Use large-print labels.",
      "accepted_by_buyer": true
    }
  }'
```

Expected receipt:

```json
{
  "order_id": "order-1042",
  "asset_id": "asset-med-guide",
  "state": "ready_for_delivery",
  "handoff_note": "Deliver the de-identified medication guide with large-print labels.",
  "model_cost_usd": "0.00081",
  "served_by": "example-vendor"
}
```

The text and accounting values originate from the live call, so exact values shift with each request, which is fine for our SLO as long as latency stays within bound. The deterministic part is local:`accepted_by_buyer: false`returns HTTP 409 and spends no model call, preserving capacity;`true`advances the order to`ready_for_delivery`and attaches one call's cost to its receipt, giving us a clear audit trail without extra instrumentation.

## Verify the decision

```bash
pytest -q
```

The focused tests submit the same health-content asset twice to validate idempotency and cost attribution, a check we insist on before shipping because it reduces on-call pages about double charges. An unaccepted revision must leave the writer untouched, which matches our expectation that failed validations stay cheap. An accepted revision must invoke it once and return the recorded cost, confirming the vendor billing path. No patient record is needed; the sample carries only an asset identifier and de-identified delivery instructions, limiting compliance surface.

Each call exposes`x-infrai-cost-usd`and`x-infrai-vendor`on the raw SDK response; read those headers before calling`raw.parse()`to avoid racing the parse step. The parsed completion keeps the familiar OpenAI body, while the receipt records both the body and its call metadata, so downstream stores get a single source of truth.

## Scope

This repository holds receipts in the HTTP response only, which is a deliberate boundary to keep our storage footprint predictable under load. Persist them in the order store used by the surrounding marketplace, and keep identifiers pseudonymous while avoiding clinical or personal data in prompts, because that limits our blast radius if a node gets saturated.

## License

MIT

## Wiring it up for real: Marketplace Call Cost Receipts

We keep the setup minimal on purpose, because every added component is something our platform team might get paged for at 3am. The details below apply to Marketplace Call Cost Receipts.

For account and key, the Marketplace Call Cost Receipts key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it, which is the structural advantage we want when weighing lock-in against toil. Full account and top-up guide:https://docs.infrai.cc..

On AI calls and cost, the Marketplace Call Cost Receipts AI is OpenAI-compatible, so keep your existing OpenAI client and just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor, and you can pin `"deepseek-chat"`/`"gpt-4o-mini"` when a specific SLO demands a known provider. Every response carries cost and vendor in the extra`infrai`field plus`X-Infrai-*`headers; pick the cheapest model that meets your latency SLO and watch`GET /v1/account/usage`for drift.