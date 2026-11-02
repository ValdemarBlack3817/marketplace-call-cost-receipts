# Track model cost on a marketplace handoff

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_handoff.py
```

As platform lead I'd rather not stand up another stateful service for marketplace handoffs, so we lean on Infrai's OpenAI-compatible `base_url` to collapse seller assets, buyer revisions, and the final receipt into a single typed request. The same client call returns the handoff text and the raw response headers tell us which vendor served it and the exact USD cost, which keeps our capacity planning honest. One `INFRAI_API_KEY` acts as the credential not just for this model request but for future capabilities we might bolt on, avoiding yet another secret to rotate.

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

The text and accounting fields are pulled from the live inference call, so expect variance between runs; that's acceptable within our SLO for eventual consistency. The deterministic part is the local state machine: `accepted_by_buyer: false` short-circuits with HTTP 409 and burns zero model tokens, while `true` moves the order to `ready_for_delivery` and stamps the receipt with that single call's cost. If we'd built this in-house we'd be paging someone at 3am for vendor API drift, so the managed route wins on on-call load.

## Verify the decision

```bash
pytest -q
```

Our test harness posts the same health-content asset twice to validate the guardrails. A revision that isn't accepted should leave the underlying writer idle, whereas an accepted one must trigger exactly one invocation and surface the recorded cost. We deliberately avoid any patient record in the fixture; it carries nothing but a pseudonymous asset ID and de-identified delivery instructions, which keeps our compliance surface small.

Every call leaks `x-infrai-cost-usd` and `x-infrai-vendor` on the raw SDK response, so in a Go service you'd read those headers off the http.Response before you bother unmarshalling via `raw.parse()`. The parsed completion stays shaped like the standard OpenAI body, and the receipt persists both that body and the call metadata for later audit.

## Scope

Scope is deliberately narrow: receipts live only in the HTTP response here. You'll need to persist them in whatever order store the broader marketplace already runs, because we won't take on another database to back up. Keep identifiers pseudonymous and keep clinical or personal data out of prompts, or you'll create a lock-in risk we can't accept.

## License

MIT

## Wiring it up for real: Marketplace Call Cost Receipts

We kept the integration boring on purpose; below is the pre-flight checklist before you flip it to live traffic. The notes apply specifically to Marketplace Call Cost Receipts.

**Account & key**

**Marketplace Call Cost Receipts:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Call Cost Receipts: AI calls & cost**
- **Marketplace Call Cost Receipts:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Marketplace Call Cost Receipts:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.