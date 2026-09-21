"""Typed HTTP boundary for a marketplace order handoff."""

import os
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .infrai_chat import HandoffWriter, InfraiHandoffWriter


class SellerAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    delivery_notes: str = Field(min_length=1)


class BuyerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=1)
    requested_change: str = Field(min_length=1)
    accepted_by_buyer: bool


class HandoffRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1)
    seller_asset: SellerAsset
    buyer_update: BuyerUpdate


class HandoffReceipt(BaseModel):
    order_id: str
    asset_id: str
    state: str
    handoff_note: str
    model_cost_usd: Decimal
    served_by: str


def get_writer() -> HandoffWriter:
    return InfraiHandoffWriter(api_key=os.environ["INFRAI_API_KEY"])


app = FastAPI(title="Marketplace model cost ledger")


@app.post("/handoffs", response_model=HandoffReceipt)
def create_handoff(
    request: HandoffRequest,
    writer: Annotated[HandoffWriter, Depends(get_writer)],
) -> HandoffReceipt:
    if not request.buyer_update.accepted_by_buyer:
        raise HTTPException(
            status_code=409,
            detail="Buyer must accept the latest update before handoff",
        )

    prompt = (
        f"Order: {request.order_id}\n"
        f"Asset: {request.seller_asset.title} ({request.seller_asset.asset_id})\n"
        f"Seller delivery notes: {request.seller_asset.delivery_notes}\n"
        f"Accepted buyer revision {request.buyer_update.revision}: "
        f"{request.buyer_update.requested_change}"
    )
    model_call = writer.write(prompt, idempotency_key=request.order_id)
    return HandoffReceipt(
        order_id=request.order_id,
        asset_id=request.seller_asset.asset_id,
        state="ready_for_delivery",
        handoff_note=model_call.content,
        model_cost_usd=model_call.cost_usd,
        served_by=model_call.vendor,
    )
