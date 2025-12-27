# Fix Database Connection - Step by Step Guide

## Current Issue
Your database host `db.bggywlojaocixdpelyts.supabase.co` cannot be reached.

## Solution Steps

### Step 1: Access Supabase Dashboard
1. Go to: https://supabase.com/dashboard
2. Sign in with your account

### Step 2: Check Your Project Status

**If you see your project in the dashboard:**
- ✅ Click on your project name
- Look for any warnings about "paused" or "inactive" status
- If paused, click "Resume Project" or "Restore Project"

**If you DON'T see your project:**
- ❌ The project may have been deleted (free tier auto-deletes after extended inactivity)
- You'll need to create a new project (see Step 5 below)

### Step 3: Get the Correct Connection String

**For EXISTING project:**
1. In your Supabase project dashboard, click ⚙️ **Settings** (bottom left)
2. Click **Database** in the left sidebar
3. Scroll to **Connection String** section
4. Select **URI** tab (NOT Session mode)
5. Copy the connection string that looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxx.supabase.co:5432/postgres
   ```
6. **IMPORTANT:** Replace `[YOUR-PASSWORD]` with your actual database password

**To find/reset your database password:**
- Settings → Database → Database Password
- Click "Reset Database Password" if you forgot it
- **Save the password securely!**

### Step 4: Update Your .env File

1. Open `C:\Users\keang\Financial-Assistant\.env` in a text editor
2. Find the line starting with `DATABASE_URL=`
3. Replace it with your new connection string:
   ```
   DATABASE_URL=postgresql://postgres:YOUR_ACTUAL_PASSWORD@db.xxxxxx.supabase.co:5432/postgres
   ```
4. Save the file

### Step 5: If You Need a NEW Supabase Project

**If your project was deleted:**

1. Go to https://supabase.com/dashboard
2. Click **"New Project"**
3. Fill in:
   - **Name:** Financial-Assistant (or any name)
   - **Database Password:** Create a STRONG password and SAVE IT
   - **Region:** Choose closest to you (asia-southeast1 for Philippines)
4. Click **"Create new project"** (wait 2-3 minutes for setup)

5. Once created, get the connection string (Step 3 above)

6. **IMPORTANT:** You'll need to run ALL migrations:
   ```bash
   # In your project directory
   python run_migration.py  # This will fail first, then...
   ```

7. **Manually run the first migration** (since run_migration.py only runs 002):
   - Go to Supabase Dashboard → SQL Editor
   - Open `migrations/001_create_recurring_expenses.sql` from your project
   - Copy and paste the SQL into the SQL Editor
   - Click "Run"
   - Then do the same for `migrations/002_create_users_auth.sql`

### Step 6: Test the Connection

Run this test command:
```bash
python -c "import psycopg2; from dotenv import load_dotenv; import os; load_dotenv(); conn = psycopg2.connect(os.getenv('DATABASE_URL')); print('✓ Database connection successful!'); conn.close()"
```

**If you see:** `✓ Database connection successful!`
- ✅ You're good to go! Run `python run_migration.py`

**If you see an error:**
- Check the password in your .env file
- Make sure you replaced `[YOUR-PASSWORD]` with actual password
- Verify the connection string format is correct

## Quick Test Commands

### Test 1: Check .env file has DATABASE_URL
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DATABASE_URL exists:', bool(os.getenv('DATABASE_URL')))"
```

### Test 2: Try to connect
```bash
python -c "import psycopg2; from dotenv import load_dotenv; import os; load_dotenv(); psycopg2.connect(os.getenv('DATABASE_URL'))"
```

### Test 3: Run migration
```bash
python run_migration.py
```

## Common Issues

### Issue: "password authentication failed"
**Fix:** Reset your database password in Supabase dashboard, update .env

### Issue: "SSL connection required"
**Fix:** Add `?sslmode=require` to end of DATABASE_URL:
```
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres?sslmode=require
```

### Issue: "database does not exist"
**Fix:** Make sure the database name is `postgres` (default Supabase database)

### Issue: "could not translate host name"
**Fix:** The project doesn't exist - create a new one (Step 5)

## Need Help?

If you're still stuck:
1. Check Supabase status: https://status.supabase.com
2. Verify your account: https://supabase.com/dashboard
3. Check Supabase Discord for known issues
4. Share the error message (without password) for specific help

## Alternative: Use Local PostgreSQL

If Supabase is giving you trouble, you can temporarily use local PostgreSQL:

1. Install PostgreSQL: https://www.postgresql.org/download/windows/
2. During install, set a password for the `postgres` user
3. Create a database named `financial_assistant`
4. Update .env:
   ```
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/financial_assistant
   ```
5. Run migrations: `python run_migration.py`

---

**After fixing the connection, run:**
```bash
python run_migration.py
```

This will create all the authentication tables needed for the webapp!
