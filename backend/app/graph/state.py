from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    State representing the context of the Multi-Agent conversation.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_intent: str
    booking_context: dict
