import logging
import uuid
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.providers.notification.base import NotificationProvider, NotificationResult

logger = logging.getLogger("app.providers.notification.sendgrid")


class SendGridNotificationProvider(NotificationProvider):
    """
    SendGrid Web API v3 notification adapter transmitting transactional reminder emails
    via HTTPS REST endpoints.
    """

    SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
    ):
        super().__init__()
        self.api_key = api_key or getattr(settings, "SENDGRID_API_KEY", None)
        self.from_email = from_email or getattr(settings, "SENDGRID_FROM_EMAIL", "reminders@receivables.local")

    def send_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationResult:
        """Transmit email via SendGrid Web API v3."""
        sanitized_to = self.sanitize_header(recipient_email)
        sanitized_subject = self.sanitize_header(subject)
        sanitized_name = self.sanitize_header(recipient_name)

        if not self.api_key:
            return NotificationResult(
                success=False,
                recipient=sanitized_to,
                error_message="SendGrid API key not configured.",
                provider_name="sendgrid",
            )

        payload = {
            "personalizations": [
                {
                    "to": [{"email": sanitized_to, "name": sanitized_name or sanitized_to}],
                    "subject": sanitized_subject,
                }
            ],
            "from": {"email": self.from_email, "name": "AR Automation Platform"},
            "content": [{"type": "text/plain", "value": body_text}],
        }
        if body_html:
            payload["content"].append({"type": "text/html", "value": body_html})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.SENDGRID_API_URL, json=payload, headers=headers)
                if response.status_code in [200, 202]:
                    msg_id = response.headers.get("X-Message-Id", f"sg-{uuid.uuid4()}")
                    logger.info(f"SendGrid email dispatched to {sanitized_to} (ID: {msg_id})")
                    return NotificationResult(
                        success=True,
                        recipient=sanitized_to,
                        message_id=msg_id,
                        provider_name="sendgrid",
                    )
                else:
                    err_msg = f"SendGrid API rejected request ({response.status_code}): {response.text}"
                    logger.error(err_msg)
                    return NotificationResult(
                        success=False,
                        recipient=sanitized_to,
                        error_message=err_msg,
                        provider_name="sendgrid",
                    )
        except Exception as exc:
            logger.exception(f"SendGrid request failed for {sanitized_to}: {str(exc)}")
            return NotificationResult(
                success=False,
                recipient=sanitized_to,
                error_message=f"SendGrid connection failure: {str(exc)}",
                provider_name="sendgrid",
            )

    def ping(self) -> bool:
        """Probe SendGrid API credential configuration."""
        return bool(self.api_key and len(self.api_key) > 10)
