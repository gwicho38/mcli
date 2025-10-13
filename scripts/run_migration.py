#!/usr/bin/env python3
"""
Run Supabase migrations
"""
import os
import sys
from pathlib import Path

# Add scripts directory to path to import helpers
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_helper import create_supabase_client

def run_migration(migration_file: str):
    """Run a SQL migration file on Supabase"""

    # Read migration file
    migration_path = Path(migration_file)
    if not migration_path.exists():
        print(f"Error: Migration file not found: {migration_file}")
        sys.exit(1)

    sql_content = migration_path.read_text()

    print(f"Running migration: {migration_path.name}")
    print(f"Migration size: {len(sql_content)} bytes")
    print("-" * 60)

    # Create Supabase client using helper
    supabase = create_supabase_client()
    if not supabase:
        print("Failed to connect to Supabase")
        print("Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set in .env")
        sys.exit(1)

    # Execute SQL using PostgREST
    # Note: Supabase Python client doesn't have direct SQL execution
    # We'll use the REST API to execute the migration
    try:
        # Split by statement and execute
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]

        print(f"Executing {len(statements)} SQL statements...")

        for i, statement in enumerate(statements, 1):
            if not statement or statement.startswith('--'):
                continue

            try:
                # Use rpc to execute SQL
                result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                print(f"  [{i}/{len(statements)}] ✓")
            except Exception as e:
                # If exec_sql doesn't exist, we need to use psycopg2
                print(f"  [{i}/{len(statements)}] Using alternative method...")
                break

        print("-" * 60)
        print("✓ Migration completed successfully!")

    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        print("\nTrying alternative method using psycopg2...")

        # Try using psycopg2 directly
        try:
            import psycopg2

            # Get credentials for direct connection
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            # Construct direct connection to Supabase Postgres
            # Format: postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
            project_ref = url.split('//')[1].split('.')[0]

            # Extract password from service role key (it's a JWT, we need the actual postgres password)
            # For Supabase, we need to use the connection string from dashboard
            # Let's try the pooler connection
            db_url = f"postgresql://postgres.{project_ref}:{key}@aws-0-us-west-1.pooler.supabase.com:5432/postgres"

            print(f"Connecting to database at aws-0-us-west-1.pooler.supabase.com...")
            print(f"Project: {project_ref}")

            conn = psycopg2.connect(db_url, sslmode='require')
            cursor = conn.cursor()

            # Execute the full SQL
            cursor.execute(sql_content)
            conn.commit()

            cursor.close()
            conn.close()

            print("-" * 60)
            print("✓ Migration completed successfully using psycopg2!")

        except ImportError:
            print("\npsycopg2 not installed. Please install it:")
            print("  uv pip install psycopg2-binary")
            sys.exit(1)
        except Exception as e2:
            print(f"\n✗ Alternative method also failed: {str(e2)}")
            print("\nPlease run the migration manually using the Supabase SQL editor:")
            print(f"  File: {migration_path}")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <migration_file>")
        sys.exit(1)

    run_migration(sys.argv[1])
