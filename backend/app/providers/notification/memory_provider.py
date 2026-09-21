import uuid
from typing import Any, Dict, List, Optional

from app.providers.notification.base import NotificationProvider, NotificationResult


class MemoryNotificationProvider(NotificationProvider):
    """
    In-memory notification provider capturing dispatched messages for verification
    and local execution environments.
    """

    def __init__(self):
        super().__init__()
        self.sent_messages: List[Dict[str, Any]] = []

    def send_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationResult:
        sanitized_to = self.sanitize_header(recipient_email)
        sanitized_subject = self.sanitize_header(subject)
        sanitized_name = self.sanitize_header(recipient_name)

        msg_id = f"mem-{uuid.uuid4()}"
        self.sent_messages.append(
            {
                "message_id": msg_id,
                "recipient_email": sanitized_to,
                "recipient_name": sanitized_name,
                "subject": sanitized_subject,
                "body_text": body_text,
                "body_html": body_html,
                "metadata": metadata or {},
            }
        )

        return NotificationResult(
            success=True,
            recipient=sanitized_to,
            message_id=msg_id,
            provider_name="memory",
        )

    def ping(self) -> bool:
        return True

    def clear(self) -> None:
        self.sent_messages.clear()
