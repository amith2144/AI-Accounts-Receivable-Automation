import logging
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from app.core.config import settings
from app.providers.notification.base import NotificationProvider, NotificationResult

logger = logging.getLogger("app.providers.notification.smtp")


class SMTPNotificationProvider(NotificationProvider):
    """
    Production SMTP notification adapter supporting TLS encryption,
    MIME multipart plain/html bodies, and header injection sanitization.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        use_tls: bool = True,
    ):
        super().__init__()
        self.host = host or getattr(settings, "SMTP_HOST", "localhost")
        self.port = port or getattr(settings, "SMTP_PORT", 587)
        self.username = username or getattr(settings, "SMTP_USER", None)
        self.password = password or getattr(settings, "SMTP_PASSWORD", None)
        self.from_email = from_email or getattr(settings, "SMTP_FROM_EMAIL", "billing@receivables.local")
        self.use_tls = use_tls

    def send_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationResult:
        """Transmit email via configured SMTP server with error isolation."""
        sanitized_to = self.sanitize_header(recipient_email)
        sanitized_subject = self.sanitize_header(subject)
        sanitized_name = self.sanitize_header(recipient_name)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = sanitized_subject
        msg["From"] = f"AR Automation Platform <{self.from_email}>"
        msg["To"] = f"{sanitized_name} <{sanitized_to}>" if sanitized_name else sanitized_to

        # Attach text part
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        # Attach html part if provided
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        message_id = f"smtp-{uuid.uuid4()}"
        msg["Message-ID"] = f"<{message_id}@receivables.local>"

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_email, [sanitized_to], msg.as_string())

            logger.info(f"Successfully transmitted SMTP email to {sanitized_to} (ID: {message_id})")
            return NotificationResult(
                success=True,
                recipient=sanitized_to,
                message_id=message_id,
                provider_name="smtp",
            )
        except Exception as exc:
            logger.error(f"SMTP dispatch failure to {sanitized_to}: {str(exc)}")
            return NotificationResult(
                success=False,
                recipient=sanitized_to,
                message_id=message_id,
                error_message=f"SMTP transmission error: {str(exc)}",
                provider_name="smtp",
            )

    def ping(self) -> bool:
        """Probe SMTP server reachability."""
        try:
            with smtplib.SMTP(self.host, self.port, timeout=5) as server:
                server.ehlo()
                return True
        except Exception as exc:
            logger.warning(f"SMTP ping check failed: {str(exc)}")
            return False
