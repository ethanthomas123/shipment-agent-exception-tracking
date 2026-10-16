"""Run the successful proof-of-delivery branch without external calls."""

from logistics_agent.shipment_exception_loop import (
    ProofOfDelivery,
    ShipmentEvent,
    decide_delivery,
)


event = ShipmentEvent(
    shipment_id="SHP-2048",
    event_type="delivery_attempted",
    occurred_at="2026-09-23T09:30:00Z",
    proof=ProofOfDelivery(
        object_key="pod/SHP-2048/receipt.jpg",
        sha256="8f14e45fceea167a5a36dedd4bea2543",
        expected_sha256="8f14e45fceea167a5a36dedd4bea2543",
    ),
)
decision = decide_delivery(event)
print({"shipment_id": decision.shipment_id, "state": decision.state.value, "reason": decision.reason})

