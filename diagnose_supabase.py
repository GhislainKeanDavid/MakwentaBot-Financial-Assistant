"""
Deep diagnostic script for Supabase connection issues.
This will test multiple aspects of the connection.
"""

import os
import socket
import psycopg2
from dotenv import load_dotenv

print("="*70)
print("SUPABASE CONNECTION DIAGNOSTIC")
print("="*70)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("[ERROR] No DATABASE_URL in .env file")
    exit(1)

# Parse the connection string
print("\n[STEP 1] Parsing connection string...")
try:
    # Format: postgresql://user:password@host:port/database
    parts = DATABASE_URL.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")

    username = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else None
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 5432
    database = host_db[1].split("?")[0] if len(host_db) > 1 else "postgres"

    print(f"[OK] Username: {username}")
    print(f"[OK] Host: {host}")
    print(f"[OK] Port: {port}")
    print(f"[OK] Database: {database}")
    print(f"[OK] Password: {'*' * len(password) if password else 'NOT SET'}")

except Exception as e:
    print(f"[ERROR] Failed to parse DATABASE_URL: {e}")
    print("\nExpected format:")
    print("postgresql://user:password@host:port/database")
    exit(1)

# Test 1: DNS Resolution
print("\n[STEP 2] Testing DNS resolution...")
try:
    ip_address = socket.gethostbyname(host)
    print(f"[OK] Host resolved to IP: {ip_address}")
except socket.gaierror as e:
    print(f"[FAIL] Cannot resolve hostname: {host}")
    print(f"       Error: {e}")
    print("\n⚠️  DIAGNOSIS: Your Supabase project host doesn't exist!")
    print("\nThis means one of:")
    print("1. Your Supabase project was DELETED (most likely)")
    print("2. Your Supabase project was PAUSED and hostname changed")
    print("3. You're using an OLD connection string from a deleted project")
    print("\n✅ SOLUTION:")
    print("1. Go to https://supabase.com/dashboard")
    print("2. Check if your project exists")
    print("3. If it exists, get a fresh connection string")
    print("4. If it doesn't exist, create a NEW project")
    print("5. Update DATABASE_URL in .env with the new connection string")
    exit(1)

# Test 2: Port connectivity
print("\n[STEP 3] Testing port connectivity...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((host, port))
    sock.close()

    if result == 0:
        print(f"[OK] Port {port} is open and accepting connections")
    else:
        print(f"[FAIL] Port {port} is not reachable")
        print("\n⚠️  DIAGNOSIS: Database server is not responding")
        print("\nPossible causes:")
        print("1. Supabase project is PAUSED")
        print("2. Firewall blocking port 5432")
        print("3. Network connectivity issue")
        print("\n✅ SOLUTION:")
        print("1. Check Supabase dashboard - look for 'Paused' status")
        print("2. Click 'Resume Project' if paused")
        print("3. Try disabling antivirus/firewall temporarily")
        exit(1)

except Exception as e:
    print(f"[FAIL] Socket error: {e}")
    exit(1)

# Test 3: PostgreSQL Connection
print("\n[STEP 4] Testing PostgreSQL connection...")
try:
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    print("[OK] Successfully connected to PostgreSQL!")

    # Test 4: Database query
    print("\n[STEP 5] Testing database query...")
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    result = cur.fetchone()
    print(f"[OK] Query successful: {result}")

    # Test 5: Check tables
    print("\n[STEP 6] Checking existing tables...")
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()

    if tables:
        print(f"[OK] Found {len(tables)} tables:")
        for table in tables:
            print(f"     - {table[0]}")
    else:
        print("[INFO] No tables found - database is empty")

    cur.close()
    conn.close()

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED - DATABASE IS WORKING!")
    print("="*70)
    print("\nYour database connection is fine. The error might be:")
    print("1. Temporary network glitch (try running your Telegram bot again)")
    print("2. Missing tables (run: python run_migration.py)")
    print("3. Application-level error (check your bot logs)")

except psycopg2.OperationalError as e:
    error_str = str(e).lower()
    print(f"[FAIL] PostgreSQL connection failed")
    print(f"       Error: {e}")

    print("\n⚠️  DIAGNOSIS:")

    if "password authentication failed" in error_str:
        print("WRONG PASSWORD!")
        print("\n✅ SOLUTION:")
        print("1. Go to Supabase Dashboard → Settings → Database")
        print("2. Click 'Reset Database Password'")
        print("3. Copy the NEW password")
        print("4. Update DATABASE_URL in .env with new password")
        print("   Format: postgresql://postgres:NEW_PASSWORD@host:5432/postgres")

    elif "timeout" in error_str or "timed out" in error_str:
        print("CONNECTION TIMEOUT - Server not responding")
        print("\n✅ SOLUTION:")
        print("1. Your Supabase project is likely PAUSED")
        print("2. Go to https://supabase.com/dashboard")
        print("3. Look for your project - it may say 'Paused'")
        print("4. Click 'Resume Project' or 'Restore Project'")
        print("5. Wait 2-3 minutes for it to wake up")

    elif "ssl" in error_str:
        print("SSL CONNECTION REQUIRED")
        print("\n✅ SOLUTION:")
        print("Add ?sslmode=require to your DATABASE_URL:")
        if "?" in DATABASE_URL:
            print(f"   {DATABASE_URL}&sslmode=require")
        else:
            print(f"   {DATABASE_URL}?sslmode=require")

    else:
        print("UNKNOWN CONNECTION ERROR")
        print("\n✅ SOLUTION:")
        print("1. Verify connection string in Supabase Dashboard")
        print("2. Make sure project is not paused")
        print("3. Try creating a NEW Supabase project")

    exit(1)

except Exception as e:
    print(f"[FAIL] Unexpected error: {e}")
    exit(1)
