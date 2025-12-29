import os
import psycopg2
from dotenv import load_dotenv
from typing import Optional, Dict

load_dotenv()

# Get connection string from .env
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Establishes and returns a database connection using the environment variable."""
    if not DATABASE_URL:
        raise ConnectionError("DATABASE_URL not set in environment variables.")
    
    # We use the connection string obtained from Supabase (PostgreSQL)
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def record_transaction_db(user_id: str, amount: float, category: str, description: Optional[str] = None, expense_date: Optional[str] = None) -> bool:
    """Inserts a new transaction record into the database. Supports both Telegram (user_id) and web (web_user_id) users."""
    try:
        from datetime import date

        # Default to today if no expense_date provided
        if expense_date is None:
            expense_date = date.today().isoformat()

        conn = get_db_connection()
        cur = conn.cursor()

        # Determine if this is a web user (numeric) or Telegram user (text)
        try:
            web_user_id_val = int(user_id)
            # Numeric user_id -> web user
            sql = """
                INSERT INTO transactions (web_user_id, amount, category, description, expense_date)
                VALUES (%s, %s, %s, %s, %s);
            """
            cur.execute(sql, (web_user_id_val, amount, category, description, expense_date))
        except ValueError:
            # Text user_id -> Telegram user
            sql = """
                INSERT INTO transactions (user_id, amount, category, description, expense_date)
                VALUES (%s, %s, %s, %s, %s);
            """
            cur.execute(sql, (user_id, amount, category, description, expense_date))

        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Database Error on insert: {e}")
        return False

def get_spending_sum_db(user_id: str, period: str, category: Optional[str] = None) -> float:
    """Queries the database to get the sum of spending for a given period."""
    try:
        from datetime import datetime, timedelta

        conn = get_db_connection()
        cur = conn.cursor()

        # Define time filters based on the required period
        time_filter = ""
        if period == "day":
            time_filter = "AND expense_date = CURRENT_DATE"
        elif period == "week":
            # Calculate Monday of current week (same logic as get_weekly_breakdown_db)
            today = datetime.now()
            days_since_monday = today.weekday()  # 0 = Monday, 6 = Sunday
            monday = today - timedelta(days=days_since_monday)
            monday_str = monday.strftime("%Y-%m-%d")
            time_filter = f"AND expense_date >= '{monday_str}'"
        elif period == "daily":
            # Alias for "day"
            time_filter = "AND expense_date = CURRENT_DATE"
        elif period == "weekly":
            # Alias for "week"
            today = datetime.now()
            days_since_monday = today.weekday()
            monday = today - timedelta(days=days_since_monday)
            monday_str = monday.strftime("%Y-%m-%d")
            time_filter = f"AND expense_date >= '{monday_str}'"

        # Build parameterized query to prevent SQL injection
        # Support both Telegram users (user_id) and web users (web_user_id)
        try:
            web_user_id_val = int(user_id)
            user_filter = "web_user_id = %s"
            params = [web_user_id_val]
        except ValueError:
            user_filter = "user_id = %s"
            params = [user_id]

        category_filter = ""
        # Only apply category filter if a specific category is requested
        if category and category.lower() != 'all':
            category_filter = "AND category ILIKE %s"
            params.append(category)

        # SQL query to sum the amounts (using expense_date, not transaction_date)
        sql = f"""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE {user_filter} {category_filter} {time_filter};
        """
        cur.execute(sql, tuple(params))

        total_sum = cur.fetchone()[0]

        cur.close()
        conn.close()
        return float(total_sum)
    except Exception as e:
        print(f"Database Error on query: {e}")
        return 0.0


def get_expenses_by_date_db(user_id: str, query_date: str) -> str:
    """Retrieves expenses for a specific date from the database. Supports both Telegram and web users."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Support both Telegram users (user_id) and web users (web_user_id)
        try:
            web_user_id_val = int(user_id)
            sql = """
                SELECT category, amount, description
                FROM transactions
                WHERE web_user_id = %s AND expense_date = %s
                ORDER BY record_date ASC;
            """
            cur.execute(sql, (web_user_id_val, query_date))
        except ValueError:
            sql = """
                SELECT category, amount, description
                FROM transactions
                WHERE user_id = %s AND expense_date = %s
                ORDER BY record_date ASC;
            """
            cur.execute(sql, (user_id, query_date))

        rows = cur.fetchall()
        
        cur.close()
        conn.close()

        if not rows:
            return f"No expenses found for {query_date}."

        # Format the output into a readable string for the LLM
        report = f"Expenses for {query_date}:\n"
        total = 0.0
        for row in rows:
            category, amount, description = row
            desc_str = f" ({description})" if description else ""
            report += f"- {category}: ₱{float(amount):,.2f}{desc_str}\n"
            total += float(amount)
        
        report += f"\nTotal: ₱{total:,.2f}"
        return report

    except Exception as e:
        print(f"Database Error on query: {e}")
        return f"Error retrieving data: {str(e)}"


