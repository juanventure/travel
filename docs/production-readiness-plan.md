# Production Readiness & Booking Implementation Plan

Goal: take Horizon Voyages from demo to a live site that supports **both**
booking models:

- **Advisor lead-gen** — capture a qualified lead, notify the agency, advisor
  follows up (this flow exists today, needs hardening).
- **Self-serve booking** — customer pays online and receives a confirmed
  reservation without a human in the loop (not built yet).

This document is the source of truth for the roadmap. Each phase lists concrete
tasks, the files involved, and how to verify.

---

## 0. Current state (what's real vs. mock)

| Area | State |
|------|-------|
| AI chat (consultation/inventory/booking) | ✅ Working (Gemini 2.5-flash) |
| Inventory | ❌ Mock — 3 hardcoded cruises in `tools.py` (`MOCK_GDS`) |
| Lead capture | ⚠️ Email + logs only; **no persistence** |
| Agency email | ✅ Working (Gmail SMTP); deliverability not production-grade |
| Payments / reservations | ❌ Stub — `execute_final_booking`/`check_booking_status` return fake data |
| Auth | ⚠️ Single shared `X-API-Key`, exposed in frontend JS |
| CORS | ⚠️ `allow_origins=["*"]` |
| Rate limiting | ❌ None (Redis provisioned but unused) |
| Conversation state | ⚠️ In-memory `MemorySaver` (lost on restart, not multi-instance) |
| Frontend backend URL | ⚠️ Hardcoded `http://localhost:8000` |
| Consultation form | ⚠️ `mailto:` (unreliable) |
| Hosting / domain / TLS | ❌ None |
| Tests / CI / monitoring | ❌ None |
| Legal (privacy/terms) | ❌ None |

---

## Phase 1 — Security & abuse controls (LAUNCH BLOCKERS)

Protects the public LLM endpoint from cost-abuse and locks the browser surface.

- [x] **1a. Rate limiting** (Redis-backed, per-IP) on `/api/cruise-chat` and
      `/api/execute-booking`. — `ratelimit.py`, `main.py` ✅
- [x] **1b. Lock CORS** to configured origins via `ALLOWED_ORIGINS`. — `main.py` ✅
- [x] **1c. Bot check** (Cloudflare Turnstile) on the chat first message ✅
      — `captcha.py`, frontend Turnstile widget. Uses test keys by default;
      swap in real site/secret keys for production. (Consultation form gets it
      with 2c.)
- [x] **1d. Honour `X-Forwarded-For`** for client IP behind a proxy/ALB. ✅

Verify: hammer an endpoint past the limit → `429`; browser requests from a
non-allowed origin are blocked while the real frontend works.

## Phase 2 — Lead-gen production

Make the advisor flow durable and reliable.

- [x] **2a. Persist leads to Postgres** (`booking_leads` table) — saved before
      the email so a lead is never lost; record `email_sent`. — `db.py`,
      `agents.py`, `main.py` ✅
- [ ] **2b. Production email** — move from Gmail SMTP to a transactional
      provider (SES/SendGrid/Resend) with SPF/DKIM for deliverability.
- [x] **2c. Consultation form posts to backend** instead of `mailto:` ✅ — new
      `/api/consultation` endpoint (Turnstile-gated, rate-limited) persists to a
      `consultation_inquiries` table BEFORE emailing the agency; frontend POSTs
      via `fetch` with the bot-check widget. — `main.py`, `db.py`,
      `notifications.py`, `captcha.py`, `script.js`, `index.html`
- [x] **2d. Replace Calendly placeholder** ✅ — "Open Calendly" now links to
      https://calendly.com/horizonvoyages (new tab); removed the `alert()` stub. — `index.html`, `script.js`
- [x] **2e. Admin view** ✅ — HTTP Basic–protected `/admin` page lists booking
      leads + consultation inquiries. Separate `ADMIN_USER`/`ADMIN_PASSWORD`
      auth (not the public API key); disabled (503) when unconfigured. — `admin.py`, `db.py`, `main.py`

## Phase 3 — Self-serve booking & payments

The new capability. Recommended stack: **Stripe Checkout (hosted)** to avoid
PCI scope.

