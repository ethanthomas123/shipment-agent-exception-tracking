"""Typed HTTP boundary for the shipment agent loop."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .infrai_errors import InfraiError, InfraiErrors
from .shipment_exception_loop import ProofOfDelivery, ShipmentEvent, process_event


class ProofRequest(BaseModel):
    object_key: str
    sha256: str
    expected_sha256: str


class ShipmentEventRequest(BaseModel):
    shipment_id: str
    event_type: str
    occurred_at: str
    proof: ProofRequest | None = None


class DecisionResponse(BaseModel):
    shipment_id: str
    state: str
    reason: str


app = FastAPI(title="Shipment exception loop")


@app.post("/shipment-events", response_model=DecisionResponse)
def receive_shipment_event(body: ShipmentEventRequest) -> DecisionResponse:
    proof = ProofOfDelivery(**body.proof.model_dump()) if body.proof else None
    event = ShipmentEvent(
        shipment_id=body.shipment_id,
        event_type=body.event_type,
        occurred_at=body.occurred_at,
        proof=proof,
    )
    try:
        decision = process_event(event, InfraiErrors())
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    return DecisionResponse(
        shipment_id=decision.shipment_id,
        state=decision.state.value,
        reason=decision.reason,
    )

