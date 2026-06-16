from pydantic import BaseModel
from typing import Optional, Dict, Any

class ChatRequest(BaseModel):
    session_id: str
    message: str
    # Cloudflare Turnstile token, required on the first message of a session
    # when bot protection is enabled.
    captcha_token: Optional[str] = None

class BookingStatusResponse(BaseModel):
    booking_id: str
    status: str
    details: Optional[Dict[str, Any]] = None

class ExecuteBookingRequest(BaseModel):
    session_id: str
    booking_id: str
    payment_token: str

class ExecuteBookingResponse(BaseModel):
    success: bool
    confirmation_code: Optional[str] = None
    message: str
