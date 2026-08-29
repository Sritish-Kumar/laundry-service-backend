from abc import ABC, abstractmethod
from typing import Any


class RazorpayProvider(ABC):

    @abstractmethod
    def create_order(self, *, amount: int, currency: str, receipt: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def fetch_payment(self, *, payment_id: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def verify_payment_signature(self, *, params: dict[str, Any]) -> bool:
        ...

    @abstractmethod
    def verify_webhook_signature(self, *, payload: str, signature: str) -> bool:
        ...
