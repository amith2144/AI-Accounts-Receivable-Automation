import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from jinja2 import Environment, Template, select_autoescape
from pydantic import BaseModel, Field


class NotificationResult(BaseModel):
    """Execution status and audit telemetry resulting from a notification dispatch attempt."""
    success: bool
    recipient: str
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    provider_name: str = "base"


class NotificationProvider(ABC):
    """
    Abstract communication adapter decoupling messaging delivery channels from AR cadence logic.
    Enforces Rule 02 (Architectural Layering) and Rule 03 (Untrusted Input Sanitization).
    """

    def __init__(self):
        self._jinja_env = Environment(
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_template(self, template_str: str, context: Dict[str, Any]) -> str:
        """Render parameterized email subject or body using Jinja2 with auto-escaping."""
        template = self._jinja_env.from_string(template_str)
        return template.render(**context)

    @staticmethod
    def sanitize_header(header_value: str) -> str:
        """Prevent SMTP/Email header injection attacks by stripping newline and carriage return characters."""
        if not header_value:
            return ""
        return re.sub(r"[\r\n]+", " ", header_value).strip()

    @abstractmethod
    def send_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationResult:
        """Transmit email notification to recipient."""
        pass

    @abstractmethod
    def ping(self) -> bool:
        """Probe notification provider connectivity and credential validity."""
        pass
