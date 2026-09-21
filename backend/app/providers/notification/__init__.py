from typing import Optional
from app.core.config import settings
from app.providers.notification.base import NotificationProvider, NotificationResult
from app.providers.notification.email_provider import SMTPNotificationProvider
from app.providers.notification.memory_provider import MemoryNotificationProvider
from app.providers.notification.sendgrid_provider import SendGridNotificationProvider

_default_notification_provider: Optional[NotificationProvider] = None


def get_notification_provider(provider_type: Optional[str] = None) -> NotificationProvider:
    """Factory returning configured NotificationProvider singleton or specified instance."""
    global _default_notification_provider

    ptype = (provider_type or getattr(settings, "NOTIFICATION_PROVIDER", "memory")).lower().strip()

    if provider_type is None and _default_notification_provider is not None:
        return _default_notification_provider

    provider: NotificationProvider
    if ptype == "smtp":
        provider = SMTPNotificationProvider()
    elif ptype == "sendgrid":
        provider = SendGridNotificationProvider()
    elif ptype == "memory":
        provider = MemoryNotificationProvider()
    else:
        provider = MemoryNotificationProvider()

    if provider_type is None:
        _default_notification_provider = provider

    return provider


__all__ = [
    "NotificationProvider",
    "NotificationResult",
    "SMTPNotificationProvider",
    "SendGridNotificationProvider",
    "MemoryNotificationProvider",
    "get_notification_provider",
]
