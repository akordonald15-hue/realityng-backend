from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.mail import send_mail


@dataclass(frozen=True)
class EmailMessage:
    subject: str
    body: str
    recipient: str


class EmailProvider:
    def send(self, message: EmailMessage) -> bool:
        raise NotImplementedError


class DjangoEmailProvider(EmailProvider):
    def send(self, message: EmailMessage) -> bool:
        sent = send_mail(
            subject=message.subject,
            message=message.body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@realityng.com"),
            recipient_list=[message.recipient],
            fail_silently=False,
        )
        return sent > 0


def get_email_provider() -> EmailProvider:
    return DjangoEmailProvider()
