#!/usr/bin/env python3
"""Test script for the migration framework."""

import sys

from k3l.fcgraph.embeds import get_migration_status, migrate_down, migrate_up


def main():
    connection_string = "postgresql:///"

    print("Testing migration framework...")

    # Test migration status
    print("\n1. Getting migration status before any migrations:")
    try:
        status = get_migration_status(connection_string)
        print(f"Current revision: {status['current_revision']}")
        print(f"Pending migrations: {status['pending_migrations']}")
        print(
            f"Migration history: {len(status['migration_history'])} migrations available"
        )
    except Exception as e:
        print(f"Error getting status: {e}")
        return 1

    # Test migration up
    print("\n2. Running migration up:")
    try:
        migrate_up(connection_string)
        print("Migration up completed successfully!")
    except Exception as e:
        print(f"Error during migration up: {e}")
        return 1

    # Test migration status after up
    print("\n3. Getting migration status after migration:")
    try:
        status = get_migration_status(connection_string)
        print(f"Current revision: {status['current_revision']}")
        print(f"Pending migrations: {status['pending_migrations']}")
    except Exception as e:
        print(f"Error getting status: {e}")
        return 1

    # Test table existence
    print("\n4. Checking if k3l_cast_embeds table was created:")
    try:
        import psycopg2

        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = 'k3l_cast_embeds'"
        )
        table_count = cur.fetchone()[0]
        cur.close()
        conn.close()

        if table_count == 1:
            print("✓ k3l_cast_embeds table exists!")
        else:
            print("✗ k3l_cast_embeds table not found")
            return 1
    except Exception as e:
        print(f"Error checking table: {e}")
        return 1

    print("\n✓ All migration tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
