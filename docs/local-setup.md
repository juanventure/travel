# Local Setup / Move to a New Machine

How to get the whole project running on a fresh computer. The code lives on
GitHub; only a couple of secret files and (optionally) local data must be moved
by hand.

## What lives where

| Thing | Location | Travels via |
|-------|----------|-------------|
| All code, docs, `config.js`, `render.yaml` | GitHub (`juanventure/travel`) | `git clone` |
| Secrets | `.env`, `backend/.env` (git-ignored) | copy by hand |
| Local tool permissions | `.claude/settings.local.json` (git-ignored) | optional copy |
| Captured leads/inquiries | Docker volume `postgres_data` | optional `pg_dump` |
| Claude Code conversation + memory | `~/.claude/projects/<project-path>/` | copy by hand |

## 1. Prerequisites

- **Git**
- **Docker Desktop** (runs backend + Postgres + Redis)
- **Claude Code** (to continue the AI-assisted work)
- Node.js / Python are optional (only for occasional local scripts)

## 2. Clone the code

```powershell
cd $HOME\Desktop
git clone https://github.com/juanventure/travel.git "Travel Agency"
```

## 3. Copy the secret files (NOT in git)

Copy these from the old machine to the **same paths** on the new one:

- `Travel Agency\.env`
- `Travel Agency\backend\.env`

They contain real credentials, so move them on a **USB drive or encrypted
transfer** — never email or a public cloud share. Keys they hold:

- `GOOGLE_API_KEY` — Gemini
- `SMTP_USER`, `SMTP_APP_PASSWORD`, `SMTP_HOST`, `SMTP_PORT`, `LEAD_NOTIFICATION_EMAIL` — Gmail lead/consultation email
- `TURNSTILE_SECRET_KEY` — Cloudflare Turnstile (pairs with the public site key in `config.js`)

If you'd rather recreate them from scratch, copy `backend/.env.example` to
`backend/.env` and fill in the values.

## 4. Start the stack

```powershell
cd "$HOME\Desktop\Travel Agency"
docker compose up -d --build
```

Verify:
- Backend health: <http://localhost:8000/healthz> → `{"status":"ok"}`
- Frontend: serve the static files (e.g. `python -m http.server 5500`) and open
  <http://localhost:5500>, or open `index.html`. The chat + consultation form
  talk to the backend on `http://localhost:8000` (set in `config.js`).

Tables are created automatically on first boot, so the database starts ready.

## 5. (Optional) Move captured leads

The `postgres_data` Docker volume holds any real consultation/booking rows and
does **not** transfer with a clone. To preserve them:

```powershell
# On the OLD machine — dump both tables:
docker compose exec -T db pg_dump -U user -d travel_db `
  -t booking_leads -t consultation_inquiries --data-only > leads_backup.sql

# On the NEW machine — after `docker compose up`, restore:
Get-Content leads_backup.sql | docker compose exec -T db psql -U user -d travel_db
```

For a fresh dev machine you can skip this — the tables just start empty.

## 6. (Optional) Bring the Claude Code conversation + memory

Claude Code stores per-project history under
`~/.claude/projects/<sanitized-project-path>/` — a `*.jsonl` transcript plus a
`memory/` folder. Copy that whole folder to the same location on the new PC.

**Caveat:** the folder name encodes the project's absolute path (drive colon,
backslashes, and spaces all become `-`). For the history to attach to the
project:

- **Same Windows username + same path** (`C:\Users\juanv\Desktop\Travel Agency`)
  → it just works.
- **Different username/path** → rename the copied folder to match the new path's
  encoding, e.g. user `alice` →
  `C--Users-alice-Desktop-Travel-Agency`.

Then run `claude` in the project folder and use `/resume`.

> Even without the transcript, the durable context survives in the repo:
> [`production-readiness-plan.md`](production-readiness-plan.md) (roadmap +
> decisions) and [`deploy.md`](deploy.md) (deployment). A fresh Claude session
> reading those has the full picture.
