# Production Readiness & Booking Implementation Plan

Goal: take Horizon Voyages from demo to a live site that supports **both**
booking models:

- **Advisor lead-gen** — capture a qualified lead, notify the agency, advisor
  follows up (this flow exists today, needs hardening).
- **Self-serve booking** — the guest books without a human in the loop, by
  clicking through to the cruise line's own booking page on an
  agency-attributed Partner Booking Link (not built yet; see Phase 3).

**Business model constraint (recorded 2026-09-08).** Horizon Voyages operates
under a host agency (Fora). The host is the agency of record: bookings sit
under the host's IATA number, the guest pays the cruise line directly, and
commission flows cruise line → host → advisor. We never take cruise fare into
our own payment processor. Doing so would (a) earn no commission, since the
booking would not sit with the host, (b) make us the merchant of record for
travel, triggering seller-of-travel registration and trust-accounting duties in
CA/FL/WA/HI, and (c) almost certainly breach the host's advisor agreement.
Every design decision below follows from this.

This document is the source of truth for the roadmap. Each phase lists concrete
tasks, the files involved, and how to verify.

---

## 0. Current state (what's real vs. mock)

| Area | State |
|------|-------|
| AI chat (consultation/inventory/booking) | Working (Gemini 2.5-flash) |
| Inventory | Mock — 3 hardcoded cruises in `tools.py` (`MOCK_GDS`) |
| Lead capture | Email + logs only; **no persistence** |
| Agency email | Working (Gmail SMTP); deliverability not production-grade |
| Payments / reservations | **Removed 2026-09-08.** `/api/execute-booking` and `/api/booking-status` returned fabricated confirmation codes from a public endpoint; deleted along with their models, `agent_wrapper` stubs and the `CruiseChatClient.js` methods. We do not take payment — see the business model constraint above. |
| Auth | Single shared `X-API-Key`, exposed in frontend JS |
| CORS | `allow_origins=["*"]` |
| Rate limiting | None (Redis provisioned but unused) |
| Conversation state | In-memory `MemorySaver` (lost on restart, not multi-instance) |
| Frontend backend URL | Hardcoded `http://localhost:8000` |
| Consultation form | `mailto:` (unreliable) |
| Hosting / domain / TLS | None |
| Tests / CI / monitoring | None |
| Legal (privacy/terms) | None |

---

## Phase 1 — Security & abuse controls (LAUNCH BLOCKERS)

Protects the public LLM endpoint from cost-abuse and locks the browser surface.

- [x] **1a. Rate limiting** (Redis-backed, per-IP) on `/api/cruise-chat` and
      `/api/execute-booking`. — `ratelimit.py`, `main.py`
- [x] **1b. Lock CORS** to configured origins via `ALLOWED_ORIGINS`. — `main.py`
- [x] **1c. Bot check** (Cloudflare Turnstile) on the chat first message
      — `captcha.py`, frontend Turnstile widget. Uses test keys by default;
      swap in real site/secret keys for production. (Consultation form gets it
      with 2c.)
- [x] **1d. Honour `X-Forwarded-For`** for client IP behind a proxy/ALB.

Verify: hammer an endpoint past the limit → `429`; browser requests from a
non-allowed origin are blocked while the real frontend works.

## Phase 2 — Lead-gen production

Make the advisor flow durable and reliable.

- [x] **2a. Persist leads to Postgres** (`booking_leads` table) — saved before
      the email so a lead is never lost; record `email_sent`. — `db.py`,
      `agents.py`, `main.py`
- [x] **2b. Production email** — **DECISION (2026-06-16): stay on Gmail SMTP.**
      Lead/consultation volume is low, so Gmail's limits are not a concern and a
      transactional provider isn't warranted. Keep the existing
      `notifications.py` Gmail-SMTP path. Caveats accepted (see below).
- [x] **2c. Consultation form posts to backend** instead of `mailto:`  — new
      `/api/consultation` endpoint (Turnstile-gated, rate-limited) persists to a
      `consultation_inquiries` table BEFORE emailing the agency; frontend POSTs
      via `fetch` with the bot-check widget. — `main.py`, `db.py`,
      `notifications.py`, `captcha.py`, `script.js`, `index.html`
- [x] **2d. Replace Calendly placeholder**  — "Open Calendly" now links to
      https://calendly.com/horizonvoyages (new tab); removed the `alert()` stub. — `index.html`, `script.js`
- [x] **2e. Admin view**  — HTTP Basic–protected `/admin` page lists booking
      leads + consultation inquiries. Separate `ADMIN_USER`/`ADMIN_PASSWORD`
      auth (not the public API key); disabled (503) when unconfigured. — `admin.py`, `db.py`, `main.py`

## Phase 3 — Self-serve booking via Partner Booking Links

**Superseded 2026-09-08.** The original plan here (Stripe Checkout, a
`reservations` table, webhooks, refund reconciliation) is cancelled — see the
business model constraint at the top. We cannot take cruise fare.

