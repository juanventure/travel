"""
FastAPI Router for Digital Itineraries & AI Confirmation Parsing.
Handles parsing unstructured cruise booking texts, saving records to PostgreSQL,
and retrieving itineraries by unique secure token.
"""

import os
import secrets
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional

from app.ratelimit import rate_limiter

from app.models import (
    ParseItineraryRequest, ParseItineraryResponse,
    SaveItineraryRequest, SaveItineraryResponse,
)
from app.itinerary_parser import parse_confirmation_text
from app.db import save_itinerary, get_itinerary_by_token, list_itineraries

router = APIRouter(prefix="/api/itinerary", tags=["itinerary"],
                   dependencies=[Depends(rate_limiter(60, "itinerary"))])

# Base URL used for constructing share links
ITINERARY_BASE_URL = os.getenv("ITINERARY_BASE_URL", "https://horizonvoyages.net/itinerary/?token=")

def _configured_secrets() -> list:
    """Advisor secrets come ONLY from the environment — never from source code.

    ADVISOR_PASSKEY is the dedicated portal passkey; ADMIN_PASSWORD (also the
    HTTP Basic password for /admin) is accepted too. The public API_KEY is NOT
    accepted: it ships in config.js, so every site visitor has it.
    """
    return [s for s in (os.getenv("ADVISOR_PASSKEY"), os.getenv("ADMIN_PASSWORD")) if s]


_basic = HTTPBasic(auto_error=False)


def verify_admin_auth(x_admin_password: Optional[str] = Header(None),
                      basic: Optional[HTTPBasicCredentials] = Depends(_basic)):
    """Authenticate advisor requests (portal passkey header, or /admin Basic auth)."""
    secrets_list = _configured_secrets()
    if not secrets_list:  # fail CLOSED: never fall back to a default or open access
        raise HTTPException(status_code=503, detail="Advisor access is not configured.")

    if x_admin_password and any(
            secrets.compare_digest(x_admin_password.encode(), s.encode())
            for s in secrets_list):
        return True

    # Same-origin fetches from the Basic-auth protected /admin page carry the
    # browser's cached Basic credentials.
    admin_user = os.getenv("ADMIN_USER")
    admin_pass = os.getenv("ADMIN_PASSWORD")
    if basic and admin_user and admin_pass:
        user_ok = secrets.compare_digest(basic.username.encode(), admin_user.encode())
        pass_ok = secrets.compare_digest(basic.password.encode(), admin_pass.encode())
        if user_ok and pass_ok:
            return True

    # Plain 401, deliberately without a WWW-Authenticate header: that would make
    # browsers pop a Basic-auth dialog when the portal's fetch fails.
    raise HTTPException(status_code=401, detail="Invalid or missing advisor credentials.")


@router.post("/auth/verify", dependencies=[Depends(rate_limiter(10, "advisor-auth"))])
async def verify_passkey(_: bool = Depends(verify_admin_auth)):
    """Verify advisor passkey (server-side; the portal calls this to unlock)."""
    return {"success": True, "message": "Advisor passkey verified."}


@router.post("/parse", response_model=ParseItineraryResponse, dependencies=[Depends(verify_admin_auth)])
async def parse_cruise_confirmation(req: ParseItineraryRequest):
    """
    Ingest unstructured confirmation text or PDF extracts (e.g. Carnival, Norwegian,
    Celebrity) and parse them into the structured Horizon Voyages itinerary schema.
    Optionally saves the record in PostgreSQL and generates a shareable client URL.
    """
    try:
        itinerary_data = await parse_confirmation_text(req.raw_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse confirmation text: {exc}")

    token = None
    share_url = None

    if req.auto_save:
        token, record_id = await save_itinerary(
            itinerary_data=itinerary_data,
            client_email=req.client_email
        )
        share_url = f"{ITINERARY_BASE_URL}{token}"

    return ParseItineraryResponse(
        success=True,
        token=token,
        share_url=share_url,
        itinerary=itinerary_data,
        message="Confirmation parsed and structured successfully."
    )


@router.post("", response_model=SaveItineraryResponse, dependencies=[Depends(verify_admin_auth)])
async def save_or_update_itinerary(req: SaveItineraryRequest):
    """
    Persist or update an itinerary JSON record in PostgreSQL.
    Returns a unique URL token and client share link.
    """
    if not req.itinerary:
        raise HTTPException(status_code=400, detail="Itinerary data payload cannot be empty.")

    token, record_id = await save_itinerary(
        itinerary_data=req.itinerary,
        token=req.token
    )
    share_url = f"{ITINERARY_BASE_URL}{token}"

    return SaveItineraryResponse(
        success=True,
        token=token,
        share_url=share_url,
        message="Itinerary saved to database successfully."
    )


@router.get("/list/all", dependencies=[Depends(verify_admin_auth)])
@router.get("s/list", dependencies=[Depends(verify_admin_auth)])
async def get_all_itineraries(limit: int = 50):
    """
    Administrative overview: returns recent itineraries metadata.
    """
    return await list_itineraries(limit=limit)


@router.get("/{token}")
async def get_client_itinerary(token: str):
    """
    Retrieve full itinerary data for client-facing portal by unique token.
    Publicly accessible read-only endpoint.
    """
    itinerary_data = await get_itinerary_by_token(token)
    if not itinerary_data:
        raise HTTPException(status_code=404, detail="Itinerary not found or token has expired.")
    return itinerary_data
