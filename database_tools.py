from datetime import datetime
from models.state import Transaction
from typing import List
from typing import Optional
from langchain_core.tools import tool 
from models.budget import Budget
from db_manager import record_transaction_db, get_spending_sum_db, get_expenses_by_date_db, get_weekly_breakdown_db, upsert_budget_db, get_budget_db, create_goal_db, get_goals_db


# --- FINANCIAL AGENT TOOLS ---

@tool
def record_transaction(
    amount: float,
    category: str,
    user_id: str,
    description: Optional[str] = None,
    expense_date: Optional[str] = None
) -> str:
    """Records a new financial transaction (expense or income) to the database."""
    if amount <= 0:
        return "Error: Amount must be positive. Please specify a valid expense."
    
    # NEW LOGIC: Call the database manager
    success = record_transaction_db(user_id, amount, category, description, expense_date)

    if success:
        # Tell the agent what to do next
        return f"Transaction of ${amount} recorded successfully. You MUST now use the check_budget tool."
    else:
        return "ERROR: Failed to record transaction due to a database error."

@tool
def check_budget(user_id: str) -> str:
    """Checks current spending against the user's defined database budget."""
    
    # 1. Get Limits from DB
    limits = get_budget_db(user_id)
    if not limits:
        return "You haven't set a budget yet. Please tell me your daily, weekly, or monthly budget."
    
    # 2. Get Spending from DB (Existing logic re-used)
    daily_spend = get_spending_sum_db(user_id, "daily")
    weekly_spend = get_spending_sum_db(user_id, "weekly")
    
    # 3. Compare
    status = "📊 **Budget Status:**\n"
    
    # Daily Check
    status += f"Daily: ₱{daily_spend:,.2f} / ₱{limits['daily']:,.2f} "
    if daily_spend > limits['daily']:
        status += "⚠️ (OVER)\n"
    else:
        status += "✅\n"
        
    # Weekly Check
    status += f"Weekly: ₱{weekly_spend:,.2f} / ₱{limits['weekly']:,.2f} "
    if weekly_spend > limits['weekly']:
        status += "⚠️ (OVER)\n"
    else:
        status += "✅"
        
    return status

@tool
def get_daily_summary(user_id: str, current_budget: Budget) -> str:
    """Generates a formatted daily budget and spending summary for a proactive notification."""
    # ... (code to get name and currency remains the same)
    
    # NEW LOGIC: Get real total weekly expense from the database
    total_week_expense = get_spending_sum_db(user_id, "week", "All")
    weekly_budget = current_budget.weekly_limits.get("All", 2000.00) 
    
    # ... (rest of summary formatting remains the same)
    # The return summary will now use real data.
    
    summary = f"Hello {name}!\n📅 {today}\n\n"
    summary += "--- WEEKLY FINANCIAL STATUS ---\n"
    summary += f"Weekly Budget: **{currency}{weekly_budget:,.2f}**\n"
    summary += f"Spent This Week: **{currency}{total_week_expense:,.2f}**\n"
    summary += f"Remaining: **{currency}{(weekly_budget - total_week_expense):,.2f}**\n"

    return summary

@tool
def get_expenses_by_date(
    user_id: str,
    date: str
) -> str:
    """
    Retrieves a list of expenses for a specific date.
    The date parameter MUST be in 'YYYY-MM-DD' format.
    """
    return get_expenses_by_date_db(user_id, date)

@tool
def get_weekly_breakdown(
    user_id: str,
    week_start_date: str
) -> str:
    """
    Retrieves a day-by-day breakdown of expenses for a full week (Monday-Sunday).
    Shows total spent each day with indicators for days that exceeded the daily budget.

    'week_start_date': The Monday of the week to analyze, in 'YYYY-MM-DD' format.
                       You must calculate the correct Monday based on today's date.
    """
    return get_weekly_breakdown_db(user_id, week_start_date)

