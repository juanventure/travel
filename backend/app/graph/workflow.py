from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.agents import router_node, consultation_node, inventory_node, tool_execution_node, booking_node

def should_execute_tool(state: AgentState):
    """Determines if the Inventory agent returned a tool call."""
    messages = state["messages"]
    last_msg = messages[-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "execute_tools"
    return "end"

def router_edge(state: AgentState):
    """Routes based on the router_node's decision."""
    intent = state.get("current_intent", "Consultation")
    if intent == "Inventory":
        return "inventory"
    elif intent == "Booking":
        return "booking"
    return "consultation"

# Build Graph
builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("router", router_node)
builder.add_node("consultation", consultation_node)
builder.add_node("inventory", inventory_node)
builder.add_node("tools", tool_execution_node)
builder.add_node("booking", booking_node)

# Add Edges
builder.set_entry_point("router")
builder.add_conditional_edges("router", router_edge, {
    "inventory": "inventory",
    "consultation": "consultation",
    "booking": "booking"
})

builder.add_conditional_edges("inventory", should_execute_tool, {
    "execute_tools": "tools",
    "end": END
})

# After tool execution, route back to inventory agent to interpret results
builder.add_edge("tools", "inventory")

builder.add_edge("consultation", END)
builder.add_edge("booking", END)

from langgraph.checkpoint.memory import MemorySaver

# Compile Graph
memory = MemorySaver()
multi_agent_graph = builder.compile(checkpointer=memory)
