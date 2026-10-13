from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from app.graph.state import AgentState
from app.graph.tools import (
    search_gds_inventory, search_live_cruises, SEARCH_LIVE_CRUISES_SCHEMA,
)
import asyncio
import json
import os
from datetime import datetime

# Initialize Gemini Model
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

# Tool-enabled LLM for the Inventory Agent. The raw JSON schema is registered so
# the model can pause generation and request a live web search.
inventory_llm = llm.bind_tools([SEARCH_LIVE_CRUISES_SCHEMA])

# Appended to EVERY agent prompt. Prompts are the soft layer; app/guardrails.py
# enforces the same rules in code (links and prices are stripped regardless).
COMPLIANCE_RULES = (
    "\n\nCOMPLIANCE RULES (always apply):\n"
    "1. Never state, estimate or hint at prices, fares, deals, discounts or dollar "
    "amounts for any cruise or cabin, and never share commission, compensation or "
    "host-agency rates. If asked about price, cost or how the advisor is paid, say "
    "your Horizon Voyages advisor will cover that personally.\n"
    "2. Never give out website addresses, links, or the names of other sites or "
    "agencies where the guest could book or compare prices. Never suggest booking "
    "anywhere else or on their own. Every booking goes through their Horizon "
    "Voyages advisor.\n"
    "3. Always steer toward the next step with the advisor: share their name and "
    "email (say 'book'), request a call back, or use the consultation form on this "
    "page. Say 'your advisor' rather than naming the host agency."
)

