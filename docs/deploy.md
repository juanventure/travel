# Deployment Guide — Horizon Voyages

This guide takes the site live on the **recommended low-cost, reliable stack**:

| Piece | Service | Cost |
|-------|---------|------|
| Frontend (static site) | **Cloudflare Pages** | Free |
| Backend (FastAPI) | **Render** (Starter) | ~$7/mo |
| Postgres database | **Neon** | Free |
| Redis (rate limit + captcha) | **Upstash** | Free |
| Bot protection | **Cloudflare Turnstile** | Free |
| Domain | **Porkbun** or **Cloudflare Registrar** | ~$10/yr |

**Total: ~$7/mo + ~$10/yr.**

> Want to start at $0? Use Render's **Free** plan instead of Starter (set
> `plan: free` in [`render.yaml`](../render.yaml)). The only downside is the
> backend sleeps after ~15 min idle, so the first visitor waits ~50s for it to
> wake. Fine for testing; upgrade to Starter before promoting the site.

The repo is already prepared for this: the Dockerfile binds to the host's
`$PORT`, [`db.py`](../backend/app/db.py) handles managed-Postgres SSL, and
[`render.yaml`](../render.yaml) is a ready Blueprint.

---

## Launch status (updated 2026-06-22)

External services and secrets are **already provisioned** — their values live in
`backend/.env` (gitignored) and the owner's secrets file, never in this repo:

| Prerequisite | Status |
|---|---|
| Neon Postgres (`DATABASE_URL`) | provisioned |
| Upstash Redis (`REDIS_URL`) | provisioned |
| Cloudflare Turnstile (site + secret keys) | have real keys (add prod domain as an allowed hostname in step 3) |
| Google Gemini API key | Done |
| Gmail App Password (SMTP) | Done |
| Admin dashboard password | Done |
| Code on GitHub (`juanventure/travel`) | Done |
| Local end-to-end test (chat, inventory tool, DB, admin) | passing on Python 3.11 |

**Remaining owner steps to go live:** §4 (deploy backend on Render) → §5 (deploy
frontend on Cloudflare Pages) → §6 (wire `config.js` to the Render URL) → §7
(lock `ALLOWED_ORIGINS`) → §9 (verify) → §10 (rotate secrets). §8 (custom domain)
is optional for a first launch — you can go live on the free `*.pages.dev` URL.

---

## 0. Prerequisites

- The repo is on GitHub (it is: `juanventure/travel`).
- You can sign in to each service with GitHub (fastest).
- Have your **Google Gemini API key** handy and your **Gmail App Password**
  (for lead/consultation emails).

Architecture once deployed:

```
  Browser ──HTTPS──> Cloudflare Pages (static frontend)
                          │  fetch() to API_BASE
                          ▼
                     Render (FastAPI)  ──> Neon (Postgres)
                                        └─> Upstash (Redis)
```

---

## 1. Postgres on Neon (free)

1. Go to <https://neon.tech> → sign up → **Create project** (pick a region close
   to where you'll host the backend, e.g. US East).
2. After it's created, open **Connection Details** / **Connect**.
3. Copy the **connection string**. It looks like:
   ```
   postgresql://USER:PASSWORD@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Save it — this is your **`DATABASE_URL`**. (The backend automatically handles
   the `sslmode=require` part.)

> Tables are created automatically on first boot (`init_db`), so there's nothing
> to run by hand.

---

## 2. Redis on Upstash (free)

1. Go to <https://upstash.com> → sign up → **Create Database** (Redis).
2. Pick a region near your backend. Leave TLS **enabled**.
3. On the database page, find the connection string in **`rediss://`** form
   (the one starting with `rediss://`, with TLS). It looks like:
   ```
   rediss://default:PASSWORD@xxx.upstash.io:6379
   ```
4. Save it — this is your **`REDIS_URL`**.

---

## 3. Bot protection keys on Cloudflare Turnstile (free)

The repo ships with Cloudflare's *test* keys (which always pass). For production,
get real keys:

1. Go to <https://dash.cloudflare.com> → **Turnstile** → **Add site**.
2. Add your domain (you can add `localhost` too for testing).
3. Copy the **Site Key** (public) and **Secret Key** (private).
   - **Secret Key** → backend env `TURNSTILE_SECRET_KEY` (step 4).
   - **Site Key** → frontend [`config.js`](../config.js) `TURNSTILE_SITE_KEY`
     (step 6).

> Skipping this? You can deploy with the test keys first and add real keys later.

---

## 4. Backend on Render

1. Go to <https://render.com> → sign up with GitHub.
2. **New → Blueprint** → connect the `juanventure/travel` repo. Render reads
   [`render.yaml`](../render.yaml) and proposes the `horizon-voyages-backend`
   web service.
