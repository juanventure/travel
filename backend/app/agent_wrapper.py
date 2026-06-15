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

    # Track messages we have already streamed so we never send a duplicate.
    emitted_ids = set()

    def content_to_text(content):
        """
        Normalize a message's content to a plain string. Gemini 2.5+ returns
        content as a list of parts (e.g. [{'type': 'text', 'text': '...'}]) once
        thought signatures are involved, so we concatenate the text parts.
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, str):
                    parts.append(p)
                elif isinstance(p, dict) and p.get("type") == "text":
                    parts.append(p.get("text", ""))
            return "".join(parts)
        return ""

    def emit_message(msg):
        """
        Yields an SSE 'message' frame for an assistant text message, deduplicating
        by message id. Returns the SSE string, or None if it should be skipped.
        """
        if getattr(msg, "tool_calls", None):
            return None
        text = content_to_text(getattr(msg, "content", None))
        if not text.strip():
            return None
        msg_id = getattr(msg, "id", None)
        if msg_id is not None and msg_id in emitted_ids:
            return None
        if msg_id is not None:
            emitted_ids.add(msg_id)
        return f"data: {json.dumps({'type': 'message', 'content': text})}\n\n"

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
            # Stream the model's reply when it is plain text (not a tool call).
            msg = event["data"].get("output")
            if msg is not None:
                frame = emit_message(msg)
                if frame:
                    yield frame

        elif kind == "on_chain_end" and event.get("metadata", {}).get("langgraph_node"):
            # A node may append assistant messages that were NOT produced by the chat
            # model (e.g. the Booking agent's hardcoded confirmation). Those never fire
            # an on_chat_model_end event, so stream them here. Deduplication by id keeps
            # model-generated messages from being sent twice.
            output = event["data"].get("output")
            messages = output.get("messages") if isinstance(output, dict) else None
            for msg in messages or []:
                # Only assistant (AIMessage) text frames; skip tool results and dict messages.
                if getattr(msg, "type", None) != "ai":
                    continue
                frame = emit_message(msg)
                if frame:
                    yield frame

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
