from app.graph.workflow import multi_agent_graph
from langchain_core.messages import HumanMessage
import json
from typing import AsyncGenerator

async def simulate_agent_thought_process(session_id: str, message: str) -> AsyncGenerator[str, None]:
    """
    Invokes the LangGraph Multi-Agent architecture and yields SSE-formatted strings.
    """
    # Only pass the new message; the checkpointer will merge it with existing state
    input_state = {
        "messages": [HumanMessage(content=message)]
    }
    
    config = {"configurable": {"thread_id": session_id}}
    
    # We use astream_events to get granular updates
    # v2 API requires version="v2"
    async for event in multi_agent_graph.astream_events(input_state, config=config, version="v2"):
        kind = event["event"]
        
        # When a node starts
        if kind == "on_chat_model_start":
            yield f"data: {json.dumps({'type': 'thought', 'content': 'Consulting AI model...'})}\n\n"
            
        elif kind == "on_tool_start":
            tool_name = event["name"]
            yield f"data: {json.dumps({'type': 'thought', 'content': f'Executing tool: {tool_name}...'})}\n\n"
            
        elif kind == "on_chat_model_end":
            # Extract final message from model if it's not a tool call
            msg = event["data"].get("output")
            if msg and getattr(msg, "content", None) and not getattr(msg, "tool_calls", None):
                # Ensure we only output text strings for the client
                yield f"data: {json.dumps({'type': 'message', 'content': msg.content})}\n\n"

    yield "data: [DONE]\n\n"

async def check_booking_status(booking_id: str) -> dict:
    """
    Simulates checking a long-running GDS booking task.
    """
    return {
        "booking_id": booking_id,
        "status": "completed",
        "details": {
            "cruise_line": "Celebrity Cruises",
            "ship": "Edge",
            "sail_date": "2026-05-15"
        }
    }

async def execute_final_booking(session_id: str, booking_id: str, payment_token: str) -> dict:
    """
    Simulates the host_agency_booking_agent securing the booking securely.
    """
    # In a real scenario, this connects to Stripe and the GDS system
    return {
        "success": True,
        "confirmation_code": f"CONF-{booking_id[:6].upper()}",
        "message": "Booking successful and secured."
    }
