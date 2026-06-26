from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from app.graph.state import AgentState
from app.graph.tools import search_gds_inventory
import asyncio
import json
import os

# Initialize Gemini Model
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

# Tool-enabled LLM for the Inventory Agent
inventory_llm = llm.bind_tools([search_gds_inventory])

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
    elif any(keyword in latest_msg for keyword in ["price", "cost", "alaska", "caribbean", "mediterranean", "find", "search"]):
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
    ))
    response = await llm.ainvoke([sys_msg] + state["messages"])
    return {"messages": [response]}

async def inventory_node(state: AgentState):
    sys_msg = SystemMessage(content=(
        "You are the Inventory Agent for Horizon Voyages. Use the search_gds_inventory "
        "tool to find sailings that match what the guest is looking for. "
        "After the tool returns results, reply in warm, concise natural language with a "
        "summary of the matching sailings — include the voyage ID, ship, number of "
        "nights, and sail date for each. "
        "Do NOT quote specific prices, fares, or dollar amounts. Cruise pricing changes "
        "until a deposit is placed, so instead let the guest know their dedicated "
        "Horizon Voyages advisor will provide current, personalized pricing — and warmly "
        "invite them to share their name and email (or say 'book') so we can follow up "
        "with a tailored quote. "
        "If there are no matches, say so politely and invite them to adjust their criteria."
    ))
    
    # We invoke the tool-bound LLM
    response = await inventory_llm.ainvoke([sys_msg] + state["messages"])
    return {"messages": [response]}

async def tool_execution_node(state: AgentState):
    """
    Executes the tool call returned by the Inventory agent.
    """
    messages = state["messages"]
    last_msg = messages[-1]
    
    tool_messages = []
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        for tool_call in last_msg.tool_calls:
            if tool_call["name"] == "search_gds_inventory":
                args = tool_call["args"]
                result = search_gds_inventory.invoke(args)
                # Use a proper ToolMessage incl. the tool name; Gemini requires the
                # function name on the response to correlate it with the call,
                # otherwise the follow-up model turn comes back empty.
                tool_messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"],
                    name=tool_call["name"],
                ))
    
    return {"messages": tool_messages}

from app.graph.tools import search_gds_inventory, submit_booking_lead, get_cruise_details
from app.notifications import send_booking_lead_email
from app.db import save_booking_lead, mark_lead_emailed

async def booking_node(state: AgentState):
    sys_msg = SystemMessage(content=(
        "You are the secure Booking Agent. Gather the details needed to start a "
        "reservation: the user's full name, email, the cruise ID they want, the "
        "number of passengers, their preferred cruise length (in nights), and "
        "their preferred travel dates or date range. Ask for whichever are still "
        "missing — it's fine to collect them over a few messages, one or two at a "
        "time. Once you have at least the full name, email, and cruise ID, YOU "
        "MUST call the submit_booking_lead tool, passing everything you've "
        "collected (including passengers, cruise length, and travel dates when "
        "known). Do not make up a confirmation number."
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
            cruise_id = args.get("cruise_id", "")
            num_passengers = args.get("num_passengers")
            cruise_length = args.get("cruise_length")
            travel_dates = args.get("travel_dates")
            details = get_cruise_details(cruise_id)

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
            voyage = cruise_id or "your selected voyage"
            if sent:
                final_text = (
                    f"Wonderful, {first_name}! I've sent your reservation details for "
                    f"{voyage} to our travel advisors. They'll be in touch by email at "
                    f"{email} shortly with your secure payment link to confirm. Bon voyage!"
                )
            else:
                final_text = (
                    f"Thank you, {first_name}! Your reservation request for {voyage} is "
                    f"recorded. We hit a snag notifying our team automatically just now, "
                    f"but your details are saved and an advisor will follow up at {email} "
                    f"as soon as possible."
                )
            messages_to_return.append(AIMessage(content=final_text))

    return {"messages": messages_to_return}
