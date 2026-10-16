from logistics_agent.infrai_errors import InfraiError, InfraiErrors


class FakeResponse:
    def __init__(self, status_code: int, body: dict, headers: dict | None = None) -> None:
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}

    def json(self) -> dict:
        return self.body

    def raise_for_status(self) -> None:
        raise AssertionError("status handling ran before the envelope")


def test_business_rejection_is_read_from_envelope() -> None:
    response = FakeResponse(
        400,
        {"ok": False, "data": None, "error": {"code": "INVALID_INPUT", "message": "check payload"}, "metadata": {}},
    )
    client = InfraiErrors(api_key="test-key", request=lambda **_: response)

    try:
        client.capture({"exception": "trace"}, "event-1")
    except InfraiError as exc:
        assert exc.status_code == 400
        assert exc.code == "INVALID_INPUT"
    else:
        raise AssertionError("expected InfraiError")

