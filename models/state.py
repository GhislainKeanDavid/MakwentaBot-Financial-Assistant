from typing import TypedDict, List, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel
# Import the new Budget model
from .budget import Budget

# Pydantic model for a Transaction (Used by LLM for structured tool calling)
class Transaction(BaseModel):
    """Schema for a single financial transaction."""
    amount: float
    category: str
    description: str = ""
    
# The core state object passed between nodes in the LangGraph workflow.
class GraphState(TypedDict):
    """Represents the state of the financial assistant agent."""
    
    # Unique identifier for the conversation (Telegram chat_id)
    thread_id: str 
    
    # The history of messages. The 'add_messages' function ensures new messages are appended, not overwritten.
    messages: Annotated[List[BaseMessage], add_messages]
    
    # List of tool calls requested by the LLM (for the ReAct loop)
    tool_calls: List[dict]
    
    # Observation result from the executed tool
    tool_observation: str
    
    # Intent for conditional routing (e.g., 'record_expense', 'report_spending', 'answer_chat')
    intent: str

    # **NEW:** The budget configuration for the user.
    budget: Budget