- [ ] **3a. Real inventory** — replace `MOCK_GDS` with a curated DB table (or a
      supplier/GDS integration). Inventory has price, availability, deposit.
- [ ] **3b. Orders/reservations data model** — `reservations` (customer, cruise,
      status: pending→paid→confirmed→failed, amount, Stripe ids).
- [ ] **3c. Create Checkout Session** — `/api/checkout` creates a Stripe Checkout
      session for the selected cruise/deposit and returns the URL; chat/UI
      redirects the customer there.
- [ ] **3d. Stripe webhook** — `/api/webhooks/stripe` verifies signature, marks
      the reservation paid, and triggers the confirmation.
- [ ] **3e. Customer confirmation email** — receipt + booking reference (closes
      the "you'll receive an email" promise for the self-serve path).
- [ ] **3f. Route in chat** — the booking agent offers "pay now (self-serve)"
      vs. "have an advisor call me (lead)" and routes accordingly.
- [ ] **3g. Idempotency & reconciliation** — handle duplicate webhooks, abandoned
      checkouts, refunds.

## Phase 4 — Reliability & ops

- [ ] **4a. Durable LangGraph checkpointer** — replace `MemorySaver` with a
      Postgres/Redis saver so chat state survives restarts and scales.
- [ ] **4b. Health-check endpoint** (`/healthz`) for the load balancer.
- [ ] **4c. Config-driven frontend** — backend URL + public keys from build/env,
      not hardcoded.
- [ ] **4d. Secrets manager** (AWS Secrets Manager per README) instead of `.env`.
- [ ] **4e. Error tracking + logging** (Sentry), uptime monitoring, structured logs.
- [ ] **4f. LLM cost controls** — paid Gemini tier, budget alerts, per-session caps.
- [ ] **4g. DB backups + migrations** (Alembic).
- [ ] **4h. CI/CD** — tests + build + deploy pipeline; bring back a test suite.

## Phase 5 — Deploy & domain

- [ ] **5a. Frontend** → S3+CloudFront (per README) or Netlify/Vercel.
- [ ] **5b. Backend** → start simple (Render/Fly.io/Railway) or the README's
      ECS Fargate + RDS + ElastiCache for full AWS.
- [ ] **5c. Domain + TLS** everywhere; HTTPS-only.
- [ ] **5d. Rotate all exposed secrets** (incl. the Gemini key shared earlier).

## Phase 6 — Legal & business

- [ ] **6a. Privacy policy + terms** (collecting PII; GDPR/CCPA).
- [ ] **6b. Cookie/consent** if analytics added.
- [ ] **6c. PCI** — minimized by using Stripe hosted checkout; document scope.
- [ ] **6d. Content cleanup** — footer says "About Juan" but copy references
      "Elena"; align branding.

---

## Target data model (Phases 2–3)

```
booking_leads   (advisor flow)         reservations (self-serve flow)
  id                                     id
  full_name, email                       customer_name, email
  cruise_id, cruise_details              cruise_id
  session_id                             amount_cents, currency
  email_sent (bool)                      status (pending/paid/confirmed/failed)
  created_at                             stripe_session_id, stripe_payment_intent
                                         booking_reference
                                         created_at, updated_at
```

## Decisions still needed from owner

1. Email provider for production (SES vs SendGrid vs Resend).
2. Bot-protection choice + keys (Turnstile vs reCAPTCHA).
3. Inventory source — curated list vs. real supplier/GDS integration.
4. Deposit vs. full payment for self-serve; refund/cancellation policy.
5. Hosting target (simple PaaS vs. full AWS per README).

## Status — done

- Phase 1a, 1b, 1d — rate limiting + CORS lock + proxy IP handling.
- Phase 1c — Cloudflare Turnstile bot protection on the chat (test keys; swap
  in real keys for prod).
- Phase 2a — lead persistence to Postgres.
- Phase 2c — consultation form posts to `/api/consultation` (persist + email,
  Turnstile-gated), replacing the `mailto:` flow.
- Phase 2e — HTTP Basic–protected `/admin` dashboard listing leads + inquiries.
- Phase 2d — "Open Calendly" links to the real scheduler (new tab).
