"""
Email notifications for booking leads.

Uses Python's stdlib smtplib over Gmail SMTP (SSL). No third-party dependency.
All configuration comes from environment variables so credentials never live
in source:

    SMTP_USER                Gmail address used to authenticate / send from   (required)
    SMTP_APP_PASSWORD        16-char Gmail App Password (NOT your login pwd)   (required)
    SMTP_HOST                default: smtp.gmail.com
    SMTP_PORT                default: 465 (implicit SSL)
    LEAD_NOTIFICATION_EMAIL  recipient of lead emails; default juanventure@gmail.com

If SMTP_USER / SMTP_APP_PASSWORD are not set, sending is skipped gracefully so a
booking never fails just because email isn't configured.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional


def send_booking_lead_email(full_name: str, email: str, cruise_id: str,
                            cruise_details: Optional[str] = None) -> bool:
    """
    Email a new booking lead to the agency. Returns True if the email was sent,
    False if it was skipped (not configured) or failed (error is logged).
    """
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")
    if not smtp_user or not smtp_password:
        print("[notifications] SMTP not configured (set SMTP_USER and "
              "SMTP_APP_PASSWORD); skipping booking-lead email.")
        return False

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "465"))
    recipient = os.getenv("LEAD_NOTIFICATION_EMAIL", "juanventure@gmail.com")

    msg = EmailMessage()
    msg["Subject"] = f"New Cruise Booking Lead: {full_name}"
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg["Reply-To"] = email  # so the advisor can reply straight to the customer
    body = (
        "A new booking lead was submitted through the Horizon Voyages AI assistant.\n\n"
        f"Name:   {full_name}\n"
        f"Email:  {email}\n"
        f"Cruise: {cruise_id}\n"
    )
    if cruise_details:
        body += f"\nVoyage details:\n{cruise_details}\n"
    body += "\nFollow up to send the customer their secure payment link."
    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        print(f"[notifications] Booking-lead email sent to {recipient}")
        return True
    except Exception as exc:  # noqa: BLE001 - log and degrade, never break booking
        print(f"[notifications] Failed to send booking-lead email: {exc!r}")
        return False