@tool
def set_my_budget(
    user_id: str,
    amount: float,
    period: str
) -> str:
    """
    Sets the user's financial budget.
    'amount': The numeric value of the budget.
    'period': MUST be one of 'daily', 'weekly', or 'monthly'.
    """
    period = period.lower()
    daily = 0.0
    weekly = 0.0
    monthly = 0.0
    
    # Automatic Calculation Logic
    if period == 'daily':
        daily = amount
        weekly = amount * 7
        monthly = amount * 30
    elif period == 'weekly':
        weekly = amount
        daily = amount / 7
        monthly = amount * 4.3  # Approx weeks in a month
    elif period == 'monthly':
        monthly = amount
        daily = amount / 30
        weekly = amount / 4.3
    else:
        return "Error: Period must be 'daily', 'weekly', or 'monthly'."

    # Save to Database
    success = upsert_budget_db(user_id, daily, weekly, monthly)
    
    if success:
        return (f"Budget set successfully!\n"
                f"Daily: ₱{daily:,.2f}\n"
                f"Weekly: ₱{weekly:,.2f}\n"
                f"Monthly: ₱{monthly:,.2f}")
    else:
        return "Failed to save budget to database."

@tool
def set_financial_goal(
    user_id: str,
    goal_name: str,
    target_amount: float,
    deadline_date: str
) -> str:
    """
    Sets a financial savings goal.
    'goal_name': What the user is saving for (e.g., 'Laptop').
    'target_amount': The total cost.
    'deadline_date': When they need it by (YYYY-MM-DD).
    """

    print(f"DEBUG: Starting set_financial_goal for {goal_name}")

    try:
        # --- FIX 1: Force inputs to correct types ---
        target_amount = float(target_amount) 
        deadline_dt = datetime.strptime(deadline_date, "%Y-%m-%d")
        
        today = datetime.now()
        days_remaining = (deadline_dt - today).days
        
        if days_remaining <= 0:
            return "Error: The deadline must be in the future."
            
        daily_save = target_amount / days_remaining
        weekly_save = daily_save * 7
        monthly_save = daily_save * 30
        
        breakdown = (
            f"To reach ₱{target_amount:,.2f} by {deadline_date}:\n"
            f"• Daily: ₱{daily_save:,.2f}\n"
            f"• Weekly: ₱{weekly_save:,.2f}\n"
            f"• Monthly: ₱{monthly_save:,.2f}"
        )
        
    except Exception as e:
        # --- FIX 2: Catch ANY error and print it ---
        error_msg = f"DEBUG: Crash during calculation: {str(e)}"
        print(error_msg)
        return f"Error calculating goal details: {str(e)}"

    # 2. Database Call
    print("DEBUG: Calling Database...") 
    result = create_goal_db(user_id, goal_name, target_amount, deadline_date)
    print(f"DEBUG: Database returned type: {type(result)} and value: {result}")
    
    # Check if result is a tuple (New version) or just a bool (Old version)
    if isinstance(result, tuple):
        success, message = result
    else:
        success = result
        message = "Goal saved (details unavailable)."

    # 3. Return Success Message
    if success:
        return f"✅ Goal '{goal_name}' set successfully!\n\n{breakdown}"
    else:
        return f"Failed to save goal. Database message: {message}"

# 3. Define the CHECK GOALS tool
@tool
def check_goals(user_id: str) -> str:
    """Retrieves the status of all current savings goals."""
    return get_goals_db(user_id)

# ===== RECURRING EXPENSE TOOLS =====

