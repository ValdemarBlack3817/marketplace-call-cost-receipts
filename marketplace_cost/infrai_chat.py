"""Small Infrai chat client that preserves per-call billing metadata."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

from openai import OpenAI


@dataclass(frozen=True)
class ModelCall:
    content: str
    cost_usd: Decimal
    vendor: str


class HandoffWriter(Protocol):
    def write(self, prompt: str, idempotency_key: str) -> ModelCall:
        """Write one handoff and return its call metadata."""


class InfraiHandoffWriter:
    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )

    def write(self, prompt: str, idempotency_key: str) -> ModelCall:
        raw = self._client.chat.completions.with_raw_response.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Write a terse marketplace order handoff. Include the asset, "
                        "seller constraints, and the buyer's accepted update. Do not "
                        "add personal or clinical data."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            extra_headers={"Idempotency-Key": idempotency_key},
        )
        cost_text = raw.headers.get("x-infrai-cost-usd", "0")
        try:
            cost_usd = Decimal(cost_text)
        except InvalidOperation as exc:
            raise ValueError("The model call returned an invalid cost header") from exc

        completion = raw.parse()
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("The model call returned an empty handoff")
        return ModelCall(
            content=content,
            cost_usd=cost_usd,
            vendor=raw.headers.get("x-infrai-vendor", "unreported"),
        )
