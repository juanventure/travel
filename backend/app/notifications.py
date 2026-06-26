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

import httpx


def send_booking_lead_email(full_name: str, email: str, cruise_id: str,
                            cruise_details: Optional[str] = None,
                            num_passengers: Optional[str] = None,
                            cruise_length: Optional[str] = None,
                            travel_dates: Optional[str] = None) -> bool:
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
        f"Name:          {full_name}\n"
        f"Email:         {email}\n"
        f"Cruise:        {cruise_id}\n"
        f"Passengers:    {num_passengers or '—'}\n"
        f"Cruise length: {cruise_length or '—'}\n"
        f"Travel dates:  {travel_dates or '—'}\n"
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


def send_consultation_email(first_name: str, last_name: str, email: str,
                            phone: Optional[str] = None,
                            destination: Optional[str] = None,
                            budget: Optional[str] = None,
                            num_passengers: Optional[str] = None,
                            cruise_length: Optional[str] = None,
                            travel_dates: Optional[str] = None,
                            message: Optional[str] = None) -> bool:
    """
    Email a new consultation inquiry to the agency. Returns True if sent, False
    if skipped (not configured) or failed (error is logged). Same SMTP config as
    the booking-lead email above.
    """
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")
    if not smtp_user or not smtp_password:
        print("[notifications] SMTP not configured (set SMTP_USER and "
              "SMTP_APP_PASSWORD); skipping consultation email.")
        return False

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "465"))
    recipient = os.getenv("LEAD_NOTIFICATION_EMAIL", "juanventure@gmail.com")

    full_name = f"{first_name} {last_name}".strip()
    msg = EmailMessage()
    msg["Subject"] = f"New Cruise Consultation Request: {full_name}"
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg["Reply-To"] = email  # so the advisor can reply straight to the customer
    body = (
        "A new consultation request was submitted through the Horizon Voyages site.\n\n"
        f"Name:          {full_name}\n"
        f"Email:         {email}\n"
        f"Phone:         {phone or '—'}\n"
        f"Destination:   {destination or '—'}\n"
        f"Budget:        {budget or '—'}\n"
        f"Passengers:    {num_passengers or '—'}\n"
        f"Cruise length: {cruise_length or '—'}\n"
        f"Travel dates:  {travel_dates or '—'}\n"
    )
    if message:
        body += f"\nMessage:\n{message}\n"
    body += "\nFollow up within one business day to confirm a consultation time."
    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        print(f"[notifications] Consultation email sent to {recipient}")
        return True
    except Exception as exc:  # noqa: BLE001 - log and degrade, never break submit
        print(f"[notifications] Failed to send consultation email: {exc!r}")
        return False


def _callback_recipients() -> list[str]:
    """Advisor emails for callback alerts (ADVISOR_EMAILS, else the lead inbox)."""
    raw = os.getenv("ADVISOR_EMAILS") or os.getenv(
        "LEAD_NOTIFICATION_EMAIL", "juanventure@gmail.com")
    return [e.strip() for e in raw.split(",") if e.strip()]


def send_callback_email(name: str, phone: str, trip_summary: Optional[str] = None,
                        urgent: bool = True) -> bool:
    """
    Email the advisor team that a customer requested a callback. Returns True if
    sent, False if skipped (not configured) or failed.
    """
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")
    if not smtp_user or not smtp_password:
        print("[notifications] SMTP not configured; skipping callback email.")
        return False

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "465"))
    recipients = _callback_recipients()

    msg = EmailMessage()
    flag = "CALL NOW" if urgent else "Callback (after hours)"
    msg["Subject"] = f"[{flag}] Callback requested: {name} — {phone}"
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)
    body = (
        "A customer asked an advisor to call them.\n\n"
        f"Name:  {name}\n"
        f"Phone: {phone}\n"
        f"Trip:  {trip_summary or '—'}\n\n"
    )
    body += ("Call them within ~15 minutes." if urgent
             else "Outside business hours — follow up first thing.")
    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        print(f"[notifications] Callback email sent to {recipients}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[notifications] Failed to send callback email: {exc!r}")
        return False


def send_callback_sms(name: str, phone: str, trip_summary: Optional[str] = None) -> int:
    """
    Text each advisor (ADVISOR_SMS_NUMBERS) via Twilio that a callback is waiting.
    Returns the number of messages sent. No-op (returns 0) unless TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, and ADVISOR_SMS_NUMBERS are all set.
    """
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    numbers = [n.strip() for n in os.getenv("ADVISOR_SMS_NUMBERS", "").split(",") if n.strip()]
    if not (sid and token and from_number and numbers):
        print("[notifications] Twilio not configured; skipping callback SMS.")
        return 0

    text = (f"Horizon Voyages — callback requested: {name} at {phone}. "
            f"{trip_summary or ''} Call within ~15 min.").strip()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    sent = 0
    try:
        with httpx.Client(timeout=15) as client:
            for to in numbers:
                resp = client.post(url, auth=(sid, token),
                                   data={"To": to, "From": from_number, "Body": text})
                if resp.status_code in (200, 201):
                    sent += 1
                else:
                    print(f"[notifications] Twilio SMS to {to} failed: "
                          f"{resp.status_code} {resp.text[:200]}")
    except Exception as exc:  # noqa: BLE001
        print(f"[notifications] Twilio SMS error: {exc!r}")
    print(f"[notifications] Callback SMS sent to {sent}/{len(numbers)} advisor(s)")
    return sent