3. Click **Apply**. Render will prompt for the env vars marked `sync:false` —
   fill them in:

 | Variable | Value |
 |----------|-------|
 | `DATABASE_URL` | Neon string (step 1) |
 | `REDIS_URL` | Upstash `rediss://` string (step 2) |
 | `GOOGLE_API_KEY` | your Gemini key |
 | `API_KEY` | invent a value, e.g. `hv-prod-<random>` — you'll reuse it in `config.js` |
 | `ALLOWED_ORIGINS` | leave blank for now; set in step 7 once you know the frontend URL |
 | `TURNSTILE_SECRET_KEY` | Turnstile secret (step 3), or leave the test key |
 | `ADMIN_USER` | e.g. `admin` |
 | `ADMIN_PASSWORD` | a strong password |
 | `SMTP_USER` | your Gmail address |
 | `SMTP_APP_PASSWORD` | your 16-char Gmail App Password |
 | `LEAD_NOTIFICATION_EMAIL` | where leads should be emailed |

4. Deploy. When it's live, copy the service URL, e.g.
   `https://horizon-voyages-backend.onrender.com`.
5. Verify: open `https://…onrender.com/healthz` → should return
   `{"status":"ok"}`.

---

## 5. Frontend on Cloudflare Pages

1. Go to <https://dash.cloudflare.com> → **Workers & Pages** → **Create** →
   **Pages** → **Connect to Git** → pick `juanventure/travel`.
2. Build settings (this is a plain static site — **no build step**):
   - **Framework preset:** None
   - **Build command:** *(leave empty)*
   - **Build output directory:** `/` (repo root — `index.html` lives there)
3. Deploy. You'll get a URL like `https://travel-xyz.pages.dev`.

> Note: Pages serves the whole repo root, including `config.js`. You'll point
> that at the backend in the next step.

---

## 6. Wire frontend → backend

Edit [`config.js`](../config.js) in the repo and commit the change (these values
are **not** secrets — the API key is always visible in browser JS; real
protection is the backend's rate limiting + Turnstile):

```js
window.APP_CONFIG = {
  API_BASE: 'https://horizon-voyages-backend.onrender.com',  // your Render URL
  API_KEY: 'hv-prod-<random>',                               // must match Render's API_KEY
  TURNSTILE_SITE_KEY: '<your real Turnstile site key>',      // or keep the test key
};
```

Push to GitHub → Cloudflare Pages auto-redeploys.

---

## 7. Lock CORS on the backend

Back in Render → your service → **Environment**, set:

```
ALLOWED_ORIGINS = https://travel-xyz.pages.dev,https://horizonvoyages.com,https://www.horizonvoyages.com
```

(Include the `.pages.dev` URL and your custom domain once you have it — step 8.)
Save; Render redeploys. This stops other sites from calling your API.

---

## 8. Custom domain (~$10/yr)

1. Buy a domain at <https://porkbun.com> or **Cloudflare Registrar**
   (e.g. `horizonvoyages.com`). A `.com` is best for credibility.
2. **Frontend domain (Cloudflare Pages):**
   - Pages → your project → **Custom domains** → **Set up a domain** →
     enter `horizonvoyages.com` (and `www`).
   - Follow the DNS instructions. If the domain is on Cloudflare, records are
     added automatically; otherwise add the CNAME they show at your registrar.
   - TLS is issued automatically (free).
3. **(Optional) Backend custom domain:** Render → Settings → **Custom Domains** →
   add e.g. `api.horizonvoyages.com`, then add the CNAME they give you at your
   DNS. Update `API_BASE` in `config.js` and `ALLOWED_ORIGINS` accordingly.
4. Re-run step 7 so `ALLOWED_ORIGINS` includes the final domain(s).

---

## 9. Verify end-to-end

On your live site:

1. **Chat** — open the assistant, send a message. It should respond (confirms
   `API_BASE`, `API_KEY`, CORS, Gemini, and Turnstile are all wired).
2. **Consultation form** — submit it → "You're on the list!" and you receive the
   email. (Confirms DB + SMTP.)
3. **Admin** — visit `https://<backend>/admin`, log in with `ADMIN_USER` /
   `ADMIN_PASSWORD` → you should see the lead + inquiry you just created.

If chat fails, check the browser console for a CORS error (fix `ALLOWED_ORIGINS`)
or a 403 (check `API_KEY` matches on both sides).

---

## 10. Go-live security checklist

- [ ] **Rotate the Gemini API key** if it was ever shared/committed, and set the
      new one only in Render env. *(Plan item 5d.)*
- [ ] `API_KEY` is a fresh production value (not `dev-secret-key-12345`).
- [ ] `ADMIN_PASSWORD` is strong (not `changeme`), and `/admin` is only reached
      over HTTPS.
- [ ] Real **Turnstile** keys in place (not the test keys).
- [ ] `ALLOWED_ORIGINS` lists only your real frontend domain(s).
- [ ] Privacy policy + terms published (you collect names/emails/phones).
      *(Plan item 6a.)*

---

## Cost recap

- **Render Starter:** ~$7/mo (or $0 on Free with cold starts)
- **Neon, Upstash, Cloudflare Pages, Turnstile:** $0
- **Domain:** ~$10–12/yr

≈ **$7/month + ~$10/year.**
