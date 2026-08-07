from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class EmailMessage:
    recipient: str
    subject: str
    html: str


class EmailProvider(ABC):

    @abstractmethod
    def send(self, *, email_message: EmailMessage) -> None:
        ...