def router_node(state: AgentState):
    """
    Analyzes the latest message and decides the next agent.
    If the user asks about a specific cruise, destination, or pricing, route to Inventory.
    If they just say hello or ask general advice, route to Consultation.
    If they say they want to book, route to Booking.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"current_intent": "Consultation"}
        
    latest_msg = messages[-1].content.lower()
    
    # If the user is currently in the booking flow, keep them there so they can provide their name and email
    if state.get("current_intent") == "Booking":
        if "cancel" not in latest_msg and "stop" not in latest_msg and "nevermind" not in latest_msg:
            return {"current_intent": "Booking"}
    
    if "book" in latest_msg or "reserve" in latest_msg or "pay" in latest_msg:
        next_intent = "Booking"
    elif any(keyword in latest_msg for keyword in [
        "price", "cost", "alaska", "caribbean", "mediterranean", "find", "search",
        "january", "february", "march", "april", "june", "july", "august",
        "september", "october", "november", "december",
    ]):
        next_intent = "Inventory"
    else:
        next_intent = "Consultation"
        
    return {"current_intent": next_intent}

async def consultation_node(state: AgentState):
    sys_msg = SystemMessage(content=(
        "You are the AI concierge for Horizon Voyages, representing our team of cruise "
        "advisors. Provide polite, highly professional, concierge-level general advice "
        "about cruising. When you introduce yourself, speak as the Horizon Voyages team "
        "— for example, 'This is the Horizon Voyages staff and we are delighted to help "
        "you plan your journey.' Never invent a personal name or use a placeholder such "
        "as '[Your Name]'. Use warm, collective 'we' phrasing. Do not search for "
        "specific inventory; just answer questions or ask where they would like to go."
        + COMPLIANCE_RULES
    ))
    response = await llm.ainvoke([sys_msg] + state["messages"])
    return {"messages": [response]}

async def inventory_node(state: AgentState):
    today = datetime.now().strftime("%B %d, %Y")
    sys_msg = SystemMessage(content=(
        "You are the Inventory Agent for Horizon Voyages. Today's date is "
        f"{today}. Use the search_live_cruises tool to research real, current "
        "sailings for what the guest is looking for. You need a "
        "destination, a month and a year before searching: if the guest gives a "
        "month without a year, use the next upcoming occurrence of that month; if "
        "the destination or month is missing, ask for it instead of guessing. Only "
        "set cruise_line if the guest named one.\n\n"
        "The tool returns JSON: {\"ok\", \"results\": [{\"title\", \"snippet\"}]} or "
        "{\"ok\": false, \"message\"}. It is background research for you — it has no "
        "links or prices by design. Base your answer ONLY on those results. In warm, "
        "concise natural language, summarise the most relevant sailings or "
        "itineraries (cruise line, ship, nights, dates, ports) when the snippets "
        "state them, and never invent details they don't. Offer two or three "
        "options at most.\n\n"
        "Finish every answer by inviting the guest to have their Horizon Voyages "
        "advisor price and book the one they like: ask them to share their name and "
        "email (or say 'book'), or offer a call back or the consultation form. "
        "Their advisor will provide current, personalized pricing and handle the "
        "booking.\n\n"
        "If the tool reports an error, a past date, or no results, say so politely "
        "(for a past date, ask for a future one) and offer to connect them with an "
        "advisor or the consultation form instead. Never present these results as "
        "something Horizon Voyages has reserved or can guarantee."
        + COMPLIANCE_RULES
    ))
    
    # We invoke the tool-bound LLM. If it emits a tool call, the graph routes to
    # tool_execution_node, then back here with the results in the history.
    response = await inventory_llm.ainvoke([sys_msg] + state["messages"])
    return {"messages": [response]}

async def _run_tool_call(tool_call) -> ToolMessage:
    """Execute one model tool call and wrap the result as a ToolMessage."""
    name = tool_call["name"]
    args = tool_call.get("args") or {}
    try:
        if name == "search_live_cruises":
            result = await search_live_cruises(
                destination=args.get("destination", ""),
                month=args.get("month", ""),
                year=args.get("year"),
                cruise_line=args.get("cruise_line"),
            )
        elif name == "search_gds_inventory":
            result = search_gds_inventory.invoke(args)
        else:
            result = json.dumps({"ok": False, "message": f"Unknown tool: {name}"})
    except Exception as exc:  # noqa: BLE001 - always answer the tool call
        print(f"[tools] {name} failed: {exc!r}")
        result = json.dumps({"ok": False, "message": "The tool failed unexpectedly."})
    # A proper ToolMessage with the tool name and matching tool_call_id: Gemini
    # requires the function name on the response to correlate it with the call,
    # otherwise the follow-up model turn comes back empty.
    return ToolMessage(content=result, tool_call_id=tool_call["id"], name=name)

async def tool_execution_node(state: AgentState):
    """
    Executes the tool call(s) returned by the Inventory agent. Each call is run
    concurrently and answered with exactly one ToolMessage.
    """
    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []
    tool_messages = await asyncio.gather(*(_run_tool_call(tc) for tc in tool_calls))
    return {"messages": list(tool_messages)}

from app.graph.tools import search_gds_inventory, submit_booking_lead, get_cruise_details
from app.notifications import send_booking_lead_email
from app.db import save_booking_lead, mark_lead_emailed

async def booking_node(state: AgentState):
    sys_msg = SystemMessage(content=(
        "You are the Reservation Request Agent for Horizon Voyages. Gather the "
        "details an advisor needs to price and hold a sailing: the guest's full "
        "name, email, the sailing they want, the number of passengers, their "
        "preferred cruise length (in nights), and their preferred travel dates or "
        "date range. For 'the sailing', use a short plain-language description of "
        "what they chose — cruise line, ship or itinerary, destination and month/"
        "year (for example 'Celebrity Edge, 7-night Eastern Caribbean, July 2027'); "
        "if they mention a voyage ID like VOY-123, use that. Ask for whichever are "
        "still missing — it's fine to collect "
        "them over a few messages, one or two at a time. Once you have at least "
        "the full name, email, and the sailing, YOU MUST call the "
        "submit_booking_lead tool, passing the sailing description as cruise_id and "
        "everything else you've collected "
        "(including passengers, cruise length, and travel dates when known).\n\n"
        "Hard rules. You are collecting a reservation REQUEST, not taking a "
        "booking. Never state or imply that a cabin is held, reserved, or "
        "confirmed. Never invent a confirmation or booking number. Never ask for "
        "card, bank or passport details, and never promise to send a payment "
        "link — Horizon Voyages does not collect payment. When a guest is ready "
        "to deposit, their advisor books it with the cruise line and the guest "
        "pays the cruise line directly. If asked about paying, say exactly that."
        + COMPLIANCE_RULES
    ))
    booking_llm = llm.bind_tools([submit_booking_lead])
    response = await booking_llm.ainvoke([sys_msg] + state["messages"])

    messages_to_return = [response]
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] != "submit_booking_lead":
                continue
            args = tool_call["args"]

            # 1. Record the lead (fast, synchronous).
            result = submit_booking_lead.invoke(args)
            messages_to_return.append(ToolMessage(
                content=result, tool_call_id=tool_call["id"], name=tool_call["name"],
            ))

            full_name = args.get("full_name", "")
            email = args.get("email", "")
            sailing = (args.get("cruise_id") or "").strip()
            num_passengers = args.get("num_passengers")
            cruise_length = args.get("cruise_length")
            travel_dates = args.get("travel_dates")
            # A known mock ID gets its formatted details; otherwise the guest's
            # plain-language sailing description IS the details. cruise_id is a
            # VARCHAR(64) column, so store a truncated copy there.
            details = get_cruise_details(sailing) or sailing or None
            cruise_id = sailing[:64]

            # 2. Persist the lead BEFORE emailing, so it is never lost even if the
            #    email fails. Soft-fails (returns None) if the DB is unavailable.
            lead_id = await save_booking_lead(
                full_name, email, cruise_id, details,
                num_passengers=num_passengers, cruise_length=cruise_length,
                travel_dates=travel_dates,
            )

            # 3. Notify the agency by email, OFF the event loop so the blocking
            #    SMTP call doesn't stall this (or any other) request.
            sent = await asyncio.to_thread(
                send_booking_lead_email, full_name, email, cruise_id, details,
                num_passengers, cruise_length, travel_dates,
            )
            await mark_lead_emailed(lead_id, sent)

            # 3. Confirm truthfully: only promise advisor follow-up if it was sent.
            #    Built without an LLM call to save Gemini API quota.
            first_name = full_name.split()[0] if full_name.strip() else "there"
            voyage = sailing or "your selected voyage"
            if sent:
                final_text = (
                    f"Wonderful, {first_name} — I've passed your request for {voyage} to "
                    f"your Horizon Voyages advisor. They'll email you at {email} with "
                    f"current pricing, cabin options and anything worth knowing about "
                    f"that sailing. Nothing is held or charged yet: when you're happy "
                    f"with the details, your advisor places the booking and you pay the "
                    f"cruise line directly."
                )
            else:
                final_text = (
                    f"Thank you, {first_name} — your request for {voyage} is saved. We "
                    f"hit a snag notifying the team automatically just now, but your "
                    f"details are recorded and an advisor will follow up at {email} as "
                    f"soon as possible. Nothing is held or charged at this stage."
                )
            messages_to_return.append(AIMessage(content=final_text))

    return {"messages": messages_to_return}
