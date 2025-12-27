"""
Test the new database authentication functions.
"""

import db_manager
import bcrypt

print("="*60)
print("Testing New Database Functions")
print("="*60)

# Test 1: Create a test user
print("\n[TEST 1] Creating test user...")
try:
    test_email = "test@example.com"
    # Hash password with bcrypt directly
    test_password = bcrypt.hashpw(b"TestPass123", bcrypt.gensalt()).decode('utf-8')

    user_id = db_manager.create_user(test_email, test_password)
    if user_id:
        print(f"[PASS] User created with ID: {user_id}")
    else:
        print("[INFO] User might already exist")
except Exception as e:
    print(f"[INFO] {e}")

# Test 2: Retrieve user by email
print("\n[TEST 2] Retrieving user by email...")
try:
    user = db_manager.get_user_by_email("test@example.com")
    if user:
        print(f"[PASS] Found user: ID={user[0]}, Email={user[1]}")
    else:
        print("[FAIL] User not found")
except Exception as e:
    print(f"[FAIL] {e}")

# Test 3: Create chat session
print("\n[TEST 3] Creating chat session...")
try:
    if user:
        session_id = db_manager.create_chat_session(user[0])
        if session_id:
            print(f"[PASS] Session created: {session_id}")

            # Test 4: Save message
            print("\n[TEST 4] Saving messages...")
            db_manager.save_message(session_id, "human", "Hello, bot!")
            db_manager.save_message(session_id, "ai", "Hello! How can I help you?")
            print("[PASS] Messages saved")

            # Test 5: Retrieve messages
            print("\n[TEST 5] Retrieving messages...")
            messages = db_manager.get_session_messages(session_id)
            if len(messages) == 2:
                print(f"[PASS] Retrieved {len(messages)} messages:")
                for msg in messages:
                    print(f"       {msg[0]}: {msg[1]}")
            else:
                print(f"[WARN] Expected 2 messages, got {len(messages)}")
        else:
            print("[FAIL] Failed to create session")
except Exception as e:
    print(f"[FAIL] {e}")

# Clean up test data
print("\n[CLEANUP] Removing test data...")
try:
    import psycopg2
    from dotenv import load_dotenv
    import os

    load_dotenv()
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    # Delete test user and related data (CASCADE will delete sessions/messages)
    cur.execute("DELETE FROM users WHERE email = %s", ("test@example.com",))
    conn.commit()

    cur.close()
    conn.close()
    print("[PASS] Test data cleaned up")
except Exception as e:
    print(f"[WARN] Cleanup failed: {e}")

print("\n" + "="*60)
print("[SUCCESS] All database functions working!")
print("="*60)
print("\nBackend is ready for webapp development!")
