"""Make delivery state transitions visible and capture agent failures."""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from enum import Enum

from .infrai_errors import InfraiErrors, new_event_id


class ShipmentState(str, Enum):
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    EXCEPTION_REVIEW = "exception_review"


@dataclass(frozen=True)
class ProofOfDelivery:
    object_key: str
    sha256: str
    expected_sha256: str


@dataclass(frozen=True)
class ShipmentEvent:
    shipment_id: str
    event_type: str
    occurred_at: str
    proof: ProofOfDelivery | None = None


@dataclass(frozen=True)
class AgentDecision:
    shipment_id: str
    state: ShipmentState
    reason: str


class DeliveryEvidenceError(ValueError):
    pass


def decide_delivery(event: ShipmentEvent) -> AgentDecision:
    """Accept delivery only when a proof object and its expected digest agree."""
    if event.event_type != "delivery_attempted":
        return AgentDecision(event.shipment_id, ShipmentState.IN_TRANSIT, "event_not_final")
    if event.proof is None:
        raise DeliveryEvidenceError("proof_of_delivery_missing")
    if event.proof.sha256 != event.proof.expected_sha256:
        raise DeliveryEvidenceError("proof_checksum_mismatch")
    return AgentDecision(event.shipment_id, ShipmentState.DELIVERED, "proof_verified")


def process_event(event: ShipmentEvent, errors: InfraiErrors) -> AgentDecision:
    """Run one agent decision and capture evidence exceptions before review."""
    try:
        return decide_delivery(event)
    except DeliveryEvidenceError as exc:
        errors.capture(
            exception_payload={
                "title": "shipment-agent/delivery-evidence failed",
                "message": str(exc),
                "level": "error",
                "fingerprint": ["shipment-agent", "delivery-evidence", str(exc)],
                "exception": traceback.format_exc(),
                "context": {
                    "shipment_id": event.shipment_id,
                    "event_type": event.event_type,
                    "occurred_at": event.occurred_at,
                    "proof_object_key": event.proof.object_key if event.proof else None,
                },
            },
            event_id=new_event_id(),
        )
        return AgentDecision(event.shipment_id, ShipmentState.EXCEPTION_REVIEW, str(exc))

