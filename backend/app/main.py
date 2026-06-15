import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.models import ChatRequest, BookingStatusResponse, ExecuteBookingRequest, ExecuteBookingResponse
from app.security import get_api_key
from app.agent_wrapper import simulate_agent_thought_process, check_booking_status, execute_final_booking
from app.ratelimit import rate_limiter
from app.db import init_db

# Per-IP request caps (per minute). Override via env.
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "20"))
BOOKING_RATE_LIMIT = int(os.getenv("BOOKING_RATE_LIMIT_PER_MINUTE", "10"))

# Comma-separated list of allowed browser origins. Default "*" for dev; set to
# your real frontend domain(s) in production.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the leads table exists. Soft-fail so the app still boots if the DB
    # is unavailable (e.g. local runs without Postgres).
    try:
        await init_db()
        print("[db] tables ready")
    except Exception as exc:  # noqa: BLE001
        print(f"[db] init skipped/failed: {exc!r}")
    yield


app = FastAPI(title="Headless AI Cruise Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # Auth is via the X-API-Key header, not cookies, so credentials are not needed.
    # A wildcard origin with allow_credentials=True is rejected by browsers, so keep this False.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz():
    """Liveness probe for load balancers."""
    return {"status": "ok"}


@app.post("/api/cruise-chat", dependencies=[Depends(rate_limiter(CHAT_RATE_LIMIT, "chat"))])
async def cruise_chat(request: ChatRequest, api_key: str = Depends(get_api_key)):
    """
    Handles user queries and streams the AI agent's responses.
    """
    return StreamingResponse(
        simulate_agent_thought_process(request.session_id, request.message),
        media_type="text/event-stream"
    )

@app.get("/api/booking-status/{booking_id}", response_model=BookingStatusResponse)
async def get_booking_status(booking_id: str, api_key: str = Depends(get_api_key)):
    """
    Polls for long-running agent tasks (e.g., GDS search).
    """
    status_data = await check_booking_status(booking_id)
    return BookingStatusResponse(**status_data)

@app.post("/api/execute-booking", response_model=ExecuteBookingResponse,
          dependencies=[Depends(rate_limiter(BOOKING_RATE_LIMIT, "booking"))])
async def execute_booking(request: ExecuteBookingRequest, api_key: str = Depends(get_api_key)):
    """
    Securely handles payment and final commit.
    """
    result = await execute_final_booking(
        session_id=request.session_id,
        booking_id=request.booking_id,
        payment_token=request.payment_token
    )
    return ExecuteBookingResponse(**result)
