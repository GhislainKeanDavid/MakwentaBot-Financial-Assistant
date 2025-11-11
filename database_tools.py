import datetime
import random # Used for simulation/placeholders
from langchain.tools import tool
from models.state import Transaction
from models.budget import Budget
from typing import List

# --- SIMULATED PERSISTENCE ---
# IMPORTANT: In a real "Anywhere, Anytime" deployment, this dictionary 
# will be replaced by a connection to a HOSTED DATABASE (PostgreSQL, Supabase).
FINANCIAL_DATA = {} 

def _get_current_spending(user_id: str, category: str, period: str) -> float:
    """Helper function to simulate querying current spending from a database."""
    # In a real database, this would execute a complex SELECT SUM() query 
    # filtered by user_id, category, and date range (daily/weekly).
    
    # Placeholder Logic:
    if period == "day":
        # Simulates different spending for demonstration
        return random.choice([25.0, 50.0, 75.0]) 
    if period == "week":
        return random.choice([500.0, 750.0, 900.0])
    return 0.0

# --- FINANCIAL AGENT TOOLS ---

@tool
def record_transaction(
    amount: float,
    category: str,
    user_id: str,
    description: str = ""
) -> str:
    """Records a new financial transaction (expense or income) to the database."""
    if user_id not in FINANCIAL_DATA:
        FINANCIAL_DATA[user_id] = []
    
    if amount <= 0:
        return "Error: Amount must be positive. Please specify a valid expense."
    
    # 1. Simulate saving the transaction
    FINANCIAL_DATA[user_id].append(
        {"date": datetime.date.today().isoformat(), "amount": amount, "category": category, "description": description}
    )
    
    # 2. Tell the agent to proceed to budget check or confirmation
    return f"Transaction of ${amount} recorded successfully. Ready for budget check."

@tool
def check_budget(
    amount: float, 
    category: str, 
    user_id: str,
    current_budget: Budget # Passed from the GraphState
) -> str:
    """Checks the daily and weekly budget limits against a pending expense for a category."""
    
    # Get limits from the Budget model
    daily_limit = current_budget.daily_limits.get(category, float('inf')) 
    weekly_limit = current_budget.weekly_limits.get(category, float('inf')) 

    # Get current spending using the placeholder function
    current_day_spending = _get_current_spending(user_id, category, "day")
    current_week_spending = _get_current_spending(user_id, category, "week")

    is_daily_over = (current_day_spending + amount) > daily_limit
    is_weekly_over = (current_week_spending + amount) > weekly_limit
    
    if is_daily_over or is_weekly_over:
        details = ""
        if is_daily_over:
            details += f"Daily limit of ${daily_limit:,.2f} will be exceeded (Current: ${current_day_spending:,.2f}). "
        if is_weekly_over:
            details += f"Weekly limit of ${weekly_limit:,.2f} will be exceeded (Current: ${current_week_spending:,.2f}). "
            
        return f"BUDGET WARNING! The expense would cause an overspend. {details} Please confirm if you wish to proceed."
    
    return "BUDGET SUCCESS: Transaction is within both daily and weekly budget limits. Proceed with confirmation."

@tool
def get_daily_summary(user_id: str, current_budget: Budget) -> str:
    """Generates a formatted daily budget and spending summary for a proactive notification."""
    today = datetime.date.today().strftime("%m/%d/%Y")
    currency = current_budget.currency_symbol
    name = current_budget.user_name

    # Example placeholders for total spending and budget
    total_week_expense = _get_current_spending(user_id, "All", "week")
    weekly_budget = current_budget.weekly_limits.get("All", 2000.00) 
    
    summary = f"Hello {name}!\n📅 {today}\n\n"
    summary += "--- WEEKLY FINANCIAL STATUS ---\n"
    summary += f"Weekly Budget: **{currency}{weekly_budget:,.2f}**\n"
    summary += f"Spent This Week: **{currency}{total_week_expense:,.2f}**\n"
    summary += f"Remaining: **{currency}{(weekly_budget - total_week_expense):,.2f}**\n\n"
    summary += "You are on track!" # In a real agent, this would be a detailed analysis.

    return summary

# List of tools to be used by the LangGraph agent
FINANCIAL_TOOLS = [record_transaction, check_budget, get_daily_summary]