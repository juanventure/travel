from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    session_id: str
    message: str
    # Cloudflare Turnstile token, required on the first message of a session
    # when bot protection is enabled.
    captcha_token: Optional[str] = None

class ConsultationRequest(BaseModel):
    fname: str
    lname: str
    email: str
    phone: Optional[str] = None
    destination: Optional[str] = None
    budget: Optional[str] = None
    num_passengers: Optional[str] = None
    cruise_length: Optional[str] = None
    travel_dates: Optional[str] = None
    message: Optional[str] = None
    # Cloudflare Turnstile token (required when bot protection is enabled).
    captcha_token: Optional[str] = None

class ConsultationResponse(BaseModel):
    success: bool
    message: str

class CallbackRequest(BaseModel):
    name: str
    phone: str
    # Free-text trip summary the AI assembled (cruise, passengers, length, dates).
    trip_summary: Optional[str] = None
    session_id: Optional[str] = None
    # Cloudflare Turnstile token (required when bot protection is enabled).
    captcha_token: Optional[str] = None


class ParseItineraryRequest(BaseModel):
    raw_text: str
    auto_save: bool = True
    client_email: Optional[str] = None


class ParseItineraryResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    share_url: Optional[str] = None
    itinerary: dict
    message: Optional[str] = None


class SaveItineraryRequest(BaseModel):
    itinerary: dict
    token: Optional[str] = None


class SaveItineraryResponse(BaseModel):
    success: bool
    token: str
    share_url: str
    message: str
