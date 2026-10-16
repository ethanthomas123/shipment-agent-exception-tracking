from logistics_agent.shipment_exception_loop import (
    AgentDecision,
    ShipmentEvent,
    ShipmentState,
    process_event,
)


class RecordingErrors:
    def __init__(self) -> None:
        self.captures: list[dict] = []

    def capture(self, exception_payload: dict, event_id: str) -> dict:
        self.captures.append({"payload": exception_payload, "event_id": event_id})
        return {"event_id": event_id}


def test_missing_delivery_proof_moves_shipment_to_review() -> None:
    errors = RecordingErrors()
    event = ShipmentEvent(
        shipment_id="SHP-91",
        event_type="delivery_attempted",
        occurred_at="2026-09-23T09:30:00Z",
    )

    decision = process_event(event, errors)  # type: ignore[arg-type]

    assert decision == AgentDecision(
        shipment_id="SHP-91",
        state=ShipmentState.EXCEPTION_REVIEW,
        reason="proof_of_delivery_missing",
    )
    assert len(errors.captures) == 1
    payload = errors.captures[0]["payload"]
    assert payload["fingerprint"] == [
        "shipment-agent",
        "delivery-evidence",
        "proof_of_delivery_missing",
    ]
    assert payload["context"]["shipment_id"] == "SHP-91"

