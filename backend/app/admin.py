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

from app.db import list_booking_leads, list_consultations
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


def _fmt(value) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M UTC")
    if isinstance(value, bool):
        return "yes" if value else "no"
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

    leads_table = _table(
        "Booking leads",
        ["ID", "Name", "Email", "Cruise", "Session", "Emailed", "Created"],
        [[l.id, l.full_name, l.email, l.cruise_id, l.session_id, l.email_sent,
          l.created_at] for l in leads],
    )
    inquiries_table = _table(
        "Consultation inquiries",
        ["ID", "Name", "Email", "Phone", "Destination", "Budget", "Message",
         "Emailed", "Created"],
        [[i.id, f"{i.first_name} {i.last_name}".strip(), i.email, i.phone,
          i.destination, i.budget, i.message, i.email_sent, i.created_at]
         for i in inquiries],
    )

    page = (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Horizon Voyages — Admin</title><style>{_STYLE}</style></head><body>"
        f"<h1>Horizon Voyages — Admin</h1>"
        f"<p class='sub'>Captured leads and consultation inquiries.</p>"
        f"{leads_table}{inquiries_table}</body></html>"
    )
    return HTMLResponse(content=page)
