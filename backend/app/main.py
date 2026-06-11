from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.models import ChatRequest, BookingStatusResponse, ExecuteBookingRequest, ExecuteBookingResponse
from app.security import get_api_key
from app.agent_wrapper import simulate_agent_thought_process, check_booking_status, execute_final_booking

app = FastAPI(title="Headless AI Cruise Backend")

# Allow CORS from our frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/cruise-chat")
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

@app.post("/api/execute-booking", response_model=ExecuteBookingResponse)
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
