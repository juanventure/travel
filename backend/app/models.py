from pydantic import BaseModel
from typing import Optional, Dict, Any

class ChatRequest(BaseModel):
    session_id: str
    message: str

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