@tool
def add_recurring_expense(
    user_id: str,
    amount: float,
    category: str,
    frequency: str,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Creates a new recurring expense that will automatically record transactions.

    'amount': The transaction amount for each occurrence.
    'category': Expense category (e.g., 'Rent', 'Subscription').
    'frequency': Must be 'daily', 'weekly', 'biweekly', 'monthly', or 'yearly'.
    'description': Optional details about the recurring expense.
    'start_date': When to start (YYYY-MM-DD). Defaults to today.
    'end_date': When to stop (YYYY-MM-DD). Leave empty for indefinite.
    """
    from db_manager import create_recurring_expense_db

    # Validation
    valid_frequencies = ['daily', 'weekly', 'biweekly', 'monthly', 'yearly']
    if frequency.lower() not in valid_frequencies:
        return f"Error: Frequency must be one of {valid_frequencies}."

    if amount <= 0:
        return "Error: Amount must be positive."

    # Call database
    success, message = create_recurring_expense_db(
        user_id, amount, category, frequency.lower(),
        description, start_date, end_date
    )

    if success:
        return (f"✅ Recurring expense created: {category} - ₱{amount:,.2f} ({frequency})\n"
                f"{message}\n"
                f"This will be automatically recorded when due.")
    else:
        return f"❌ Failed to create recurring expense: {message}"

@tool
def view_recurring_expenses(
    user_id: str,
    include_paused: bool = False
) -> str:
    """
    Lists all recurring expenses for the user.

    'include_paused': Set to True to include paused/inactive recurring expenses.
    """
    from db_manager import get_recurring_expenses_db

    active_only = not include_paused
    return get_recurring_expenses_db(user_id, active_only)

@tool
def edit_recurring_expense(
    user_id: str,
    recurring_id: int,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    frequency: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Modifies an existing recurring expense.

    'recurring_id': The ID number of the recurring expense to edit (from view_recurring_expenses).
    'amount': New amount (optional).
    'category': New category (optional).
    'description': New description (optional).
    'frequency': New frequency - 'daily', 'weekly', 'biweekly', 'monthly', 'yearly' (optional).
    'end_date': New end date in YYYY-MM-DD format (optional).
    """
    from db_manager import update_recurring_expense_db

    if frequency and frequency.lower() not in ['daily', 'weekly', 'biweekly', 'monthly', 'yearly']:
        return "Error: Invalid frequency value."

    success, message = update_recurring_expense_db(
        user_id, recurring_id, amount, category, description,
        frequency.lower() if frequency else None, end_date
    )

    if success:
        return f"✅ {message}"
    else:
        return f"❌ {message}"

@tool
def pause_recurring_expense(
    user_id: str,
    recurring_id: int
) -> str:
    """
    Pauses a recurring expense (stops auto-recording without deleting).

    'recurring_id': The ID number of the recurring expense to pause.
    """
    from db_manager import toggle_recurring_expense_db

    success, message = toggle_recurring_expense_db(user_id, recurring_id, False)

    if success:
        return f"⏸️ {message} It will no longer auto-record transactions."
    else:
        return f"❌ {message}"

@tool
def resume_recurring_expense(
    user_id: str,
    recurring_id: int
) -> str:
    """
    Resumes a paused recurring expense (re-enables auto-recording).

    'recurring_id': The ID number of the recurring expense to resume.
    """
    from db_manager import toggle_recurring_expense_db

    success, message = toggle_recurring_expense_db(user_id, recurring_id, True)

    if success:
        return f"▶️ {message} It will resume auto-recording transactions."
    else:
        return f"❌ {message}"

@tool
def delete_recurring_expense(
    user_id: str,
    recurring_id: int
) -> str:
    """
    Permanently deletes a recurring expense.

    'recurring_id': The ID number of the recurring expense to delete.
    WARNING: This action cannot be undone. Consider using pause_recurring_expense instead.
    """
    from db_manager import delete_recurring_expense_db

    success, message = delete_recurring_expense_db(user_id, recurring_id)

    if success:
        return f"🗑️ {message}"
    else:
        return f"❌ {message}"

@tool
def forecast_recurring_expenses(
    user_id: str,
    days: int = 30
) -> str:
    """
    Shows predicted recurring expenses for upcoming days (for budget planning).

    'days': Number of days to forecast (default: 30).
    """
    from db_manager import forecast_recurring_expenses_db

    if days < 1 or days > 365:
        return "Error: Days must be between 1 and 365."

    return forecast_recurring_expenses_db(user_id, days)

# List of tools to be used by the LangGraph agent
FINANCIAL_TOOLS = [
    record_transaction, check_budget, get_daily_summary, get_expenses_by_date,
    get_weekly_breakdown, set_my_budget, set_financial_goal, check_goals,
    # Recurring expense tools
    add_recurring_expense, view_recurring_expenses, edit_recurring_expense,
    pause_recurring_expense, resume_recurring_expense, delete_recurring_expense,
    forecast_recurring_expenses
]