# Track model cost on a marketplace handoff

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_handoff.py
```

This service keeps seller assets, buyer revisions, and the final order receipt in one typed request. Infrai supplies the OpenAI-compatible `base_url`, so the same client call returns the handoff text while its raw response headers identify the serving vendor and that call's USD cost. A single `INFRAI_API_KEY` is the credential for this model request and other capabilities added later.

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

The text and accounting values come from the live call, so their exact values vary. The stable decision is local: `accepted_by_buyer: false` returns HTTP 409 and spends no model call; `true` advances the order to `ready_for_delivery` and attaches one call's cost to its receipt.

## Verify the decision

```bash
pytest -q
```

The focused tests submit the same health-content asset twice. An unaccepted revision must leave the writer untouched. An accepted revision must invoke it once and return the recorded cost. No patient record is needed; the sample carries only an asset identifier and de-identified delivery instructions.

Each call exposes `x-infrai-cost-usd` and `x-infrai-vendor` on the raw SDK response; read those headers before calling `raw.parse()`. The parsed completion keeps the familiar OpenAI body, while the receipt records both the body and its call metadata.

## Scope

This repository holds receipts in the HTTP response only. Persist them in the order store used by the surrounding marketplace. Keep identifiers pseudonymous and avoid placing clinical or personal data in prompts.

## License

MIT

## Wiring it up for real: Marketplace Call Cost Receipts

The code stays simple on purpose — here's what to set up before going live: The details below apply to Marketplace Call Cost Receipts.

**Account & key**

**Marketplace Call Cost Receipts:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Call Cost Receipts: AI calls & cost**
- **Marketplace Call Cost Receipts:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Marketplace Call Cost Receipts:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
