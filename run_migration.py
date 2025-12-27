"""
Database migration runner script.
Executes SQL migration files against the configured database.
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration(migration_file: str):
    """Execute a migration SQL file."""
    print(f"\n{'='*60}")
    print(f"Running migration: {migration_file}")
    print(f"{'='*60}\n")

    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL not found in environment variables")
        return False

    conn = None
    try:
        # Read migration file
        with open(migration_file, 'r') as f:
            sql = f.read()

        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Execute migration
        print("Executing SQL commands...")
        cur.execute(sql)

        # Commit changes
        conn.commit()
        print("[SUCCESS] Migration completed successfully!")

        # Close connection
        cur.close()
        conn.close()

        return True

    except psycopg2.errors.DuplicateTable as e:
        print(f"[WARNING] Tables already exist (skipping): {e}")
        if conn:
            conn.rollback()
        return True

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        if conn:
            conn.rollback()
        return False


if __name__ == "__main__":
    # Run the auth migration
    migration_path = "migrations/002_create_users_auth.sql"

    if not os.path.exists(migration_path):
        print(f"[ERROR] Migration file not found: {migration_path}")
        exit(1)

    success = run_migration(migration_path)

    if success:
        print("\n" + "="*60)
        print("[SUCCESS] All migrations completed successfully!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("[ERROR] Migration failed. Check the errors above.")
        print("="*60)
        exit(1)
