from decimal import Decimal

from fastapi.testclient import TestClient

from marketplace_cost.handoff_service import app, get_writer
from marketplace_cost.infrai_chat import ModelCall


class RecordingWriter:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.idempotency_keys: list[str] = []

    def write(self, prompt: str, idempotency_key: str) -> ModelCall:
        self.prompts.append(prompt)
        self.idempotency_keys.append(idempotency_key)
        return ModelCall(
            content="Deliver the de-identified medication guide with large-print labels.",
            cost_usd=Decimal("0.00081"),
            vendor="example-vendor",
        )


def request_body(*, accepted: bool) -> dict[str, object]:
    return {
        "order_id": "order-1042",
        "seller_asset": {
            "asset_id": "asset-med-guide",
            "title": "De-identified medication guide",
            "delivery_notes": "PDF only; remove patient identifiers before delivery.",
        },
        "buyer_update": {
            "revision": 2,
            "requested_change": "Use large-print labels.",
            "accepted_by_buyer": accepted,
        },
    }


def test_unaccepted_update_blocks_handoff_without_model_spend() -> None:
    writer = RecordingWriter()
    app.dependency_overrides[get_writer] = lambda: writer
    try:
        response = TestClient(app).post("/handoffs", json=request_body(accepted=False))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert writer.prompts == []


def test_accepted_update_records_one_call_cost_on_receipt() -> None:
    writer = RecordingWriter()
    app.dependency_overrides[get_writer] = lambda: writer
    try:
        response = TestClient(app).post("/handoffs", json=request_body(accepted=True))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "order_id": "order-1042",
        "asset_id": "asset-med-guide",
        "state": "ready_for_delivery",
        "handoff_note": "Deliver the de-identified medication guide with large-print labels.",
        "model_cost_usd": "0.00081",
        "served_by": "example-vendor",
    }
    assert len(writer.prompts) == 1
    assert "remove patient identifiers" in writer.prompts[0]
    assert writer.idempotency_keys == ["order-1042"]
