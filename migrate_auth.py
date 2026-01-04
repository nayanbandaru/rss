"""
Database migration script to add authentication fields.
Run this ONCE to update existing database schema.

Supports both SQLite and PostgreSQL.

Usage:
    python migrate_auth.py
"""
import os
from datetime import datetime
from sqlalchemy import text, inspect
from db import engine


def is_postgresql():
    """Check if using PostgreSQL"""
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./watch.db")
    return "postgresql" in db_url.lower()


def get_existing_columns(conn, table_name):
    """Get list of existing columns in a table (works with both SQLite and PostgreSQL)"""
    inspector = inspect(conn)
    columns = inspector.get_columns(table_name)
    return [col['name'] for col in columns]


def table_exists(conn, table_name):
    """Check if table exists (works with both SQLite and PostgreSQL)"""
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def migrate():
    """Add authentication columns to existing database"""

    is_pg = is_postgresql()
    db_type = "PostgreSQL" if is_pg else "SQLite"

    with engine.begin() as conn:
        print(f"Starting database migration for authentication ({db_type})...")
        print()

        # Check if users table exists
        if not table_exists(conn, 'users'):
            print("ERROR: 'users' table does not exist.")
            print("Please run the application first to create the base schema.")
            return

        # Check if columns already exist
        columns = get_existing_columns(conn, 'users')

        if 'password_hash' in columns:
            print("Migration already completed. Columns already exist.")
            return

        # Boolean syntax differs between databases
        bool_false = "FALSE" if is_pg else "0"

        # Date/time handling
        now = datetime.utcnow()
        if is_pg:
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        else:
            now_str = now.isoformat()

        try:
            # Add new columns to users table
            print("Adding password_hash column...")
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN password_hash VARCHAR NULL
            """))

            print("Adding is_verified column...")
            if is_pg:
                conn.execute(text(f"""
                    ALTER TABLE users
                    ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT {bool_false}
                """))
            else:
                conn.execute(text(f"""
                    ALTER TABLE users
                    ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT {bool_false}
                """))

            print("Adding created_at column...")
            if is_pg:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                """))
            else:
                conn.execute(text(f"""
                    ALTER TABLE users
                    ADD COLUMN created_at DATETIME NOT NULL DEFAULT '{now_str}'
                """))

            print("Adding updated_at column...")
            if is_pg:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                """))
            else:
                conn.execute(text(f"""
                    ALTER TABLE users
                    ADD COLUMN updated_at DATETIME NOT NULL DEFAULT '{now_str}'
                """))

            # Create password_reset_tokens table
            print("Creating password_reset_tokens table...")
            if is_pg:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        token VARCHAR UNIQUE NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        used BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMP NOT NULL
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        token VARCHAR UNIQUE NOT NULL,
                        expires_at DATETIME NOT NULL,
                        used BOOLEAN NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))

            # Create index on token for faster lookups
            print("Creating index on password_reset_tokens...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_password_reset_token
                ON password_reset_tokens(token)
            """))

            print()
            print("=" * 50)
            print("Migration completed successfully!")
            print("=" * 50)
            print()
            print("NOTE: Existing users will need to set up passwords using:")
            print("  POST /api/v1/auth/setup-password")
            print()

        except Exception as e:
            print(f"ERROR: Migration failed: {e}")
            print("Please check your database and try again.")
            raise


if __name__ == "__main__":
    migrate()