def get_weekly_breakdown_db(user_id: str, week_start_date: str) -> str:
    """
    Retrieves daily expense totals for a full week (Mon-Sun) starting from week_start_date.
    week_start_date should be a Monday in YYYY-MM-DD format. Supports both Telegram and web users.
    """
    try:
        from datetime import datetime, timedelta

        conn = get_db_connection()
        cur = conn.cursor()

        # Parse the start date
        start = datetime.strptime(week_start_date, "%Y-%m-%d")

        # Determine if this is a web user or Telegram user
        try:
            web_user_id_val = int(user_id)
            is_web_user = True
        except ValueError:
            is_web_user = False

        # Get user's daily budget limit for comparison
        if is_web_user:
            budget_sql = "SELECT daily_limit FROM budgets WHERE web_user_id = %s;"
            cur.execute(budget_sql, (web_user_id_val,))
        else:
            budget_sql = "SELECT daily_limit FROM budgets WHERE user_id = %s;"
            cur.execute(budget_sql, (user_id,))

        budget_row = cur.fetchone()
        daily_limit = float(budget_row[0]) if budget_row else 0.0

        # Build report for all 7 days
        report = f"📊 **Weekly Breakdown** ({week_start_date} to {(start + timedelta(days=6)).strftime('%Y-%m-%d')})\n\n"
        week_total = 0.0

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for i in range(7):
            current_date = start + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            day_name = day_names[i]

            # Query expenses for this specific day
            if is_web_user:
                sql = """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions
                    WHERE web_user_id = %s AND expense_date = %s;
                """
                cur.execute(sql, (web_user_id_val, date_str))
            else:
                sql = """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions
                    WHERE user_id = %s AND expense_date = %s;
                """
                cur.execute(sql, (user_id, date_str))

            day_total = float(cur.fetchone()[0])
            week_total += day_total

            # Format the line
            if day_total == 0:
                report += f"{day_name} ({date_str}): ₱0.00\n"
            else:
                over_indicator = " ⚠️ OVER" if daily_limit > 0 and day_total > daily_limit else ""
                report += f"{day_name} ({date_str}): ₱{day_total:,.2f}{over_indicator}\n"

        report += f"\n**Week Total:** ₱{week_total:,.2f}"

        cur.close()
        conn.close()
        return report

    except Exception as e:
        print(f"Database Error on weekly breakdown: {e}")
        return f"Error retrieving weekly breakdown: {str(e)}"


