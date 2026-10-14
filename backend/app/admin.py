"""
Authenticated admin view: lists captured booking leads and consultation
inquiries in a simple HTML page.

Auth is HTTP Basic via ADMIN_USER / ADMIN_PASSWORD env vars — deliberately
SEPARATE from the public X-API-Key (which ships in the frontend JS and so is
not a secret). If either env var is unset, the admin interface is disabled
(503) rather than left open.
"""
import html
import os
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.db import (
    list_booking_leads, list_consultations, list_callback_requests, list_itineraries,
)
from app.ratelimit import rate_limiter

router = APIRouter()
_basic = HTTPBasic(auto_error=False)


def require_admin(credentials: HTTPBasicCredentials = Depends(_basic)) -> str:
    """HTTP Basic gate for admin routes. Disabled (503) when not configured."""
    user = os.getenv("ADMIN_USER")
    password = os.getenv("ADMIN_PASSWORD")
    if not user or not password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin interface is not configured.",
        )
    # Constant-time comparison; check both fields regardless to avoid leaking
    # which one was wrong via timing.
    ok = credentials is not None
    user_ok = ok and secrets.compare_digest(credentials.username, user)
    pass_ok = ok and secrets.compare_digest(credentials.password, password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class _Raw(str):
    """Marks trusted, server-built HTML so _fmt doesn't escape it. User/AI-derived
    text must never be wrapped in this."""


def _fmt(value) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M UTC")
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, _Raw):
        return str(value)
    return html.escape(str(value))


def _table(title: str, headers: list[str], rows: list[list]) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    if rows:
        body = "".join(
            "<tr>" + "".join(f"<td>{_fmt(c)}</td>" for c in r) + "</tr>" for r in rows
        )
    else:
        body = f'<tr><td colspan="{len(headers)}" class="empty">No records yet.</td></tr>'
    return (
        f"<section><h2>{html.escape(title)} "
        f'<span class="count">({len(rows)})</span></h2>'
        f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></section>"
    )


_STYLE = """
  body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 24px;
         background: #0f1b2d; color: #e8eef6; }
  h1 { font-size: 1.4rem; margin: 0 0 4px; }
  .sub { color: #93a4bd; margin: 0 0 24px; font-size: .9rem; }
  section { margin-bottom: 40px; }
  h2 { font-size: 1.1rem; border-bottom: 1px solid #2a3a52; padding-bottom: 6px; }
  .count { color: #93a4bd; font-weight: normal; font-size: .9rem; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #20304a;
           vertical-align: top; }
  th { color: #c8a96e; font-weight: 600; white-space: nowrap; }
  tr:hover td { background: rgba(255,255,255,.03); }
  .empty { color: #93a4bd; text-align: center; padding: 20px; }
"""


@router.get("/admin", response_class=HTMLResponse,
            dependencies=[Depends(rate_limiter(30, "admin"))])