The same goal — the guest books with no human in the loop — is met instead by a
**Partner Booking Link (PBL)**: a deep link from our site into the cruise
line's own consumer booking flow, carrying the host agency's attribution. The
guest shops live inventory and live pricing on the cruise line's site, pays the
cruise line, and the booking lands with full commission to the agency. No
payment code, no PCI scope, no inventory feed, no confirmation emails to send.

Royal Caribbean Group's CruisingPower portal documents PBL explicitly ("When
consumers book through your Partner Booking Link, you receive full
commission"), which covers Royal Caribbean, Celebrity and Silversea from a
single portal.

- [x] **3a. Confirm PBL is permitted under the host's IATA** — **Answered by
      Fora (Merritt, Membership, 2026-09-16):** yes, as long as everything is
      tied to Fora's IATA#. A booking made through your link/quote, or by you on
      the guest's behalf, either loads automatically or is submitted in Fora's
      Portal. Portal access to the IATA# comes after joining + a brief ID
      verification. *Still unanswered:* whether PBL bookings count toward
      commission tiers / the CLIA card threshold.

      **Link policy (2026-10-13).** Fora also allows the AI assistant provided it
      never shares Fora fares or commissions with clients. And a guest handed any
      third-party booking link can book around the advisor (no commission, not
      under the Fora IATA#). So the chatbot gives out **no outbound links** except
      an allowlist (own site + Calendly, `OUTBOUND_LINK_ALLOWLIST`), enforced in
      code (`app/guardrails.py`): search results reach the model as titles +
      snippets only, with URLs and dollar amounts stripped; every outbound
      message is link-filtered; prompts steer every conversation to the advisor.
      The only booking link that may ever be added to the allowlist is a Fora-
      attributed Partner Booking Link (3e/3f).
- [ ] **3b. Per-line attribution audit** — for each line we build for, confirm
      with the BDM that a consumer-facing attributed booking link exists and get
      the URL format. Confirmed so far: Royal Caribbean Group (CruisingPower).
      Unconfirmed: Virgin, and everything else.
- [ ] **3c. Curated sailings table** — replace `MOCK_GDS` with a DB table of
      hand-picked sailings. Each row: line, ship, region, nights, sail date,
      short editorial note, and `booking_url` (the PBL deep link). No fares
      stored — pricing lives on the cruise line's page, which also keeps the
      inventory agent's existing "never quote a price" rule honest.
- [ ] **3d. Admin CRUD for sailings** — extend `/admin` so sailings can be added
      and retired without a deploy. Dead sail dates are worse than none.
- [ ] **3e. Route in chat** — the inventory agent offers two paths: "book this
      yourself" (hand over the PBL) or "have an advisor handle it" (existing
      `submit_booking_lead` flow). Log which path each session takes.
- [ ] **3f. Attribution tracking** — tag outbound PBL clicks so we can reconcile
      site clicks against commission statements. Without this we cannot tell
      whether the self-serve path works at all.

### Line strategy (decided 2026-09-08)

