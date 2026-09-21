import pytest
from app.providers.notification import (
    MemoryNotificationProvider,
    SMTPNotificationProvider,
    SendGridNotificationProvider,
    get_notification_provider,
)
from app.providers.notification.base import NotificationProvider


def test_jinja2_template_rendering():
    provider = MemoryNotificationProvider()

    template = "Hello {{ customer_name }}, your invoice {{ invoice_number }} of ${{ balance_due }} is due on {{ due_date }}."
    context = {
        "customer_name": "Apex Industries",
        "invoice_number": "INV-100",
        "balance_due": "1,500.00",
        "due_date": "2026-04-01",
    }
    rendered = provider.render_template(template, context)
    assert rendered == "Hello Apex Industries, your invoice INV-100 of $1,500.00 is due on 2026-04-01."


def test_email_header_injection_sanitization():
    # Attempt newline injection in header
    malicious_email = "victim@example.com\r\nBcc: attacker@evil.com"
    sanitized = NotificationProvider.sanitize_header(malicious_email)
    assert "\r" not in sanitized
    assert "\n" not in sanitized
    assert sanitized == "victim@example.com Bcc: attacker@evil.com"


def test_memory_notification_provider():
    provider = MemoryNotificationProvider()
    assert provider.ping() is True

    result = provider.send_email(
        recipient_email="billing@test.com",
        recipient_name="John Doe",
        subject="Payment Reminder: INV-001",
        body_text="Your payment is past due.",
        body_html="<p>Your payment is past due.</p>",
    )
    assert result.success is True
    assert result.recipient == "billing@test.com"
    assert len(provider.sent_messages) == 1
    assert provider.sent_messages[0]["subject"] == "Payment Reminder: INV-001"

    provider.clear()
    assert len(provider.sent_messages) == 0


def test_smtp_notification_provider_error_isolation():
    # Attempt connection to a non-existent port/server; should return failure result cleanly
    provider = SMTPNotificationProvider(host="127.0.0.1", port=9999)
    result = provider.send_email(
        recipient_email="test@example.com",
        recipient_name="Test",
        subject="Subject",
        body_text="Body",
    )
    assert result.success is False
    assert "SMTP transmission error" in result.error_message


def test_sendgrid_notification_provider_no_key():
    provider = SendGridNotificationProvider(api_key=None)
    result = provider.send_email(
        recipient_email="test@example.com",
        recipient_name="Test",
        subject="Subject",
        body_text="Body",
    )
    assert result.success is False
    assert "SendGrid API key not configured" in result.error_message


def test_notification_provider_factory():
    mem = get_notification_provider("memory")
    assert isinstance(mem, MemoryNotificationProvider)

    smtp = get_notification_provider("smtp")
    assert isinstance(smtp, SMTPNotificationProvider)

    sg = get_notification_provider("sendgrid")
    assert isinstance(sg, SendGridNotificationProvider)
