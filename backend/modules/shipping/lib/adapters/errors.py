"""Carrier integration errors — mirror mercato-shipping-hub CarrierIntegrationError."""


class CarrierIntegrationError(RuntimeError):
    def __init__(self, carrier_code: str, message: str) -> None:
        self.carrier_code = carrier_code
        self.carrier_message = message
        super().__init__(f"[{carrier_code}] {message}")