def upsert_budget_db(user_id: str, daily: float, weekly: float, monthly: float) -> bool:
    """Updates the budget limits for a user. Supports both Telegram and web users."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Determine if this is a web user or Telegram user
        try:
            web_user_id_val = int(user_id)
            # Web user - use web_user_id column
            sql = """
                INSERT INTO budgets (web_user_id, daily_limit, weekly_limit, monthly_limit, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (web_user_id)
                DO UPDATE SET
                    daily_limit = EXCLUDED.daily_limit,
                    weekly_limit = EXCLUDED.weekly_limit,
                    monthly_limit = EXCLUDED.monthly_limit,
                    updated_at = NOW();
            """
            cur.execute(sql, (web_user_id_val, daily, weekly, monthly))
        except ValueError:
            # Telegram user - use user_id column
            sql = """
                INSERT INTO budgets (user_id, daily_limit, weekly_limit, monthly_limit, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET
                    daily_limit = EXCLUDED.daily_limit,
                    weekly_limit = EXCLUDED.weekly_limit,
                    monthly_limit = EXCLUDED.monthly_limit,
                    updated_at = NOW();
            """
            cur.execute(sql, (user_id, daily, weekly, monthly))

        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Database Error on upsert_budget: {e}")
        return False

def get_budget_db(user_id: str):
    """Retrieves the current budget limits for a user. Supports both Telegram and web users."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Support both Telegram users (user_id) and web users (web_user_id)
        try:
            web_user_id_val = int(user_id)
            cur.execute("SELECT daily_limit, weekly_limit, monthly_limit FROM budgets WHERE web_user_id = %s", (web_user_id_val,))
        except ValueError:
            cur.execute("SELECT daily_limit, weekly_limit, monthly_limit FROM budgets WHERE user_id = %s", (user_id,))

        row = cur.fetchone()

        cur.close()
        conn.close()

        if row:
            return {"daily": float(row[0]), "weekly": float(row[1]), "monthly": float(row[2])}
        return None
    except Exception as e:
        print(f"Database Error on get_budget: {e}")
        return None

def create_goal_db(user_id: str, name: str, target: float, deadline: str) -> tuple[bool, str]:
    """Creates a new financial goal. Returns (Success, Message). Supports both Telegram and web users."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Determine if this is a web user or Telegram user
        try:
            web_user_id_val = int(user_id)
            sql = """
                INSERT INTO goals (web_user_id, goal_name, target_amount, deadline)
                VALUES (%s, %s, %s, %s);
            """
            cur.execute(sql, (web_user_id_val, name, target, deadline))
        except ValueError:
            sql = """
                INSERT INTO goals (user_id, goal_name, target_amount, deadline)
                VALUES (%s, %s, %s, %s);
            """
            cur.execute(sql, (user_id, name, target, deadline))

        conn.commit()
        cur.close()
        conn.close()
        return True, "Goal created successfully."
    except Exception as e:
        error_msg = f"Database Error: {str(e)}"
        print(error_msg) # This prints to Cloud Run logs
        return False, error_msg # Return the specific error

def get_goals_db(user_id: str) -> str:
    """Retrieves all active goals for a user. Supports both Telegram and web users."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Support both Telegram users (user_id) and web users (web_user_id)
        try:
            web_user_id_val = int(user_id)
            sql = "SELECT goal_name, target_amount, current_amount, deadline FROM goals WHERE web_user_id = %s;"
            cur.execute(sql, (web_user_id_val,))
        except ValueError:
            sql = "SELECT goal_name, target_amount, current_amount, deadline FROM goals WHERE user_id = %s;"
            cur.execute(sql, (user_id,))

        rows = cur.fetchall()

        cur.close()
        conn.close()

        if not rows:
            return "You have no active savings goals."

        report = "🎯 **Your Financial Goals:**\n"
        for row in rows:
            name, target, current, deadline = row
            target = float(target)
            current = float(current)

            # Progress calculation
            progress = (current / target) * 100 if target > 0 else 0

            report += f"\n📌 **{name}**\n"
            report += f"   Target: ₱{target:,.2f}\n"
            report += f"   Saved: ₱{current:,.2f} ({progress:.1f}%)\n"
            report += f"   Deadline: {deadline}\n"

        return report

    except Exception as e:
        print(f"Database Error on get_goals: {e}")
        return "Error retrieving goals."

# ===== RECURRING EXPENSES FUNCTIONS =====

def create_recurring_expense_db(
    user_id: str,
    amount: float,
    category: str,
    frequency: str,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> tuple[bool, str]:
    """
    Creates a new recurring expense entry.
    Returns (Success, Message/Error).
    """
    try:
        from datetime import datetime, timedelta
        import calendar

        conn = get_db_connection()
        cur = conn.cursor()

        # Determine start_date
        if not start_date:
            start_dt = datetime.now().date()
        else:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()

        # Calculate next_occurrence (first future occurrence)
        today = datetime.now().date()
        next_occ = start_dt

        # If start_date is in the past, calculate the next future occurrence
        while next_occ < today:
            if frequency == 'daily':
                next_occ += timedelta(days=1)
            elif frequency == 'weekly':
                next_occ += timedelta(weeks=1)
            elif frequency == 'biweekly':
                next_occ += timedelta(weeks=2)
            elif frequency == 'monthly':
                # Handle month-end edge cases
                month = next_occ.month + 1
                year = next_occ.year
                if month > 12:
                    month = 1
                    year += 1
                try:
                    next_occ = next_occ.replace(year=year, month=month)
                except ValueError:
                    # Day doesn't exist in new month (e.g., Jan 31 -> Feb 31)
                    last_day = calendar.monthrange(year, month)[1]
                    next_occ = next_occ.replace(year=year, month=month, day=last_day)
            elif frequency == 'yearly':
                try:
                    next_occ = next_occ.replace(year=next_occ.year + 1)
                except ValueError:
                    # Handle leap year edge case (Feb 29)
                    next_occ = next_occ.replace(year=next_occ.year + 1, day=28)

        # Insert into database - support both Telegram and web users
        try:
            web_user_id_val = int(user_id)
            sql = """
                INSERT INTO recurring_expenses
                (web_user_id, amount, category, description, frequency, start_date, end_date, next_occurrence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING recurring_id;
            """
            params = (web_user_id_val, amount, category, description, frequency,
                      start_dt.strftime("%Y-%m-%d"), end_date, next_occ.strftime("%Y-%m-%d"))
        except ValueError:
            sql = """
                INSERT INTO recurring_expenses
                (user_id, amount, category, description, frequency, start_date, end_date, next_occurrence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING recurring_id;
            """
            params = (user_id, amount, category, description, frequency,
                      start_dt.strftime("%Y-%m-%d"), end_date, next_occ.strftime("%Y-%m-%d"))

        cur.execute(sql, params)
        recurring_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        # Provide feedback about next occurrence
        if next_occ > start_dt:
            return True, f"Recurring expense created with ID {recurring_id}. Next occurrence: {next_occ}."
        else:
            return True, f"Recurring expense created with ID {recurring_id}."

    except Exception as e:
        error_msg = f"Database Error: {str(e)}"
        print(error_msg)
        return False, error_msg

def get_recurring_expenses_db(user_id: str, active_only: bool = True) -> str:
    """
    Retrieves all recurring expenses for a user.
    Returns formatted string for LLM.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        active_filter = "AND is_active = TRUE" if active_only else ""

        sql = f"""
            SELECT recurring_id, category, amount, description, frequency,
                   next_occurrence, end_date, is_active
            FROM recurring_expenses
            WHERE user_id = %s {active_filter}
            ORDER BY next_occurrence ASC;
        """
        cur.execute(sql, (user_id,))
        rows = cur.fetchall()

        cur.close()
        conn.close()

        if not rows:
            return "You have no recurring expenses set up."

        report = "📅 **Your Recurring Expenses:**\n\n"
        for row in rows:
            rec_id, cat, amt, desc, freq, next_occ, end_dt, active = row
            status = "✅ Active" if active else "⏸️ Paused"
            end_info = f" (until {end_dt})" if end_dt else " (indefinite)"
            desc_str = f" - {desc}" if desc else ""

            report += f"**#{rec_id}** {cat}: ₱{float(amt):,.2f}{desc_str}\n"
            report += f"   {freq.title()}{end_info} | Next: {next_occ} | {status}\n\n"

        return report

    except Exception as e:
        print(f"Database Error on get_recurring_expenses: {e}")
        return f"Error retrieving recurring expenses: {str(e)}"

def update_recurring_expense_db(
    user_id: str,
    recurring_id: int,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    frequency: Optional[str] = None,
    end_date: Optional[str] = None
) -> tuple[bool, str]:
    """
    Updates an existing recurring expense.
    Only updates provided fields (partial update).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Build dynamic UPDATE query
        update_fields = []
        params = []

        if amount is not None:
            update_fields.append("amount = %s")
            params.append(amount)
        if category is not None:
            update_fields.append("category = %s")
            params.append(category)
        if description is not None:
            update_fields.append("description = %s")
            params.append(description)
        if frequency is not None:
            update_fields.append("frequency = %s")
            params.append(frequency)
        if end_date is not None:
            update_fields.append("end_date = %s")
            params.append(end_date)

        if not update_fields:
            return False, "No fields to update."

        update_fields.append("updated_at = NOW()")
        params.extend([user_id, recurring_id])

        sql = f"""
            UPDATE recurring_expenses
            SET {', '.join(update_fields)}
            WHERE user_id = %s AND recurring_id = %s
            RETURNING recurring_id;
        """

        cur.execute(sql, params)
        result = cur.fetchone()

        if not result:
            conn.rollback()
            cur.close()
            conn.close()
            return False, f"Recurring expense #{recurring_id} not found or access denied."

        conn.commit()
        cur.close()
        conn.close()
        return True, f"Recurring expense #{recurring_id} updated successfully."

    except Exception as e:
        error_msg = f"Database Error: {str(e)}"
        print(error_msg)
        return False, error_msg

def toggle_recurring_expense_db(
    user_id: str,
    recurring_id: int,
    set_active: bool
) -> tuple[bool, str]:
    """
    Pauses or resumes a recurring expense by setting is_active flag.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = """
            UPDATE recurring_expenses
            SET is_active = %s, updated_at = NOW()
            WHERE user_id = %s AND recurring_id = %s
            RETURNING recurring_id;
        """

        cur.execute(sql, (set_active, user_id, recurring_id))
        result = cur.fetchone()

        if not result:
            conn.rollback()
            cur.close()
            conn.close()
            return False, f"Recurring expense #{recurring_id} not found."

        conn.commit()
        cur.close()
        conn.close()

        action = "resumed" if set_active else "paused"
        return True, f"Recurring expense #{recurring_id} {action}."

    except Exception as e:
        error_msg = f"Database Error: {str(e)}"
        print(error_msg)
        return False, error_msg

def delete_recurring_expense_db(user_id: str, recurring_id: int) -> tuple[bool, str]:
    """
    Permanently deletes a recurring expense.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = """
            DELETE FROM recurring_expenses
            WHERE user_id = %s AND recurring_id = %s
            RETURNING recurring_id;
        """

        cur.execute(sql, (user_id, recurring_id))
        result = cur.fetchone()

        if not result:
            conn.rollback()
            cur.close()
            conn.close()
            return False, f"Recurring expense #{recurring_id} not found."

        conn.commit()
        cur.close()
        conn.close()
        return True, f"Recurring expense #{recurring_id} deleted permanently."

    except Exception as e:
        error_msg = f"Database Error: {str(e)}"
        print(error_msg)
        return False, error_msg

def process_due_recurring_expenses_db(user_id: Optional[str] = None) -> tuple[int, str]:
    """
    Auto-processes all recurring expenses that are due.
    Records transactions and updates next_occurrence.

    Args:
        user_id: If provided, only process for this user. If None, process for all users.

    Returns:
        (count, message): Number of expenses processed and summary message.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Find all due recurring expenses
        user_filter = "AND user_id = %s" if user_id else ""
        params = [user_id] if user_id else []

        sql = f"""
            SELECT recurring_id, user_id, amount, category, description,
                   frequency, next_occurrence, end_date
            FROM recurring_expenses
            WHERE is_active = TRUE
              AND next_occurrence <= CURRENT_DATE
              {user_filter}
            ORDER BY next_occurrence ASC;
        """

        cur.execute(sql, params)
        due_expenses = cur.fetchall()

        if not due_expenses:
            cur.close()
            conn.close()
            return 0, "No recurring expenses due for processing."

        processed_count = 0
        errors = []

        for expense in due_expenses:
            rec_id, uid, amount, cat, desc, freq, next_occ, end_dt = expense

            try:
                # 1. Record the transaction (with next_occurrence as expense_date)
                desc_text = f"[Auto] {desc}" if desc else "[Auto-recurring]"
                insert_sql = """
                    INSERT INTO transactions (user_id, amount, category, description, expense_date)
                    VALUES (%s, %s, %s, %s, %s);
                """
                cur.execute(insert_sql, (uid, amount, cat, desc_text, next_occ))

                # 2. Calculate next occurrence using SQL INTERVAL
                frequency_map = {
                    'daily': "next_occurrence + INTERVAL '1 day'",
                    'weekly': "next_occurrence + INTERVAL '1 week'",
                    'biweekly': "next_occurrence + INTERVAL '2 weeks'",
                    'monthly': "next_occurrence + INTERVAL '1 month'",
                    'yearly': "next_occurrence + INTERVAL '1 year'"
                }
                next_occ_calc = frequency_map.get(freq, "next_occurrence + INTERVAL '1 month'")

                # 3. Update recurring_expenses with new next_occurrence
                update_sql = f"""
                    UPDATE recurring_expenses
                    SET next_occurrence = {next_occ_calc},
                        last_processed = CURRENT_DATE,
                        updated_at = NOW()
                    WHERE recurring_id = %s
                    RETURNING next_occurrence;
                """
                cur.execute(update_sql, (rec_id,))
                new_next_occ = cur.fetchone()[0]

                # 4. Check if we've passed end_date, deactivate if so
                if end_dt and new_next_occ > end_dt:
                    deactivate_sql = """
                        UPDATE recurring_expenses
                        SET is_active = FALSE
                        WHERE recurring_id = %s;
                    """
                    cur.execute(deactivate_sql, (rec_id,))

                processed_count += 1

            except Exception as inner_e:
                errors.append(f"#{rec_id}: {str(inner_e)}")
                continue

        conn.commit()
        cur.close()
        conn.close()

        message = f"Processed {processed_count} recurring expense(s)."
        if errors:
            message += f" Errors: {'; '.join(errors)}"

        return processed_count, message

    except Exception as e:
        error_msg = f"Database Error: {str(e)}"
        print(error_msg)
        return 0, error_msg

def forecast_recurring_expenses_db(user_id: str, forecast_days: int = 30) -> str:
    """
    Predicts upcoming recurring expenses for the next N days.
    Used for budget forecasting.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get all active recurring expenses
        sql = """
            SELECT recurring_id, category, amount, description, frequency,
                   next_occurrence, end_date
            FROM recurring_expenses
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY next_occurrence ASC;
        """
        cur.execute(sql, (user_id,))
        recurring = cur.fetchall()

        cur.close()
        conn.close()

        if not recurring:
            return "You have no active recurring expenses to forecast."

        # Python-side calculation of all occurrences within forecast period
        from datetime import datetime, timedelta
        import calendar

        forecast_end = datetime.now().date() + timedelta(days=forecast_days)
        forecast_items = []

        for rec in recurring:
            rec_id, cat, amt, desc, freq, next_occ, end_dt = rec

            # Generate all occurrences for this expense
            current_date = next_occ
            while current_date <= forecast_end:
                # Check if past end_date
                if end_dt and current_date > end_dt:
                    break

                forecast_items.append({
                    'date': current_date,
                    'category': cat,
                    'amount': float(amt),
                    'description': desc or 'Recurring'
                })

                # Calculate next occurrence
                if freq == 'daily':
                    current_date += timedelta(days=1)
                elif freq == 'weekly':
                    current_date += timedelta(weeks=1)
                elif freq == 'biweekly':
                    current_date += timedelta(weeks=2)
                elif freq == 'monthly':
                    # Handle month-end edge cases
                    month = current_date.month + 1
                    year = current_date.year
                    if month > 12:
                        month = 1
                        year += 1
                    try:
                        current_date = current_date.replace(year=year, month=month)
                    except ValueError:
                        # Day doesn't exist in new month (e.g., Jan 31 -> Feb 31)
                        # Fall back to last day of month
                        last_day = calendar.monthrange(year, month)[1]
                        current_date = current_date.replace(year=year, month=month, day=last_day)
                elif freq == 'yearly':
                    try:
                        current_date = current_date.replace(year=current_date.year + 1)
                    except ValueError:
                        # Handle leap year edge case (Feb 29)
                        current_date = current_date.replace(year=current_date.year + 1, day=28)
                else:
                    break  # Unknown frequency

        # Sort by date
        forecast_items.sort(key=lambda x: x['date'])

        # Format output
        report = f"📊 **Recurring Expense Forecast (Next {forecast_days} days):**\n\n"

        if not forecast_items:
            return report + "No recurring expenses scheduled in this period."

        total_forecast = sum(item['amount'] for item in forecast_items)

        for item in forecast_items:
            report += f"• {item['date']} - {item['category']}: ₱{item['amount']:,.2f}"
            if item['description'] != 'Recurring':
                report += f" ({item['description']})"
            report += "\n"

        report += f"\n**Total Forecasted: ₱{total_forecast:,.2f}**"

        return report

    except Exception as e:
        print(f"Database Error on forecast: {e}")
        return f"Error generating forecast: {str(e)}"


# ===== USER AUTHENTICATION FUNCTIONS =====

def create_user(email: str, password_hash: str = None, google_id: str = None) -> Optional[int]:
    """
    Creates a new user account.

    Args:
        email: User's email address (required)
        password_hash: Bcrypt hashed password (for email/password auth)
        google_id: Google OAuth user ID (for Google auth)

    Returns:
        user_id if successful, None otherwise
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = """
            INSERT INTO users (email, password_hash, google_id, created_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING user_id;
        """
        cur.execute(sql, (email, password_hash, google_id))
        user_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()
        return user_id
    except Exception as e:
        print(f"Database Error on create_user: {e}")
        return None


def get_user_by_email(email: str) -> Optional[tuple]:
    """
    Retrieves user by email address.

    Args:
        email: User's email address

    Returns:
        Tuple of (user_id, email, password_hash, google_id) if found, None otherwise
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = "SELECT user_id, email, password_hash, google_id FROM users WHERE email = %s;"
        cur.execute(sql, (email,))
        user = cur.fetchone()

        cur.close()
        conn.close()
        return user
    except Exception as e:
        print(f"Database Error on get_user_by_email: {e}")
        return None


def get_user_by_id(user_id: int) -> Optional[tuple]:
    """
    Retrieves user by user ID.

    Args:
        user_id: User's database ID

    Returns:
        Tuple of (user_id, email) if found, None otherwise
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = "SELECT user_id, email FROM users WHERE user_id = %s;"
        cur.execute(sql, (user_id,))
        user = cur.fetchone()

        cur.close()
        conn.close()
        return user
    except Exception as e:
        print(f"Database Error on get_user_by_id: {e}")
        return None


def update_user_last_login(user_id: int) -> bool:
    """
    Updates the last login timestamp for a user.

    Args:
        user_id: User's database ID

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = "UPDATE users SET last_login = NOW() WHERE user_id = %s;"
        cur.execute(sql, (user_id,))

        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Database Error on update_user_last_login: {e}")
        return False


# ===== CHAT SESSION FUNCTIONS =====

def create_chat_session(user_id: int) -> Optional[str]:
    """
    Creates a new chat session for a user.

    Args:
        user_id: User's database ID

    Returns:
        session_id (UUID string) if successful, None otherwise
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = "INSERT INTO chat_sessions (user_id) VALUES (%s) RETURNING session_id;"
        cur.execute(sql, (user_id,))
        session_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()
        return str(session_id)
    except Exception as e:
        print(f"Database Error on create_chat_session: {e}")
        return None


def get_session_messages(session_id: str, limit: int = 50) -> list:
    """
    Retrieves messages from a chat session.

    Args:
        session_id: UUID of the chat session
        limit: Maximum number of messages to retrieve (default 50)

    Returns:
        List of tuples (role, content, tool_calls) ordered oldest first
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = """
            SELECT role, content, tool_calls
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            LIMIT %s;
        """
        cur.execute(sql, (session_id, limit))
        messages = cur.fetchall()

        cur.close()
        conn.close()
        return messages
    except Exception as e:
        print(f"Database Error on get_session_messages: {e}")
        return []


def save_message(session_id: str, role: str, content: str, tool_calls: dict = None) -> bool:
    """
    Saves a message to a chat session.

    Args:
        session_id: UUID of the chat session
        role: Message role ('human', 'ai', 'tool')
        content: Message content
        tool_calls: Optional JSON data for tool calls

    Returns:
        True if successful, False otherwise
    """
    try:
        import json

        conn = get_db_connection()
        cur = conn.cursor()

        sql = """
            INSERT INTO chat_messages (session_id, role, content, tool_calls)
            VALUES (%s, %s, %s, %s);
        """
        cur.execute(sql, (session_id, role, content, json.dumps(tool_calls) if tool_calls else None))

        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Database Error on save_message: {e}")
        return False


def get_user_sessions(user_id: int, limit: int = 10) -> list:
    """
    Retrieves recent chat sessions for a user.

    Args:
        user_id: User's database ID
        limit: Maximum number of sessions to retrieve (default 10)

    Returns:
        List of tuples (session_id, created_at, updated_at)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = """
            SELECT session_id, created_at, updated_at
            FROM chat_sessions
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT %s;
        """
        cur.execute(sql, (user_id, limit))
        sessions = cur.fetchall()

        cur.close()
        conn.close()
        return sessions
    except Exception as e:
        print(f"Database Error on get_user_sessions: {e}")
        return []


# ===== TELEGRAM MIGRATION FUNCTIONS =====

def migrate_telegram_user_data(telegram_user_id: str, web_user_id: int) -> bool:
    """
    Transfers all data from a Telegram user to a web user account.
    This is used when a Telegram user creates a web account and links them.

    Args:
        telegram_user_id: The Telegram chat_id
        web_user_id: The new web user's ID

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Update all tables to point to the web user
        tables = ['transactions', 'budgets', 'goals', 'recurring_expenses']
        for table in tables:
            sql = f"UPDATE {table} SET web_user_id = %s WHERE user_id = %s;"
            cur.execute(sql, (web_user_id, telegram_user_id))

        # Record the migration
        sql = """
            INSERT INTO telegram_migrations (telegram_user_id, web_user_id, migrated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (telegram_user_id) DO NOTHING;
        """
        cur.execute(sql, (telegram_user_id, web_user_id))

        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Database Error on migrate_telegram_user_data: {e}")
        if conn:
            conn.rollback()
        return False


def check_telegram_migration(telegram_user_id: str) -> Optional[int]:
    """
    Checks if a Telegram user has been migrated to a web account.

    Args:
        telegram_user_id: The Telegram chat_id

    Returns:
        web_user_id if migrated, None otherwise
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = "SELECT web_user_id FROM telegram_migrations WHERE telegram_user_id = %s;"
        cur.execute(sql, (telegram_user_id,))
        result = cur.fetchone()

        cur.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Database Error on check_telegram_migration: {e}")
        return None