async def admin_dashboard(request: Request, _: str = Depends(require_admin)):
    leads = await list_booking_leads()
    inquiries = await list_consultations()
    callbacks = await list_callback_requests()

    itins = await list_itineraries()

    callbacks_table = _table(
        "Callback requests",
        ["ID", "Name", "Phone", "Trip", "Notified", "Created"],
        [[c.id, c.name, c.phone, c.trip_summary, c.notified, c.created_at]
         for c in callbacks],
    )

    itins_table = _table(
        "Client Digital Itineraries",
        ["ID", "Client", "Vessel & Line", "Sail Date", "Token Portal Link", "Created"],
        [[it.get("id"),
          it.get("client_name") or "—",
          f"{it.get('cruise_line') or ''} ({it.get('ship_name') or ''})".strip() or "—",
          it.get("sail_date") or "—",
          _Raw(f'<a href="/itinerary/?token={html.escape(str(it.get("token")), quote=True)}" target="_blank" rel="noopener noreferrer" style="color:#c8a96e; font-weight:600;">Open Itinerary ({html.escape(str(it.get("token"))[:8])}…) ↗</a>'),
          it.get("created_at")]
         for it in itins],
    )

    generator_html = """
    <section>
      <h2>Generate Client Digital Itinerary (AI Confirmation Parser)</h2>
      <p class="sub" style="margin-bottom:12px;">Paste raw confirmation text from cruise lines (Norwegian, Carnival, Celebrity, Virgin, Royal Caribbean, etc.) to extract logistics and issue an authenticated client portal link.</p>
      <div style="display:flex; flex-direction:column; gap:10px; max-width:850px;">
        <textarea id="rawConfirmation" rows="6" placeholder="Paste booking confirmation email or PDF extract here..." style="width:100%; padding:10px; border-radius:6px; background:#162438; color:#fff; border:1px solid #2a3a52; font-family:monospace; font-size:0.85rem; box-sizing:border-box;"></textarea>
        <div style="display:flex; gap:12px; align-items:center;">
          <input type="email" id="clientEmail" placeholder="Client email (optional)" style="flex:1; padding:8px 12px; border-radius:6px; background:#162438; color:#fff; border:1px solid #2a3a52; font-size:0.85rem;" />
          <button onclick="generateItinerary()" id="btnGen" style="background:#c8a96e; color:#060d1f; border:none; padding:9px 18px; border-radius:6px; font-weight:600; cursor:pointer;">Generate & Save Itinerary</button>
        </div>
        <div id="genResult" style="display:none; padding:12px; border-radius:6px; background:rgba(200,169,110,0.1); border:1px solid #c8a96e; margin-top:8px;"></div>
      </div>
    </section>
    <script>
    async function generateItinerary() {
      const text = document.getElementById('rawConfirmation').value.trim();
      const email = document.getElementById('clientEmail').value.trim();
      const resDiv = document.getElementById('genResult');
      const btn = document.getElementById('btnGen');
      if (!text) { alert('Please paste confirmation text first.'); return; }
      btn.disabled = true;
      btn.innerText = 'Parsing with AI...';
      try {
        const res = await fetch('/api/itinerary/parse', {
          method: 'POST',
          credentials: 'same-origin',  // sends this page's cached Basic-auth credentials
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ raw_text: text, client_email: email, auto_save: true })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          const portalUrl = '/itinerary/?token=' + encodeURIComponent(data.token);
          const shareUrl = data.share_url || (window.location.origin + portalUrl);
          const guest = (data.itinerary && data.itinerary.client && data.itinerary.client.leadGuest) || 'Guest';
          const ship = (data.itinerary && data.itinerary.booking && data.itinerary.booking.ship) || 'Ship';
          // DOM nodes + textContent only: AI-parsed text must never become markup.
          resDiv.style.display = 'block';
          resDiv.textContent = '';
          const strong = document.createElement('strong');
          strong.textContent = 'Success! ';
          resDiv.appendChild(strong);
          resDiv.appendChild(document.createTextNode('Itinerary generated for ' + guest + ' (' + ship + ')'));
          resDiv.appendChild(document.createElement('br'));
          resDiv.appendChild(document.createTextNode('Client Portal URL: '));
          const link = document.createElement('a');
          link.href = portalUrl;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.style.cssText = 'color:#c8a96e; font-weight:bold;';
          link.textContent = shareUrl;
          resDiv.appendChild(link);
          resDiv.appendChild(document.createElement('br'));
          const copyBtn = document.createElement('button');
          copyBtn.textContent = 'Copy Client Link';
          copyBtn.style.cssText = 'margin-top:8px; padding:6px 12px; border-radius:4px; border:none; background:#c8a96e; color:#060d1f; font-weight:600; cursor:pointer;';
          copyBtn.addEventListener('click', () => { navigator.clipboard.writeText(shareUrl); alert('Copied to clipboard!'); });
          resDiv.appendChild(copyBtn);
          const refreshBtn = document.createElement('button');
          refreshBtn.textContent = 'Refresh Table';
          refreshBtn.style.cssText = 'margin-left:10px; padding:6px 12px; border-radius:4px; border:1px solid #2a3a52; background:#162438; color:#fff; cursor:pointer;';
          refreshBtn.addEventListener('click', () => window.location.reload());
          resDiv.appendChild(refreshBtn);
        } else {
          alert('Error: ' + (data.detail || 'Failed to parse confirmation.'));
        }
      } catch (err) {
        alert('Request failed: ' + err);
      } finally {
        btn.disabled = false;
        btn.innerText = 'Generate & Save Itinerary';
      }
    }
    </script>
    """

    leads_table = _table(
        "Booking leads",
        ["ID", "Name", "Email", "Cruise", "Passengers", "Length", "Dates",
         "Session", "Emailed", "Created"],
        [[l.id, l.full_name, l.email, l.cruise_id, l.num_passengers,
          l.cruise_length, l.travel_dates, l.session_id, l.email_sent,
          l.created_at] for l in leads],
    )
    inquiries_table = _table(
        "Consultation inquiries",
        ["ID", "Name", "Email", "Phone", "Destination", "Budget", "Passengers",
         "Length", "Dates", "Message", "Emailed", "Created"],
        [[i.id, f"{i.first_name} {i.last_name}".strip(), i.email, i.phone,
          i.destination, i.budget, i.num_passengers, i.cruise_length,
          i.travel_dates, i.message, i.email_sent, i.created_at]
         for i in inquiries],
    )

    page = (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Horizon Voyages — Admin</title><style>{_STYLE}</style></head><body>"
        f"<h1>Horizon Voyages — Admin</h1>"
        f"<p class='sub'>Captured leads, active itineraries, and consultation inquiries.</p>"
        f"{generator_html}{itins_table}{callbacks_table}{leads_table}{inquiries_table}</body></html>"
    )
    return HTMLResponse(content=page)
