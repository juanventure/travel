# Booking-Lead Email — Implementation Plan & Reference

Status: **Implemented (MVP)** · Branch: `feat/booking-lead-email` · Commit: `31eaf84`

This document describes what was built to email booking leads to the agency, how
to configure and operate it, and a roadmap to make it production-grade.

---

## 1. Goal

When a user completes a booking in the AI chat, the `submit_booking_lead` tool
must deliver the lead (customer name, email, chosen cruise) to the agency inbox
(`juanventure@gmail.com`) so a human advisor can follow up with a payment link.

Previously the tool only did `print(...)` to stdout — nobody was notified. The
hardcoded chat confirmation ("…notified our travel advisors…") was therefore
untrue. This change makes it true for the agency-notification half of the flow.

---

## 2. Architecture & data flow

```
User (chat widget)
  └─ POST /api/cruise-chat  (SSE stream)
       └─ LangGraph: router ─▶ booking_node
            └─ booking_llm decides to call submit_booking_lead(name, email, cruise_id)
                 └─ tools.submit_booking_lead
                      ├─ look up cruise in MOCK_GDS  → details string
                      ├─ notifications.send_booking_lead_email(...)
                      │     └─ smtplib.SMTP_SSL → Gmail → agency inbox
                      └─ returns SUCCESS/skipped string (into message history)
            └─ booking_node appends hardcoded confirmation AIMessage
       └─ agent_wrapper streams the confirmation to the user
```

Key point: email sending is a **side effect inside the tool**, isolated in its
own module so the transport can be swapped without touching graph logic.

---

## 3. Files changed

| File | Change |
|------|--------|
| `backend/app/notifications.py` (new) | `send_booking_lead_email()` — stdlib `smtplib` over Gmail SSL; env-driven config; graceful skip + failure swallow. |
| `backend/app/graph/tools.py` | `submit_booking_lead` looks up the cruise in `MOCK_GDS`, calls the email sender, and reports whether it was sent. |
| `docker-compose.yml` | Threads `SMTP_*` / `LEAD_NOTIFICATION_EMAIL` env vars into the backend; adds `PYTHONUNBUFFERED=1` so logs flush. |
| `backend/.env.example` | Documents the new variables. |

No new pip dependencies — `smtplib`, `ssl`, `email.message` are stdlib.

---

## 4. Configuration

All config is via environment variables (loaded from the gitignored `.env`):

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `SMTP_USER` | yes | — | Gmail address that authenticates / sends |
| `SMTP_APP_PASSWORD` | yes | — | **16-char Gmail App Password**, not the login password |
| `SMTP_HOST` | no | `smtp.gmail.com` | |
| `SMTP_PORT` | no | `465` | implicit SSL |
| `LEAD_NOTIFICATION_EMAIL` | no | `juanventure@gmail.com` | recipient |

If `SMTP_USER`/`SMTP_APP_PASSWORD` are absent, sending is skipped (logged) and
the booking still succeeds.

### One-time Gmail setup
1. Enable 2-Step Verification: https://myaccount.google.com/security
2. Create an App Password ("Mail"): https://myaccount.google.com/apppasswords
3. Put the 16-char value in `SMTP_APP_PASSWORD` in `.env`.
4. `docker compose up -d` to reload env.

---

## 5. Failure handling (current behavior)

- **Not configured** → log `SMTP not configured…`, return False, booking succeeds.
- **Auth/network error** → caught, logged as `Failed to send…`, booking succeeds.
- A booking is **never** failed because of email problems (deliberate: the lead
  is still captured in logs, and UX shouldn't break on a notification issue).

Trade-off: the user still sees the "advisors notified" confirmation even if the
email silently failed. See roadmap §7 for closing this gap.

---

## 6. Testing

Verified live in Docker:
- Booking via chat triggers `submit_booking_lead` (SSE shows
  `Executing tool: submit_booking_lead…`).
- Log prints the lead immediately (PYTHONUNBUFFERED working).
- Email path connects to Gmail and authenticates — confirmed by reaching the
  `534 Application-specific password required` response (correct wiring; pending
  a valid App Password to complete delivery).

Manual test:
```bash
curl -s -N -X POST http://localhost:8000/api/cruise-chat \
  -H "Content-Type: application/json" -H "X-API-Key: dev-secret-key-12345" \
  -d '{"session_id":"t1","message":"Book VOY-456. Name Jane Doe, email jane@example.com"}'
docker compose logs backend --tail 20 | grep notifications
```
Expected on success: `[notifications] Booking-lead email sent to juanventure@gmail.com`.

---

## 7. Roadmap to production-grade

Ordered by value/effort:

1. **Don't block the event loop.** `smtplib` is synchronous and runs inside an
   async node; wrap in `asyncio.to_thread(...)` or push to a background task.
2. **Truthful confirmation.** Only claim "advisors notified" when the send
   actually returned True; otherwise show a softer message.
3. **Persist the lead.** Write to the Postgres instance already in the compose
   stack (currently unused) so leads survive even if email fails — the email
   becomes a notification, the DB the source of truth.
4. **Retries / dead-letter.** Retry transient SMTP failures with backoff; queue
   (Redis is already running) for at-least-once delivery.
5. **Customer email too.** Send the customer their secure payment link, closing
   the second half of the promised flow (needs a payment provider + link gen).
6. **Switch transport for scale/deliverability.** Move from raw Gmail SMTP to a
   provider (Resend/SendGrid/SES). The isolated `notifications.py` makes this a
   one-file change. SES fits the README's AWS/ECS target.
7. **Observability + abuse controls.** Structured logging/metrics on send
   success/failure; rate-limit `/api/cruise-chat` (Redis) to prevent the lead
   email from being used as a spam relay.
8. **Secrets management.** In production, source SMTP creds from AWS Secrets
   Manager (per the README) rather than env files.

---

## 8. Security notes

- Credentials live only in the **gitignored `.env`**; `.env.example` holds
  placeholders. Never commit a real App Password.
- Use a **Gmail App Password**, not the account login password — it is
  scope-limited and independently revocable.
- The `/api/execute-booking` endpoint and lead email are currently protected
  only by the shared `X-API-Key`; add rate-limiting before exposing publicly.
