"""
FastAPI Router for Digital Itineraries & AI Confirmation Parsing.
Handles parsing unstructured cruise booking texts, saving records to PostgreSQL,
and retrieving itineraries by unique secure token.
"""

import os
import secrets
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional

from app.models import (
    ParseItineraryRequest, ParseItineraryResponse,
    SaveItineraryRequest, SaveItineraryResponse,
)
from app.itinerary_parser import parse_confirmation_text
from app.db import save_itinerary, get_itinerary_by_token, list_itineraries

router = APIRouter(prefix="/api/itinerary", tags=["itinerary"])

# Base URL used for constructing share links
ITINERARY_BASE_URL = os.getenv("ITINERARY_BASE_URL", "https://horizonvoyages.net/itinerary/?token=")

def verify_admin_auth(x_admin_password: Optional[str] = Header(None),
                      x_api_key: Optional[str] = Header(None)):
    """Authenticate advisor requests to prevent unauthorized parsing or data inspection."""
    token = x_admin_password or x_api_key
    if not token:
        raise HTTPException(status_code=401, detail="Missing advisor passkey.")

    # 1. Accept the chosen advisor passkey
    if secrets.compare_digest(token, "K@4L4nn202"):
        return True

    # 2. Also accept any configured ADMIN_PASSWORD from environment
    env_admin = os.getenv("ADMIN_PASSWORD")
    if env_admin and secrets.compare_digest(token, env_admin):
        return True

    # 3. Also accept the configured API_KEY from environment
    env_key = os.getenv("API_KEY")
    if env_key and secrets.compare_digest(token, env_key):
        return True

    raise HTTPException(status_code=401, detail="Invalid advisor passkey.")


@router.post("/auth/verify")
async def verify_passkey(x_admin_password: Optional[str] = Header(None),
                         x_api_key: Optional[str] = Header(None)):
    """Verify advisor passkey."""
    verify_admin_auth(x_admin_password, x_api_key)
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


@router.post("", response_model=SaveItineraryResponse)
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
