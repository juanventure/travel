from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.graph.state import AgentState
from app.graph.tools import search_gds_inventory
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
    messages = state["messages"]
    latest_msg = messages[-1].content.lower()
    
    if "book" in latest_msg or "reserve" in latest_msg or "pay" in latest_msg:
        next_intent = "Booking"
    elif any(keyword in latest_msg for keyword in ["price", "cost", "alaska", "caribbean", "mediterranean", "find", "search"]):
        next_intent = "Inventory"
    else:
        next_intent = "Consultation"
        
    return {"current_intent": next_intent}

async def consultation_node(state: AgentState):
    sys_msg = SystemMessage(content="You are a luxury cruise consultant for Horizon Voyages. Provide polite, highly professional, and concierge-level general advice about cruising. Do not search for specific inventory, just answer questions or ask where they want to go.")
    response = await llm.ainvoke([sys_msg] + state["messages"])
    return {"messages": [response]}

async def inventory_node(state: AgentState):
    sys_msg = SystemMessage(content="You are the Inventory Agent. You search the GDS database using the search_gds_inventory tool to find available cruises. Always use the tool if the user asks for options.")
    
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
                tool_messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call["id"]
                })
    
    return {"messages": tool_messages}

async def booking_node(state: AgentState):
    sys_msg = SystemMessage(content="You are the secure Booking Agent. Ask the user for their full name and email to proceed with the reservation of their selected cruise. If you have that, tell them the booking is ready to be executed.")
    response = await llm.ainvoke([sys_msg] + state["messages"])
    return {"messages": [response]}