**Build for** — curated sailings, PBLs, dedicated landing copy:
Royal Caribbean, Celebrity, Silversea (one portal, CruisingPower, covering
mainstream → premium → luxury) and Virgin Voyages (strong advisor program,
adults-only positioning that matches the site's existing voice).

**Book on request** — everything else, including Carnival. Handled by the
existing consultation form and chat lead flow; no per-line build work. Carnival
in particular is deliberately not a build target: lowest fares in the
mainstream segment means the fewest commission dollars per booking, and it sits
badly against the site's premium positioning. Revisit with real booking data.

## Phase 4 — Reliability & ops

- [ ] **4a. Durable LangGraph checkpointer** — replace `MemorySaver` with a
      Postgres/Redis saver so chat state survives restarts and scales.
- [ ] **4b. Health-check endpoint** (`/healthz`) for the load balancer.
- [x] **4c. Config-driven frontend**  — backend URL + public keys moved out of
      `script.js` into `config.js` (`window.APP_CONFIG`), loaded before the app
      and swappable per environment with no rebuild. `script.js` reads it with
      safe fallbacks. — `config.js`, `index.html`, `script.js`
- [ ] **4d. Secrets manager** (AWS Secrets Manager per README) instead of `.env`.
- [ ] **4e. Error tracking + logging** (Sentry), uptime monitoring, structured logs.
- [ ] **4f. LLM cost controls** — paid Gemini tier, budget alerts, per-session caps.
- [ ] **4g. DB backups + migrations** (Alembic).
- [ ] **4h. CI/CD** — tests + build + deploy pipeline; bring back a test suite.

## Phase 5 — Deploy & domain

**Stack chosen (2026-06-16):** Cloudflare Pages (frontend) + Render Starter
(backend) + Neon (Postgres) + Upstash (Redis) + Cloudflare Turnstile + a `.com`
domain. ≈ $7/mo + ~$10/yr. **Repo is prepped + a step-by-step guide is written:
[`docs/deploy.md`](deploy.md).** Remaining work is owner account setup per the guide.

- [~] **5a. Frontend** → Cloudflare Pages. *Ready — follow deploy.md §5.*
- [~] **5b. Backend** → Render (Docker, `$PORT`-aware) + Neon + Upstash;
      Blueprint at `render.yaml`, `db.py` handles managed-Postgres SSL.
      *Ready — follow deploy.md §1–4.*
- [ ] **5c. Domain + TLS** everywhere; HTTPS-only. *Guide: deploy.md §8 (TLS auto).*
- [ ] **5d. Rotate all exposed secrets** (incl. the Gemini key shared earlier).
      *Checklist: deploy.md §10.*

## Phase 6 — Legal & business

- [ ] **6a. Privacy policy + terms** (collecting PII; GDPR/CCPA).
- [ ] **6b. Cookie/consent** if analytics added.
- [ ] **6c. PCI** — minimized by using Stripe hosted checkout; document scope.
- [ ] **6d. Content cleanup** — footer says "About Juan" but copy references
      "Elena"; align branding.

---

## Target data model (Phases 2–3)

The `reservations` table is cancelled with the Stripe plan — we hold no orders,
because we take no money. The self-serve path stores curated sailings and click
attribution instead.

```
booking_leads   (advisor flow)         sailings (self-serve flow)
  id                                     id
  full_name, email                       cruise_line, ship
  cruise_id, cruise_details              region, nights, sail_date
  session_id                             editorial_note
  email_sent (bool)                      booking_url   (Partner Booking Link)
  created_at                             active (bool)
                                         created_at, updated_at

                                       pbl_clicks (attribution)
                                         id, sailing_id, session_id
                                         clicked_at
```

## Decisions still needed from owner

1. ~~Email provider for production (SES vs SendGrid vs Resend).~~ **Decided
   2026-06-16: stay on Gmail SMTP.** Caveats accepted:
   - Gmail free-tier sends ~500 emails/day (Workspace ~2,000) — fine at current
     lead volume, revisit if it grows.
   - These are internal *notification* emails to the agency, not bulk mail to
     customers, so spam/deliverability risk is minimal. If customer-facing email
     (Phase 3e receipts) is added later, reconsider a transactional provider.
   - Requires a Gmail **App Password** (`SMTP_APP_PASSWORD`), not the login
     password; 2FA must stay enabled on the account.
2. Bot-protection choice + keys (Turnstile vs reCAPTCHA).
3. ~~Inventory source — curated list vs. real supplier/GDS integration.~~
   **Decided 2026-09-08: curated list.** A real GDS/supplier feed needs
   agency-level contracts we cannot hold as an advisor under a host, and the
   bookings would attribute to whoever holds the feed. Live pricing comes from
   the cruise line's own page at the end of the PBL.
4. ~~Deposit vs. full payment for self-serve; refund/cancellation policy.~~
   **Moot 2026-09-08** — we take no payment. Deposit terms, refunds and
   cancellation are the cruise line's, governed by their contract of carriage.
5. **Partly answered 2026-09-16 (see 3a).** Fora: (a) PBLs allowed if tied to
   Fora's IATA#; (b) disclosure — say you're affiliated with Fora *somewhere on
   the site* (done: footer + legal pages); their registration covers your SOT via
   a form after joining; (c) AI assistant allowed if it never shares Fora fares
   or commissions. **Still open — ask in writing:** literal disclosure wording;
   whether Fora wants to review the AI assistant / any required AI disclosure;
   whether PBL bookings count toward commission tiers and the CLIA card
   threshold; any restrictions on advertising fares or promotions on our own site.
6. ~~Hosting target (simple PaaS vs. full AWS per README).~~ **Decided
   2026-06-16:** Cloudflare Pages + Render + Neon + Upstash (see Phase 5 / `docs/deploy.md`).

## Status — done

- Phase 1a, 1b, 1d — rate limiting + CORS lock + proxy IP handling.
- Phase 1c — Cloudflare Turnstile bot protection on the chat (test keys; swap
  in real keys for prod).
- Phase 2a — lead persistence to Postgres.
- Phase 2c — consultation form posts to `/api/consultation` (persist + email,
  Turnstile-gated), replacing the `mailto:` flow.
- Phase 2e — HTTP Basic–protected `/admin` dashboard listing leads + inquiries.
- Phase 2d — "Open Calendly" links to the real scheduler (new tab).
- Phase 2b — decided to stay on Gmail SMTP (no transactional provider).
- Phase 4c — config-driven frontend (`config.js` / `window.APP_CONFIG`).
- Phase 5 prep — deploy stack chosen, repo prepped (`render.yaml`, `$PORT`,
  managed-Postgres SSL), step-by-step guide at `docs/deploy.md`.
- 2026-09-08 — business model constraint recorded; Phase 3 rewritten around
  Partner Booking Links; `/api/execute-booking` + `/api/booking-status` and
  their client methods deleted; booking agent copy corrected so it no longer
  promises a payment link or implies a cabin is held.
