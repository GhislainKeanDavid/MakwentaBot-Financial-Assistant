# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangGraph-based Financial Assistant bot that helps users track expenses, manage budgets, and set financial goals through Telegram. The bot uses OpenAI's GPT-4o-mini as the LLM backend and PostgreSQL (via Supabase) for persistent storage.

## Environment Setup

```bash
# Activate virtual environment
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

```bash
# Local development
python main.py

# The server runs on port 8080 by default (configurable via PORT env var)
# Access the API at http://localhost:8080
```

## Testing Endpoints

```bash
# Test the chat endpoint directly
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_input": "I spent 50 pesos on groceries", "thread_id": "test_user"}'

# Webhook endpoint (receives Telegram updates)
# POST /webhook
```

## Deployment

The application is deployed to Google Cloud Run using Docker. Deploy using:

```powershell
.\deploy.ps1
```

This script:
1. Builds a Docker image
2. Pushes to Google Container Registry
3. Deploys to Cloud Run in asia-southeast1 region
4. Injects secrets from Google Secret Manager (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, DATABASE_URL)

## Architecture

### Core Components

**LangGraph Agent Flow** (agent_graph.py):
- Uses a ReAct-style agent loop with two nodes: `planner` and `tool_executor`
- `planner` node: Calls the LLM with available tools to decide the next action
- `tool_executor` node: Executes requested tools and returns observations as ToolMessages
- Conditional routing via `should_continue()` determines whether to loop back or end

**State Management** (models/state.py):
- `GraphState`: TypedDict containing thread_id, messages (with add_messages reducer), tool_calls, tool_observation, intent, and budget
- `Transaction`: Pydantic model for financial transactions
- State persists per user in memory via `USER_AGENTS` dictionary in main.py

**Tools** (database_tools.py):
- `record_transaction`: Logs expense/income to database
- `check_budget`: Compares current spending against user's daily/weekly limits
- `get_expenses_by_date`: Retrieves transactions for a specific date (YYYY-MM-DD format)
- `set_my_budget`: Sets or updates budget limits (auto-calculates daily/weekly/monthly)
- `set_financial_goal`: Creates a savings goal with target amount and deadline
- `check_goals`: Retrieves all active savings goals
- `get_daily_summary`: Generates proactive budget notifications

**Database Layer** (db_manager.py):
- Uses `psycopg2` for PostgreSQL connections
- Database schema has three tables: `transactions`, `budgets`, `goals`
- All functions follow pattern: get connection → execute query → commit → close
- Connection string from `DATABASE_URL` environment variable

**API Server** (main.py):
- FastAPI app with two main routes: `/api/chat` (internal agent endpoint) and `/webhook` (Telegram updates)
- Telegram handler calls `/api/chat` internally via httpx, then sends response back to user
- State initialization: New users get `GraphState` with default budget configuration
- Application startup event initializes Telegram bot asynchronously

### Request Flow

1. User sends message to Telegram bot
2. Telegram servers POST to `/webhook` endpoint
3. `handle_message()` calls internal `/api/chat` via HTTP
4. `/api/chat` retrieves or initializes user state from `USER_AGENTS`
5. LangGraph agent processes message through planner → tool_executor loop
6. Final state saved back to `USER_AGENTS`, response extracted
7. Response sent back to user via Telegram

### Key Design Patterns

**Tool Injection Pattern**: The `call_tool_executor` node injects runtime state (user_id, current_budget) into tool arguments before execution. This allows tools to access user context without it being in the LLM's tool schema.

**Manual Tool Execution**: Rather than using ToolExecutor from LangGraph, tools are executed manually by looking up the function from `FINANCIAL_TOOLS` list and calling `tool.func(**args)`. This provides more control over argument injection.

**Date Handling**: The system prompt includes today's date. Tools expect dates in YYYY-MM-DD format. The LLM is instructed to convert relative dates ("yesterday", "last Friday") to absolute dates before calling tools.

## Database Schema

**transactions** table:
- user_id (TEXT): Telegram chat_id
- amount (NUMERIC): Transaction amount
- category (TEXT): Expense category
- description (TEXT): Optional details
- expense_date (DATE): The actual date of the expense (distinct from record_date)
- transaction_date/record_date (TIMESTAMP): When recorded

**budgets** table:
- user_id (TEXT, PRIMARY KEY): Telegram chat_id
- daily_limit (NUMERIC)
- weekly_limit (NUMERIC)
- monthly_limit (NUMERIC)
- updated_at (TIMESTAMP)

**goals** table:
- user_id (TEXT): Telegram chat_id
- goal_name (TEXT): Name of the goal
- target_amount (NUMERIC): Target savings amount
- current_amount (NUMERIC): Amount saved so far
- deadline (DATE): Target completion date

## Environment Variables

Required in `.env` file:
- `OPENAI_API_KEY`: OpenAI API key for GPT-4o-mini
- `TELEGRAM_BOT_TOKEN`: Bot token from @BotFather
- `DATABASE_URL`: PostgreSQL connection string (format: postgresql://user:password@host:port/database)
- `PORT`: Server port (default: 8080)

## Important Implementation Notes

- User state is stored in-memory (`USER_AGENTS` dict). State will be lost on server restart. Consider adding Redis or database persistence for production.
- The expense_date field allows backdating transactions - crucial for "I spent X yesterday" scenarios
- Budget checking uses PostgreSQL date functions: `CURRENT_DATE` for daily, `date_trunc('week', NOW())` for weekly
- Tool calls must return specific instructions to the LLM (e.g., "You MUST now use the check_budget tool") to ensure proper follow-up actions
- Telegram bot uses webhooks (not polling) for scalability on Cloud Run
- The startup event handler (`@app_fastapi.on_event("startup")`) must call `await application.initialize()` for Telegram bot to work properly

## QA and Testing

### QA Validation Skill

A specialized QA Agent skill is available at `.claude/skills/QA_GUIDE.md` to validate features and identify bugs.

**Invoke the QA skill when:**
- Testing new features before deployment
- Investigating user-reported bugs
- Validating data consistency across tools
- Testing edge cases (date boundaries, empty states, etc.)
- After making database schema changes

**Triggers**: Use keywords like "test", "qa", "validate", "bug check", "edge cases", or "acceptance criteria"

**What the QA Agent checks:**
1. **Data Consistency**: All tools querying the same data return identical values
2. **Date Handling**: Correct use of `expense_date` vs `transaction_date`, proper week boundaries
3. **Financial Accuracy**: Budget calculations, spending sums, and breakdowns are mathematically correct
4. **Tool Parameter Matching**: Tools receive only parameters they actually accept
5. **LLM Response Accuracy**: Bot responses match actual database state

**Critical Validation Rules:**
- All weekly queries MUST use `expense_date` column (not `transaction_date`)
- All weekly queries MUST calculate Monday start using Python's `weekday()` (not PostgreSQL `date_trunc`)
- Tools reporting the same metric (e.g., weekly spending) MUST return identical values
- Always test on day/week/month boundaries (midnight transitions)

**Example Usage:**
```
"Run QA validation on the weekly breakdown feature"
"Test edge cases for recurring expense processing"
"Validate that check_budget and get_weekly_breakdown return consistent totals"
```
