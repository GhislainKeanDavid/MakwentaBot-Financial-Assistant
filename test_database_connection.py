"""
Quick test script to verify database connection.
Run this after updating your DATABASE_URL in .env
"""

import os
import psycopg2
from dotenv import load_dotenv

print("="*60)
print("Database Connection Test")
print("="*60)

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Test 1: Check if DATABASE_URL exists
print("\n[TEST 1] Checking .env configuration...")
if not DATABASE_URL:
    print("[FAIL] DATABASE_URL not found in .env file")
    print("\nPlease add DATABASE_URL to your .env file:")
    print("DATABASE_URL=postgresql://postgres:password@host:5432/database")
    exit(1)
else:
    print("[PASS] DATABASE_URL found in .env")
    # Show partial URL for verification (hide password)
    if "@" in DATABASE_URL:
        parts = DATABASE_URL.split("@")
        user_part = parts[0].split(":")
        if len(user_part) >= 2:
            masked = f"{user_part[0]}:****@{parts[1]}"
        else:
            masked = f"****@{parts[1]}"
        print(f"       URL: {masked}")

# Test 2: Try to connect
print("\n[TEST 2] Testing database connection...")
try:
    conn = psycopg2.connect(DATABASE_URL)
    print("[PASS] Successfully connected to database!")

    # Test 3: Check database info
    print("\n[TEST 3] Checking database info...")
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"[PASS] PostgreSQL Version: {version.split(',')[0]}")

    cur.execute("SELECT current_database();")
    db_name = cur.fetchone()[0]
    print(f"[PASS] Database Name: {db_name}")

    # Test 4: Check if auth tables exist
    print("\n[TEST 4] Checking for existing tables...")
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()

    if tables:
        print(f"[INFO] Found {len(tables)} existing tables:")
        for table in tables:
            print(f"       - {table[0]}")

        # Check if auth tables exist
        table_names = [t[0] for t in tables]
        auth_tables = ['users', 'chat_sessions', 'chat_messages']
        missing_auth_tables = [t for t in auth_tables if t not in table_names]

        if missing_auth_tables:
            print(f"\n[INFO] Auth tables need to be created: {', '.join(missing_auth_tables)}")
            print("       Run: python run_migration.py")
        else:
            print("\n[PASS] All auth tables already exist!")
    else:
        print("[INFO] No tables found - database is empty")
        print("       Run: python run_migration.py")

    cur.close()
    conn.close()

    print("\n" + "="*60)
    print("[SUCCESS] Database connection is working!")
    print("="*60)
    print("\nNext steps:")
    if not tables or 'users' not in [t[0] for t in tables]:
        print("1. Run database migration: python run_migration.py")
    print("2. Continue with webapp development")

except psycopg2.OperationalError as e:
    error_msg = str(e)
    print(f"[FAIL] Connection failed: {error_msg}")
    print("\n" + "="*60)
    print("Troubleshooting Steps:")
    print("="*60)

    if "could not translate host name" in error_msg:
        print("\n❌ Host not found - Your Supabase project may not exist")
        print("\nSolutions:")
        print("1. Check if your Supabase project is active:")
        print("   https://supabase.com/dashboard")
        print("2. If project is paused, click 'Resume Project'")
        print("3. If project doesn't exist, create a new one")
        print("4. Get fresh connection string from Settings → Database")

    elif "password authentication failed" in error_msg:
        print("\n❌ Wrong password")
        print("\nSolutions:")
        print("1. Reset password in Supabase: Settings → Database → Reset Password")
        print("2. Update DATABASE_URL in .env with new password")

    elif "SSL" in error_msg or "ssl" in error_msg:
        print("\n❌ SSL connection issue")
        print("\nSolution:")
        print("Add ?sslmode=require to your DATABASE_URL:")
        print("DATABASE_URL=postgresql://...?sslmode=require")

    else:
        print(f"\n❌ Unknown error")
        print("Check the error message above for details")

    print("\n📖 See fix_database_connection.md for detailed guide")
    exit(1)

except Exception as e:
    print(f"[FAIL] Unexpected error: {e}")
    exit(1)
